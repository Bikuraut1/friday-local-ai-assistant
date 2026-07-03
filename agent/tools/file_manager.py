from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import requests
from pypdf import PdfReader

from safe_paths import SafetyError, require_allowed_path


OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("FRIDAY_AGENT_MODEL", "friday:phi4")
DEFAULT_VISION_MODEL = os.environ.get("FRIDAY_VISION_MODEL", "llava:13b")


def emit(data: dict, code: int = 0) -> int:
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return code


def iter_matches(root: Path, pattern: str):
    for path in root.rglob(pattern):
        try:
            yield require_allowed_path(path, must_exist=True)
        except SafetyError:
            continue


def cmd_list(args: argparse.Namespace) -> int:
    root = require_allowed_path(args.root, must_exist=True)
    if not root.is_dir():
        return emit({"ok": False, "error": f"Not a directory: {root}"}, 2)
    items = []
    for child in sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))[: args.limit]:
        safe = require_allowed_path(child, must_exist=True)
        stat = safe.stat()
        items.append({
            "path": str(safe),
            "type": "directory" if safe.is_dir() else "file",
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        })
    return emit({"ok": True, "root": str(root), "items": items})


def cmd_search(args: argparse.Namespace) -> int:
    root = require_allowed_path(args.root, must_exist=True)
    if not root.is_dir():
        return emit({"ok": False, "error": f"Not a directory: {root}"}, 2)
    results = []
    for path in iter_matches(root, args.pattern):
        if len(results) >= args.limit:
            break
        if args.files_only and not path.is_file():
            continue
        stat = path.stat()
        results.append({
            "path": str(path),
            "type": "directory" if path.is_dir() else "file",
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        })
    return emit({"ok": True, "root": str(root), "pattern": args.pattern, "count": len(results), "results": results})


def cmd_largest(args: argparse.Namespace) -> int:
    root = require_allowed_path(args.root, must_exist=True)
    matches = [path for path in iter_matches(root, args.pattern) if path.is_file()]
    matches.sort(key=lambda p: p.stat().st_size, reverse=True)
    results = []
    for path in matches[: args.limit]:
        stat = path.stat()
        results.append({
            "path": str(path),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        })
    return emit({"ok": True, "root": str(root), "pattern": args.pattern, "count": len(results), "results": results})


def cmd_read(args: argparse.Namespace) -> int:
    path = require_allowed_path(args.path, must_exist=True)
    if not path.is_file():
        return emit({"ok": False, "error": f"Not a file: {path}"}, 2)
    text = path.read_text(encoding=args.encoding, errors="replace")
    truncated = len(text) > args.max_chars
    return emit({"ok": True, "path": str(path), "truncated": truncated, "text": text[: args.max_chars]})


def cmd_write(args: argparse.Namespace) -> int:
    path = require_allowed_path(args.path)
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.append else "w"
    with path.open(mode, encoding=args.encoding) as handle:
        handle.write(args.text)
    return emit({"ok": True, "path": str(path), "mode": "append" if args.append else "write", "bytes": path.stat().st_size})


def cmd_organize(args: argparse.Namespace) -> int:
    root = require_allowed_path(args.root, must_exist=True)
    if not root.is_dir():
        return emit({"ok": False, "error": f"Not a directory: {root}"}, 2)
    planned = []
    for path in root.iterdir():
        path = require_allowed_path(path, must_exist=True)
        if not path.is_file():
            continue
        ext = path.suffix.lower().lstrip(".") or "no-extension"
        dest_dir = require_allowed_path(root / ext)
        dest = require_allowed_path(dest_dir / path.name)
        if path == dest:
            continue
        planned.append({"from": str(path), "to": str(dest)})
        if args.apply:
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(dest))
    return emit({"ok": True, "root": str(root), "applied": args.apply, "moves": planned})


def extract_pdf_text(path: Path, max_pages: int, max_chars: int) -> str:
    reader = PdfReader(str(path))
    chunks = []
    for page in reader.pages[:max_pages]:
        chunks.append(page.extract_text() or "")
        if sum(len(chunk) for chunk in chunks) >= max_chars:
            break
    return "\n".join(chunks)[:max_chars].strip()


