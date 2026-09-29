"""AI Summarizer Agent - Gradio web app, deployed on Render.

Inputs:  text, PDF, DOCX, images (OCR), audio, video
Outputs: summaries, Q&A, quizzes, exam answers - all source-grounded and
         free of padding.
"""

from __future__ import annotations

import inspect
import os
import traceback

import gradio as gr

from agents import config
from agents.client import AllModelsFailedError, MissingAPIKeyError
from agents.exam_agent import answer_exam
from agents.qa_agent import answer_question
from agents.quiz_agent import generate_quiz
from agents.summarizer import summarize
from utils.helpers import SUPPORTED_EXTENSIONS, clean_text, route_file, truncate

# ---------------------------------------------------------------------------
# Error presentation
# ---------------------------------------------------------------------------

# Exceptions whose message is meaningful to the end user.
_FRIENDLY = (
    ValueError,
    FileNotFoundError,
    RuntimeError,
)

_FRIENDLY_MARKERS = (
    "no ocr engine",
    "not supported",
    "no text",
    "could not",
    "exceeds",
    "no audio track",
    "no readable text",
    "not found in the provided",
    "password protected",
    "empty",
    "ffmpeg",
    "no speech was detected",
)


def _friendly(exc: Exception) -> str:
    """Render an exception as a short, user-facing message."""
    message = str(exc).strip() or exc.__class__.__name__

    if isinstance(exc, MissingAPIKeyError):
        return message

    if isinstance(exc, AllModelsFailedError):
        return f"❌ {message}"

    if isinstance(exc, _FRIENDLY):
        lowered = message.lower()
        if any(marker in lowered for marker in _FRIENDLY_MARKERS):
            return f"❌ {message}"
        return f"❌ {message}"

    # Anything else is a bug: show the type, and log the traceback server-side.
    print(f"[error] {exc.__class__.__name__}: {exc}\n{traceback.format_exc()}")
    return f"❌ Unexpected error: {exc.__class__.__name__}: {message}"


# ---------------------------------------------------------------------------
# Input resolution
# ---------------------------------------------------------------------------

def _resolve(text_input: str, file_obj) -> tuple[str, str | None]:
    """Combine pasted text with any uploaded file into one text blob.

    Returns:
        A tuple of (text, error). When error is not None, text is empty.
    """
    text = (text_input or "").strip()

    if file_obj is not None:
        try:
            extracted = clean_text(route_file(file_obj.name))
        except Exception as exc:  # noqa: BLE001
            return "", _friendly(exc)

        if not extracted:
            return "", (
                "❌ No text could be extracted from that file. If it is a "
                "scanned PDF, export it as text first, or upload a "
                "screenshot as an image instead."
            )

        text = f"{text}\n\n{extracted}" if text else extracted

    if not text:
        return "", "❌ Please paste some text or upload a file."

    return text, None


def _preview_limit() -> int:
    return int(os.environ.get("PREVIEW_CHARS", 6000))


# ---------------------------------------------------------------------------
# Tab handlers
# ---------------------------------------------------------------------------

def handle_summarize(text_input: str, file_obj, max_bullets: int):
    if not config.is_configured():
        return config.MISSING_KEY_MESSAGE

    text, error = _resolve(text_input, file_obj)
    if error:
        return error

    try:
        return summarize(text, max_bullets=int(max_bullets or 12))
    except Exception as exc:  # noqa: BLE001
        return _friendly(exc)


def handle_qa(text_input: str, file_obj, question: str):
    if not config.is_configured():
        return config.MISSING_KEY_MESSAGE

    question = (question or "").strip()
    if not question:
        return "❌ Please enter a question."

    text, error = _resolve(text_input, file_obj)
    if error:
        return error

    try:
        return answer_question(question, text)
    except Exception as exc:  # noqa: BLE001
        return _friendly(exc)


def handle_quiz(text_input: str, file_obj, num_questions: int):
    if not config.is_configured():
        return config.MISSING_KEY_MESSAGE

    text, error = _resolve(text_input, file_obj)
    if error:
        return error

    try:
        return generate_quiz(text, num_questions=int(num_questions or 5))
    except Exception as exc:  # noqa: BLE001
        return _friendly(exc)


