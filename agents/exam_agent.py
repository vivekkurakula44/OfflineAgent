"""Structured exam-answer generation from study notes."""

from __future__ import annotations

from . import config
from .client import chat

_SYSTEM_PROMPT = (
    "You write exam answers from supplied study material.\n\n"
    "Format, exactly:\n"
    "Answer: <the direct answer in one or two sentences>\n\n"
    "<then a compact breakdown of the supporting points, one per line, "
    "using '-' for each point>\n\n"
    "Hard rules:\n"
    "- No preamble, no meta-commentary, no 'I hope this helps'.\n"
    "- The first line must be the actual answer, not a restatement of the "
    "question.\n"
    "- Draw only on the supplied notes. Do not import outside facts.\n"
    "- If the notes do not cover the question, say so plainly and list what "
    "relevant material is present instead.\n"
    "- Include every detail the notes give that bears on the question, but "
    "drop anything irrelevant to it.\n"
    "- Preserve exact terminology, figures, dates, and formulas.\n"
    "- Keep each supporting point to a single line."
)


def answer_exam(question: str, context: str) -> str:
    """Produce a structured, source-grounded exam answer.

    Args:
        question: The exam question to answer.
        context: Study material extracted from the uploaded document.

    Returns:
        A direct answer followed by its supporting points.
    """
    question = (question or "").strip()
    if not question:
        return "Please enter an exam question."

    context = (context or "").strip()
    if not context:
        return (
            "Answer: No study material was supplied.\n\n"
            "- Upload your notes or paste them into the text box."
        )

    body = context[: config.MAX_INPUT_CHARS]
    truncated_note = (
        ""
        if len(context) <= config.MAX_INPUT_CHARS
        else f"\n(Only the first {config.MAX_INPUT_CHARS} characters of the "
             f"notes were used.)"
    )

    return chat(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=(
            f"Notes:\n---\n{body}\n---{truncated_note}\n\n"
            f"Exam question: {question}"
        ),
        max_tokens=1024,
        temperature=0.1,
    )
