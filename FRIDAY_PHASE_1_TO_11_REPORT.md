# FRIDAY Local AI Assistant Project Report

Generated: 2026-06-28 20:55 IST  
Project root: `D:\Friday`  
Target reader: ChatGPT or another AI systems reviewer  
Owner/user: Biku Raut  
System goal: Fully local personal AI assistant named FRIDAY, built phase-by-phase on Windows 11 with local models, memory, RAG, web search, voice, tools, automation, vision, routing, and dashboard.

## Executive Summary

FRIDAY is a local-first Windows AI assistant stack. It uses Ollama for local inference, Open WebUI for browser chat, Mem0 and Qdrant for long-term memory, Open WebUI RAG plus local reranking for document knowledge, SearXNG for live web search, openWakeWord plus Whisper/Kokoro for voice, Open Interpreter/tool scripts for agentic actions, n8n for automation, LLaVA for vision, a Python model router for intelligence routing, and a local dashboard for monitoring.

The full requested roadmap has been completed through Phase 11. A post-roadmap maintenance layer was also added with health reporting, backup, startup installation, and an operations runbook.

Sensitive credentials and tokens are intentionally omitted from this report.

## Current Live Status

Latest health report:

```text
D:\Friday\maintenance\reports\friday-health-20260628-205352.json
Endpoints OK: 11/11
```

Latest dashboard status snapshot:

```text
D:\Friday\maintenance\reports\latest-dashboard-status.json
Timestamp: 2026-06-28T20:53:48
```

Current local service health from dashboard:

```text
Open WebUI:      OK, HTTP 200
Ollama:          OK, HTTP 200
Memory bridge:   OK, HTTP 200
RAG reranker:    OK, HTTP 200
SearXNG:         OK, HTTP 200
Kokoro TTS:      OK, HTTP 200
n8n:             OK, HTTP 200
n8n automation:  OK, HTTP 200
Router:          OK, HTTP 200
```

GPU snapshot:

```text
GPU: NVIDIA GeForce RTX 3070
VRAM total: 8192 MB
VRAM used at snapshot: 1772 MB
VRAM free at snapshot: 6246 MB
GPU utilization at snapshot: 0%
```

Installed Ollama models:

```text
qwen2.5:0.5b-instruct           397 MB
nomic-embed-text:latest         274 MB
friday:phi4                     9.1 GB
llava:13b                       8.0 GB
llama3.1:70b-instruct-q4_K_M    42 GB
phi4:14b-q4_K_M                 9.1 GB
```

Running Docker containers:

```text
friday-open-webui       openwebui/open-webui:latest
friday-n8n              n8nio/n8n:latest
friday-n8n-automation   node:22-alpine
friday-kokoro           ghcr.io/remsky/kokoro-fastapi-cpu:latest
friday-searxng          searxng/searxng:latest
friday-qdrant           qdrant/qdrant:latest
```

Primary URLs:

```text
Open WebUI:      http://localhost:3000
Ollama:          http://localhost:11434
Memory bridge:   http://localhost:8765
Qdrant:          http://localhost:6333
RAG reranker:    http://localhost:8770
SearXNG:         http://localhost:8081
Kokoro TTS:      http://localhost:8880
n8n:             http://localhost:5678
n8n automation:  http://localhost:8788
Model router:    http://localhost:8790
Dashboard:       http://localhost:8888
```

## Repository Layout

```text
D:\Friday
  agent\             Phase 7 Open Interpreter tooling and safe scripts
  dashboard\         Phase 11 dashboard
  knowledge-base\    Phase 4 local document folder
  maintenance\       Post-roadmap health, backup, startup, operations scripts
  mem0\              Phase 3 memory bridge and Qdrant storage
  n8n\               Phase 8 automation workflows and API bridge
  ollama\            Phase 1 model storage and Modelfile
  open-webui\        Phase 2 Open WebUI compose and persistent data
  rag\               Phase 4 reranker and RAG tests
  router\            Phase 10 model router
  searxng\           Phase 5 local search
  vision\            Phase 9 screenshot analysis
  voice\             Phase 6 wake word, STT, TTS, voice loop
  start-friday.ps1   Main startup script
  status-friday.ps1  Main status script
  stop-friday.ps1    Main stop script
```

