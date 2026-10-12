# 🥇 AI Document Assistant (RAG)

Upload des PDF / DOCX / TXT, pose des questions, obtiens une réponse **avec sources (document + page)**.

```
PDF → Extraction (pypdf, page par page) → Chunking (LangChain) → Embeddings (OpenAI)
    → PostgreSQL + pgvector (HNSW cosine) → Retriever (top 20) → Reranking (LLM, top 5)
    → LLM (OpenAI, sortie structurée) → Réponse + Sources
```

| Couche   | Techno                                   |
|----------|------------------------------------------|
| Frontend | Next.js 14 + TypeScript                  |
| Backend  | Python 3.11 + FastAPI                    |
| IA       | OpenAI + LangChain                       |
| DB       | PostgreSQL 16 + pgvector                 |

## Prérequis
- Une clé API OpenAI (https://platform.openai.com/api-keys)
- **Option A (le plus simple)** : Docker + Docker Compose
- **Option B (dev local)** : Docker (pour la DB), Python 3.11+, Node.js 18+

## Option A — Tout avec Docker (1 commande)

```bash
cp .env.example .env
# édite .env et mets ta clé : OPENAI_API_KEY=sk-...
docker compose up --build
```
- Frontend : http://localhost:3000
- API (Swagger) : http://localhost:8000/docs

## Option B — Développement local

**1. Base de données**
```bash
docker compose -f docker-compose.db.yml up -d
```

**2. Backend**
```bash
cp .env.example .env        # puis mets OPENAI_API_KEY
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**3. Frontend** (autre terminal)
```bash
cd frontend
npm install
npm run dev
```
Ouvre http://localhost:3000

## Utilisation
1. Upload `Company HR Policy.pdf` (panneau de gauche).
2. Demande : *How many days of annual leave can an employee take?*
3. Réponse attendue :
   ```
   25 days
   Sources:
   Company HR Policy - page 12
   Company HR Policy - page 13
   ```
4. Coche des documents à gauche pour limiter la recherche à ceux-ci.

## Test API en curl
```bash
curl -F "file=@HR_Policy.pdf" http://localhost:8000/api/documents
curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" \
     -d '{"question":"How many days of annual leave?"}'
```

## Endpoints
| Méthode | Route                    | Description                      |
|---------|--------------------------|----------------------------------|
| GET     | `/health`                | Healthcheck                      |
| GET     | `/api/documents`         | Liste des documents              |
| POST    | `/api/documents`         | Upload + ingestion (champ `file`)|
| DELETE  | `/api/documents/{id}`    | Supprime document + chunks       |
| POST    | `/api/chat`              | `{question, document_ids?}`      |

## Configuration (`.env`)
| Variable          | Défaut                    | Rôle                                  |
|-------------------|---------------------------|---------------------------------------|
| `OPENAI_API_KEY`  | —                         | Obligatoire                           |
| `CHAT_MODEL`      | `gpt-4o-mini`             | LLM de réponse + reranking            |
| `EMBEDDING_MODEL` | `text-embedding-3-small`  | Embeddings (1536 dims)                |
| `CHUNK_SIZE`      | 1000                      | Taille des chunks (caractères)        |
| `CHUNK_OVERLAP`   | 150                       | Chevauchement                         |
| `RETRIEVAL_K`     | 20                        | Candidats récupérés par pgvector      |
| `FINAL_K`         | 5                         | Passages envoyés au LLM après rerank  |
| `RERANK_ENABLED`  | true                      | Désactive le reranking si `false`     |

> Si tu changes de modèle d'embedding avec une autre dimension (ex. `text-embedding-3-large` = 3072),
> mets `EMBEDDING_DIM` à jour et recrée la DB : `docker compose down -v`.

## Dépannage
- **`OPENAI_API_KEY n'est pas configurée`** : vérifie `.env` (à la racine) puis relance le backend.
- **`Backend injoignable` dans l'UI** : le backend ne tourne pas sur :8000, ou `CORS_ORIGINS` ne contient pas l'URL du front.
- **`Aucun texte extractible`** : PDF scanné (images). Passe-le d'abord dans un OCR (`ocrmypdf in.pdf out.pdf`).
- **Port 5432 déjà utilisé** : arrête ton PostgreSQL local ou change le port dans le compose.
- **Reset complet de la DB** : `docker compose down -v`.
- **Changer l'URL de l'API du front (Docker)** : modifie `NEXT_PUBLIC_API_URL` dans `docker-compose.yml` puis `docker compose up --build`.

## Structure
```
rag-document-assistant/
├── docker-compose.yml        # db + backend + frontend
├── docker-compose.db.yml     # db seule (dev local)
├── .env.example
├── backend/
│   ├── Dockerfile · requirements.txt
│   └── app/
│       ├── main.py           # routes FastAPI
│       ├── config.py         # settings (.env)
│       ├── db.py             # pool psycopg + schéma pgvector
│       ├── ingestion.py      # extraction, chunking, embeddings, insert
│       ├── rag.py            # retriever, reranking, génération, sources
│       └── schemas.py
└── frontend/
    ├── app/ (layout, page, globals.css)
    ├── components/ (Chat, DocumentPanel)
    └── lib/api.ts
```

## Pistes d'amélioration
Streaming des réponses (SSE), historique de conversation + réécriture de requête, recherche hybride (BM25 + vecteurs),
reranker cross-encoder (Cohere / bge-reranker), authentification multi-utilisateurs, OCR intégré, évaluation (RAGAS).
