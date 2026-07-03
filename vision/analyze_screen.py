from __future__ import annotations

import argparse
import base64
import ctypes
import io
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import sounddevice as sd
import soundfile as sf
from PIL import Image, ImageGrab


ROOT = Path(os.getenv("FRIDAY_ROOT", "D:/Friday"))
VISION_ROOT = ROOT / "vision"
SCREENSHOT_DIR = VISION_ROOT / "screenshots"
OUTPUT_DIR = VISION_ROOT / "logs"

OLLAMA = os.getenv("FRIDAY_OLLAMA_URL", "http://localhost:11434")
KOKORO = os.getenv("FRIDAY_KOKORO_URL", "http://localhost:8880/v1")
VISION_MODEL = os.getenv("FRIDAY_VISION_MODEL", "llava:13b")
TTS_MODEL = os.getenv("FRIDAY_TTS_MODEL", "kokoro")
TTS_VOICE = os.getenv("FRIDAY_TTS_VOICE", "af_bella")
TTS_FALLBACK_VOICE = os.getenv("FRIDAY_TTS_FALLBACK_VOICE", "bf_emma")
ALLOW_NON_ENGLISH_TTS = os.getenv("FRIDAY_ALLOW_NON_ENGLISH_TTS", "0").lower() in {"1", "true", "yes"}
DEFAULT_PROMPT = "Analyze what's on my screen. Summarize the visible content and mention any useful next action."


def ensure_dirs() -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def capture_screen() -> Path:
    ensure_dirs()
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

    image = ImageGrab.grab(all_screens=True)
    if image.mode != "RGB":
        image = image.convert("RGB")

    path = SCREENSHOT_DIR / f"screenshot-{timestamp()}.jpg"
    image.save(path, format="JPEG", quality=88, optimize=True)
    latest = SCREENSHOT_DIR / "latest.jpg"
    image.save(latest, format="JPEG", quality=88, optimize=True)
    return path


def encoded_image(path: Path, max_edge: int = 1800) -> str:
    image = Image.open(path).convert("RGB")
    width, height = image.size
    largest = max(width, height)
    if largest > max_edge:
        scale = max_edge / largest
        image = image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=88, optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def analyze_image(path: Path, prompt: str) -> str:
    started = time.perf_counter()
    payload = {
        "model": VISION_MODEL,
        "prompt": prompt,
        "images": [encoded_image(path)],
        "stream": False,
        "keep_alive": "15m",
        "options": {
            "temperature": 0.2,
            "num_predict": 260,
        },
    }
    response = requests.post(f"{OLLAMA}/api/generate", json=payload, timeout=300)
    response.raise_for_status()
    answer = response.json().get("response", "").strip()
    print(f"Vision model: {time.perf_counter() - started:.2f}s")
    return answer


def speak(text: str) -> None:
    spoken = text.strip()
    if not spoken:
        return
    if len(spoken) > 1100:
        spoken = spoken[:1100].rsplit(" ", 1)[0] + "."

    started = time.perf_counter()
    response = None
    last_error = None
    voices = [TTS_VOICE, TTS_FALLBACK_VOICE, "af_bella"]
    if not ALLOW_NON_ENGLISH_TTS:
        voices = [voice for voice in voices if re.match(r"^[ab][fm]_", voice or "")]
        if TTS_VOICE not in voices:
            print(f"TTS voice rejected for English speech: {TTS_VOICE}")
    for voice in dict.fromkeys(voice for voice in voices if voice):
        try:
            response = requests.post(
                f"{KOKORO}/audio/speech",
                json={
                    "model": TTS_MODEL,
                    "voice": voice,
                    "input": spoken,
                    "response_format": "wav",
                },
                timeout=180,
            )
            response.raise_for_status()
            if voice != TTS_VOICE:
                print(f"TTS fallback voice used: {voice}")
            break
        except Exception as exc:
            last_error = exc
            response = None
    if response is None:
        raise last_error or RuntimeError("No TTS voice was accepted.")
    data, sample_rate = sf.read(io.BytesIO(response.content), dtype="float32")
    sd.play(data, sample_rate)
    sd.wait()
    print(f"TTS+playback: {time.perf_counter() - started:.2f}s")


def write_latest(image_path: Path, prompt: str, answer: str) -> Path:
    ensure_dirs()
    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "model": VISION_MODEL,
        "image": str(image_path),
        "prompt": prompt,
        "answer": answer,
    }
    path = OUTPUT_DIR / "latest-analysis.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def run_once(prompt: str, *, no_speak: bool = False) -> str:
    image_path = capture_screen()
    print(f"Screenshot: {image_path}")
    answer = analyze_image(image_path, prompt)
    write_latest(image_path, prompt, answer)
    print("FRIDAY Vision:")
    print(answer)
    if not no_speak:
        speak(answer)
    return answer


def run_hotkey(prompt: str, *, no_speak: bool = False) -> None:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    hotkey_id = 1
    mod_shift = 0x0004
    mod_win = 0x0008
    mod_norepeat = 0x4000
    vk_f = ord("F")
    registered = user32.RegisterHotKey(None, hotkey_id, mod_shift | mod_win | mod_norepeat, vk_f)
    if not registered:
        raise RuntimeError(f"RegisterHotKey failed. Windows error: {kernel32.GetLastError()}")

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    class MSG(ctypes.Structure):
        _fields_ = [
            ("hwnd", ctypes.c_void_p),
            ("message", ctypes.c_uint),
            ("wParam", ctypes.c_void_p),
            ("lParam", ctypes.c_void_p),
            ("time", ctypes.c_ulong),
            ("pt", POINT),
        ]

    wm_hotkey = 0x0312
    msg = MSG()
    busy = False
    print("FRIDAY vision hotkey armed. Press Win + Shift + F.")
    try:
        while True:
            result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if result == 0:
                break
            if result == -1:
                raise RuntimeError("GetMessageW failed.")
            if msg.message == wm_hotkey and int(msg.wParam or 0) == hotkey_id:
                if busy:
                    print("Vision analysis already running; ignored duplicate hotkey.")
                    continue
                busy = True
                try:
                    run_once(prompt, no_speak=no_speak)
                except Exception as exc:
                    print(f"Vision analysis failed: {exc}", file=sys.stderr)
                finally:
                    busy = False
    finally:
        user32.UnregisterHotKey(None, hotkey_id)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FRIDAY screenshot vision assistant")
    parser.add_argument("--hotkey", action="store_true", help="Run persistent Win+Shift+F listener.")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--no-speak", action="store_true", help="Print analysis without TTS playback.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.hotkey:
            run_hotkey(args.prompt, no_speak=args.no_speak)
        else:
            run_once(args.prompt, no_speak=args.no_speak)
        return 0
    except Exception as exc:
        print(f"FRIDAY vision failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
