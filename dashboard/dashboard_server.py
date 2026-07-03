from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import requests


ROOT = Path(os.getenv("FRIDAY_ROOT", "D:/Friday"))
DASHBOARD_ROOT = ROOT / "dashboard"
STATIC_ROOT = DASHBOARD_ROOT / "static"
LOG_ROOT = DASHBOARD_ROOT / "logs"

HOST = os.getenv("FRIDAY_DASHBOARD_HOST", "127.0.0.1")
PORT = int(os.getenv("FRIDAY_DASHBOARD_PORT", "8888"))

OLLAMA = os.getenv("FRIDAY_OLLAMA_URL", "http://localhost:11434")
OPEN_WEBUI = os.getenv("FRIDAY_OPEN_WEBUI_URL", "http://localhost:3000")
MEMORY = os.getenv("FRIDAY_MEMORY_BRIDGE_URL", "http://localhost:8765")
RERANKER = os.getenv("FRIDAY_RERANKER_URL", "http://localhost:8770")
SEARXNG = os.getenv("FRIDAY_SEARXNG_URL", "http://localhost:8081")
KOKORO = os.getenv("FRIDAY_KOKORO_URL", "http://localhost:8880/v1")
ROUTER = os.getenv("FRIDAY_ROUTER_URL", "http://localhost:8790")
N8N = os.getenv("FRIDAY_N8N_URL", "http://localhost:5678")
N8N_AUTOMATION = os.getenv("FRIDAY_N8N_AUTOMATION_URL", "http://localhost:8788")


def ensure_dirs() -> None:
    LOG_ROOT.mkdir(parents=True, exist_ok=True)


def http_status(url: str, timeout: float = 2.5) -> dict:
    try:
        response = requests.get(url, timeout=timeout)
        return {"ok": response.ok, "status": response.status_code}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def process_status(pattern: str) -> dict:
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "Get-CimInstance Win32_Process | "
            f"Where-Object {{ $_.ProcessId -ne $PID -and $_.CommandLine -like '*{pattern}*' }} | "
            "Select-Object -First 1 ProcessId,Name,CommandLine | ConvertTo-Json -Compress"
        ),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=4, check=False)
        output = result.stdout.strip()
        if not output:
            return {"ok": False, "error": "process not running"}
        data = json.loads(output)
        return {"ok": True, "pid": data.get("ProcessId"), "name": data.get("Name")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def post_status(url: str, timeout: int = 10) -> dict:
    try:
        response = requests.post(url, timeout=timeout)
        return {"ok": response.ok, "status": response.status_code, "body": safe_json(response)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def safe_json(response: requests.Response) -> object:
    try:
        return response.json()
    except Exception:
        return response.text[:500]


def ollama_models() -> dict:
    try:
        tags = requests.get(f"{OLLAMA}/api/tags", timeout=3).json().get("models", [])
        active = requests.get(f"{OLLAMA}/api/ps", timeout=3).json().get("models", [])
        return {
            "installed": [{"name": item.get("name"), "size": item.get("size"), "capabilities": item.get("capabilities", [])} for item in tags],
            "active": [
                {
                    "name": item.get("name"),
                    "size": item.get("size"),
                    "size_vram": item.get("size_vram"),
                    "expires_at": item.get("expires_at"),
                }
                for item in active
            ],
        }
    except Exception as exc:
        return {"installed": [], "active": [], "error": str(exc)}


def nvidia_vram() -> dict:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=4,
            check=True,
        )
        gpus = []
        for line in result.stdout.splitlines():
            parts = [part.strip() for part in line.split(",")]
            if len(parts) != 5:
                continue
            name, total, used, free, util = parts
            gpus.append(
                {
                    "name": name,
                    "total_mb": int(total),
                    "used_mb": int(used),
                    "free_mb": int(free),
                    "utilization_percent": int(util),
                }
            )
        return {"ok": True, "gpus": gpus}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "gpus": []}


def memory_snapshot() -> dict:
    try:
        all_items = requests.get(f"{MEMORY}/memory", params={"top_k": 100}, timeout=3).json().get("results", [])
        followups = requests.get(
            f"{MEMORY}/memory",
            params={"category": "FOLLOW_UPS", "top_k": 20},
            timeout=3,
        ).json().get("results", [])
        return {
            "ok": True,
            "count": len(all_items),
            "recent": simplify_memory(all_items[:6]),
            "followups": simplify_memory(followups[:8]),
        }
    except Exception as exc:
        return {"ok": False, "count": 0, "recent": [], "followups": [], "error": str(exc)}


def simplify_memory(items: list[dict]) -> list[dict]:
    rows = []
    for item in items:
        meta = item.get("metadata") or {}
        rows.append(
            {
                "text": item.get("memory") or item.get("text") or str(item),
                "category": meta.get("category") or item.get("category") or "UNKNOWN",
                "source": meta.get("source") or "",
                "updated_at": item.get("updated_at") or item.get("created_at") or "",
            }
        )
    return rows


def recent_conversations() -> list[dict]:
    candidates = [
        ROOT / "open-webui" / "data" / "webui.db",
        ROOT / "open-webui" / "data" / "data" / "webui.db",
    ]
    for db in candidates:
        if db.exists():
            return [{"title": "Open WebUI database found", "detail": str(db)}]
    return [{"title": "Open WebUI recent conversations", "detail": "Not exposed by local unauthenticated API."}]