def summarize_with_ollama(text: str, model: str) -> str:
    prompt = (
        "Summarize this PDF for Boss in concise bullet points. "
        "Mention the likely topic, key facts, and any action items. "
        "If the extracted text is weak, say so.\n\n"
        f"{text}"
    )
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=180,
    )
    response.raise_for_status()
    return response.json().get("response", "").strip()


def render_pdf_pages(path: Path, max_pages: int) -> list[str]:
    import fitz

    images = []
    with tempfile.TemporaryDirectory(prefix="friday_pdf_") as temp_dir:
        doc = fitz.open(str(path))
        for index in range(min(max_pages, len(doc))):
            page = doc.load_page(index)
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            out = Path(temp_dir) / f"page-{index + 1}.jpg"
            pix.save(str(out))
            images.append(base64.b64encode(out.read_bytes()).decode("ascii"))
        doc.close()
    return images


def summarize_pdf_images_with_ollama(path: Path, model: str, max_pages: int) -> str:
    images = render_pdf_pages(path, max_pages)
    if not images:
        raise RuntimeError("No pages rendered from scanned PDF.")
    prompt = (
        "Summarize this scanned PDF for Boss in concise bullet points. "
        "Read the visible text if possible. Mention if the image quality limits accuracy."
    )
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": model, "prompt": prompt, "images": images, "stream": False},
        timeout=240,
    )
    response.raise_for_status()
    return response.json().get("response", "").strip()


def cmd_summarize_largest_pdf(args: argparse.Namespace) -> int:
    root = require_allowed_path(args.root, must_exist=True)
    pdfs = [path for path in iter_matches(root, "*.pdf") if path.is_file()]
    if not pdfs:
        return emit({"ok": False, "error": f"No PDF files found under {root}"}, 1)
    pdfs.sort(key=lambda p: p.stat().st_size, reverse=True)
    target = pdfs[0]
    text = extract_pdf_text(target, args.max_pages, args.max_chars)
    if text:
        summary = summarize_with_ollama(text, args.model)
        method = "text"
        model = args.model
    else:
        summary = summarize_pdf_images_with_ollama(target, args.vision_model, args.vision_pages)
        method = "vision"
        model = args.vision_model
    return emit({"ok": True, "path": str(target), "size": target.stat().st_size, "method": method, "model": model, "summary": summary})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FRIDAY safe file manager")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list")
    p.add_argument("root")
    p.add_argument("--limit", type=int, default=100)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("search")
    p.add_argument("root")
    p.add_argument("--pattern", default="*")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--files-only", action="store_true")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("largest")
    p.add_argument("root")
    p.add_argument("--pattern", default="*")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=cmd_largest)

    p = sub.add_parser("read")
    p.add_argument("path")
    p.add_argument("--max-chars", type=int, default=8000)
    p.add_argument("--encoding", default="utf-8")
    p.set_defaults(func=cmd_read)

    p = sub.add_parser("write")
    p.add_argument("path")
    p.add_argument("text")
    p.add_argument("--append", action="store_true")
    p.add_argument("--encoding", default="utf-8")
    p.set_defaults(func=cmd_write)

    p = sub.add_parser("organize")
    p.add_argument("root")
    p.add_argument("--apply", action="store_true", help="Actually move files. Without this, only prints planned moves.")
    p.set_defaults(func=cmd_organize)

    p = sub.add_parser("summarize-largest-pdf")
    p.add_argument("root")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--vision-model", default=DEFAULT_VISION_MODEL)
    p.add_argument("--vision-pages", type=int, default=2)
    p.add_argument("--max-pages", type=int, default=12)
    p.add_argument("--max-chars", type=int, default=24000)
    p.set_defaults(func=cmd_summarize_largest_pdf)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except SafetyError as exc:
        return emit({"ok": False, "error": str(exc)}, 3)
    except Exception as exc:
        return emit({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 4)


if __name__ == "__main__":
    raise SystemExit(main())
