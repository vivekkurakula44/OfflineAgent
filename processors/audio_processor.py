"""Audio transcription, delegating the actual work to Groq's Whisper API.

This file intentionally does not import `whisper` or `torch`. Those pull in
roughly 800MB of dependencies, which exceeds the 512MB available on a
Render Free instance and causes an out-of-memory crash on startup.

Large recordings are re-encoded with ffmpeg rather than rejected. A user
uploading a 40MB .mp3 would exceed Groq's 25MB ceiling, but re-encoding it
to mono 16kHz at a low bitrate brings it comfortably under the limit.
"""

from __future__ import annotations

import os
import subprocess
import tempfile

from agents import config
from agents.transcribe import TranscriptionError
from agents.transcribe import transcribe as _transcribe
from processors.media import FFmpegUnavailableError, ffmpeg_binary

# Mono 16kHz at 32kbps, which is plenty for speech recognition and is
# roughly 4KB per second, so 25MB of budget covers about 100 minutes.
_COMPRESSED_BITRATE = "32k"


def _compress_to_fit(file_path: str) -> str | None:
    """Re-encode an oversized audio file so it fits Groq's size limit.

    Returns:
        Path to a new compressed file, or None if compression did not help.
    """
    try:
        ffmpeg = ffmpeg_binary()
    except FFmpegUnavailableError as exc:
        raise TranscriptionError(str(exc)) from exc

    handle, out_path = tempfile.mkstemp(suffix=".mp3")
    os.close(handle)

    command = [
        ffmpeg,
        "-y",
        "-i", file_path,
        "-vn",
        "-ac", "1",                 # mono
        "-ar", "16000",             # 16kHz, what Whisper expects
        "-b:a", _COMPRESSED_BITRATE,
        "-f", "mp3",
        out_path,
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            timeout=config.FFMPEG_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        if os.path.exists(out_path):
            os.remove(out_path)
        raise TranscriptionError(
            "Re-compressing this recording took too long and was stopped. "
            "Try trimming it to a shorter clip."
        )

    if result.returncode != 0 or not os.path.exists(out_path):
        if os.path.exists(out_path):
            os.remove(out_path)
        return None

    if os.path.getsize(out_path) >= config.MAX_AUDIO_BYTES:
        os.remove(out_path)
        return None

    return out_path


def transcribe_audio(file_path: str) -> str:
    """Transcribe an audio file to text using Groq's Whisper models.

    Args:
        file_path: Path to a local audio file.

    Returns:
        The transcript as plain text.

    Raises:
        TranscriptionError: The file is empty, cannot be shrunk enough to
            fit, contains no speech, or every configured model failed.
    """
    if not os.path.exists(file_path):
        raise TranscriptionError("The uploaded audio file could not be read.")

    if os.path.getsize(file_path) == 0:
        raise TranscriptionError("The audio file is empty (0 bytes).")

    # Send as-is when it already fits.
    if os.path.getsize(file_path) <= config.MAX_AUDIO_BYTES:
        try:
            return _transcribe(file_path)
        except TranscriptionError as exc:
            if "exceeds" not in str(exc):
                raise
            # Fall through and try compression anyway.
            compressed_error = exc

        compressed = _compress_to_fit(file_path)
        if compressed is None:
            raise compressed_error

        try:
            return _transcribe(compressed)
        finally:
            if os.path.exists(compressed):
                os.remove(compressed)

    # Oversized on arrival: compress first, then transcribe the smaller file.
    compressed = _compress_to_fit(file_path)
    if compressed is None:
        actual_mb = os.path.getsize(file_path) / (1024 * 1024)
        limit_mb = config.MAX_AUDIO_BYTES / (1024 * 1024)
        raise TranscriptionError(
            f"This recording is {actual_mb:.1f}MB and could not be reduced "
            f"below the {limit_mb:.0f}MB limit of Groq's transcription API.\n\n"
            f"Trim it to a shorter clip, or convert it to a more compressed "
            f"format and try again."
        )

    try:
        return _transcribe(compressed)
    finally:
        if os.path.exists(compressed):
            os.remove(compressed)