def router_log() -> list[dict]:
    path = ROOT / "router" / "logs" / "routing-decisions.jsonl"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-8:]
    rows = []
    for line in lines:
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def service_snapshot() -> dict:
    checks = {
        "open_webui": (f"{OPEN_WEBUI}/health", 2.5),
        "ollama": (f"{OLLAMA}/api/tags", 3.0),
        "memory": (f"{MEMORY}/health", 2.5),
        "rag_reranker": (f"{RERANKER}/health", 2.5),
        "searxng": (SEARXNG, 2.5),
        "kokoro": (f"{KOKORO}/models", 2.5),
        "n8n": (f"{N8N}/healthz", 2.5),
        "n8n_automation": (f"{N8N_AUTOMATION}/health", 2.5),
        "router": (f"{ROUTER}/health", 2.5),
        "dashboard": (f"http://{HOST}:{PORT}/health", 2.5),
    }
    with ThreadPoolExecutor(max_workers=len(checks)) as pool:
        futures = {name: pool.submit(http_status, url, timeout) for name, (url, timeout) in checks.items()}
        services = {name: future.result() for name, future in futures.items()}
    services["wake_listener"] = process_status("wake_listener.py")
    services["vision_hotkey"] = process_status("analyze_screen.py")
    return services


def dashboard_state() -> dict:
    with ThreadPoolExecutor(max_workers=4) as pool:
        services_future = pool.submit(service_snapshot)
        models_future = pool.submit(ollama_models)
        vram_future = pool.submit(nvidia_vram)
        memory_future = pool.submit(memory_snapshot)
        services = services_future.result()
        models = models_future.result()
        vram = vram_future.result()
        memory = memory_future.result()
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "services": services,
        "models": models,
        "vram": vram,
        "memory": memory,
        "routing": router_log(),
        "conversations": recent_conversations(),
    }


def run_action(name: str) -> dict:
    if name == "monday_briefing":
        return post_status(f"{N8N}/webhook/friday/monday-briefing", timeout=240)
    if name == "memory_consolidation":
        return post_status(f"{N8N}/webhook/friday/memory-consolidation", timeout=240)
    if name == "router_health":
        return http_status(f"{ROUTER}/health")
    if name == "vision_latest":
        latest = ROOT / "vision" / "logs" / "latest-analysis.json"
        if not latest.exists():
            return {"ok": False, "error": "No vision analysis has been created yet."}
        return {"ok": True, "body": json.loads(latest.read_text(encoding="utf-8"))}
    if name == "health_report":
        return run_script(ROOT / "maintenance" / "health-report.ps1", timeout=90)
    if name == "backup_standard":
        return run_script(ROOT / "maintenance" / "backup-friday.ps1", timeout=180)
    if name == "start_voice":
        return run_script(ROOT / "voice" / "start-voice.ps1", timeout=240)
    if name == "stop_voice":
        return run_script(ROOT / "voice" / "stop-voice.ps1", timeout=90)
    if name == "start_router":
        return run_script(ROOT / "router" / "start-router.ps1", timeout=90)
    if name == "stop_router":
        return run_script(ROOT / "router" / "stop-router.ps1", timeout=90)
    if name == "start_vision":
        return run_script(ROOT / "vision" / "start-vision-hotkey.ps1", timeout=90)
    if name == "stop_vision":
        return run_script(ROOT / "vision" / "stop-vision-hotkey.ps1", timeout=90)
    return {"ok": False, "error": f"Unknown action: {name}"}


def run_script(path: Path, timeout: int = 120) -> dict:
    if not path.exists():
        return {"ok": False, "error": f"Missing script: {path}"}
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(path)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout[-6000:],
            "stderr": result.stderr[-6000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "error": f"Timed out after {timeout} seconds",
            "stdout": (exc.stdout or "")[-3000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-3000:] if isinstance(exc.stderr, str) else "",
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def websocket_accept_key(key: str) -> str:
    guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    digest = hashlib.sha1((key + guid).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


def send_ws_text(sock: socket.socket, payload: dict) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    header = bytearray([0x81])
    length = len(data)
    if length < 126:
        header.append(length)
    elif length < 65536:
        header.extend([126, (length >> 8) & 255, length & 255])
    else:
        header.extend([127])
        header.extend(length.to_bytes(8, "big"))
    sock.sendall(header + data)


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "FRIDAYDashboard/1.0"

    def log_message(self, fmt: str, *args) -> None:
        return

    def send_json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/ws":
            self.handle_ws()
            return
        if parsed.path == "/api/status":
            self.send_json(200, dashboard_state())
            return
        if parsed.path == "/health":
            self.send_json(200, {"ok": True, "service": "friday-dashboard"})
            return
        path = "index.html" if parsed.path in {"", "/"} else parsed.path.lstrip("/")
        file_path = (STATIC_ROOT / path).resolve()
        if not str(file_path).startswith(str(STATIC_ROOT.resolve())) or not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content = file_path.read_bytes()
        mime = "text/html; charset=utf-8"
        if file_path.suffix == ".css":
            mime = "text/css; charset=utf-8"
        elif file_path.suffix == ".js":
            mime = "application/javascript; charset=utf-8"
        self.send_response(200)
        self.send_header("content-type", mime)
        self.send_header("content-length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/action":
            self.send_json(404, {"ok": False, "error": "Not found"})
            return
        length = int(self.headers.get("content-length") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
            self.send_json(200, run_action(str(payload.get("action", ""))))
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})

    def handle_ws(self) -> None:
        key = self.headers.get("Sec-WebSocket-Key")
        if not key:
            self.send_error(400, "Missing Sec-WebSocket-Key")
            return
        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", websocket_accept_key(key))
        self.end_headers()
        sock = self.connection
        try:
            while True:
                send_ws_text(sock, dashboard_state())
                time.sleep(3)
        except Exception:
            return


def serve() -> None:
    ensure_dirs()
    server = ThreadingHTTPServer((HOST, PORT), DashboardHandler)
    print(f"FRIDAY dashboard online: http://localhost:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    serve()