## Phase 1 - Core Engine

What was built:

- Ollama installed and configured for local model serving.
- Models installed for primary chat, secondary reasoning, vision, and embeddings.
- A custom `friday:phi4` model was created for the FRIDAY persona.

Models:

```text
Primary:    friday:phi4 and phi4:14b-q4_K_M
Secondary:  llama3.1:70b-instruct-q4_K_M
Vision:     llava:13b
Embedding:  nomic-embed-text:latest
Classifier: qwen2.5:0.5b-instruct
```

Important files:

```text
D:\Friday\ollama\start-ollama-d.ps1
D:\Friday\ollama\modelfiles\friday-phi4.Modelfile
D:\Friday\ollama\models\
```

Verification:

```powershell
ollama list
Invoke-WebRequest http://localhost:11434/api/tags
```

Status:

```text
Complete. Ollama is reachable and all required models are installed.
```

Notes:

- Llama 70B is present but heavy. It is routed only for complex reasoning.
- VRAM cap is practical rather than hard-enforced by a central scheduler. The router and model choices are designed to avoid unnecessary 70B usage.

## Phase 2 - Interface: Open WebUI

What was built:

- Open WebUI installed with Docker Desktop.
- Connected to local Ollama backend.
- Configured for local RAG, web search, local STT/TTS integration, and FRIDAY defaults.

Important files:

```text
D:\Friday\open-webui\docker-compose.yml
D:\Friday\open-webui\data\webui.db
```

Container:

```text
friday-open-webui
Image: openwebui/open-webui:latest
Port: 3000 -> 8080
Restart policy: unless-stopped
```

Important configuration:

```text
OLLAMA_BASE_URL=http://host.docker.internal:11434
DEFAULT_MODELS=friday:phi4
TASK_MODEL=friday:phi4
WEBUI_NAME=FRIDAY
WEBUI_AUTH=False
```

Status:

```text
Complete. Open WebUI is reachable at http://localhost:3000.
```

Implementation note:

- The originally requested GHCR image pull stalled, so the reliable image used is `openwebui/open-webui:latest`.

## Phase 3 - Long-Term Memory: Mem0 + Qdrant

What was built:

- Local Qdrant vector database.
- Python memory bridge exposing a local API at `http://localhost:8765`.
- Structured memory categories for FRIDAY.
- Memory startup persistence.

Memory categories:

```text
USER_PROFILE
GOALS
PROJECTS
PREFERENCES
RELATIONSHIPS
DECISIONS_MADE
FOLLOW_UPS
```

Important files:

```text
D:\Friday\mem0\docker-compose.yml
D:\Friday\mem0\start-memory.ps1
D:\Friday\mem0\stop-memory.ps1
D:\Friday\mem0\start-memory-on-login.ps1
D:\Friday\mem0\install-memory-startup-task.ps1
D:\Friday\mem0\bridge\memory_bridge.py
D:\Friday\mem0\open-webui-tool-friday-memory.py
D:\Friday\mem0\qdrant\storage\
```

Container:

```text
friday-qdrant
Image: qdrant/qdrant:latest
Ports: 6333, 6334
Restart policy: unless-stopped
```

Current memory snapshot:

```text
Memory count: 3
Known user profile: Boss's name is Biku Raut.
Known preference: concise, direct answers with exact commands.
Follow-ups: none
```

Status:

```text
Complete. Memory bridge is live and recall works.
```

Known issue addressed:

- Voice previously logged memory bridge connection failures. Startup scripts and status checks were improved so memory is started as part of the full FRIDAY stack.

## Phase 4 - Personal Knowledge Base: RAG

What was built:

- Local folder-based knowledge base at `D:\Friday\knowledge-base`.
- Open WebUI RAG connected to Qdrant.
- Hybrid semantic plus keyword retrieval configured.
- External local reranker service added.
- Automated RAG verification scripts added.

Important files:

```text
D:\Friday\knowledge-base\
D:\Friday\rag\reranker.py
D:\Friday\rag\start-rag.ps1
D:\Friday\rag\stop-reranker.ps1
D:\Friday\rag\test-rag.ps1
D:\Friday\rag\test-open-webui-rag.ps1
D:\Friday\rag\README.md
```

