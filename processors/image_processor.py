"""OCR for image files.

Two engines are supported, tried in this order:

  1. pytesseract  - needs the `tesseract` binary. On Render this is provided
                    by the aptPackages entry in render.yaml.
  2. rapidocr     - pure-Python ONNX OCR, installed via
                    requirements-ocr-fallback.txt. Needs no system binary.

Whichever is available is used, so OCR degrades gracefully rather than
crashing when a backend is missing.
"""

from __future__ import annotations

import os
import shutil
import tempfile

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

# Windows install paths checked when tesseract is not on PATH.
_WINDOWS_TESSERACT_PATHS = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
)

# Cached detection results, so we probe the backends once per process.
_tesseract_ok: bool | None = None
_rapidocr_engine = None


class OCRUnavailableError(RuntimeError):
    """Raised when no OCR engine is installed."""


def _configure_tesseract() -> bool:
    """Point pytesseract at a tesseract binary if one can be found."""
    global _tesseract_ok
    if _tesseract_ok is not None:
        return _tesseract_ok

    try:
        import pytesseract
    except ImportError:
        _tesseract_ok = False
        return False

    # An explicit path in the environment always wins.
    explicit = os.environ.get("TESSERACT_CMD", "").strip()
    if explicit and os.path.exists(explicit):
        pytesseract.pytesseract.tesseract_cmd = explicit
        _tesseract_ok = True
        return True

    if shutil.which("tesseract"):
        _tesseract_ok = True
        return True

    for path in _WINDOWS_TESSERACT_PATHS:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            _tesseract_ok = True
            return True

    # The binary may exist without a version string; treat that as success.
    try:
        pytesseract.get_tesseract_version()
        _tesseract_ok = True
    except Exception:
        _tesseract_ok = False

    return _tesseract_ok


def _load_rapidocr():
    """Return a cached RapidOCR engine, or None if unavailable."""
    global _rapidocr_engine
    if _rapidocr_engine is not None:
        return _rapidocr_engine
    try:
        from rapidocr_onnxruntime import RapidOCR

        _rapidocr_engine = RapidOCR()
    except Exception:
        _rapidocr_engine = None
    return _rapidocr_engine


def _preprocess(image: Image.Image) -> Image.Image:
    """Grayscale, normalise, upscale small images and sharpen for OCR."""
    if image.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        image = Image.alpha_composite(
            background, image.convert("RGBA")
        ).convert("RGB")

    image = ImageOps.exif_transpose(image)
    image = image.convert("L")

    # OCR engines need roughly 300 DPI; upscale small images to help.
    if max(image.size) < 1000:
        scale = min(3.0, 1000 / max(image.size))
        new_size = (int(image.width * scale), int(image.height * scale))
        image = image.resize(new_size, Image.LANCZOS)

    image = ImageOps.autocontrast(image, cutoff=1)
    image = ImageEnhance.Contrast(image).enhance(1.8)
    image = image.filter(ImageFilter.SHARPEN)
    return image


def _ocr_tesseract(image: Image.Image) -> str:
    import pytesseract

    text = pytesseract.image_to_string(image, config="--psm 6")
    return text.strip()


def _ocr_rapidocr(image: Image.Image) -> str:
    engine = _load_rapidocr()
    if engine is None:
        raise OCRUnavailableError("RapidOCR is not installed.")

    rgb = image.convert("RGB")
    result, _ = engine(rgb)
    if not result:
        return ""
    # RapidOCR returns [box, text, score] triples.
    return "\n".join(str(item[1]) for item in result if len(item) >= 2).strip()


def extract_text_from_image(file_path: str) -> str:
    """Extract text from an image using whichever OCR engine is available.

    Raises:
        OCRUnavailableError: Neither OCR backend is installed.
        ValueError: The image contained no readable text.
    """
    prepared = _preprocess(Image.open(file_path))

    if _configure_tesseract():
        try:
            text = _ocr_tesseract(prepared)
            if text:
                return text
        except Exception:
            # Fall through and try RapidOCR instead.
            pass

    if _load_rapidocr() is not None:
        text = _ocr_rapidocr(prepared)
        if text:
            return text

    if not _configure_tesseract():
        raise OCRUnavailableError(
            "No OCR engine is available on this server.\n\n"
            "To enable image OCR on Render, either:\n"
            "  1. Add 'tesseract-ocr' to aptPackages in render.yaml, or\n"
            "  2. Add 'rapidocr-onnxruntime' to requirements.txt\n\n"
            "Until then, PDF, DOCX, TXT, audio and video inputs still work."
        )

    raise ValueError(
        "No readable text was found in this image. It may be blank, or it "
        "may be handwriting or a photo rather than a screenshot of text."
    )
