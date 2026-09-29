"""Shared Groq client with automatic model fallback and retry handling.

Two failure modes are handled separately, because they need different
responses:

  * "this model is gone"      -> stop retrying, move to the next model
  * "rate limited / 5xx / net" -> back off and retry the same model
"""

from __future__ import annotations

import time

from groq import Groq
from groq import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

from . import config

_client: Groq | None = None

# Substrings Groq uses when a model id is invalid or has been retired.
_DEAD_MODEL_MARKERS = (
    "model_decommissioned",
    "model_not_found",
    "not_found_error",
    "does not exist",
    "invalid model",
)

# Substrings that mean "this specific model is the problem", not a blip.
_TRANSIENT_MARKERS = (
    "rate_limit",
    "rate limit",
    "too many requests",
    "overloaded",
    "service unavailable",
    "internal server",
    "bad gateway",
    "gateway timeout",
)


class MissingAPIKeyError(RuntimeError):
    """Raised when GROQ_API_KEY is absent or blank."""


class AllModelsFailedError(RuntimeError):
    """Raised when every configured model failed, for any reason."""


def get_client() -> Groq:
    """Return a cached Groq client, or raise if no API key is configured."""
    global _client

    if not config.GROQ_API_KEY:
        raise MissingAPIKeyError(config.MISSING_KEY_MESSAGE)

    if _client is None:
        _client = Groq(
            api_key=config.GROQ_API_KEY,
            timeout=float(config.REQUEST_TIMEOUT_SECONDS),
            # We do our own retrying so we can also rotate models.
            max_retries=0,
        )
    return _client


def _describe(exc: Exception) -> str:
    body = getattr(exc, "body", None) or ""
    if body:
        return f"{type(exc).__name__}: {body}"
    return f"{type(exc).__name__}: {exc}"


def _is_dead_model(exc: Exception) -> bool:
    blob = _describe(exc).lower()
    return any(marker in blob for marker in _DEAD_MODEL_MARKERS)


def _is_transient(exc: Exception) -> bool:
    """True when the failure is worth retrying the same request for."""
    if isinstance(exc, (RateLimitError, APIConnectionError, APITimeoutError)):
        return True

    if isinstance(exc, APIStatusError):
        if exc.status_code in (408, 429):
            return True
        if exc.status_code >= 500:
            return True

    # Also inspect the payload for any exception type, so a rate-limit or
    # server error is retried even when it arrives as an unexpected class.
    blob = _describe(exc).lower()
    return any(marker in blob for marker in _TRANSIENT_MARKERS)


def chat(
    system_prompt: str,
    user_prompt: str,
    *,
    max_tokens: int = 1024,
    temperature: float = 0.2,
) -> str:
    """Send a chat completion, rotating models and retrying as needed.

    Args:
        system_prompt: Instructions that shape tone and strict formatting.
        user_prompt: The user-visible content to act on.
        max_tokens: Upper bound on the response length.
        temperature: 0.2 keeps output terse and deterministic, which is
            what this app wants. Raise it for more varied phrasing.

    Returns:
        The assistant's text, stripped of surrounding whitespace.

    Raises:
        MissingAPIKeyError: No API key configured.
        AllModelsFailedError: Every model in the fallback list failed.
    """
    client = get_client()
    models = config.chat_models()

    if not models:
        raise AllModelsFailedError("No chat models are configured.")

    problems: list[str] = []

    for model in models:
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                content = (response.choices[0].message.content or "").strip()
                if not content:
                    raise AllModelsFailedError(
                        f"Model '{model}' returned an empty response. Try again."
                    )
                return content

            except Exception as exc:  # noqa: BLE001 - deliberate catch-all
                if _is_dead_model(exc):
                    problems.append(f"{model}: model unavailable ({_describe(exc)})")
                    break  # move to the next model immediately

                if _is_transient(exc) and attempt < config.MAX_RETRIES:
                    # 1s, 2s, 4s, ... capped so a request never hangs.
                    backoff = min(2 ** (attempt - 1), 8)
                    time.sleep(backoff)
                    continue

                problems.append(f"{model}: {_describe(exc)}")
                break  # non-retryable, try the next model

    details = "\n".join(f"  - {line}" for line in problems)
    raise AllModelsFailedError(
        f"All configured models failed.\n\n{details}\n\n"
        f"Check that GROQ_API_KEY is valid and that your account has quota. "
        f"See https://console.groq.com/docs/models for the active model list."
    )
