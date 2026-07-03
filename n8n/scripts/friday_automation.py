from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import requests


ROOT = Path(os.getenv("FRIDAY_ROOT", "/friday"))
OUT_DIR = ROOT / "n8n" / "output"
STATE_DIR = ROOT / "n8n" / "state"
KNOWLEDGE_DIR = ROOT / "knowledge-base"

OLLAMA = os.getenv("FRIDAY_OLLAMA_URL", "http://host.docker.internal:11434")
OPEN_WEBUI = os.getenv("FRIDAY_OPEN_WEBUI_URL", "http://host.docker.internal:3000")
MEMORY = os.getenv("FRIDAY_MEMORY_BRIDGE_URL", "http://host.docker.internal:8765")
SEARXNG = os.getenv("FRIDAY_SEARXNG_URL", "http://host.docker.internal:8081/search")
MODEL = os.getenv("FRIDAY_MODEL", "friday:phi4")

MEMORY_CATEGORIES = [
    "USER_PROFILE",
    "GOALS",
    "PROJECTS",
    "PREFERENCES",
    "RELATIONSHIPS",
    "DECISIONS_MADE",
    "FOLLOW_UPS",
]


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required.")
    return value


def ensure_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def write_json(name: str, data: dict[str, Any]) -> Path:
    ensure_dirs()
    path = OUT_DIR / name
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def write_text(name: str, text: str) -> Path:
    ensure_dirs()
    path = OUT_DIR / name
    path.write_text(text, encoding="utf-8")
    return path


def request_json(method: str, url: str, **kwargs: Any) -> Any:
    response = requests.request(method, url, timeout=kwargs.pop("timeout", 45), **kwargs)
    response.raise_for_status()
    if not response.text:
        return {}
    return response.json()


def ollama_generate(prompt: str, *, model: str = MODEL, timeout: int = 180) -> str:
    data = request_json(
        "POST",
        f"{OLLAMA}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=timeout,
    )
    return str(data.get("response", "")).strip()


def memory_list(category: str | None = None, top_k: int = 20) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"top_k": top_k}
    if category:
        params["category"] = category
    try:
        data = request_json("GET", f"{MEMORY}/memory", params=params, timeout=30)
        return list(data.get("results") or [])
    except Exception:
        return []


def memory_add(text: str, category: str, source: str) -> dict[str, Any]:
    return request_json(
        "POST",
        f"{MEMORY}/memory",
        json={"text": text, "category": category, "source": source, "infer": False},
        timeout=60,
    )


def searx(query: str, count: int = 6) -> list[dict[str, str]]:
    try:
        data = request_json(
            "GET",
            SEARXNG,
            params={"q": query, "format": "json", "language": "en"},
            timeout=25,
        )
        results = []
        for item in list(data.get("results") or [])[:count]:
            results.append({
                "title": str(item.get("title", "")),
                "url": str(item.get("url", "")),
                "content": str(item.get("content", "")),
            })
        return results
    except Exception as exc:
        return [{"title": "Search unavailable", "url": "", "content": str(exc)}]


def compact_memory_items(items: list[dict[str, Any]]) -> str:
    lines = []
    for item in items:
        text = item.get("memory") or item.get("text") or item.get("content") or str(item)
        meta = item.get("metadata") or {}
        category = meta.get("category") or item.get("category") or "UNKNOWN"
        lines.append(f"- [{category}] {text}")
    return "\n".join(lines[:60])


def monday_briefing() -> int:
    today = datetime.now().strftime("%A, %Y-%m-%d %H:%M")
    memories = []
    for category in ["USER_PROFILE", "GOALS", "PROJECTS", "FOLLOW_UPS", "DECISIONS_MADE"]:
        memories.extend(memory_list(category=category, top_k=10))
    news = searx("India top news today", count=8)
    weather = searx("today weather near me", count=3)

    prompt = f"""You are FRIDAY preparing Boss's Monday briefing.
Date/time: {today}

Relevant memory:
{compact_memory_items(memories) or "- No memory returned."}

News search results:
{json.dumps(news, ensure_ascii=False, indent=2)}

Weather search results:
{json.dumps(weather, ensure_ascii=False, indent=2)}

Write a concise briefing with sections:
1. Priorities
2. Pending follow-ups
3. News that may matter
4. Weather note
5. Suggested first action
No filler. Address Boss directly.
"""
    briefing = ollama_generate(prompt)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    md_path = write_text(f"monday-briefing-{stamp}.md", briefing + "\n")
    json_path = write_json(
        "latest-monday-briefing.json",
        {"ok": True, "created_at": datetime.now(timezone.utc).isoformat(), "briefing_file": str(md_path), "briefing": briefing},
    )
    print(json.dumps({"ok": True, "briefing_file": str(md_path), "latest": str(json_path), "preview": briefing[:1000]}, ensure_ascii=False, indent=2))
    return 0


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def openwebui_token() -> str:
    email = os.getenv("FRIDAY_OPENWEBUI_EMAIL", "admin@localhost")
    password = required_env("FRIDAY_OPENWEBUI_PASSWORD")
    data = request_json(
        "POST",
        f"{OPEN_WEBUI}/api/v1/auths/signin",
        json={"email": email, "password": password},
        timeout=30,
    )
    token = data.get("token")
    if not token:
        raise RuntimeError("Open WebUI signin did not return a token.")
    return str(token)


