# FRIDAY Local AI Assistant

FRIDAY is a local-first Windows AI assistant stack. It combines Ollama, Open WebUI, Qdrant/Mem0 memory, local RAG, SearXNG search, Kokoro TTS, n8n automation, screenshot vision, a model router, a dashboard, and a guarded local agent tool layer.

The project is designed to run on your own machine. Secrets, databases, logs, recordings, vector stores, virtual environments, and downloaded model files are intentionally not committed.

## What You Get

- Local chat UI through Open WebUI
- Ollama-backed models with a FRIDAY system persona
- Long-term memory through Mem0 and Qdrant
- Personal document RAG with local embeddings and a local reranker
- Web search through SearXNG
- Voice input/output with openWakeWord, Whisper, and Kokoro TTS
- Screenshot understanding with `llava:13b`
- n8n workflows for local automation
- A dashboard for health, model, memory, and action status
- Windows PowerShell scripts for start, stop, status, backup, and cleanup

## Important Path Requirement

Most scripts and Docker volumes currently assume this exact path:

```text
D:\Friday
```

Clone the repo there for the smooth setup path. If you clone somewhere else, update the hardcoded `D:\Friday` paths in the PowerShell scripts and Compose files first.

## Prerequisites

- Windows 11
- PowerShell 7 recommended
- Git
- Docker Desktop with Linux containers
- Python 3.11 available as `py -3.11`
- Ollama installed and available as `ollama`
- A microphone if you want voice mode
- Enough disk space for local models and Docker data

Recommended Ollama models:

```powershell
ollama pull phi4:14b-q4_K_M
ollama pull nomic-embed-text
ollama pull llava:13b
ollama pull qwen2.5:0.5b-instruct
```

Optional large model for complex routing:

```powershell
ollama pull llama3.1:70b-instruct-q4_K_M
```

## 1. Clone

```powershell
git clone https://github.com/Bikuraut1/friday-local-ai-assistant.git D:\Friday
cd D:\Friday
```

Create FRIDAY's persona model:

```powershell
ollama create friday:phi4 -f .\ollama\modelfiles\friday-phi4.Modelfile
```

## 2. Create Local Environment Files

Copy the templates:

```powershell
Copy-Item .\n8n\.env.example .\n8n\.env
Copy-Item .\open-webui\.env.example .\open-webui\.env
Copy-Item .\rag\.env.example .\rag\.env
Copy-Item .\searxng\.env.example .\searxng\.env
Copy-Item .\voice\.env.example .\voice\.env
```

Edit the new `.env` files and replace every `replace-with-*` value.

Set `FRIDAY_OPENWEBUI_EMAIL` and `FRIDAY_OPENWEBUI_PASSWORD` in `n8n\.env` to the Open WebUI account FRIDAY should use. On first Open WebUI launch, create or use the same account there.

The same shared reranker key must be used in both places:

```text
open-webui\.env: RAG_EXTERNAL_RERANKER_API_KEY
rag\.env:        FRIDAY_RERANKER_API_KEY
```

Generate random values in PowerShell:

```powershell
function New-FridaySecret {
  $bytes = New-Object byte[] 32
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  [Convert]::ToBase64String($bytes)
}

New-FridaySecret
```

Security notes:

- Do not commit real `.env` files.
- Keep `N8N_ENCRYPTION_KEY` stable once n8n has been initialized. Changing it later can make saved n8n credentials unreadable.
- `AUDIO_TTS_OPENAI_API_KEY` is used against local Kokoro's OpenAI-compatible endpoint. Use any local placeholder value unless your setup requires something else.

## 3. Create Python Environments

Voice, dashboard, router, and vision share `voice\.venv`:

```powershell
py -3.11 -m venv D:\Friday\voice\.venv
D:\Friday\voice\.venv\Scripts\python.exe -m pip install --upgrade pip
D:\Friday\voice\.venv\Scripts\python.exe -m pip install -r D:\Friday\voice\requirements.txt
D:\Friday\voice\.venv\Scripts\python.exe -m pip install -r D:\Friday\dashboard\requirements.txt
D:\Friday\voice\.venv\Scripts\python.exe -m pip install -r D:\Friday\router\requirements.txt
D:\Friday\voice\.venv\Scripts\python.exe -m pip install -r D:\Friday\vision\requirements.txt
```

Memory and RAG reranker share `mem0\.venv`:

```powershell
py -3.11 -m venv D:\Friday\mem0\.venv
D:\Friday\mem0\.venv\Scripts\python.exe -m pip install --upgrade pip
D:\Friday\mem0\.venv\Scripts\python.exe -m pip install -r D:\Friday\mem0\requirements.txt
D:\Friday\mem0\.venv\Scripts\python.exe -m pip install -r D:\Friday\rag\requirements.txt
```

The optional agent tool layer uses `agent\.venv`:

```powershell
py -3.11 -m venv D:\Friday\agent\.venv
D:\Friday\agent\.venv\Scripts\python.exe -m pip install --upgrade pip
D:\Friday\agent\.venv\Scripts\python.exe -m pip install -r D:\Friday\agent\requirements.txt
```

## 4. Download Voice Models

These files are not committed because they are generated/downloaded artifacts.

```powershell
cd D:\Friday
.\voice\download-openwakeword-models.ps1
.\voice\download-whisper-models.ps1
```

Start Open WebUI once before downloading its internal Whisper cache:

```powershell
.\open-webui\pull-and-start-open-webui.ps1
.\voice\download-openwebui-whisper-models.ps1
```

