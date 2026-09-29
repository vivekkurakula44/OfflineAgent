"""Audio transcription via Groq's hosted Whisper models.

This replaces the local `openai-whisper` + `torch` stack. Those two together
need roughly 800MB of RAM, which does not fit on a Render Free instance
(512MB). Calling Groq's API keeps the container small and is also much
faster, since inference runs on Groq's GPUs rather than the web service.
"""

from __future__ import annotations

import os

from groq import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

from . import config
from .client import _describe, get_client

_DEAD_MODEL_MARKERS = (
    "model_decommissioned",
    "model_not_found",
    "not_found_error",
    "does not exist",
    "invalid model",
)

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


class TranscriptionError(RuntimeError):
    """Raised when audio could not be transcribed."""


def _is_transient(exc: Exception) -> bool:
    if isinstance(exc, (RateLimitError, APIConnectionError, APITimeoutError)):
        return True
    if isinstance(exc, APIStatusError):
        if exc.status_code in (408, 429) or exc.status_code >= 500:
            return True
    blob = _describe(exc).lower()
    return any(marker in blob for marker in _TRANSIENT_MARKERS)


def transcribe(file_path: str) -> str:
    """Transcribe an audio file to text.

    Args:
        file_path: Path to a local audio file (wav, mp3, m4a, ogg, flac, webm).

    Returns:
        The transcript, stripped.

    Raises:
        TranscriptionError: The file is too large, or every STT model failed.
    """
    size = os.path.getsize(file_path)

    if size == 0:
        raise TranscriptionError("The audio file is empty (0 bytes).")

    if size > config.MAX_AUDIO_BYTES:
        limit_mb = config.MAX_AUDIO_BYTES / (1024 * 1024)
        actual_mb = size / (1024 * 1024)
        raise TranscriptionError(
            f"Audio file is {actual_mb:.1f}MB, which exceeds the {limit_mb:.0f}MB "
            f"limit of Groq's transcription API.\n\n"
            f"Trim the recording, or raise MAX_AUDIO_BYTES if your Groq plan "
            f"allows larger uploads."
        )

    client = get_client()
    models = config.stt_models()
    problems: list[str] = []

    for model in models:
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                with open(file_path, "rb") as handle:
                    response = client.audio.transcriptions.create(
                        model=model,
                        file=handle,
                    )
                text = (getattr(response, "text", "") or "").strip()

                if not text:
                    raise TranscriptionError(
                        "No speech was detected in this recording."
                    )
                return text

            except TranscriptionError:
                raise
            except Exception as exc:  # noqa: BLE001
                if any(m in _describe(exc).lower() for m in _DEAD_MODEL_MARKERS):
                    problems.append(f"{model}: model unavailable")
                    break

                if _is_transient(exc) and attempt < config.MAX_RETRIES:
                    import time

                    time.sleep(min(2 ** (attempt - 1), 8))
                    continue

                problems.append(f"{model}: {_describe(exc)}")
                break

    details = "\n".join(f"  - {line}" for line in problems)
    raise TranscriptionError(
        f"Audio transcription failed.\n\n{details}\n\n"
        f"Supported formats: .wav, .mp3, .m4a, .ogg, .flac, .webm"
    )
