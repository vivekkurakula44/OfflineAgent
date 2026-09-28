import os
import gradio as gr

from agents.summarizer import summarize
from agents.qa_agent import answer_question
from agents.quiz_agent import generate_quiz
from agents.exam_agent import answer_exam
from utils.helpers import route_file, clean_text

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = [".txt", ".pdf", ".docx", ".png", ".jpg", ".jpeg", ".mp3", ".wav", ".mp4"]


def _check_api_key() -> str | None:
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        return (
            "⚠️ GROQ_API_KEY is not set.\n"
            "Please add it as an environment variable (Spaces → Settings → Repository secrets)."
        )
    return None


def _get_text(text_input: str, file_obj) -> tuple[str, str | None]:
    """
    Resolve the text to operate on from either the text area or the uploaded file.
    Returns (text, error_message). If error_message is not None, text is empty.
    """
    text = (text_input or "").strip()

    if file_obj is not None:
        try:
            extracted = route_file(file_obj.name)
            extracted = clean_text(extracted)
            if not extracted:
                return "", "❌ Could not extract any text from the uploaded file."
            # Merge with manually entered text if both provided
            if text:
                text = text + "\n\n" + extracted
            else:
                text = extracted
        except Exception as exc:
            return "", f"❌ File processing error: {exc}"

    if not text:
        return "", "❌ Please provide text or upload a file."

    return text, None


# ---------------------------------------------------------------------------
# Tab handler functions
# ---------------------------------------------------------------------------

def handle_summarize(text_input: str, file_obj):
    err = _check_api_key()
    if err:
        return err

    text, err = _get_text(text_input, file_obj)
    if err:
        return err

    try:
        return summarize(text)
    except Exception as exc:
        return f"❌ Summarization error: {exc}"


def handle_qa(text_input: str, file_obj, question: str):
    err = _check_api_key()
    if err:
        return err

    question = (question or "").strip()
    if not question:
        return "❌ Please enter a question."

    text, err = _get_text(text_input, file_obj)
    if err:
        return err

    try:
        return answer_question(question, text)
    except Exception as exc:
        return f"❌ Q&A error: {exc}"


def handle_quiz(text_input: str, file_obj):
    err = _check_api_key()
    if err:
        return err

    text, err = _get_text(text_input, file_obj)
    if err:
        return err

    try:
        return generate_quiz(text)
    except Exception as exc:
        return f"❌ Quiz generation error: {exc}"


def handle_exam(text_input: str, file_obj, question: str):
    err = _check_api_key()
    if err:
        return err

    question = (question or "").strip()
    if not question:
        return "❌ Please enter the exam question."

    text, err = _get_text(text_input, file_obj)
    if err:
        return err

    try:
        return answer_exam(question, text)
    except Exception as exc:
        return f"❌ Exam answer error: {exc}"


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

