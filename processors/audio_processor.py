import os
import tempfile
import shutil
import whisper


def transcribe_audio(file_path: str) -> str:
    model = whisper.load_model("tiny")

    # Copy file to a temp location with a safe name to avoid path issues
    ext = os.path.splitext(file_path)[1].lower()
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp_path = tmp.name

    try:
        shutil.copy2(file_path, tmp_path)
        result = model.transcribe(tmp_path)
        return result["text"].strip()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