RAG configuration in Open WebUI:

```text
VECTOR_DB=qdrant
QDRANT_URI=http://host.docker.internal:6333
QDRANT_COLLECTION_PREFIX=friday-rag
ENABLE_RAG_HYBRID_SEARCH=True
RAG_HYBRID_BM25_WEIGHT=0.45
RAG_EMBEDDING_ENGINE=ollama
RAG_EMBEDDING_MODEL=nomic-embed-text
RAG_RERANKING_ENGINE=external
RAG_EXTERNAL_RERANKER_URL=http://host.docker.internal:8770/v1/rerank
```

Status:

```text
Complete. RAG reranker is live at http://localhost:8770 and Qdrant collections are present.
```

Known behavior:

- Voice retrieval is intent-gated to avoid injecting irrelevant document snippets into casual prompts.

## Phase 5 - Live Web Search

What was built:

- Local SearXNG instance through Docker.
- Open WebUI search integration configured.
- Voice path can use live search/news logic for current information.

Important files:

```text
D:\Friday\searxng\docker-compose.yml
D:\Friday\searxng\settings.yml
D:\Friday\searxng\start-searxng.ps1
D:\Friday\searxng\test-searxng.ps1
D:\Friday\searxng\test-open-webui-search.ps1
D:\Friday\searxng\README.md
```

Container:

```text
friday-searxng
Image: searxng/searxng:latest
Port: 8081 -> 8080
Restart policy: unless-stopped
```

Open WebUI search configuration:

```text
ENABLE_WEB_SEARCH=True
WEB_SEARCH_ENGINE=searxng
SEARXNG_QUERY_URL=http://host.docker.internal:8081/search?q=<query>&format=json
WEB_SEARCH_RESULT_COUNT=5
```

Status:

```text
Complete. SearXNG is live at http://localhost:8081.
```

Known behavior:

- Voice news output was tuned to avoid incomplete or headline-only responses. It still depends on the quality of search/RSS results.

## Phase 6 - Voice Interface

What was built:

- Wake-word listener using openWakeWord.
- Jarvis wake-word mode is currently active because it was more reliable than the custom Friday wake model.
- Open WebUI Whisper STT integration.
- Kokoro local TTS through Docker.
- Voice loop with memory, RAG, web/news, router, command handling, and audio ducking.

Current wake phrase:

```text
Hey Jarvis
```

Important files:

```text
D:\Friday\voice\wake_listener.py
D:\Friday\voice\start-voice.ps1
D:\Friday\voice\stop-voice.ps1
D:\Friday\voice\wakewords\openwakeword\hey_jarvis_v0.1.onnx
D:\Friday\voice\wakewords\hey_friday.onnx
D:\Friday\voice\kokoro\docker-compose.yml
D:\Friday\voice\README.md
```

Kokoro container:

```text
friday-kokoro
Image: ghcr.io/remsky/kokoro-fastapi-cpu:latest
Port: 8880 -> 8880
Restart policy: unless-stopped
```

Whisper configuration:

```text
WHISPER_MODEL=medium.en
WHISPER_COMPUTE_TYPE=int8
WHISPER_LANGUAGE=en
WHISPER_MULTILINGUAL=False
```

Important voice tuning history:

- Custom `Hey Friday` ONNX models were tested.
- The project rolled back to bundled Jarvis wake model for reliability.
- `large-v3-turbo` STT was attempted but caused Open WebUI transcription HTTP 500, so the system rolled back to `medium.en`.
- Audio ducking was added so music/browser audio is lowered when FRIDAY listens.
- Media commands were added or prepared for actions like open YouTube, open Chrome, play, pause, resume, and specific song/singer requests.

Status:

```text
Complete and operational, but wake-word reliability and STT latency remain the most user-visible tuning areas.
```

## Phase 7 - Agentic Tool Use: Open Interpreter + Tool Scripts

What was built:

- Open Interpreter local setup connected to Ollama.
- Safe execution boundaries for allowed folders.
- Tool scripts for files, web scraping, email, scheduler, and system info.

