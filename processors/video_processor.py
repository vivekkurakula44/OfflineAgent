import os
import tempfile
import whisper

try:
    from moviepy.editor import VideoFileClip
except ImportError:
    VideoFileClip = None


def transcribe_video(file_path: str) -> str:
    if VideoFileClip is None:
        return "Error: moviepy is not installed. Cannot process video files."

    audio_tmp = None
    try:
        # Extract audio from video to a temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            audio_tmp = tmp.name

        clip = VideoFileClip(file_path)
        if clip.audio is None:
            clip.close()
            return "Error: No audio track found in the video file."

        clip.audio.write_audiofile(audio_tmp, logger=None)
        clip.close()

        # Transcribe extracted audio with Whisper
        model = whisper.load_model("tiny")
        result = model.transcribe(audio_tmp)
        return result["text"].strip()

    finally:
        if audio_tmp and os.path.exists(audio_tmp):
            os.remove(audio_tmp)
