"""Concise summarization.

The system prompt is deliberately strict: the whole point of this app is
returning only the information that matters, with no preamble, no
restatement of the request, and no closing pleasantries.
"""

from __future__ import annotations

from . import config
from .client import chat

_SYSTEM_PROMPT = (
    "You are a precise summarizer. Produce the smallest set of bullet points "
    "that captures all substantive information in the source.\n\n"
    "Hard rules:\n"
    "- Output bullet points only. No heading, no intro, no outro, no sign-off.\n"
    "- Never add facts, commentary, or opinions that are not in the source.\n"
    "- Never add filler such as 'In summary' or 'This document discusses'.\n"
    "- Keep each bullet to one idea, stated as briefly as possible.\n"
    "- Preserve concrete details: names, dates, numbers, definitions, formulas.\n"
    "- Preserve the source's own terminology rather than paraphrasing jargon.\n"
    "- If the source has explicit sections or lists, mirror that structure.\n"
    "- Order bullets to follow the source's own order of importance."
)


def summarize(text: str, *, max_bullets: int = 12) -> str:
    """Summarize text into terse bullet points.

    Args:
        text: Source text to compress.
        max_bullets: Soft cap on the number of bullets requested.

    Returns:
        Newline-separated bullet points, or a short notice if the source
        had no summarizable content.
    """
    source = (text or "").strip()
    if not source:
        return "There is no text to summarize."

    body = source[: config.MAX_INPUT_CHARS]
    truncated_note = (
        ""
        if len(source) <= config.MAX_INPUT_CHARS
        else f"\n\n(Showing the first {config.MAX_INPUT_CHARS} characters of "
             f"{len(source)}.)"
    )

    return chat(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=(
            f"Summarize the following into at most {max_bullets} bullet "
            f"points.{truncated_note}\n\n---\n{body}\n---"
        ),
        max_tokens=1024,
        temperature=0.1,
    )
