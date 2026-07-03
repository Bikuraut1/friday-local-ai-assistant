from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

import psutil


def emit(data: dict, code: int = 0) -> int:
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return code


def gpu_info() -> dict:
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return {"available": False, "reason": "nvidia-smi not found"}
    try:
        result = subprocess.run(
            [
                nvidia_smi,
                "--query-gpu=name,memory.total,memory.used,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        gpus = []
        for line in result.stdout.splitlines():
            name, total, used, util = [part.strip() for part in line.split(",")]
            gpus.append({
                "name": name,
                "memory_total_mb": int(total),
                "memory_used_mb": int(used),
                "utilization_percent": int(util),
            })
        return {"available": True, "gpus": gpus}
    except Exception as exc:
        return {"available": False, "reason": f"{type(exc).__name__}: {exc}"}


def cmd_summary(_: argparse.Namespace) -> int:
    mem = psutil.virtual_memory()
    disks = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except PermissionError:
            continue
        disks.append({
            "mount": part.mountpoint,
            "fstype": part.fstype,
            "total_gb": round(usage.total / (1024 ** 3), 2),
            "used_gb": round(usage.used / (1024 ** 3), 2),
            "free_gb": round(usage.free / (1024 ** 3), 2),
            "percent": usage.percent,
        })
    return emit({
        "ok": True,
        "cpu_percent": psutil.cpu_percent(interval=1),
        "cpu_count_logical": psutil.cpu_count(),
        "ram_total_gb": round(mem.total / (1024 ** 3), 2),
        "ram_used_gb": round(mem.used / (1024 ** 3), 2),
        "ram_percent": mem.percent,
        "gpu": gpu_info(),
        "disks": disks,
    })


def cmd_processes(args: argparse.Namespace) -> int:
    rows = []
    for proc in psutil.process_iter(["pid", "name", "username", "memory_info", "cpu_percent"]):
        try:
            info = proc.info
            rows.append({
                "pid": info["pid"],
                "name": info["name"],
                "user": info.get("username") or "",
                "rss_mb": round(info["memory_info"].rss / (1024 ** 2), 1),
                "cpu_percent": info.get("cpu_percent") or 0,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    rows.sort(key=lambda item: item["rss_mb"], reverse=True)
    return emit({"ok": True, "processes": rows[: args.limit]})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FRIDAY system info")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("summary")
    p.set_defaults(func=cmd_summary)
    p = sub.add_parser("processes")
    p.add_argument("--limit", type=int, default=15)
    p.set_defaults(func=cmd_processes)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        return emit({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 1)


if __name__ == "__main__":
    raise SystemExit(main())