Important files:

```text
D:\Friday\agent\start-interpreter.ps1
D:\Friday\agent\test-phase7.ps1
D:\Friday\agent\FRIDAY_AGENT_SYSTEM_PROMPT.md
D:\Friday\agent\tools\file_manager.py
D:\Friday\agent\tools\web_scraper.py
D:\Friday\agent\tools\email_handler.py
D:\Friday\agent\tools\scheduler.py
D:\Friday\agent\tools\sysinfo.py
D:\Friday\agent\tools\safe_paths.py
D:\Friday\agent\README.md
```

Safety model:

```text
Allowed workspace: D:\Friday and user-safe working folders as configured.
Blocked: unsafe system paths such as System32, registry-like operations, boot/system areas.
```

Status:

```text
Complete. Phase 7 tests passed except email requires real SMTP/application credentials.
```

Security note:

- Plaintext email passwords should not be stored in project files. Use environment variables or a proper local secret manager.

## Phase 8 - Automation Engine: n8n

What was built:

- Local n8n container.
- Local automation API bridge.
- Workflows for briefing, knowledge ingestion, memory consolidation, and email digest.

Important files:

```text
D:\Friday\n8n\docker-compose.yml
D:\Friday\n8n\start-n8n.ps1
D:\Friday\n8n\stop-n8n.ps1
D:\Friday\n8n\test-n8n.ps1
D:\Friday\n8n\import-workflows.ps1
D:\Friday\n8n\scripts\automation_api.mjs
D:\Friday\n8n\scripts\friday_automation.mjs
D:\Friday\n8n\scripts\friday_automation.py
D:\Friday\n8n\workflows\
D:\Friday\n8n\output\
D:\Friday\n8n\README.md
```

Containers:

```text
friday-n8n
friday-n8n-automation
```

Workflows:

```text
FRIDAY - Monday Morning Briefing
FRIDAY - Auto Ingest Knowledge Base
FRIDAY - Weekly Memory Consolidation
FRIDAY - Email Digest Pipeline
```

Status:

```text
Complete. n8n is live at http://localhost:5678 and the automation bridge is live at http://localhost:8788.
```

Security note:

- Any email credentials previously supplied interactively are not included in this report. Review n8n credentials manually inside n8n if email sending/reading is needed.

## Phase 9 - Vision: Screenshot and Image Understanding

What was built:

- Local screenshot analyzer using LLaVA 13B through Ollama.
- Windows hotkey script for screen capture and analysis.
- Voice output through Kokoro.

Important files:

```text
D:\Friday\vision\analyze_screen.py
D:\Friday\vision\start-vision-hotkey.ps1
D:\Friday\vision\stop-vision-hotkey.ps1
D:\Friday\vision\test-vision.ps1
D:\Friday\vision\screenshots\
D:\Friday\vision\logs\latest-analysis.json
D:\Friday\vision\README.md
```

Hotkey:

```text
Win + Shift + F
```

Prompt used:

```text
Analyze what's on my screen.
```

Status:

```text
Complete. Vision hotkey and screenshot analysis were verified.
```

## Phase 10 - Model Router

What was built:

- Python routing layer to select models by request type.
- Tiny classifier model added.
- Routing logs for review.
- Voice chat integrated with router.

Important files:

```text
D:\Friday\router\model_router.py
D:\Friday\router\start-router.ps1
D:\Friday\router\stop-router.ps1
D:\Friday\router\test-router.ps1
D:\Friday\router\logs\routing-decisions.jsonl
D:\Friday\router\README.md
```

Router endpoint:

```text
http://localhost:8790
```

Routing policy:

```text
Simple Q&A/chat:      friday:phi4
Complex reasoning:    llama3.1:70b-instruct-q4_K_M
Code/debug:           friday:phi4
Image analysis:       llava:13b
Quick math/lookup:    friday:phi4
Classifier:           qwen2.5:0.5b-instruct
```

Recent verified routing decisions:

```text
Who are you? -> simple_chat -> friday:phi4
Architecture tradeoffs -> complex_reasoning -> llama3.1:70b-instruct-q4_K_M
Debug traceback -> code -> friday:phi4
Analyze screenshot -> image -> llava:13b
Calculate 27 * 38 + 14 -> quick_math -> friday:phi4
```

