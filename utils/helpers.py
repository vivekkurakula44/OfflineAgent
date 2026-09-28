import os
import re


def route_file(file_path: str) -> str:
    """Detect file type from extension and call the correct processor."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        from processors.pdf_processor import extract_text_from_pdf
        return extract_text_from_pdf(file_path)

    elif ext == ".docx":
        from processors.docx_processor import extract_text_from_docx
        return extract_text_from_docx(file_path)

    elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"):
        from processors.image_processor import extract_text_from_image
        return extract_text_from_image(file_path)

    elif ext in (".mp3", ".wav", ".m4a", ".ogg", ".flac"):
        from processors.audio_processor import transcribe_audio
        return transcribe_audio(file_path)

    elif ext in (".mp4", ".mkv", ".avi", ".mov", ".webm"):
        from processors.video_processor import transcribe_video
        return transcribe_video(file_path)

    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    else:
        raise ValueError(f"Unsupported file type: {ext}")


def clean_text(text: str) -> str:
    """Remove extra whitespace and normalize line endings."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse runs of blank lines to a single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse runs of spaces/tabs within a line
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 2000) -> list:
    """Split text into chunks of roughly chunk_size characters, respecting word boundaries."""
    text = clean_text(text)
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:])
            break

        # Try to break at a newline or space
        break_point = text.rfind("\n", start, end)
        if break_point == -1 or break_point <= start:
            break_point = text.rfind(" ", start, end)
        if break_point == -1 or break_point <= start:
            break_point = end

        chunks.append(text[start:break_point].strip())
        start = break_point + 1

    return [c for c in chunks if c]