def handle_exam(text_input: str, file_obj, question: str):
    if not config.is_configured():
        return config.MISSING_KEY_MESSAGE

    question = (question or "").strip()
    if not question:
        return "❌ Please enter an exam question."

    text, error = _resolve(text_input, file_obj)
    if error:
        return error

    try:
        return answer_exam(question, text)
    except Exception as exc:  # noqa: BLE001
        return _friendly(exc)


def handle_preview(text_input: str, file_obj):
    """Show what was extracted from the input, without calling any model."""
    text, error = _resolve(text_input, file_obj)
    if error:
        return error

    snippet, was_cut = truncate(text, _preview_limit())
    header = f"{len(text):,} characters extracted.\n"
    if was_cut:
        header += f"Showing the first {len(snippet):,}.\n"
    return f"{header}\n{snippet}"


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

_THEME = gr.themes.Base(
    primary_hue="indigo",
    secondary_hue="purple",
    neutral_hue="zinc",
).set(
    body_background_fill="#0f1117",
    body_background_fill_dark="#0f1117",
    block_background_fill="#171a23",
    block_background_fill_dark="#171a23",
    block_border_color="#2a2e40",
    block_border_color_dark="#2a2e40",
    input_background_fill="#0f1117",
    input_background_fill_dark="#0f1117",
    button_primary_background_fill="linear-gradient(90deg, #3b5bdb, #7048e8)",
    button_primary_background_fill_dark="linear-gradient(90deg, #3b5bdb, #7048e8)",
    button_primary_text_color="white",
)

_CSS = """
    h1 { text-align: center; font-size: 1.9rem; margin-bottom: .2rem; }
    .subtitle { text-align: center; color: #7d8296; margin-bottom: 1.4rem; font-size: .93rem; }
    .banner { border-radius: 8px; padding: 12px 16px; margin-bottom: 1rem; font-size: .92rem; }
    .banner-error { background: #2d1b1b; border: 1px solid #e03131; color: #ffa8a8; }
    .gr-button { border-radius: 8px !important; font-weight: 600 !important; }
    footer { display: none !important; }
    footer > div { display: none !important; }
"""

_FILE_HELP = (
    "Text, PDF, DOCX, image (OCR), audio, or video. "
    "Audio and video are transcribed with Whisper; video is capped at 15 "
    "minutes."
)


def _source_column(label: str, lines: int, placeholder: str) -> tuple:
    """Build the shared left-hand 'source material' column."""
    textbox = gr.Textbox(
        label=f"{label} (paste text)",
        placeholder=placeholder,
        lines=lines,
    )
    uploader = gr.File(
        label=f"{label} (upload file)",
        file_types=SUPPORTED_EXTENSIONS,
    )
    preview_btn = gr.Button("Preview extracted text", variant="secondary", size="sm")
    preview_out = gr.Textbox(
        label="Extracted text",
        lines=6,
        interactive=False,
        visible=False,
    )
    return textbox, uploader, preview_btn, preview_out


def _blocks_accepts_theme() -> bool:
    """True when gr.Blocks still takes theme/css in its constructor.

    Gradio 6 deprecated passing theme and css to Blocks and moved them to
    launch(). Supporting both keeps this app deployable on Gradio 5 and 6
    without a code change.
    """
    try:
        params = inspect.signature(gr.Blocks.__init__).parameters
    except (TypeError, ValueError):
        return True
    return "theme" in params and "css" in params


_BLOCKS_TAKES_THEME = _blocks_accepts_theme()


