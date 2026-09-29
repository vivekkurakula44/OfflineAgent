"""PDF text extraction using PyMuPDF (fitz)."""

from __future__ import annotations

import fitz  # PyMuPDF


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from every page of a PDF.

    Scanned PDFs contain images rather than text. If no text is found we
    tell the caller so explicitly instead of returning an empty string,
    so the user gets a useful message rather than a confusing "no text
    extracted" error.
    """
    pages: list[str] = []
    empty_pages = 0
    total_pages = 0

    with fitz.open(file_path) as doc:
        if doc.needs_pass:
            raise ValueError(
                "This PDF is password protected. Remove the password and "
                "try again."
            )

        # Captured here because the document is closed once we leave `with`.
        total_pages = doc.page_count

        if total_pages == 0:
            raise ValueError("This PDF has no pages.")

        for index, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            if text.strip():
                pages.append(text.strip())
            else:
                empty_pages += 1
                pages.append(f"[page {index}: no extractable text]")

    result = "\n\n".join(pages).strip()

    # Only treat it as a scan if literally every page had no text layer.
    # A mixed document still has usable text, so summarise what we found.
    if empty_pages == total_pages:
        raise ValueError(
            "No text could be extracted from this PDF.\n\n"
            "It is most likely a scanned document (page images with no text "
            "layer). To summarise it, export it as text first, or take a "
            "screenshot of each page and upload that as an image."
        )

    if empty_pages:
        result += (
            f"\n\n[Note: {empty_pages} of {total_pages} pages contained no "
            f"extractable text and were skipped.]"
        )

    return result
