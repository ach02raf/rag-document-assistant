"""PDF/Docs -> extraction texte -> chunking -> embeddings -> pgvector."""
import io
import logging
from pathlib import Path

import numpy as np
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from .config import settings
from .db import get_conn

log = logging.getLogger(__name__)

SUPPORTED = {".pdf", ".txt", ".md", ".docx"}
EMBED_BATCH = 100

_embeddings: OpenAIEmbeddings | None = None


def get_embeddings() -> OpenAIEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key or None,
        )
    return _embeddings


def extract_pages(filename: str, data: bytes) -> list[tuple[int, str]]:
    """Retourne une liste (numéro_de_page, texte)."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        return [(i + 1, (p.extract_text() or "")) for i, p in enumerate(reader.pages)]
    if ext in (".txt", ".md"):
        return [(1, data.decode("utf-8", errors="ignore"))]
    if ext == ".docx":
        import docx

        d = docx.Document(io.BytesIO(data))
        return [(1, "\n".join(p.text for p in d.paragraphs))]
    raise ValueError(f"Format non supporté : {ext} (supportés : {', '.join(sorted(SUPPORTED))})")


def chunk_pages(pages: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Découpe page par page pour garder le numéro de page exact."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    out: list[tuple[int, str]] = []
    for page_no, text in pages:
        text = text.strip()
        if not text:
            continue
        for piece in splitter.split_text(text):
            if piece.strip():
                out.append((page_no, piece.strip()))
    return out


def embed_texts(texts: list[str]) -> list[list[float]]:
    emb = get_embeddings()
    vectors: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH):
        vectors.extend(emb.embed_documents(texts[i : i + EMBED_BATCH]))
    return vectors


def ingest_document(filename: str, data: bytes) -> dict:
    pages = extract_pages(filename, data)
    chunks = chunk_pages(pages)
    if not chunks:
        raise ValueError(
            "Aucun texte extractible (PDF scanné ? ajoute un OCR comme ocrmypdf avant l'upload)."
        )

    log.info("%s : %d pages, %d chunks -> embeddings", filename, len(pages), len(chunks))
    vectors = embed_texts([c[1] for c in chunks])

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO documents (filename, n_pages) VALUES (%s, %s) "
                "RETURNING id, filename, n_pages, created_at",
                (filename, len(pages)),
            )
            doc = cur.fetchone()
            cur.executemany(
                "INSERT INTO chunks (document_id, page, chunk_index, content, embedding) "
                "VALUES (%s, %s, %s, %s, %s)",
                [
                    (doc["id"], page, idx, text, np.array(vec, dtype=np.float32))
                    for idx, ((page, text), vec) in enumerate(zip(chunks, vectors))
                ],
            )
        conn.commit()

    doc["n_chunks"] = len(chunks)
    return doc
