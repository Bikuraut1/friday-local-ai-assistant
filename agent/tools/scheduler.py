from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime
from pathlib import Path


STATE_DIR = Path(r"D:\Friday\agent\state")
SCHEDULE_FILE = STATE_DIR / "schedule.json"


def emit(data: dict, code: int = 0) -> int:
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return code


def load_items() -> list[dict]:
    if not SCHEDULE_FILE.exists():
        return []
    return json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))


def save_items(items: list[dict]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    SCHEDULE_FILE.write_text(json.dumps(items, indent=2), encoding="utf-8")


def parse_due(value: str) -> str:
    try:
        return datetime.fromisoformat(value).isoformat(timespec="minutes")
    except ValueError as exc:
        raise ValueError("Use ISO time, for example 2026-06-27T18:30") from exc


def cmd_add(args: argparse.Namespace) -> int:
    items = load_items()
    item = {
        "id": str(uuid.uuid4()),
        "title": args.title,
        "due": parse_due(args.due),
        "notes": args.notes,
        "done": False,
        "created": datetime.now().isoformat(timespec="seconds"),
    }
    items.append(item)
    save_items(items)
    return emit({"ok": True, "item": item})


def cmd_list(args: argparse.Namespace) -> int:
    items = load_items()
    if not args.all:
        items = [item for item in items if not item.get("done")]
    items.sort(key=lambda item: item.get("due", ""))
    return emit({"ok": True, "items": items})


def cmd_due(args: argparse.Namespace) -> int:
    now = datetime.now()
    items = []
    for item in load_items():
        if item.get("done"):
            continue
        try:
            due = datetime.fromisoformat(item["due"])
        except Exception:
            continue
        if due <= now:
            items.append(item)
    return emit({"ok": True, "items": items})


def cmd_complete(args: argparse.Namespace) -> int:
    items = load_items()
    found = False
    for item in items:
        if item["id"].startswith(args.id):
            item["done"] = True
            item["completed"] = datetime.now().isoformat(timespec="seconds")
            found = True
            break
    if not found:
        return emit({"ok": False, "error": f"No item found for id prefix: {args.id}"}, 1)
    save_items(items)
    return emit({"ok": True})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FRIDAY local scheduler")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add")
    p.add_argument("title")
    p.add_argument("--due", required=True)
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("list")
    p.add_argument("--all", action="store_true")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("due")
    p.set_defaults(func=cmd_due)

    p = sub.add_parser("complete")
    p.add_argument("id")
    p.set_defaults(func=cmd_complete)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        return emit({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 1)


if __name__ == "__main__":
    raise SystemExit(main())
