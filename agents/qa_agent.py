"""Question answering grounded in the provided document text."""

from __future__ import annotations

from . import config
from .client import chat

_SYSTEM_PROMPT = (
    "You answer questions using only the supplied context. You never use "
    "outside knowledge.\n\n"
    "Hard rules:\n"
    "- Answer directly. No preamble, no restating the question, no closing "
    "remarks.\n"
    "- Be as brief as the question allows. A one-line answer beats a paragraph.\n"
    "- If the context does not contain the answer, reply exactly: "
    "'Not found in the provided material.'\n"
    "- Never speculate, never fill gaps with general knowledge, never hedge "
    "with phrases like 'typically' or 'in general'.\n"
    "- Quote exact wording from the context when precision matters.\n"
    "- For list-style answers, use one short bullet per item."
)


def answer_question(question: str, context: str) -> str:
    """Answer a question using only the given context.

    Args:
        question: The user's question.
        context: Text extracted from the uploaded document.

    Returns:
        A direct, concise answer.
    """
    question = (question or "").strip()
    if not question:
        return "Please enter a question."

    context = (context or "").strip()
    if not context:
        return "Not found in the provided material."

    body = context[: config.MAX_INPUT_CHARS]
    truncated_note = (
        ""
        if len(context) <= config.MAX_INPUT_CHARS
        else f"\n(Only the first {config.MAX_INPUT_CHARS} characters of the "
             f"document were searched.)"
    )

    return chat(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=(
            f"Context:\n---\n{body}\n---{truncated_note}\n\n"
            f"Question: {question}"
        ),
        max_tokens=512,
        temperature=0.1,
    )