Status:

```text
Complete. Router is live and logs routing decisions.
```

Known design tradeoff:

- The classifier is intentionally small and fast, but keyword safeguards still override it for obvious code, vision, math, and complex reasoning prompts.

## Phase 11 - Dashboard

What was built:

- Local HTML/JS dashboard at `http://localhost:8888`.
- Python backend with REST and WebSocket endpoints.
- Real-time local status display for services, models, VRAM, memory, recent routes, conversation availability, and quick actions.

Important files:

```text
D:\Friday\dashboard\dashboard_server.py
D:\Friday\dashboard\static\index.html
D:\Friday\dashboard\static\styles.css
D:\Friday\dashboard\static\app.js
D:\Friday\dashboard\start-dashboard.ps1
D:\Friday\dashboard\stop-dashboard.ps1
D:\Friday\dashboard\test-dashboard.ps1
D:\Friday\dashboard\README.md
```

Dashboard endpoints:

```text
GET  http://localhost:8888/
GET  http://localhost:8888/health
GET  http://localhost:8888/api/status
POST http://localhost:8888/api/action
WS   ws://localhost:8888/ws
```

Dashboard quick actions:

```text
Monday briefing
Memory consolidation
Router health
Latest vision analysis
```

Status:

```text
Complete. Dashboard is live and integrated into start/status/stop scripts.
```

Performance note:

- Dashboard status collection was optimized with parallel probes after the initial synchronous version took too long.

## Post-Roadmap Maintenance Layer

What was added after Phase 11:

```text
D:\Friday\maintenance\health-report.ps1
D:\Friday\maintenance\backup-friday.ps1
D:\Friday\maintenance\install-friday-startup.ps1
D:\Friday\maintenance\OPERATIONS.md
```

Health report command:

```powershell
cd D:\Friday
.\maintenance\health-report.ps1
```

Backup command:

```powershell
cd D:\Friday
.\maintenance\backup-friday.ps1
```

Latest backup:

```text
D:\Friday\backups\friday-backup-20260628-204854.zip
Size: 8.86 MB
Entries: 109
```

Backup policy:

```text
Default backup includes scripts, configs, local DBs, workflows, prompts, and critical state.
Voice recordings are excluded unless -IncludeVoiceRecordings is passed.
Qdrant/Open WebUI vector stores are excluded unless -IncludeVectorStores is passed.
Ollama model blobs are excluded unless -IncludeOllamaModels is passed.
```

Startup installer:

```powershell
cd D:\Friday
.\maintenance\install-friday-startup.ps1
```

Startup removal:

```powershell
cd D:\Friday
.\maintenance\install-friday-startup.ps1 -Remove
```

Current startup state:

```text
Startup auto-launch was not installed at report time.
```

## Main Operator Commands

Start full stack:

```powershell
cd D:\Friday
.\start-friday.ps1
```

Check full stack:

```powershell
cd D:\Friday
.\status-friday.ps1
```

Stop only Open WebUI:

```powershell
cd D:\Friday
.\stop-friday.ps1
```

Stop everything managed by scripts:

```powershell
cd D:\Friday
.\stop-friday.ps1 -StopOllama -StopMemory -StopRag -StopSearch -StopVoice -StopAutomation -StopVision -StopRouter -StopDashboard
```

Run voice:

```powershell
cd D:\Friday
.\voice\start-voice.ps1
```

Current wake phrase:

```text
Hey Jarvis
```

## Key Architecture Decisions

1. Local-first operation:
   - Core inference, memory, RAG, search, voice, automation, and dashboard are local.
   - Cloud dependency is limited to initial image/model downloads.

2. Open WebUI as primary interface:
   - Browser UI runs on port 3000.
   - It connects to Ollama, Qdrant, SearXNG, Whisper, and Kokoro.

3. Qdrant as shared vector storage:
   - Used for Mem0-style long-term memory and RAG collections.

4. Router for cost/performance control:
   - Most prompts stay on `friday:phi4`.
   - Heavy 70B model is reserved for complex reasoning.
   - Vision uses LLaVA.

