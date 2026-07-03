from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import requests


ROOT = Path(os.getenv("FRIDAY_ROOT", "D:/Friday"))
ROUTER_ROOT = ROOT / "router"
LOG_DIR = ROUTER_ROOT / "logs"
DECISION_LOG = LOG_DIR / "routing-decisions.jsonl"

OLLAMA = os.getenv("FRIDAY_OLLAMA_URL", "http://localhost:11434")
HOST = os.getenv("FRIDAY_ROUTER_HOST", "127.0.0.1")
PORT = int(os.getenv("FRIDAY_ROUTER_PORT", "8790"))

PRIMARY_MODEL = os.getenv("FRIDAY_ROUTER_PRIMARY_MODEL", "friday:phi4")
REASONING_MODEL = os.getenv("FRIDAY_ROUTER_REASONING_MODEL", "llama3.1:70b-instruct-q4_K_M")
CODE_MODEL = os.getenv("FRIDAY_ROUTER_CODE_MODEL", PRIMARY_MODEL)
VISION_MODEL = os.getenv("FRIDAY_ROUTER_VISION_MODEL", "llava:13b")
CLASSIFIER_MODEL = os.getenv("FRIDAY_ROUTER_CLASSIFIER_MODEL", "qwen2.5:0.5b-instruct")

ROUTE_LABELS = {
    "simple_chat",
    "complex_reasoning",
    "code",
    "image",
    "quick_math",
    "lookup",
}

MODEL_BY_ROUTE = {
    "simple_chat": PRIMARY_MODEL,
    "complex_reasoning": REASONING_MODEL,
    "code": CODE_MODEL,
    "image": VISION_MODEL,
    "quick_math": PRIMARY_MODEL,
    "lookup": PRIMARY_MODEL,
}


def ensure_dirs() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def ollama_tags() -> set[str]:
    response = requests.get(f"{OLLAMA}/api/tags", timeout=10)
    response.raise_for_status()
    return {item["name"] for item in response.json().get("models", [])}


def model_available(model: str) -> bool:
    try:
        return model in ollama_tags()
    except Exception:
        return False


def normalize_label(value: str) -> str:
    label = re.sub(r"[^a-z_]", "", value.strip().lower().replace("-", "_"))
    return label if label in ROUTE_LABELS else "simple_chat"


def strong_guardrail(prompt: str, has_images: bool) -> tuple[str, str] | None:
    text = prompt.lower()
    if has_images:
        return "image", "image payload present"

    code_terms = [
        "write code",
        "debug",
        "traceback",
        "exception",
        "powershell",
        "python",
        "javascript",
        "typescript",
        "react",
        "dockerfile",
        "sql",
        "function",
        "class ",
        "compile error",
    ]
    if any(term in text for term in code_terms) or "```" in prompt:
        return "code", "code keyword matched"

    if re.fullmatch(r"[\s\d\.\+\-\*\/\(\)%=xX]+", prompt.strip()) or re.search(
        r"\b(calculate|what is|solve)\b.*[\d]+.*[\+\-\*\/%]", text
    ):
        return "quick_math", "math expression matched"

    image_terms = ["screenshot", "image", "photo", "picture", "screen", "analyze what is visible"]
    if any(term in text for term in image_terms):
        return "image", "vision keyword matched"

    reasoning_terms = [
        "deeply analyze",
        "tradeoff",
        "architecture",
        "strategy",
        "multi-step",
        "reason step by step",
        "compare and decide",
        "root cause",
        "design a plan",
        "complex",
    ]
    if any(term in text for term in reasoning_terms) and (
        len(prompt) > 60 or ("architecture" in text and ("tradeoff" in text or "strategy" in text))
    ):
        return "complex_reasoning", "complex reasoning keyword matched"

    lookup_terms = ["latest", "today", "current", "news", "price", "weather", "schedule"]
    if any(term in text for term in lookup_terms):
        return "lookup", "lookup/current keyword matched"

    return None


def classify_with_tiny_model(prompt: str) -> tuple[str, str, bool]:
    if not model_available(CLASSIFIER_MODEL):
        return "simple_chat", f"classifier model missing: {CLASSIFIER_MODEL}", False

    classifier_prompt = f"""Classify this user prompt for a local model router.
Return exactly one label from:
simple_chat, complex_reasoning, code, image, quick_math, lookup

Rules:
- code: programming, debugging, shell commands, scripts, software errors
- image: asks about image, photo, screenshot, screen, visual content
- quick_math: arithmetic or direct math lookup
- lookup: asks for current/latest/today/news/weather/price/schedule
- complex_reasoning: strategy, architecture, long analysis, multi-step reasoning
- simple_chat: normal chat or short factual answer

Prompt:
{prompt[:2000]}

Label:"""
    try:
        response = requests.post(
            f"{OLLAMA}/api/generate",
            json={
                "model": CLASSIFIER_MODEL,
                "prompt": classifier_prompt,
                "stream": False,
                "keep_alive": "30m",
                "options": {"temperature": 0, "num_predict": 8},
            },
            timeout=60,
        )
        response.raise_for_status()
        raw = response.json().get("response", "").strip()
        return normalize_label(raw.split()[0] if raw else ""), f"classifier={CLASSIFIER_MODEL} raw={raw!r}", True
    except Exception as exc:
        return "simple_chat", f"classifier failed: {type(exc).__name__}: {exc}", False


