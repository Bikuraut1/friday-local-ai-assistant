from __future__ import annotations

import argparse
import json
import mailbox
import os
import smtplib
from email.message import EmailMessage

from safe_paths import SafetyError, require_allowed_path


SMTP_ENV = ["FRIDAY_SMTP_HOST", "FRIDAY_SMTP_PORT", "FRIDAY_SMTP_FROM"]


def emit(data: dict, code: int = 0) -> int:
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return code


def smtp_config() -> dict:
    return {
        "host": os.environ.get("FRIDAY_SMTP_HOST", ""),
        "port": int(os.environ.get("FRIDAY_SMTP_PORT", "25")),
        "from_addr": os.environ.get("FRIDAY_SMTP_FROM", ""),
        "user": os.environ.get("FRIDAY_SMTP_USER", ""),
        "password": os.environ.get("FRIDAY_SMTP_PASSWORD", ""),
        "starttls": os.environ.get("FRIDAY_SMTP_STARTTLS", "0") == "1",
    }


def cmd_check_config(_: argparse.Namespace) -> int:
    missing = [name for name in SMTP_ENV if not os.environ.get(name)]
    return emit({"ok": not missing, "missing": missing, "note": "Local SMTP send is disabled until missing variables are set."})


def cmd_send(args: argparse.Namespace) -> int:
    cfg = smtp_config()
    missing = [name for name in SMTP_ENV if not os.environ.get(name)]
    if missing:
        return emit({"ok": False, "error": f"Missing SMTP env vars: {', '.join(missing)}"}, 2)
    msg = EmailMessage()
    msg["From"] = cfg["from_addr"]
    msg["To"] = args.to
    msg["Subject"] = args.subject
    msg.set_content(args.body)
    with smtplib.SMTP(cfg["host"], cfg["port"], timeout=20) as smtp:
        if cfg["starttls"]:
            smtp.starttls()
        if cfg["user"]:
            smtp.login(cfg["user"], cfg["password"])
        smtp.send_message(msg)
    return emit({"ok": True, "to": args.to, "subject": args.subject})


def cmd_read_mbox(args: argparse.Namespace) -> int:
    try:
        path = require_allowed_path(args.path, must_exist=True)
    except SafetyError as exc:
        return emit({"ok": False, "error": str(exc)}, 3)
    box = mailbox.mbox(path)
    messages = []
    for index, msg in enumerate(reversed(list(box))):
        if index >= args.limit:
            break
        messages.append({
            "from": msg.get("from", ""),
            "to": msg.get("to", ""),
            "subject": msg.get("subject", ""),
            "date": msg.get("date", ""),
        })
    return emit({"ok": True, "path": str(path), "messages": messages})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FRIDAY local email helper")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check-config")
    p.set_defaults(func=cmd_check_config)

    p = sub.add_parser("send")
    p.add_argument("--to", required=True)
    p.add_argument("--subject", required=True)
    p.add_argument("--body", required=True)
    p.set_defaults(func=cmd_send)

    p = sub.add_parser("read-mbox")
    p.add_argument("path")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=cmd_read_mbox)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        return emit({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 1)


if __name__ == "__main__":
    raise SystemExit(main())
