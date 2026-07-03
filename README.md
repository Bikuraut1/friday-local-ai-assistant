# FRIDAY

FRIDAY is a local-first Windows AI assistant stack under `D:\Friday`, combining Ollama, Open WebUI, Qdrant/Mem0 memory, SearXNG search, Kokoro TTS, n8n automation, voice, routing, vision, dashboard, and a local agent tool layer.

## Prerequisites

- Windows 11 with PowerShell
- Docker Desktop running Linux containers
- Ollama installed and reachable at `http://127.0.0.1:11434`
- Existing local model/data directories under `D:\Friday`
- Service `.env` files present for n8n, Open WebUI, SearXNG, and RAG

## Start

Start the Docker layer:

```powershell
cd D:\Friday
.\start-stack.ps1
```

Start the full FRIDAY stack:

```powershell
cd D:\Friday
.\start-friday.ps1
```

## Status

Quick status:

```powershell
cd D:\Friday
.\status-friday.ps1
```

Full health report:

```powershell
cd D:\Friday
.\maintenance\health-report.ps1
```

Reports are written to:

```text
D:\Friday\maintenance\reports
```

## Stop

Stop Open WebUI only:

```powershell
cd D:\Friday
.\stop-friday.ps1
```

Stop all FRIDAY-managed services:

```powershell
cd D:\Friday
.\stop-friday.ps1 -StopOllama -StopMemory -StopRag -StopSearch -StopVoice -StopAutomation -StopVision -StopRouter -StopDashboard
```

## Modules

- [agent](agent/README.md)
- [voice](voice/README.md)
- [dashboard](dashboard/README.md)
- [rag](rag/README.md)
- [router](router/README.md)
- [vision](vision/README.md)
- [mem0](mem0/README.md)
- [searxng](searxng/README.md)
- [n8n](n8n/README.md)
- [knowledge-base](knowledge-base/README.md)
- [operations](maintenance/OPERATIONS.md)
- [phase report](FRIDAY_PHASE_1_TO_11_REPORT.md)

## Security Posture

Docker-published ports are bound to `127.0.0.1` only. Secrets for n8n, Open WebUI, SearXNG, and RAG are stored in local `.env` files with matching `.env.example` templates. Open WebUI still has `WEBUI_AUTH: "False"` and must not be exposed beyond loopback until authentication is enabled.

## GitHub Publishing

This repository is intended to publish source code, scripts, workflows, documentation, and `.env.example` templates only. Local secrets, service databases, logs, backups, recordings, screenshots, downloaded models, vector stores, and virtual environments are excluded through `.gitignore`.
