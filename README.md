---
title: AI Summarizer Agent
emoji: 🧠
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
---

# 🧠 AI Summarizer Agent — OfflineAgent-Online

A powerful AI-powered document summarization and Q&A agent that runs entirely on Hugging Face Spaces using the **Groq API** (free tier).

## Features

- 📄 **Summarize** — Concise bullet-point summaries of any content
- ❓ **Q&A** — Ask questions about your documents
- 📝 **Quiz** — Auto-generate 5-question quizzes from content
- 🎓 **Exam Answer** — Structured exam-style answers using your notes

## Supported Input Formats

| Format | Details |
|--------|---------|
| Text | Direct text input |
| PDF | Text extracted via PyMuPDF |
| DOCX | Text extracted via python-docx |
| Images | OCR via pytesseract (PNG, JPG, JPEG) |
| Audio | Transcribed via Whisper (MP3, WAV) |
| Video | Audio extracted + Whisper transcription (MP4) |

## Setup

### 1. Fork / Duplicate this Space

Click **Duplicate this Space** on Hugging Face.

### 2. Set your Groq API Key

In your Space settings, go to **Settings → Repository secrets** and add:

```
Name:  GROQ_API_KEY
Value: your_groq_api_key_here
```

Get a free API key at [console.groq.com](https://console.groq.com).

### 3. That's it!

The Space will restart and your agent will be live at your public URL.

## Local Development

```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/ai-summarizer-agent
cd ai-summarizer-agent

# Install dependencies
pip install -r requirements.txt

# Copy and fill in your API key
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# Run locally
python app.py
```

## Model

Uses **llama3-8b-8192** via Groq API — fast, free, and accurate.

## License

MIT
