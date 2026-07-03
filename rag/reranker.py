import math
import os
import re
from collections import Counter
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

API_KEY = os.environ.get("FRIDAY_RERANKER_API_KEY", "change-me-local-dev")
TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


class RerankRequest(BaseModel):
    model: str = "friday-local-reranker"
    query: str = Field(..., min_length=1)
    documents: list[str] = Field(..., min_length=1)
    top_n: int | None = None


def tokens(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def score(query: str, document: str) -> float:
    query_terms = tokens(query)
    doc_terms = tokens(document)
    if not query_terms or not doc_terms:
        return 0.0

    q_counts = Counter(query_terms)
    d_counts = Counter(doc_terms)
    overlap = sum(min(q_counts[t], d_counts[t]) for t in q_counts)
    coverage = overlap / max(len(q_counts), 1)

    q_set = set(query_terms)
    d_set = set(doc_terms)
    jaccard = len(q_set & d_set) / max(len(q_set | d_set), 1)

    phrase_bonus = 0.15 if query.lower() in document.lower() else 0.0
    length_penalty = 1.0 / (1.0 + math.log10(max(len(doc_terms), 1)) / 10.0)

    return min(1.0, ((0.75 * coverage) + (0.25 * jaccard) + phrase_bonus) * length_penalty)


app = FastAPI(title="FRIDAY Local Reranker", version="1.0.0")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": True, "model": "friday-local-reranker"}


@app.post("/v1/rerank")
def rerank(payload: RerankRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if authorization and authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Invalid reranker API key")

    scored = [
        {"index": index, "document": document, "relevance_score": score(payload.query, document)}
        for index, document in enumerate(payload.documents)
    ]
    scored.sort(key=lambda item: item["relevance_score"], reverse=True)
    top_n = payload.top_n or len(scored)

    return {
        "model": payload.model,
        "results": scored[:top_n],
    }
