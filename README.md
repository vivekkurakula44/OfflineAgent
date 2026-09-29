# AI Summarizer Agent — Render Deployment

An offline-first note summarizer, deployed to the web. Accepts **text, PDF,
DOCX, images (OCR), audio and video** and returns **source-grounded**
summaries, Q&A, quizzes and exam answers — with no padding, no preamble and
no invented facts.

AI runs on the **Groq API**. File parsing runs on the server.

---

## Deploy to Render

### Step 1 — Push the code to GitHub

From this folder:

```bash
git init
git add .
git commit -m "AI Summarizer Agent"
```

Then create an empty GitHub repo and push:

```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

`.gitignore` already excludes `__pycache__`, `.venv` and `.env`.

### Step 2 — Create the service (easiest route)

1. Go to <https://dashboard.render.com>
2. **New → Blueprint**
3. Select your GitHub repo
4. Render reads `render.yaml` and configures everything
5. When prompted, paste your **GROQ_API_KEY**
6. Click **Apply** and wait for the build

### Step 2b — Create the service (manual route)

1. **New → Web Service** → pick your repo
2. **Environment:** Python
3. **Build command:**
   ```
   pip install --upgrade pip && pip install -r requirements.txt
   ```
4. **Start command:**
   ```
   python app.py
   ```
5. **Instance type:** Free
6. **Add environment variable:** `GROQ_API_KEY` = your key
7. **Create Web Service**

### Step 3 — Open your site

Render prints the URL once the build finishes:

```
https://YOUR-SERVICE-NAME.onrender.com
```

---

## What you get

| Tab | Input | Output |
|-----|-------|--------|
| 📄 Summarize | text / PDF / DOCX / image / audio / video | Bullet points, capped count |
| ❓ Q&A | reference material + question | Direct answer, or "Not found in the provided material." |
| 📝 Quiz | study material | 3–20 numbered Q/A pairs |
| 🎓 Exam Answer | notes + question | Direct answer, then supporting points |

Every tab also has **Preview extracted text**, which shows what was read from
your file *without* spending any tokens. Use it to confirm a scan or a photo
was read correctly before summarising.

---

## Design decisions worth knowing

### Models are configuration, not code

`agents/config.py` reads model IDs from environment variables:

```
GROQ_MODEL                  → openai/gpt-oss-120b
GROQ_MODEL_FALLBACKS        → openai/gpt-oss-20b,qwen/qwen3.6-27b
GROQ_STT_MODEL              → whisper-large-v3-turbo
GROQ_STT_MODEL_FALLBACKS    → whisper-large-v3,distil-whisper-large-v3-en
```

If a model is retired, the client automatically falls through to the next
entry and logs it. You can change any of these in the Render dashboard and
redeploy — no code edit.

> **Why not `llama3-8b-8192`?** It was shut down on 2025-08-30, along with
> `llama-3.1-8b-instant` and `llama-3.3-70b-versatile` on 2026-08-16. Any code
> still calling them returns `model_decommissioned` on every request.

### No PyTorch, and why

The original version used `openai-whisper` + `torch` for transcription. Together
those need roughly **800 MB of RAM**. A Render Free instance has **512 MB**, so
the container was OOM-killed before the app finished starting.

Audio and video now go to **Groq's hosted Whisper** instead. That removed
`torch` entirely — the image is far smaller, the build is faster, startup is
instant, and transcription runs on Groq's GPUs rather than a 0.1-CPU vCPU.

### No ffmpeg install needed

Video audio is extracted by shelling out to ffmpeg, resolved through
`imageio-ffmpeg`, which ships a **static ffmpeg binary inside the pip
package**. No `apt install ffmpeg`, no system dependency.

### OCR has two engines

`render.yaml` installs `tesseract-ocr` via `aptPackages`. If that is ever
unavailable, `processors/image_processor.py` falls back to
`rapidocr-onnxruntime` (pure pip, bundled ONNX models). To enable the fallback
without touching apt, add this to `requirements.txt`:

```
rapidocr-onnxruntime>=1.3.0
```

Video is transcribed up to **15 minutes**; anything longer is truncated and
noted, because longer audio exceeds Groq's 25 MB limit once encoded.

---

## Free-tier limits you should expect

| Limit | Value |
|-------|-------|
| RAM | 512 MB |
| CPU | 0.1 vCPU |
| Sleeps after | 15 minutes of inactivity |
| Cold start | 30–60 seconds |
| Bandwidth | 5 GB / month |

The cold start is the one visitors will notice: after 15 minutes idle, the
next visitor waits up to a minute while Render boots the container. This is
normal and not a bug in your app.

To remove it, upgrade to the **Starter** plan at $7/month (512 MB, 0.5 vCPU,
no spin-down). No code changes needed.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "GROQ_API_KEY is not set" | Key not saved | Dashboard → Environment → add `GROQ_API_KEY` → Save Deploy |
| "All configured models failed" | Bad or over-quota key | Check <https://console.groq.com/keys>, then logs |
| `model_decommissioned` | Model retired | Update `GROQ_MODEL`, or rely on the fallback list |
| Out of memory on startup | PyTorch present | Ensure `torch` and `openai-whisper` are **not** in `requirements.txt` |
| "No OCR engine is available" | apt package missing | Check `aptPackages` in `render.yaml` |
| Video fails | ffmpeg unresolvable | Confirm `imageio-ffmpeg` is in `requirements.txt` |
| PDF yields no text | Scanned document | Export as text, or upload page images instead |
| App sleeps mid-demo | Free tier spin-down | Normal — reload, or upgrade to Starter |

Check logs at **Dashboard → your service → Logs**.

---

## Local development

```bash
pip install -r requirements.txt

# Windows only, for OCR:
pip install -r requirements-ocr-fallback.txt

copy .env.example .env      # then add your key
set GROQ_API_KEY=gsk_...

python app.py
```

Runs at <http://localhost:7860>.

To verify everything without a network call:

```bash
python verify_local.py
```

## Project layout

```
.
├── app.py                     Gradio UI, 4 tabs
├── requirements.txt           Dependencies (deliberately no torch)
├── requirements-ocr-fallback.txt
├── render.yaml                Render Blueprint (plan, apt, env vars)
├── Procfile
├── verify_local.py            Test harness
├── agents/
│   ├── config.py              Models + limits, all from env vars
│   ├── client.py              Groq client, model fallback, retry
│   ├── transcribe.py          Whisper via Groq
│   ├── summarizer.py
│   ├── qa_agent.py
│   ├── quiz_agent.py
│   └── exam_agent.py
├── processors/
│   ├── pdf_processor.py
│   ├── docx_processor.py
│   ├── image_processor.py     tesseract, then rapidocr
│   ├── audio_processor.py
│   └── video_processor.py     ffmpeg + Whisper
└── utils/
    └── helpers.py             Routing, cleaning, chunking
```