def upload_to_openwebui(path: Path, token: str) -> dict[str, Any]:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    with path.open("rb") as handle:
        response = requests.post(
            f"{OPEN_WEBUI}/api/v1/files/?process=true&process_in_background=true",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (path.name, handle, mime)},
            timeout=180,
        )
    response.raise_for_status()
    return response.json()


def auto_ingest() -> int:
    ensure_dirs()
    state_file = STATE_DIR / "ingested-files.json"
    previous = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {}
    allowed = {".pdf", ".docx", ".txt", ".md"}
    candidates = [p for p in KNOWLEDGE_DIR.rglob("*") if p.is_file() and p.suffix.lower() in allowed]
    uploaded = []
    skipped = 0
    token = None
    for path in candidates:
        key = str(path)
        digest = file_hash(path)
        if previous.get(key, {}).get("sha256") == digest:
            skipped += 1
            continue
        if token is None:
            token = openwebui_token()
        result = upload_to_openwebui(path, token)
        previous[key] = {
            "sha256": digest,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "openwebui_id": result.get("id"),
        }
        uploaded.append({"path": key, "openwebui_id": result.get("id")})
    state_file.write_text(json.dumps(previous, indent=2, ensure_ascii=False), encoding="utf-8")
    output = {"ok": True, "uploaded": uploaded, "skipped": skipped, "state_file": str(state_file)}
    write_json("latest-auto-ingest.json", output)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def memory_consolidation() -> int:
    items = []
    for category in MEMORY_CATEGORIES:
        items.extend(memory_list(category=category, top_k=25))
    prompt = f"""Consolidate FRIDAY's long-term memory for Boss.

Raw memory:
{compact_memory_items(items) or "- No memory returned."}

Return:
- durable facts worth keeping
- duplicates or contradictions to review
- pending follow-ups
- project status summary
Keep it concise and operational.
"""
    summary = ollama_generate(prompt)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = write_text(f"memory-consolidation-{stamp}.md", summary + "\n")
    memory_add(f"Weekly memory consolidation created at {path}. Key summary: {summary[:1200]}", "DECISIONS_MADE", "n8n-memory-consolidation")
    output = {"ok": True, "summary_file": str(path), "summary": summary}
    write_json("latest-memory-consolidation.json", output)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def email_digest() -> int:
    briefing_file = OUT_DIR / "latest-monday-briefing.json"
    if briefing_file.exists():
        briefing = json.loads(briefing_file.read_text(encoding="utf-8")).get("briefing", "")
    else:
        briefing = "No Monday briefing has been generated yet."
    digest = ollama_generate(
        "Create a concise email digest for Boss from this briefing. Include subject and body.\n\n" + briefing,
        timeout=120,
    )
    path = write_text("latest-email-digest.txt", digest + "\n")

    smtp_host = os.getenv("FRIDAY_SMTP_HOST", "")
    smtp_from = os.getenv("FRIDAY_SMTP_FROM", "")
    smtp_to = os.getenv("FRIDAY_SMTP_TO", "")
    sent = False
    if smtp_host and smtp_from and smtp_to:
        msg = EmailMessage()
        msg["From"] = smtp_from
        msg["To"] = smtp_to
        msg["Subject"] = "FRIDAY digest"
        msg.set_content(digest)
        with smtplib.SMTP(smtp_host, int(os.getenv("FRIDAY_SMTP_PORT", "25")), timeout=20) as smtp:
            smtp.send_message(msg)
        sent = True
    output = {"ok": True, "digest_file": str(path), "sent": sent}
    write_json("latest-email-digest.json", output)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def status() -> int:
    checks = {}
    for name, url in {
        "ollama": f"{OLLAMA}/api/tags",
        "open_webui": f"{OPEN_WEBUI}/health",
        "memory": f"{MEMORY}/health",
    }.items():
        try:
            response = requests.get(url, timeout=8)
            checks[name] = {"ok": response.ok, "status_code": response.status_code}
        except Exception as exc:
            checks[name] = {"ok": False, "error": str(exc)}
    output = {"ok": all(item.get("ok") for item in checks.values()), "checks": checks}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["ok"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FRIDAY n8n automation runner")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("monday-briefing").set_defaults(func=lambda _: monday_briefing())
    sub.add_parser("auto-ingest").set_defaults(func=lambda _: auto_ingest())
    sub.add_parser("memory-consolidation").set_defaults(func=lambda _: memory_consolidation())
    sub.add_parser("email-digest").set_defaults(func=lambda _: email_digest())
    sub.add_parser("status").set_defaults(func=lambda _: status())
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return int(args.func(args))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