def build_ui() -> gr.Blocks:
    # Gradio 5: theme/css go on Blocks. Gradio 6: they go on launch().
    extra = {"theme": _THEME, "css": _CSS} if _BLOCKS_TAKES_THEME else {}

    with gr.Blocks(title="AI Summarizer Agent", **extra) as demo:
        gr.Markdown("# 🧠 AI Summarizer Agent")
        gr.Markdown(
            "<div class='subtitle'>Source-grounded summaries · Q&amp;A · "
            "Quizzes · Exam answers<br>No filler, no invented facts</div>"
        )

        if not config.is_configured():
            gr.HTML(
                "<div class='banner banner-error'><b>GROQ_API_KEY is not "
                "configured.</b><br>On Render, open your service → "
                "<b>Environment</b> → add <code>GROQ_API_KEY</code> → "
                "<b>Save Deploy</b>. The app restarts automatically.</div>"
            )

        with gr.Tabs():
            # -- Summarize --------------------------------------------------
            with gr.Tab("📄 Summarize"):
                with gr.Row():
                    with gr.Column(scale=1):
                        s_text, s_file, s_prev, s_prev_out = _source_column(
                            "Content", 10, "Paste your text here…"
                        )
                        s_bullets = gr.Slider(
                            3, 25, value=10, step=1,
                            label="Maximum bullet points",
                        )
                        s_btn = gr.Button("▶ Summarize", variant="primary")
                    with gr.Column(scale=1):
                        s_out = gr.Textbox(
                            label="Summary", lines=20,
                            interactive=False,
                        )
                s_prev.click(
                    handle_preview, [s_text, s_file], s_prev_out
                ).then(lambda: gr.update(visible=True), None, s_prev_out)
                s_btn.click(handle_summarize, [s_text, s_file, s_bullets], s_out)

            # -- Q&A --------------------------------------------------------
            with gr.Tab("❓ Q&A"):
                with gr.Row():
                    with gr.Column(scale=1):
                        q_text, q_file, q_prev, q_prev_out = _source_column(
                            "Reference material", 8,
                            "Paste the material your question relates to…",
                        )
                        q_input = gr.Textbox(
                            label="Your question", lines=2,
                            placeholder="What would you like to know?",
                        )
                        q_btn = gr.Button("▶ Get Answer", variant="primary")
                    with gr.Column(scale=1):
                        q_out = gr.Textbox(
                            label="Answer", lines=20,
                            interactive=False,
                        )
                q_prev.click(
                    handle_preview, [q_text, q_file], q_prev_out
                ).then(lambda: gr.update(visible=True), None, q_prev_out)
                q_btn.click(handle_qa, [q_text, q_file, q_input], q_out)

            # -- Quiz -------------------------------------------------------
            with gr.Tab("📝 Quiz"):
                with gr.Row():
                    with gr.Column(scale=1):
                        z_text, z_file, z_prev, z_prev_out = _source_column(
                            "Study material", 10,
                            "Paste the material to quiz yourself on…",
                        )
                        z_count = gr.Slider(
                            3, 20, value=5, step=1, label="Number of questions"
                        )
                        z_btn = gr.Button("▶ Generate Quiz", variant="primary")
                    with gr.Column(scale=1):
                        z_out = gr.Textbox(
                            label="Quiz", lines=20,
                            interactive=False,
                        )
                z_prev.click(
                    handle_preview, [z_text, z_file], z_prev_out
                ).then(lambda: gr.update(visible=True), None, z_prev_out)
                z_btn.click(handle_quiz, [z_text, z_file, z_count], z_out)

            # -- Exam answer ------------------------------------------------
            with gr.Tab("🎓 Exam Answer"):
                with gr.Row():
                    with gr.Column(scale=1):
                        e_text, e_file, e_prev, e_prev_out = _source_column(
                            "Notes", 8, "Paste your notes or study material…",
                        )
                        e_input = gr.Textbox(
                            label="Exam question", lines=3,
                            placeholder="Enter the exam question…",
                        )
                        e_btn = gr.Button("▶ Answer Question", variant="primary")
                    with gr.Column(scale=1):
                        e_out = gr.Textbox(
                            label="Structured answer", lines=20,
                            interactive=False,
                        )
                e_prev.click(
                    handle_preview, [e_text, e_file], e_prev_out
                ).then(lambda: gr.update(visible=True), None, e_prev_out)
                e_btn.click(handle_exam, [e_text, e_file, e_input], e_out)

        gr.Markdown(
            f"<div class='subtitle'>Model: <code>{config.CHAT_MODEL}</code> · "
            f"Transcription: <code>{config.STT_MODEL}</code> · "
            f"{_FILE_HELP}</div>"
        )

    return demo


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

demo = build_ui()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    host = os.environ.get("HOST", "0.0.0.0")

    print(f"[start] model={config.CHAT_MODEL} stt={config.STT_MODEL}")
    print(f"[start] api_key={'set' if config.is_configured() else 'MISSING'}")
    print(f"[start] listening on {host}:{port}")

    launch_kwargs = {}
    if not _BLOCKS_TAKES_THEME:
        # Gradio 6 wants these on launch() rather than Blocks().
        launch_kwargs = {"theme": _THEME, "css": _CSS}

    demo.queue(
        max_size=8,
        default_concurrency_limit=2,
    ).launch(
        server_name=host,
        server_port=port,
        max_file_size=config.MAX_UPLOAD_MB,
        show_error=True,
        share=False,
        **launch_kwargs,
    )
