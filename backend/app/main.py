import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import db, ingestion, rag
from .config import settings
from .schemas import ChatRequest, ChatResponse, DocumentInfo

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("rag")


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield
    db.close_db()


app = FastAPI(title="AI Document Assistant (RAG)", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/documents", response_model=list[DocumentInfo])
def list_documents():
    with db.get_conn() as conn:
        return conn.execute(
            """
            SELECT d.id, d.filename, d.n_pages, d.created_at, COUNT(c.id)::int AS n_chunks
            FROM documents d LEFT JOIN chunks c ON c.document_id = d.id
            GROUP BY d.id ORDER BY d.created_at DESC
            """
        ).fetchall()


@app.post("/api/documents", response_model=DocumentInfo)
def upload_document(file: UploadFile = File(...)):
    if not settings.openai_api_key:
        raise HTTPException(500, "OPENAI_API_KEY n'est pas configurée côté backend.")
    data = file.file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Fichier trop gros (max {settings.max_upload_mb} MB).")
    try:
        return ingestion.ingest_document(file.filename or "document", data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:  # noqa: BLE001
        log.exception("Ingestion failed")
        raise HTTPException(500, f"Erreur d'ingestion : {e}")


@app.delete("/api/documents/{doc_id}", status_code=204)
def delete_document(doc_id: UUID):
    with db.get_conn() as conn:
        res = conn.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
        conn.commit()
        if res.rowcount == 0:
            raise HTTPException(404, "Document introuvable")


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not settings.openai_api_key:
        raise HTTPException(500, "OPENAI_API_KEY n'est pas configurée côté backend.")
    try:
        return rag.answer_question(req.question, req.document_ids)
    except Exception as e:  # noqa: BLE001
        log.exception("Chat failed")
        raise HTTPException(500, f"Erreur : {e}")
