"""Quiz generation from source material."""

from __future__ import annotations

import re

from . import config
from .client import chat

_SYSTEM_PROMPT = (
    "You build revision quizzes from study material.\n\n"
    "Format, exactly:\n"
    "Q1: <question>\n"
    "A1: <answer>\n"
    "Q2: <question>\n"
    "A2: <answer>\n"
    "and so on.\n\n"
    "Hard rules:\n"
    "- No heading, no intro, no outro, no markdown bold.\n"
    "- Exactly the number of questions requested, numbered 1..N.\n"
    "- Each answer must be specific and checkable, one or two short sentences.\n"
    "- Questions must be answerable from the source alone. Never require "
    "outside knowledge.\n"
    "- Test understanding of the important ideas, not trivia or formatting.\n"
    "- Vary the question types across the set.\n"
    "- Quote exact figures, dates, and terms from the source where relevant."
)

_COUNT_RE = re.compile(r"\d+")


def generate_quiz(text: str, *, num_questions: int = 5) -> str:
    """Generate numbered question/answer pairs from text.

    Args:
        text: Source material to build questions from.
        num_questions: How many questions to generate.

    Returns:
        Formatted Q/A pairs, or a short notice if there is nothing to quiz.
    """
    source = (text or "").strip()
    if not source:
        return "There is no text to build a quiz from."

    # Guard against absurd values from the UI.
    try:
        count = int(num_questions)
    except (TypeError, ValueError):
        count = 5
    count = max(1, min(count, 20))

    body = source[: config.MAX_INPUT_CHARS]
    truncated_note = (
        ""
        if len(source) <= config.MAX_INPUT_CHARS
        else f"\n\n(Built from the first {config.MAX_INPUT_CHARS} characters "
             f"of {len(source)}.)"
    )

    return chat(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=(
            f"Write exactly {count} quiz questions with answers based "
            f"only on the material below.{truncated_note}\n\n---\n{body}\n---"
        ),
        max_tokens=1400,
        temperature=0.3,
    )
