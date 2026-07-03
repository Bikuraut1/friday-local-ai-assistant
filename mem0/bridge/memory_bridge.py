import os
from datetime import datetime, timezone
from typing import Any, Optional

import requests
from fastapi import FastAPI, HTTPException, Query
from mem0 import Memory
from pydantic import BaseModel, Field

os.environ.setdefault("MEM0_TELEMETRY", "False")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("DO_NOT_TRACK", "true")

ROOT = os.environ.get("FRIDAY_ROOT", r"D:\Friday")
HISTORY_DB = os.path.join(ROOT, "mem0", "history.db")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
QDRANT_HOST = os.environ.get("QDRANT_HOST", "127.0.0.1")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
COLLECTION_NAME = os.environ.get("FRIDAY_MEMORY_COLLECTION", "friday_memories")
USER_ID = os.environ.get("FRIDAY_USER_ID", "boss")

MEMORY_CATEGORIES = {
    "USER_PROFILE",
    "GOALS",
    "PROJECTS",
    "PREFERENCES",
    "RELATIONSHIPS",
    "DECISIONS_MADE",
    "FOLLOW_UPS",
}

MEMORY_CONFIG = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": COLLECTION_NAME,
            "host": QDRANT_HOST,
            "port": QDRANT_PORT,
            "embedding_model_dims": 768,
            "on_disk": True,
        },
    },
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "friday:phi4",
            "ollama_base_url": OLLAMA_BASE_URL,
            "temperature": 0.1,
            "max_tokens": 1200,
        },
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text",
            "ollama_base_url": OLLAMA_BASE_URL,
            "embedding_dims": 768,
        },
    },
    "history_db_path": HISTORY_DB,
    "version": "v1.1",
    "custom_instructions": (
        "Extract durable personal-memory facts for FRIDAY only. "
        "Preserve category context and avoid storing credentials, passwords, "
        "financial secrets, or one-time sensitive values."
    ),
}


class MemoryCreate(BaseModel):
    text: str = Field(..., min_length=1)
    category: str
    user_id: str = USER_ID
    source: str = "manual"
    infer: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemorySearch(BaseModel):
    query: str = Field(..., min_length=1)
    user_id: str = USER_ID
    category: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=50)


def validate_category(category: str) -> str:
    normalized = category.strip().upper()
    if normalized not in MEMORY_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Use one of: {', '.join(sorted(MEMORY_CATEGORIES))}",
        )
    return normalized


def normalize_mem0_result(result: Any) -> list[dict[str, Any]]:
    if isinstance(result, dict):
        if isinstance(result.get("results"), list):
            items = result["results"]
        elif isinstance(result.get("memories"), list):
            items = result["memories"]
        else:
            items = [result]
    elif isinstance(result, list):
        items = result
    else:
        items = [{"raw": str(result)}]

    normalized = []
    for item in items:
        if isinstance(item, dict):
            normalized.append(item)
        else:
            normalized.append({"raw": str(item)})
    return normalized


def build_memory() -> Memory:
    os.makedirs(os.path.dirname(HISTORY_DB), exist_ok=True)
    return Memory.from_config(MEMORY_CONFIG)


app = FastAPI(title="FRIDAY Mem0 Bridge", version="1.0.0")
memory = build_memory()


@app.get("/health")
def health() -> dict[str, Any]:
    ollama_ok = False
    qdrant_ok = False

    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/version", timeout=2)
        ollama_ok = response.status_code == 200
    except requests.RequestException:
        ollama_ok = False

    try:
        response = requests.get(f"http://{QDRANT_HOST}:{QDRANT_PORT}/readyz", timeout=2)
        qdrant_ok = response.status_code == 200
    except requests.RequestException:
        qdrant_ok = False

    return {
        "status": bool(ollama_ok and qdrant_ok),
        "ollama": ollama_ok,
        "qdrant": qdrant_ok,
        "collection": COLLECTION_NAME,
        "categories": sorted(MEMORY_CATEGORIES),
    }


@app.post("/memory")
def add_memory(payload: MemoryCreate) -> dict[str, Any]:
    category = validate_category(payload.category)
    metadata = {
        **payload.metadata,
        "category": category,
        "source": payload.source,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    result = memory.add(
        [{"role": "user", "content": payload.text}],
        user_id=payload.user_id,
        metadata=metadata,
        infer=payload.infer,
    )
    return {
        "status": "stored",
        "category": category,
        "user_id": payload.user_id,
        "result": result,
    }


@app.post("/memory/search")
def search_memory(payload: MemorySearch) -> dict[str, Any]:
    category = validate_category(payload.category) if payload.category else None
    result = memory.search(payload.query, top_k=payload.top_k, filters={"user_id": payload.user_id})
    items = normalize_mem0_result(result)

    if category:
        items = [
            item
            for item in items
            if (item.get("metadata") or {}).get("category") == category
            or item.get("category") == category
        ]

    return {
        "query": payload.query,
        "user_id": payload.user_id,
        "category": category,
        "results": items[: payload.top_k],
    }


@app.get("/memory")
def list_memory(
    user_id: str = Query(default=USER_ID),
    category: Optional[str] = Query(default=None),
    top_k: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    normalized_category = validate_category(category) if category else None
    result = memory.get_all(filters={"user_id": user_id}, top_k=top_k)
    items = normalize_mem0_result(result)

    if normalized_category:
        items = [
            item
            for item in items
            if (item.get("metadata") or {}).get("category") == normalized_category
            or item.get("category") == normalized_category
        ]

    return {
        "user_id": user_id,
        "category": normalized_category,
        "results": items[:top_k],
    }


@app.get("/categories")
def categories() -> dict[str, list[str]]:
    return {"categories": sorted(MEMORY_CATEGORIES)}
