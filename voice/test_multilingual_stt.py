from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path


def transcribe_file(label: str, path: Path) -> dict[str, object]:
    import wake_listener

    started = time.perf_counter()
    text = wake_listener.transcribe("", path)
    return {
        "label": label,
        "file": str(path),
        "ok": bool(text),
        "language": wake_listener.LAST_DETECTED_STT_LANGUAGE,
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "text": text,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run FRIDAY local STT against English, Hindi, and Hinglish WAV files.")
    parser.add_argument("--english", required=True, type=Path)
    parser.add_argument("--hindi", required=True, type=Path)
    parser.add_argument("--hinglish", required=True, type=Path)
    parser.add_argument("--model", default=os.getenv("FRIDAY_LOCAL_WHISPER_MODEL", "medium"))
    parser.add_argument("--language", default=os.getenv("FRIDAY_STT_LANGUAGE", "auto"))
    args = parser.parse_args()

    os.environ["FRIDAY_STT_ENGINE"] = "local"
    os.environ["FRIDAY_LOCAL_WHISPER_MODEL"] = args.model
    os.environ["FRIDAY_STT_LANGUAGE"] = args.language

    paths = {
        "english": args.english,
        "hindi": args.hindi,
        "hinglish": args.hinglish,
    }
    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise SystemExit(f"Missing WAV file(s): {', '.join(missing)}")

    results = [transcribe_file(label, path) for label, path in paths.items()]
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0 if all(item["ok"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
