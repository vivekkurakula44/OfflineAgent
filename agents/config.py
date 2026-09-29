"""Central configuration, driven entirely by environment variables.

Keeping every model ID and limit in one place means you can change a model
from the Render dashboard (Environment tab) and redeploy, without ever
touching the source code.
"""

from __future__ import annotations

import os


def _split_env(name: str, default: str) -> list[str]:
    """Read a comma-separated env var into a clean list of strings."""
    raw = os.environ.get(name, default) or ""
    return [item.strip() for item in raw.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()

MISSING_KEY_MESSAGE = (
    "GROQ_API_KEY is not set.\n\n"
    "On Render: open your service -> Environment tab -> add\n"
    "  Key:   GROQ_API_KEY\n"
    "  Value: gsk_...  (your key from https://console.groq.com/keys)\n"
    "Then click Save Deploy and the app will restart automatically."
)

# ---------------------------------------------------------------------------
# Chat / text models
#
# NOTE: llama3-8b-8192 and llama3-70b-8192 were shut down on 2025-08-30.
#       llama-3.1-8b-instant and llama-3.3-70b-versatile were shut down on
#       2026-08-16. The defaults below are the current replacements.
#       If a model is ever retired again, the client automatically falls
#       through to the next entry in this list.
# ---------------------------------------------------------------------------

CHAT_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b").strip()
CHAT_MODEL_FALLBACKS = _split_env(
    "GROQ_MODEL_FALLBACKS",
    "openai/gpt-oss-20b,qwen/qwen3.6-27b",
)

# ---------------------------------------------------------------------------
# Speech-to-text model
#
# We call Groq's hosted Whisper instead of installing openai-whisper locally.
# Reason: PyTorch needs ~800MB RAM, but a Render Free instance only has
# 512MB, so a local Whisper would be OOM-killed on every request.
# ---------------------------------------------------------------------------

STT_MODEL = os.environ.get("GROQ_STT_MODEL", "whisper-large-v3-turbo").strip()
STT_MODEL_FALLBACKS = _split_env(
    "GROQ_STT_MODEL_FALLBACKS",
    "whisper-large-v3,distil-whisper-large-v3-en",
)

# ---------------------------------------------------------------------------
# Request limits
# ---------------------------------------------------------------------------

# Groq's audio endpoint accepts files up to ~25MB on the free tier.
MAX_AUDIO_BYTES = int(os.environ.get("MAX_AUDIO_BYTES", 25 * 1024 * 1024))

# Cap how much video audio we transcribe. At 16kHz mono s16le that is
# roughly 32KB/s, so 15 minutes lands well under the 25MB ceiling.
MAX_VIDEO_AUDIO_SECONDS = int(os.environ.get("MAX_VIDEO_AUDIO_SECONDS", 900))

# Gradio's own upload guard. Also mirrored in render.yaml / the dashboard.
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", 40))

# Characters of document text sent to the model per request.
MAX_INPUT_CHARS = int(os.environ.get("MAX_INPUT_CHARS", 12000))

# Per-request HTTP timeout, in seconds. Long documents can be slow.
REQUEST_TIMEOUT_SECONDS = int(os.environ.get("REQUEST_TIMEOUT_SECONDS", 120))

# How many times to retry a transient failure (429 / 5xx / network) before
# giving up on the current model and trying the next one.
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", 3))

# Audio/video longer than this makes Whisper exceed the timeout on a
# 0.1-CPU free instance, so we truncate rather than fail the whole request.
FFMPEG_TIMEOUT_SECONDS = int(os.environ.get("FFMPEG_TIMEOUT_SECONDS", 300))


# ---------------------------------------------------------------------------
# Derived helpers
# ---------------------------------------------------------------------------

def chat_models() -> list[str]:
    """Every chat model to try, in order, de-duplicated."""
    seen: list[str] = []
    for model in [CHAT_MODEL, *CHAT_MODEL_FALLBACKS]:
        if model and model not in seen:
            seen.append(model)
    return seen


def stt_models() -> list[str]:
    """Every speech-to-text model to try, in order, de-duplicated."""
    seen: list[str] = []
    for model in [STT_MODEL, *STT_MODEL_FALLBACKS]:
        if model and model not in seen:
            seen.append(model)
    return seen


def is_configured() -> bool:
    """True when a Groq key is present, i.e. the app is usable."""
    return bool(GROQ_API_KEY)
