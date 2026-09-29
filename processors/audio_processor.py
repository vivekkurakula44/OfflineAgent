"""Audio transcription, delegating the actual work to Groq's Whisper API.

This file intentionally does not import `whisper` or `torch`. Those pull in
roughly 800MB of dependencies, which exceeds the 512MB available on a
Render Free instance and causes an out-of-memory crash on startup.
"""

from __future__ import annotations

from agents.transcribe import TranscriptionError, transcribe as _transcribe


def transcribe_audio(file_path: str) -> str:
    """Transcribe an audio file to text using Groq's Whisper models.

    Args:
        file_path: Path to a local audio file.

    Returns:
        The transcript as plain text.

    Raises:
        TranscriptionError: The file is empty, too large, contains no
            speech, or every configured model failed.
    """
    try:
        return _transcribe(file_path)
    except TranscriptionError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise TranscriptionError(f"Audio processing failed: {exc}") from exc
