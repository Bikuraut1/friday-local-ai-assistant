from __future__ import annotations

import argparse
import json
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


def emit(data: dict, code: int = 0) -> int:
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return code


def cmd_extract(args: argparse.Namespace) -> int:
    parsed = urlparse(args.url)
    if parsed.scheme not in {"http", "https"}:
        return emit({"ok": False, "error": "Only http and https URLs are allowed."}, 2)
    response = requests.get(
        args.url,
        timeout=args.timeout,
        headers={"User-Agent": "FRIDAY-local-agent/1.0"},
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    text = " ".join(soup.get_text("\n", strip=True).split())
    return emit({
        "ok": True,
        "url": args.url,
        "status": response.status_code,
        "title": title,
        "text": text[: args.max_chars],
        "truncated": len(text) > args.max_chars,
    })


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FRIDAY web scraper")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("extract")
    p.add_argument("url")
    p.add_argument("--max-chars", type=int, default=12000)
    p.add_argument("--timeout", type=int, default=20)
    p.set_defaults(func=cmd_extract)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        return emit({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 1)


if __name__ == "__main__":
    raise SystemExit(main())
