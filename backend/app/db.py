from contextlib import contextmanager

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import settings

_pool: ConnectionPool | None = None


def _schema() -> str:
    return f"""
    CREATE TABLE IF NOT EXISTS documents (
        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        filename    TEXT NOT NULL,
        n_pages     INT  NOT NULL,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    CREATE TABLE IF NOT EXISTS chunks (
        id           BIGSERIAL PRIMARY KEY,
        document_id  UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        page         INT  NOT NULL,
        chunk_index  INT  NOT NULL,
        content      TEXT NOT NULL,
        embedding    vector({settings.embedding_dim}) NOT NULL
    );

    CREATE INDEX IF NOT EXISTS chunks_document_idx ON chunks(document_id);
    CREATE INDEX IF NOT EXISTS chunks_embedding_idx
        ON chunks USING hnsw (embedding vector_cosine_ops);
    """


def _configure(conn: psycopg.Connection) -> None:
    register_vector(conn)
    conn.commit()


def init_db() -> None:
    global _pool
    # L'extension doit exister avant register_vector
    with psycopg.connect(settings.database_url, autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute(_schema())
    _pool = ConnectionPool(
        settings.database_url,
        min_size=1,
        max_size=10,
        configure=_configure,
        kwargs={"row_factory": dict_row},
        open=True,
    )


def close_db() -> None:
    if _pool:
        _pool.close()


@contextmanager
def get_conn():
    assert _pool is not None, "DB pool not initialised"
    with _pool.connection() as conn:
        yield conn