5. Voice reliability over branding:
   - Custom Friday wake words were tested.
   - Jarvis wake model is currently preferred because it is more reliable.

6. Maintenance scripts are explicit:
   - Startup auto-launch is not silently installed.
   - Backups avoid huge vector/model folders unless explicitly requested.

## Known Issues and Open Risks

1. Wake word reliability:
   - Current reliable wake phrase is `Hey Jarvis`, not `Hey Friday`.
   - Custom Friday wake models exist but were less reliable in testing.

2. STT latency:
   - `medium.en` is reliable but slower than desired.
   - `large-v3-turbo` was attempted and caused Open WebUI transcription HTTP 500.

3. Voice hallucinated filler from STT:
   - Whisper can sometimes transcribe silence/background audio as phrases like repeated goodbyes.
   - Thresholding and silence handling improved but may need more tuning.

4. Web news quality:
   - SearXNG returns links and snippets, not always clean complete news articles.
   - Voice news was improved but should be reviewed for source quality and article summarization.

5. Email automation:
   - Tooling exists, but production email use needs secure SMTP/app-password handling.
   - Plaintext passwords should not be stored in repo files.

6. Auth/security:
   - Open WebUI currently has `WEBUI_AUTH=False`.
   - This is acceptable for local-only development but should be changed if exposed beyond localhost.

7. Secrets:
   - Project files should be audited before sharing externally.
   - User credentials/tokens were intentionally excluded from this report.

8. Backup completeness:
   - Default backup is lightweight and excludes large vector stores.
   - For full disaster recovery, run with `-IncludeVectorStores` and optionally `-IncludeOllamaModels`.

## Recommended Next Improvements

1. Make startup persistence explicit and tested after reboot:

```powershell
cd D:\Friday
.\maintenance\install-friday-startup.ps1
```

2. Add a voice tuning pass:
   - Better VAD/silence filtering.
   - Better Indian English STT configuration.
   - Lower latency STT backend outside Open WebUI if needed.

3. Add a secure local secrets strategy:
   - Windows Credential Manager, `.env` ignored from backup, or Docker secrets.

4. Improve news extraction:
   - Fetch article text from top search results.
   - Summarize full headlines plus 1-2 sentence context.
   - Keep citations/source names.

5. Add automated nightly health reports:
   - Use Windows Task Scheduler to run `maintenance\health-report.ps1`.

6. Add weekly full backup:
   - Standard weekly backup.
   - Monthly vector-store backup.

7. Harden Open WebUI:
   - Enable authentication before exposing beyond localhost.
   - Rotate `WEBUI_SECRET_KEY` if needed.

8. Add dashboard controls:
   - Start/stop voice.
   - Start/stop model router.
   - Run health report.
   - Trigger backup.

## Review Questions for ChatGPT

Use these questions to analyze the project:

1. Is this architecture coherent for a fully local Windows personal assistant?
2. Are there unnecessary services or avoidable complexity?
3. What are the top security risks in the current design?
4. What should be hardened before daily use?
5. How should wake-word and STT reliability be improved?
6. Is the model routing policy sensible for 8 GB VRAM and 64 GB RAM?
7. Should memory, RAG, and web search be unified behind one orchestrator?
8. What should be the next high-impact improvement after Phase 11?
9. Which parts should be moved into Windows services or scheduled tasks?
10. How should backup and restore be tested?

## Final Completion State

```text
Phase 1  Core Engine                          Complete
Phase 2  Open WebUI Interface                 Complete
Phase 3  Long-Term Memory                     Complete
Phase 4  Personal Knowledge Base / RAG         Complete
Phase 5  Live Web Search                      Complete
Phase 6  Voice Interface                      Complete
Phase 7  Agentic Tool Use                     Complete
Phase 8  Automation Engine                    Complete
Phase 9  Vision                               Complete
Phase 10 Model Router                         Complete
Phase 11 Dashboard                            Complete
Post-roadmap Maintenance                      Complete
```

FRIDAY is operational as a local assistant stack. The most important remaining work is not new feature installation; it is reliability hardening, voice tuning, secure credential handling, and reboot/startup verification.
