"""File-type routing and text utilities."""

from __future__ import annotations

import os
import re

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp")
AUDIO_EXTENSIONS = (".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".webm")
VIDEO_EXTENSIONS = (".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v")

SUPPORTED_EXTENSIONS = [
    ".txt",
    ".md",
    ".pdf",
    ".docx",
    *IMAGE_EXTENSIONS,
    *AUDIO_EXTENSIONS,
    *VIDEO_EXTENSIONS,
]

# Errors that are genuinely the user's fault, so the message is shown as-is.
_USER_FACING = (ValueError, FileNotFoundError)


def route_file(file_path: str) -> str:
    """Extract text from a file by dispatching on its extension.

    Args:
        file_path: Path to the uploaded file.

    Returns:
        Plain text extracted from the file.

    Raises:
        ValueError: The extension is not supported.
    """
    if not file_path or not os.path.exists(file_path):
        raise ValueError("The uploaded file could not be read.")

    ext = os.path.splitext(file_path)[1].lower()

    if ext in (".txt", ".md", ".csv", ".json", ".log"):
        return _read_plain_text(file_path)

    if ext == ".pdf":
        from processors.pdf_processor import extract_text_from_pdf

        return extract_text_from_pdf(file_path)

    if ext == ".docx":
        from processors.docx_processor import extract_text_from_docx

        return extract_text_from_docx(file_path)

    if ext in IMAGE_EXTENSIONS:
        from processors.image_processor import extract_text_from_image

        return extract_text_from_image(file_path)

    if ext in AUDIO_EXTENSIONS and ext not in VIDEO_EXTENSIONS:
        from processors.audio_processor import transcribe_audio

        return transcribe_audio(file_path)

    if ext in VIDEO_EXTENSIONS:
        from processors.video_processor import transcribe_video

        return transcribe_video(file_path)

    if ext == ".doc":
        raise ValueError(
            "Legacy .doc files are not supported. Open the file in Word and "
            "save it as .docx, then upload it again."
        )

    raise ValueError(
        f"Unsupported file type '{ext}'.\n\n"
        f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
    )


def _read_plain_text(file_path: str) -> str:
    """Read a text file, tolerating any encoding it happens to use."""
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            with open(file_path, "r", encoding=encoding) as handle:
                return handle.read()
        except UnicodeDecodeError:
            continue

    with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
        return handle.read()


def clean_text(text: str) -> str:
    """Normalise whitespace so prompts stay compact and consistent."""
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def truncate(text: str, limit: int) -> tuple[str, bool]:
    """Cut text to a character limit, respecting word boundaries.

    Returns:
        A tuple of (text, was_truncated).
    """
    if len(text) <= limit:
        return text, False

    cut = text[:limit]
    boundary = max(cut.rfind("\n"), cut.rfind(" "))
    if boundary > limit * 0.8:
        cut = cut[:boundary]

    return cut.rstrip() + "...", True


def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks on paragraph/sentence boundaries."""
    text = clean_text(text)
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        piece = text[start:end]

        if end < len(text):
            # Prefer to break at a paragraph, then a sentence, then a space.
            for pattern in ("\n\n", "\n", ". ", " "):
                boundary = piece.rfind(pattern)
                if boundary > chunk_size * 0.5:
                    piece = piece[: boundary + len(pattern)]
                    break

        piece = piece.strip()
        if piece:
            chunks.append(piece)

        if end >= len(text):
            break

        start = max(end - overlap, start + 1)

    return chunks
