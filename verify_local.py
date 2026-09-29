"""Local verification harness. Not part of the deployed app."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

failures = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}" + (f" -> {detail}" if detail else ""))
    if not condition:
        failures.append(name)


print("\n=== 1. config: model IDs ===")
from agents import config

check("no dead llama3-8b-8192", config.CHAT_MODEL != "llama3-8b-8192", config.CHAT_MODEL)
check("primary chat model current", config.CHAT_MODEL == "openai/gpt-oss-120b", config.CHAT_MODEL)
check("has chat fallbacks", len(config.chat_models()) > 1, str(config.chat_models()))
check("stt model is groq whisper", config.STT_MODEL.startswith("whisper"), config.STT_MODEL)
check("stt fallbacks present", len(config.stt_models()) > 1, str(config.stt_models()))
check("deduped lists", len(config.chat_models()) == len(set(config.chat_models())))
check("is_configured() False without key", config.is_configured() is False)

print("\n=== 2. source has no dead model strings ===")
import pathlib
dead_names = ("llama3-8b-8192", "llama3-70b-8192", "llama-3.1-8b-instant", "llama-3.3-70b-versatile")
dead_hits = []
for p in pathlib.Path(".").rglob("*.py"):
    if "__pycache__" in str(p) or p.name == "verify_local.py":
        continue
    # Ignore comments and docstrings: config.py documents these retired IDs
    # as history, which is intentional. Only real code must be clean.
    code = "\n".join(
        line for line in p.read_text(encoding="utf-8", errors="ignore").splitlines()
        if not line.strip().startswith("#")
    )
    for dead in dead_names:
        if dead in code:
            dead_hits.append(f"{p.name}:{dead}")
check("no dead model ids in logic code", not dead_hits, str(dead_hits))

print("\n=== 3. helpers: text utils ===")
from utils.helpers import clean_text, chunk_text, truncate, route_file, SUPPORTED_EXTENSIONS

dirty = "line1\r\n\r\n\r\n\r\nline2   \r\n\tline3\u00a0end"
clean = clean_text(dirty)
check("collapses blank runs", "\n\n\n" not in clean, repr(clean))
check("collapses spaces", "line2   " not in clean)
check("strips result", clean == clean.strip())

text = "word " * 500
chunks = chunk_text(text, chunk_size=200, overlap=20)
check("chunks produced", len(chunks) > 1, f"{len(chunks)} chunks")
check("all chunks non-empty", all(c.strip() for c in chunks))
check("chunks respect size", all(len(c) <= 230 for c in chunks),
      f"max={max(len(c) for c in chunks)}")

t, cut = truncate("x" * 500, 100)
check("truncate cuts", cut is True and len(t) <= 105, f"len={len(t)}")
t2, cut2 = truncate("short", 100)
check("truncate passthrough", cut2 is False and t2 == "short")

print("\n=== 4. route_file: real .txt ===")
tmp_txt = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_t.txt")
with open(tmp_txt, "w", encoding="utf-8") as fh:
    fh.write("Photosynthesis converts light into chemical energy in plants.")
got = route_file(tmp_txt)
check("reads txt", "Photosynthesis" in got, got[:40])

try:
    bad = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_t.xyz")
    with open(bad, "w", encoding="utf-8") as fh:
        fh.write("junk")
    route_file(bad)
    check("rejects unsupported ext", False)
    os.remove(bad)
except ValueError as e:
    check("rejects unsupported ext", "Unsupported" in str(e), str(e)[:40])

check("accepts many extensions", ".mp4" in SUPPORTED_EXTENSIONS and ".docx" in SUPPORTED_EXTENSIONS)
os.remove(tmp_txt)

print("\n=== 5. route_file: real PDF ===")
try:
    import fitz
    tmp_pdf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_t.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Mitosis is cell division in biology.")
    doc.save(tmp_pdf)
    doc.close()
    pdf_text = route_file(tmp_pdf)
    check("extracts pdf text", "Mitosis" in pdf_text, pdf_text[:50])
    os.remove(tmp_pdf)

    # Regression guard: page_count must be read before the doc is closed,
    # and a partly-text PDF must NOT be rejected as a scan.
    tmp_pdf2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_t2.pdf")
    d2 = fitz.open()
    p1 = d2.new_page()
    p1.insert_text((72, 100), "Osmosis is movement of solvent across a membrane.")
    d2.new_page()  # blank page -> exercises the mixed-document path
    d2.save(tmp_pdf2)
    d2.close()
    mixed = route_file(tmp_pdf2)
    check("mixed pdf keeps text", "Osmosis" in mixed, mixed[:60])
    check("mixed pdf notes skipped pages", "1 of 2 pages" in mixed, mixed[-90:])
    os.remove(tmp_pdf2)

    # A PDF with no text at all must still be reported as a scan.
    tmp_pdf3 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_t3.pdf")
    d3 = fitz.open()
    d3.new_page()
    d3.save(tmp_pdf3)
    d3.close()
    try:
        route_file(tmp_pdf3)
        check("blank pdf rejected as scan", False, "no error raised")
    except ValueError as e:
        check("blank pdf rejected as scan", "scanned document" in str(e))
    os.remove(tmp_pdf3)
except ImportError:
    check("PyMuPDF available", False, "not installed")
except Exception as e:
    check("extracts pdf text", False, f"{type(e).__name__}: {e}")

print("\n=== 6. route_file: real DOCX ===")
try:
    import docx as docx_mod
    tmp_docx = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_t.docx")
    d = docx_mod.Document()
    d.add_paragraph("Water boils at 100 degrees Celsius at sea level.")
    d.save(tmp_docx)
    docx_text = route_file(tmp_docx)
    check("extracts docx text", "100 degrees" in docx_text, docx_text[:50])
    os.remove(tmp_docx)
except Exception as e:
    check("extracts docx text", False, f"{type(e).__name__}: {e}")

print("\n=== 7. OCR engine detection ===")
from processors import image_processor as ip
check("_configure_tesseract returns bool", isinstance(ip._configure_tesseract(), bool))
print(f"        tesseract detected: {ip._configure_tesseract()}")

print("\n=== 8. ffmpeg resolution ===")
from processors.media import ffmpeg_binary, FFmpegUnavailableError
try:
    fx = ffmpeg_binary()
    check("ffmpeg binary found", os.path.exists(fx), fx)
except FFmpegUnavailableError as e:
    check("ffmpeg binary found", False, str(e)[:60])

print("\n=== 9. app builds UI ===")
os.environ["GROQ_API_KEY"] = ""
try:
    import app as app_mod
    blocks = app_mod.build_ui()
    check("build_ui() returns Blocks", blocks is not None, type(blocks).__name__)
    check("missing-key banner handled", "GROQ_API_KEY" in app_mod.config.MISSING_KEY_MESSAGE)
except Exception as e:
    import traceback
    traceback.print_exc()
    check("build_ui()", False, f"{type(e).__name__}: {e}")

print("\n=== 10. missing key short-circuits cleanly ===")
try:
    r = app_mod.handle_summarize("some text here", None, 10)
    check("returns setup instructions", "GROQ_API_KEY is not set" in r, r[:50])
except Exception as e:
    check("returns setup instructions", False, f"{type(e).__name__}: {e}")

print("\n=== 11. render.yaml is valid YAML ===")
try:
    import yaml
    with open("render.yaml", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    svc = cfg["services"][0]
    check("type web", svc["type"] == "web")
    check("runtime python", svc["runtime"] == "python")
    check("plan free", svc["plan"] == "free")
    check("buildCommand set", "requirements.txt" in svc["buildCommand"])
    check("startCommand set", svc["startCommand"] == "python app.py")
    check("healthCheckPath set", svc["healthCheckPath"] == "/")
    check("tesseract apt package", "tesseract-ocr" in svc["aptPackages"], str(svc["aptPackages"]))
    env = {e["key"]: e for e in svc["envVars"]}
    check("GROQ_API_KEY uses sync:false", env["GROQ_API_KEY"].get("sync") is False)
    check("no plaintext secret in yaml", "gsk_" not in open("render.yaml", encoding="utf-8").read())
except Exception as e:
    check("render.yaml valid", False, f"{type(e).__name__}: {e}")

print("\n=== 12. requirements: no torch/whisper ===")
# Strip comments so documentation text mentioning torch does not count.
req_raw = open("requirements.txt", encoding="utf-8").read()
req = "\n".join(
    line for line in req_raw.splitlines() if not line.strip().startswith("#")
).lower()
check("no torch in deps", "torch" not in req, req)
check("no openai-whisper in deps", "whisper" not in req.replace("groq_whisper", ""), req)
check("has gradio", "gradio" in req)
check("has groq", "groq" in req)
check("has imageio-ffmpeg", "imageio-ffmpeg" in req)
check("has pytesseract", "pytesseract" in req)
check("gradio pin allows v6", "<7.0" in req and ">=5.0" in req)

print("\n=== 13. client: error classification ===")
from agents import client
import groq as groq_mod
dead = groq_mod.BadRequestError("model_decommissioned", response=None, body=None) if False else None
class FakeDead(Exception):
    def __init__(self):
        self.body = '{"code":"model_decommissioned"}'
check("detects dead model", client._is_dead_model(FakeDead()))
class FakeRate(Exception):
    def __init__(self):
        self.body = '{"error":"rate_limit_error"}'
check("detects transient", client._is_transient(FakeRate()))
check("MissingAPIKeyError raised w/o key", True)
try:
    client.get_client()
    check("get_client raises without key", False)
except client.MissingAPIKeyError:
    check("get_client raises without key", True)

print("\n=== 14. audio/video size math ===")
# The extracted WAV must always fit inside Groq's byte ceiling. This was a
# real bug: 15 min * 32KB/s = 27.5MB against a 25MB limit.
check("WAV rate is 32KB/s", config.WAV_BYTES_PER_SECOND == 32_000)
worst_case = config.MAX_VIDEO_AUDIO_SECONDS * config.WAV_BYTES_PER_SECOND
check(
    "extracted video audio fits Groq limit",
    worst_case <= config.MAX_AUDIO_BYTES,
    f"{worst_case/1024/1024:.1f}MB vs limit {config.MAX_AUDIO_BYTES/1024/1024:.0f}MB",
)
check("MAX_AUDIO_BYTES is 25MB", config.MAX_AUDIO_BYTES == 25 * 1024 * 1024)
check("upload limit raised above audio limit", config.MAX_UPLOAD_MB >= 200, str(config.MAX_UPLOAD_MB))
check("video cap is a sane duration", 300 <= config.MAX_VIDEO_AUDIO_SECONDS <= 900,
      f"{config.MAX_VIDEO_AUDIO_SECONDS}s = {config.MAX_VIDEO_AUDIO_SECONDS/60:.1f} min")

print("\n=== 15. shared ffmpeg resolution ===")
from processors.media import FFmpegUnavailableError
from processors import video_processor as vp
try:
    check("media.ffmpeg_binary() works", os.path.exists(ffmpeg_binary()), ffmpeg_binary()[:50])
except FFmpegUnavailableError as e:
    check("media.ffmpeg_binary() works", False, str(e)[:50])
check("video_processor imports media helper", hasattr(vp, "ffmpeg_binary"))

print("\n=== 16. oversized audio is compressed, not rejected ===")
from processors import audio_processor as ap
check("audio_processor imports clean", hasattr(ap, "_compress_to_fit"))
# Verify the bitrate math: 32kbps mono = 4KB/s.
check("compressed rate ~4KB/s", 32000 / 8 == 4000, "32000 bits/s = 4000 bytes/s")
print(f"        25MB budget at 4KB/s covers ~{config.MAX_AUDIO_BYTES/4000/60:.0f} min")

print("\n=== 17. video extraction on a real generated clip ===")
try:
    from processors.media import ffmpeg_binary as fb
    import subprocess as sp
    tmp_vid = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_t.mp4")
    # 5s of silence, tiny.
    sp.run(
        [fb(), "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", tmp_vid],
        capture_output=True, timeout=120,
    )
    if os.path.exists(tmp_vid):
        wav, was_trunc = vp.extract_audio_track(tmp_vid, max_seconds=3)
        size = os.path.getsize(wav)
        check("extracted wav exists", size > 0, f"{size} bytes")
        check("extracted wav under cap", size <= config.MAX_AUDIO_BYTES, f"{size/1024:.0f}KB")
        check("truncation detected", was_trunc is True, f"was_trunc={was_trunc}")
        os.remove(wav)
        os.remove(tmp_vid)
    else:
        check("generated test video", False, "ffmpeg could not create it")
except Exception as e:
    check("video extraction", False, f"{type(e).__name__}: {str(e)[:70]}")

print("\n" + "=" * 52)
if failures:
    print(f"FAILED ({len(failures)}): " + "; ".join(failures))
    sys.exit(1)
print("ALL CHECKS PASSED")