def route_prompt(prompt: str, images: list[str] | None = None) -> dict[str, Any]:
    images = images or []
    guardrail = strong_guardrail(prompt, bool(images))
    classifier_label, classifier_reason, classifier_used = classify_with_tiny_model(prompt)

    if guardrail:
        route, reason = guardrail
        reason = f"{reason}; {classifier_reason}"
    else:
        route = classifier_label
        reason = classifier_reason

    model = MODEL_BY_ROUTE.get(route, PRIMARY_MODEL)
    if not model_available(model):
        fallback = VISION_MODEL if route == "image" and model_available(VISION_MODEL) else PRIMARY_MODEL
        reason += f"; model {model} missing, fallback={fallback}"
        model = fallback

    decision = {
        "timestamp": now_iso(),
        "route": route,
        "model": model,
        "classifier_model": CLASSIFIER_MODEL,
        "classifier_used": classifier_used,
        "reason": reason,
        "has_images": bool(images),
        "prompt_preview": prompt[:240],
    }
    log_decision(decision)
    return decision


def log_decision(decision: dict[str, Any]) -> None:
    ensure_dirs()
    with DECISION_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(decision, ensure_ascii=False) + "\n")


def ollama_chat(prompt: str, model: str, *, system: str | None = None, num_predict: int = 400) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    response = requests.post(
        f"{OLLAMA}/api/chat",
        json={
            "model": model,
            "stream": False,
            "keep_alive": "30m",
            "options": {"temperature": 0.3, "num_predict": num_predict},
            "messages": messages,
        },
        timeout=600,
    )
    response.raise_for_status()
    return response.json()["message"]["content"].strip()


def ollama_vision(prompt: str, model: str, images: list[str], *, num_predict: int = 300) -> str:
    clean_images = []
    for image in images:
        if Path(image).exists():
            clean_images.append(base64.b64encode(Path(image).read_bytes()).decode("ascii"))
        else:
            clean_images.append(image)
    response = requests.post(
        f"{OLLAMA}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "images": clean_images,
            "stream": False,
            "keep_alive": "15m",
            "options": {"temperature": 0.2, "num_predict": num_predict},
        },
        timeout=600,
    )
    response.raise_for_status()
    return response.json().get("response", "").strip()


def answer(payload: dict[str, Any]) -> dict[str, Any]:
    prompt = str(payload.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("Missing prompt.")
    images = payload.get("images") or []
    if not isinstance(images, list):
        raise ValueError("images must be a list of base64 strings or local paths.")

    decision = route_prompt(prompt, images)
    started = time.perf_counter()
    if decision["route"] == "image":
        output = ollama_vision(prompt, decision["model"], images, num_predict=int(payload.get("num_predict", 300)))
    else:
        output = ollama_chat(
            prompt,
            decision["model"],
            system=str(payload.get("system") or "You are FRIDAY. Be concise, direct, and useful."),
            num_predict=int(payload.get("num_predict", 400)),
        )
    return {
        "ok": True,
        "decision": decision,
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "response": output,
    }


def read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("content-length") or "0")
    raw = handler.rfile.read(length) if length else b"{}"
    return json.loads(raw.decode("utf-8"))


class RouterHandler(BaseHTTPRequestHandler):
    server_version = "FRIDAYRouter/1.0"

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/health":
            try:
                models = ollama_tags()
                self._send(
                    200,
                    {
                        "ok": True,
                        "service": "friday-router",
                        "models": {
                            "primary": PRIMARY_MODEL in models,
                            "reasoning": REASONING_MODEL in models,
                            "code": CODE_MODEL in models,
                            "vision": VISION_MODEL in models,
                            "classifier": CLASSIFIER_MODEL in models,
                        },
                    },
                )
            except Exception as exc:
                self._send(503, {"ok": False, "error": str(exc)})
            return
        self._send(404, {"ok": False, "error": "Not found."})

    def do_POST(self) -> None:
        try:
            payload = read_json(self)
            prompt = str(payload.get("prompt", "")).strip()
            images = payload.get("images") or []
            if self.path == "/route":
                if not prompt:
                    raise ValueError("Missing prompt.")
                self._send(200, {"ok": True, "decision": route_prompt(prompt, images)})
                return
            if self.path == "/chat":
                self._send(200, answer(payload))
                return
            self._send(404, {"ok": False, "error": "Use POST /route or POST /chat."})
        except Exception as exc:
            self._send(400, {"ok": False, "error": f"{type(exc).__name__}: {exc}"})


def serve() -> None:
    ensure_dirs()
    server = ThreadingHTTPServer((HOST, PORT), RouterHandler)
    print(f"FRIDAY router online: http://{HOST}:{PORT}")
    server.serve_forever()


def cli_route(prompt: str, images: list[str] | None = None) -> int:
    print(json.dumps({"ok": True, "decision": route_prompt(prompt, images or [])}, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FRIDAY Phase 10 model router")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("serve")
    route = sub.add_parser("route")
    route.add_argument("prompt")
    route.add_argument("--image", action="append", default=[])
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "serve":
        serve()
        return 0
    if args.command == "route":
        return cli_route(args.prompt, args.image)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
