# FRIDAY Phase 3 - Long-Term Memory

This phase runs local long-term memory with:

- Mem0 Python package in `D:\Friday\mem0\.venv`
- Qdrant vector database in Docker
- Ollama embeddings via `nomic-embed-text`
- Ollama LLM extraction via `friday:phi4`
- Local API bridge at `http://localhost:8765`

Memory categories:

- USER_PROFILE
- GOALS
- PROJECTS
- PREFERENCES
- RELATIONSHIPS
- DECISIONS_MADE
- FOLLOW_UPS

Commands:

```powershell
powershell -ExecutionPolicy Bypass -File D:\Friday\mem0\start-memory.ps1
powershell -ExecutionPolicy Bypass -File D:\Friday\mem0\test-memory.ps1
powershell -ExecutionPolicy Bypass -File D:\Friday\mem0\stop-memory.ps1
```

Open WebUI bridge:

Import `D:\Friday\mem0\open-webui-tool-friday-memory.py` as an Open WebUI tool after the bridge is running.
