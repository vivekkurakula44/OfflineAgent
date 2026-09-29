"""Video processing: extract the audio track, then transcribe it with Groq.

`moviepy` is no longer used. We shell out to ffmpeg directly, resolved via
`imageio-ffmpeg`, which ships a static ffmpeg binary inside the pip
package. That means video support works on Render with no apt packages and
no system-level ffmpeg install.
"""

from __future__ import annotations

import os
import subprocess
import tempfile

from agents.transcribe import TranscriptionError
from agents.transcribe import transcribe as _transcribe
from agents import config


class VideoProcessingError(RuntimeError):
    """Raised when a video file cannot be processed."""


def _ffmpeg_binary() -> str:
    """Return a usable ffmpeg executable path.

    Order: the FFMPEG_BINARY env var, then the binary bundled with
    imageio-ffmpeg, then whatever is on PATH.
    """
    explicit = os.environ.get("FFMPEG_BINARY", "").strip()
    if explicit and os.path.exists(explicit):
        return explicit

    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass

    from shutil import which

    system = which("ffmpeg")
    if system:
        return system

    raise VideoProcessingError(
        "ffmpeg was not found on this server, so video cannot be processed.\n\n"
        "Add 'imageio-ffmpeg' to requirements.txt and redeploy."
    )


def extract_audio_track(
    file_path: str,
    *,
    max_seconds: int | None = None,
) -> tuple[str, bool]:
    """Extract the audio from a video as 16kHz mono WAV.

    Whisper resamples to 16kHz mono internally anyway, so doing it here
    keeps the uploaded payload small enough for Groq's file size cap.

    Args:
        file_path: Path to the source video.
        max_seconds: Truncate the audio to this many seconds.

    Returns:
        A tuple of (wav_path, was_truncated).
    """
    ffmpeg = _ffmpeg_binary()
    limit = max_seconds if max_seconds is not None else config.MAX_VIDEO_AUDIO_SECONDS

    handle, wav_path = tempfile.mkstemp(suffix=".wav")
    os.close(handle)

    command = [
        ffmpeg,
        "-y",
        "-i", file_path,
        "-vn",                    # drop video streams
        "-ac", "1",               # mono
        "-ar", "16000",           # 16 kHz, what Whisper expects
        "-c:a", "pcm_s16le",      # uncompressed, so no encoder needed
        "-t", str(limit),         # cap duration
        wav_path,
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            timeout=config.FFMPEG_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        if os.path.exists(wav_path):
            os.remove(wav_path)
        raise VideoProcessingError(
            f"Extracting audio took longer than "
            f"{config.FFMPEG_TIMEOUT_SECONDS}s and was stopped. "
            f"Try a shorter video."
        ) from exc
    except FileNotFoundError as exc:
        if os.path.exists(wav_path):
            os.remove(wav_path)
        raise VideoProcessingError(
            "ffmpeg could not be launched. Add 'imageio-ffmpeg' to "
            "requirements.txt and redeploy."
        ) from exc

    if result.returncode != 0 or not os.path.exists(wav_path):
        if os.path.exists(wav_path):
            os.remove(wav_path)
        stderr = result.stderr.decode("utf-8", errors="ignore").strip()
        tail = stderr[-400:] if stderr else "no error output"
        raise VideoProcessingError(
            f"ffmpeg could not read this video (exit {result.returncode}).\n\n"
            f"Supported formats: .mp4, .mov, .mkv, .webm, .avi\n\n"
            f"Details: {tail}"
        )

    # If we capped the duration the output will be much shorter than the
    # requested limit only when the source was itself short, so compare
    # against the WAV size implied by the cap.
    truncated = limit <= config.MAX_VIDEO_AUDIO_SECONDS and _is_near_limit(wav_path, limit)
    return wav_path, truncated


def _is_near_limit(wav_path: str, limit: int) -> bool:
    """True when the extracted audio appears to have hit the duration cap.

    16kHz mono s16le is 16000 * 2 = 32000 bytes per second.
    """
    expected = limit * 32000
    actual = os.path.getsize(wav_path)
    return actual >= expected * 0.98


def transcribe_video(file_path: str) -> str:
    """Transcribe the audio track of a video file.

    Args:
        file_path: Path to a local video file.

    Returns:
        The transcript as plain text, with a short note prepended when
        the video had to be truncated.
    """
    wav_path, truncated = extract_audio_track(file_path)

    try:
        if os.path.getsize(wav_path) == 0:
            raise VideoProcessingError(
                "This video has no audio track.\n\n"
                "Supported inputs for video are files that contain speech, "
                "such as .mp4, .mov, .mkv, .webm and .avi."
            )
        transcript = _transcribe(wav_path)
    except TranscriptionError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise VideoProcessingError(f"Video processing failed: {exc}") from exc
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)

    if truncated:
        minutes = config.MAX_VIDEO_AUDIO_SECONDS // 60
        return (
            f"[Only the first {minutes} minutes of audio were transcribed.]\n\n"
            f"{transcript}"
        )

    return transcript
