"""Retriever -> Reranking -> LLM -> Answer + Sources."""
import logging
from uuid import UUID

import numpy as np
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from .config import settings
from .db import get_conn
from .ingestion import get_embeddings
from .schemas import ChatResponse, Source

log = logging.getLogger(__name__)


def _llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.chat_model,
        temperature=0,
        api_key=settings.openai_api_key or None,
    )


# ---------------------------------------------------------------- Retriever
def retrieve(question: str, document_ids: list[UUID] | None, k: int) -> list[dict]:
    qvec = np.array(get_embeddings().embed_query(question), dtype=np.float32)
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.document_id, d.filename, c.page, c.content,
                   1 - (c.embedding <=> %(q)s) AS score
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE (%(ids)s::uuid[] IS NULL OR c.document_id = ANY(%(ids)s::uuid[]))
            ORDER BY c.embedding <=> %(q)s
            LIMIT %(k)s
            """,
            {"q": qvec, "ids": document_ids or None, "k": k},
        ).fetchall()
    return rows


# ---------------------------------------------------------------- Reranking
class _RerankItem(BaseModel):
    index: int = Field(description="Numéro du passage (1-based)")
    score: float = Field(description="Pertinence de 0 (hors sujet) à 10 (répond directement)")


class _RerankResult(BaseModel):
    items: list[_RerankItem]


def rerank(question: str, candidates: list[dict]) -> list[dict]:
    """Reranking par LLM (scoring 0-10). Fallback sur l'ordre vectoriel si erreur."""
    if not settings.rerank_enabled or len(candidates) <= 1:
        return candidates
    passages = "\n\n".join(
        f"[{i}] {c['content'][:700]}" for i, c in enumerate(candidates, start=1)
    )
    prompt = (
        "Tu es un moteur de reranking. Pour la question ci-dessous, note chaque passage "
        "de 0 à 10 selon sa capacité à contenir la réponse.\n\n"
        f"Question : {question}\n\nPassages :\n{passages}"
    )
    try:
        res: _RerankResult = _llm().with_structured_output(_RerankResult).invoke(prompt)
        scores = {it.index: it.score for it in res.items}
        ranked = sorted(
            enumerate(candidates, start=1),
            key=lambda t: (scores.get(t[0], 0.0), t[1]["score"]),
            reverse=True,
        )
        return [c for _, c in ranked]
    except Exception:  # noqa: BLE001
        log.exception("Reranking échoué, fallback sur l'ordre vectoriel")
        return candidates


# ---------------------------------------------------------------- Génération
class _LLMAnswer(BaseModel):
    answer: str = Field(description="Réponse à la question, basée uniquement sur le contexte")
    used_sources: list[int] = Field(
        default_factory=list,
        description="Numéros des passages réellement utilisés. Vide si la réponse n'est pas dans le contexte.",
    )


SYSTEM = (
    "Tu es un assistant documentaire. Réponds UNIQUEMENT à partir des passages fournis. "
    "Si la réponse n'y figure pas, dis clairement que l'information n'est pas dans les "
    "documents et laisse used_sources vide. Réponds dans la langue de la question, de "
    "façon concise et précise (chiffres exacts, conditions éventuelles)."
)


def generate(question: str, passages: list[dict]) -> _LLMAnswer:
    context = "\n\n".join(
        f"[{i}] (Source : {p['filename']}, page {p['page']})\n{p['content']}"
        for i, p in enumerate(passages, start=1)
    )
    messages = [
        ("system", SYSTEM),
        ("human", f"Contexte :\n{context}\n\nQuestion : {question}"),
    ]
    return _llm().with_structured_output(_LLMAnswer).invoke(messages)


# ---------------------------------------------------------------- Pipeline
def answer_question(question: str, document_ids: list[UUID] | None) -> ChatResponse:
    candidates = retrieve(question, document_ids, settings.retrieval_k)
    if not candidates:
        return ChatResponse(
            answer="Aucun document n'est disponible. Upload d'abord un document.", sources=[]
        )

    top = rerank(question, candidates)[: settings.final_k]
    result = generate(question, top)

    # Sources dédupliquées (document, page), dans l'ordre d'utilisation
    seen: dict[tuple, Source] = {}
    for n in result.used_sources:
        if 1 <= n <= len(top):
            p = top[n - 1]
            key = (p["document_id"], p["page"])
            if key not in seen:
                seen[key] = Source(
                    document_id=p["document_id"],
                    filename=p["filename"],
                    page=p["page"],
                    snippet=p["content"][:300],
                    score=round(float(p["score"]), 4),
                )
    sources = sorted(seen.values(), key=lambda s: (s.filename, s.page))
    return ChatResponse(answer=result.answer, sources=sources)
