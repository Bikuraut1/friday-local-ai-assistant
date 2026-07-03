# FRIDAY Phase 4 - Personal Knowledge Base

Phase 4 configures Open WebUI RAG with local Qdrant vector storage, Ollama embeddings, hybrid search, and a local external reranker.

Local services:

- Open WebUI: `http://localhost:3000`
- Qdrant: `http://localhost:6333`
- FRIDAY reranker: `http://localhost:8770/v1/rerank`

Knowledge base folder:

- `D:\Friday\knowledge-base`

Supported ingest targets through Open WebUI:

- PDF
- DOCX
- TXT
- MD
- web pages
- YouTube transcripts

Commands:

```powershell
powershell -ExecutionPolicy Bypass -File D:\Friday\rag\start-rag.ps1
powershell -ExecutionPolicy Bypass -File D:\Friday\rag\test-rag.ps1
powershell -ExecutionPolicy Bypass -File D:\Friday\rag\stop-reranker.ps1
```
