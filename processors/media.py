"""Locating an ffmpeg executable.

Shared by the audio and video processors.

`imageio-ffmpeg` ships a static ffmpeg binary inside the pip package, so
ffmpeg works on Render without any apt package or system install. The
system binary is used as a fallback if present.
"""

from __future__ import annotations

import os
from shutil import which


class FFmpegUnavailableError(RuntimeError):
    """Raised when no ffmpeg executable can be found."""


def ffmpeg_binary() -> str:
    """Return the path to a usable ffmpeg executable.

    Order of preference:
      1. ``FFMPEG_BINARY`` environment variable
      2. the static binary bundled with ``imageio-ffmpeg``
      3. ``ffmpeg`` on PATH

    Raises:
        FFmpegUnavailableError: No ffmpeg could be located.
    """
    explicit = os.environ.get("FFMPEG_BINARY", "").strip()
    if explicit and os.path.exists(explicit):
        return explicit

    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass

    system = which("ffmpeg")
    if system:
        return system

    raise FFmpegUnavailableError(
        "ffmpeg was not found on this server, so audio and video cannot be "
        "processed.\n\nAdd 'imageio-ffmpeg' to requirements.txt and redeploy."
    )