By default, the wake listener uses the bundled `hey_jarvis` openWakeWord model. If you have a custom `hey_friday.onnx`, place it at:

```text
D:\Friday\voice\wakewords\hey_friday.onnx
```

Then set this in `voice\.env`:

```text
FRIDAY_USE_JARVIS_WAKE_WORD=0
```

## 5. Start FRIDAY

Make sure Docker Desktop is running.

Start the full stack:

```powershell
cd D:\Friday
.\start-friday.ps1
```

Main local URLs:

| Service | URL |
| --- | --- |
| Open WebUI | http://localhost:3000 |
| Dashboard | http://localhost:8888 |
| n8n | http://localhost:5678 |
| Memory bridge | http://localhost:8765 |
| RAG reranker | http://localhost:8770 |
| SearXNG | http://localhost:8081 |
| Kokoro TTS | http://localhost:8880 |
| Router | http://localhost:8790 |

Voice mode starts with `start-friday.ps1`. Say the configured wake phrase, then speak normally. Say `goodbye`, `stop listening`, or `go to sleep` to return to wake-word mode.

## 6. Verify

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

Targeted checks:

```powershell
.\mem0\test-memory.ps1
.\rag\test-rag.ps1
.\searxng\test-searxng.ps1
.\voice\test-tts.ps1
.\voice\test-openwakeword.ps1
.\router\test-router.ps1
.\dashboard\test-dashboard.ps1
.\vision\test-vision.ps1
.\n8n\test-n8n.ps1
```

Open WebUI RAG verification:

```powershell
.\rag\test-open-webui-rag.ps1
```

Expected test facts:

```text
VIGIL LANTERN
amber vector memory
```

## Common Workflows

Start only Docker-backed services:

```powershell
.\start-stack.ps1
```

Start the dashboard visibly:

```powershell
.\dashboard\start-dashboard.ps1 -Visible
```

Start the model router:

```powershell
.\router\start-router.ps1
```

Start screenshot vision hotkey:

```powershell
.\vision\start-vision-hotkey.ps1
```

Then press:

```text
Win + Shift + F
```

Start Open Interpreter agent mode:

```powershell
.\agent\start-interpreter.ps1
```

Import n8n workflows:

```powershell
.\n8n\import-workflows.ps1
```

## Stop

Stop only Open WebUI:

```powershell
.\stop-friday.ps1
```

Stop everything managed by FRIDAY scripts:

```powershell
.\stop-friday.ps1 -StopOllama -StopMemory -StopRag -StopSearch -StopVoice -StopAutomation -StopVision -StopRouter -StopDashboard
```

## Backups And Cleanup

Create a normal backup:

```powershell
.\maintenance\backup-friday.ps1
```

Preview cleanup without deleting files:

```powershell
.\maintenance\cleanup-friday.ps1 -DryRun
```

Run cleanup:

```powershell
.\maintenance\cleanup-friday.ps1
```

## Project Layout

```text
agent/          Open Interpreter wrapper and guarded local tools
dashboard/      Local status and action dashboard
knowledge-base/ Local document folders for personal RAG
maintenance/    Backup, cleanup, health, startup scripts
mem0/           Qdrant Compose, memory bridge, Open WebUI memory tool
n8n/            Local automation workflows and helper API
ollama/         Ollama startup and FRIDAY Modelfile
open-webui/     Open WebUI Compose and environment template
rag/            Local reranker and RAG verification scripts
router/         Model routing API
searxng/        Local search service
vision/         Screenshot analysis and hotkey listener
voice/          Wake listener, STT, TTS, voice tests
```

## What Is Not In Git

The repo excludes:

- `.env` files
- Docker databases and service state
- Qdrant vector storage
- Open WebUI data
- n8n data
- Ollama model blobs
- Whisper and wake-word model downloads
- voice recordings
- screenshots
- logs
- backups
- Python virtual environments

This keeps the public repository usable without leaking private local state.

## Troubleshooting

Docker commands fail:

```powershell
docker info
```

If this fails, start Docker Desktop and rerun `.\start-friday.ps1`.

Ollama is not reachable:

```powershell
ollama serve
Invoke-WebRequest http://localhost:11434/api/tags
```

Missing `friday:phi4`:

```powershell
ollama pull phi4:14b-q4_K_M
ollama create friday:phi4 -f D:\Friday\ollama\modelfiles\friday-phi4.Modelfile
```

Open WebUI starts slowly on first run:

```powershell
docker logs -f friday-open-webui
```

First boot can take time while images, assets, or model caches initialize.

Memory bridge fails after Docker restart:

```powershell
.\mem0\start-memory.ps1
.\mem0\test-memory.ps1
```

RAG reranker rejects requests:

```powershell
Get-Content .\rag\.env
Get-Content .\open-webui\.env
```

Confirm the reranker key is the same in both files.

Voice sounds wrong for English:

```text
FRIDAY_TTS_VOICE=af_bella
FRIDAY_TTS_FALLBACK_VOICE=bf_emma
FRIDAY_ALLOW_NON_ENGLISH_TTS=0
```

PowerShell blocks scripts:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Or run individual scripts with:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-friday.ps1
```

## Security

All published Docker ports are bound to `127.0.0.1`. Do not expose these services to your network or the internet until authentication and service hardening are reviewed.

Open WebUI currently has:

```text
WEBUI_AUTH=False
```

That is convenient for a single-user local machine, but unsafe for any exposed deployment.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