def build_ui():
    api_warning = _check_api_key()

    with gr.Blocks(
        title="🧠 AI Summarizer Agent",
        theme=gr.themes.Base(
            primary_hue="blue",
            secondary_hue="purple",
            neutral_hue="zinc",
        ).set(
            body_background_fill="#0f1117",
            body_background_fill_dark="#0f1117",
            block_background_fill="#1a1d27",
            block_background_fill_dark="#1a1d27",
            block_border_color="#2d3148",
            block_border_color_dark="#2d3148",
            input_background_fill="#0f1117",
            input_background_fill_dark="#0f1117",
            button_primary_background_fill="linear-gradient(90deg, #3b5bdb, #7048e8)",
            button_primary_background_fill_dark="linear-gradient(90deg, #3b5bdb, #7048e8)",
            button_primary_text_color="white",
        ),
        css="""
            h1 { text-align: center; font-size: 2rem; margin-bottom: 0.25rem; }
            .subtitle { text-align: center; color: #888; margin-bottom: 1.5rem; font-size: 0.95rem; }
            .warning-box { background: #3b2a00; border: 1px solid #f59f00; border-radius: 8px;
                           padding: 12px 16px; margin-bottom: 1rem; color: #ffd43b; }
            .gr-button { border-radius: 8px !important; font-weight: 600 !important; }
            footer { display: none !important; }
        """,
    ) as demo:

        gr.Markdown("# 🧠 AI Summarizer Agent")
        gr.Markdown(
            "<div class='subtitle'>Powered by Groq · llama3-8b-8192 · "
            "Supports Text · PDF · DOCX · Images · Audio · Video</div>"
        )

        if api_warning:
            gr.HTML(f"<div class='warning-box'>{api_warning}</div>")

        with gr.Tabs():

            # ------------------------------------------------------------------
            # Tab 1 — Summarize
            # ------------------------------------------------------------------
            with gr.Tab("📄 Summarize"):
                with gr.Row():
                    with gr.Column(scale=1):
                        sum_text = gr.Textbox(
                            label="Paste text here",
                            placeholder="Paste your text, or upload a file below…",
                            lines=10,
                        )
                        sum_file = gr.File(
                            label="Upload file",
                            file_types=SUPPORTED_EXTENSIONS,
                        )
                        sum_btn = gr.Button("▶ Summarize", variant="primary")
                    with gr.Column(scale=1):
                        sum_out = gr.Textbox(
                            label="Summary",
                            lines=18,
                            interactive=False,
                            show_copy_button=True,
                        )

                sum_btn.click(
                    fn=handle_summarize,
                    inputs=[sum_text, sum_file],
                    outputs=sum_out,
                )

            # ------------------------------------------------------------------
            # Tab 2 — Q&A
            # ------------------------------------------------------------------
            with gr.Tab("❓ Q&A"):
                with gr.Row():
                    with gr.Column(scale=1):
                        qa_text = gr.Textbox(
                            label="Context / document text",
                            placeholder="Paste your text, or upload a file below…",
                            lines=8,
                        )
                        qa_file = gr.File(
                            label="Upload file",
                            file_types=SUPPORTED_EXTENSIONS,
                        )
                        qa_question = gr.Textbox(
                            label="Your question",
                            placeholder="What would you like to know?",
                            lines=2,
                        )
                        qa_btn = gr.Button("▶ Get Answer", variant="primary")
                    with gr.Column(scale=1):
                        qa_out = gr.Textbox(
                            label="Answer",
                            lines=18,
                            interactive=False,
                            show_copy_button=True,
                        )

                qa_btn.click(
                    fn=handle_qa,
                    inputs=[qa_text, qa_file, qa_question],
                    outputs=qa_out,
                )

            # ------------------------------------------------------------------
            # Tab 3 — Quiz
            # ------------------------------------------------------------------
            with gr.Tab("📝 Quiz"):
                with gr.Row():
                    with gr.Column(scale=1):
                        quiz_text = gr.Textbox(
                            label="Paste text here",
                            placeholder="Paste your text, or upload a file below…",
                            lines=10,
                        )
                        quiz_file = gr.File(
                            label="Upload file",
                            file_types=SUPPORTED_EXTENSIONS,
                        )
                        quiz_btn = gr.Button("▶ Generate Quiz", variant="primary")
                    with gr.Column(scale=1):
                        quiz_out = gr.Textbox(
                            label="Quiz (5 Questions)",
                            lines=18,
                            interactive=False,
                            show_copy_button=True,
                        )

                quiz_btn.click(
                    fn=handle_quiz,
                    inputs=[quiz_text, quiz_file],
                    outputs=quiz_out,
                )

            # ------------------------------------------------------------------
            # Tab 4 — Exam Answer
            # ------------------------------------------------------------------
            with gr.Tab("🎓 Exam Answer"):
                with gr.Row():
                    with gr.Column(scale=1):
                        exam_text = gr.Textbox(
                            label="Notes / study material",
                            placeholder="Paste your notes, or upload a file below…",
                            lines=8,
                        )
                        exam_file = gr.File(
                            label="Upload file",
                            file_types=SUPPORTED_EXTENSIONS,
                        )
                        exam_question = gr.Textbox(
                            label="Exam question",
                            placeholder="Enter the exam question here…",
                            lines=2,
                        )
                        exam_btn = gr.Button("▶ Answer Exam Question", variant="primary")
                    with gr.Column(scale=1):
                        exam_out = gr.Textbox(
                            label="Structured Answer",
                            lines=18,
                            interactive=False,
                            show_copy_button=True,
                        )

                exam_btn.click(
                    fn=handle_exam,
                    inputs=[exam_text, exam_file, exam_question],
                    outputs=exam_out,
                )

    return demo


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    demo = build_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
    )
