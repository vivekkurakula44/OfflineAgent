"""DOCX text extraction, including table contents."""

from __future__ import annotations

import docx  # python-docx


def extract_text_from_docx(file_path: str) -> str:
    """Extract paragraphs and tables from a .docx file in document order."""
    document = docx.Document(file_path)

    parts: list[str] = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text:
            parts.append(text)

    for table in document.tables:
        rows: list[str] = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            # Collapse the duplicated cells that appear in merged tables.
            deduped: list[str] = []
            for cell in cells:
                if not deduped or cell != deduped[-1]:
                    deduped.append(cell)
            if any(deduped):
                rows.append(" | ".join(deduped))
        if rows:
            parts.append("[table]\n" + "\n".join(rows))

    result = "\n\n".join(parts).strip()

    if not result:
        raise ValueError(
            "No text was found in this document. It may contain only images."
        )

    return result
