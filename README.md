# Agentic AI Decision Engine for E-commerce

Production-minded **FastAPI** demo that combines **external product data** ([DummyJSON](https://dummyjson.com)) with a **simulated decision layer** (pricing, promotion, inventory heuristics). Optional **FAISS + OpenAI agents** remain in the codebase for extension. Packaged for **Render** and local development.

## For reviewers (e.g. hiring panel)

1. Run the API locally (see **Quickstart**) and open **`http://127.0.0.1:8000/`** — enter a **Product ID**, **Fetch product** (server-side DummyJSON call), add **competitors** (title + price), **Generate Decision**, and review structured output. **Guided tour** (top right) walks the flow. **No OpenAI key is required** for this path.
2. Open **`/docs`** for OpenAPI: **`POST /v1/decisions`** example (`product_id` or manual `product` + competitor `title`/`price`).
3. **`GET /api/readiness`** — `openai_configured`, `rag_ready`, `simulated_decisions_ready` (no secrets).

## What it does

- **`GET /`**: **HTML demo** — business-oriented workflow (ingest → benchmark → decision cards).
- **`GET /api/external-products/{id}`**: fetch + normalize a DummyJSON product (for the UI preview step).
- **POST `/v1/decisions`**: **`product_id`** (live catalog) *or* manual **`product`** + **`competitors`** `[{ "title", "price" }]` → **`product`**, **`competitors`**, **`decisions`** (strategy, recommended price, promotion, inventory, reasoning), **`source`** (`dummyjson API` | `manual`).
- **GET `/health`**: liveness; `rag_ready` reflects on-disk FAISS (optional).

The repo keeps an explicit orchestrator + RAG modules for growth; the default `/v1/decisions` contract is intentionally simple for interviews and demos.

## Quickstart (local)

Use **Python 3.10+** (3.11 recommended; the repo includes **`.python-version`** for Render and pyenv).

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Build the FAISS index from data/knowledge_base.json (works offline with pseudo embeddings)
python scripts/build_index.py

# Optional: real OpenAI embeddings for retrieval (recommended when you have a key)
export OPENAI_API_KEY=... 
export EMBEDDING_MODE=embedding-3-small
python scripts/build_index.py

# Run the API (shortcut — same as uvicorn below)
# OPENAI_API_KEY is optional for the simulated DummyJSON decision path
make dev

# Or explicitly:
# uvicorn api.index:app --reload --host 0.0.0.0 --port 8000
```

`make dev` is defined in the repo **`Makefile`** (local only): it runs **`python -m uvicorn`**, prefers **`.venv/bin/python`** if present (works with paths that contain spaces), checks that **uvicorn** is importable, and errors early if **port 8000** is already taken—use **`make dev PORT=8010`** (or free another process on 8000). Production keeps the native **`uvicorn`** start command (see **Deploying on Render**).

Open `http://localhost:8000/docs` for interactive OpenAPI.

### Example request

```bash
curl -s http://localhost:8000/v1/decisions \
  -H 'content-type: application/json' \
  -d @- <<'JSON'
{
  "product_id": 1,
  "competitors": [
    { "title": "Brand A", "price": 100 },
    { "title": "Brand B", "price": 130 }
  ]
}
JSON
```

Sample payloads live in `data/sample_products.json`.

## Configuration

See `.env.example`. Important variables:

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Optional for the **simulated** `/v1/decisions` path. Required if you wire the LLM/RAG orchestrator back into an endpoint. Also used for embeddings when `EMBEDDING_MODE=embedding-3-small`. |
| `EMBEDDING_MODE` | `embedding-3-small` (default) or `pseudo` (offline deterministic vectors for demos/CI). |
| `OPENAI_CHAT_MODEL` | Defaults to `gpt-4o-mini`. |
| `OPENAI_EMBEDDING_MODEL` | Defaults to `text-embedding-3-small` (1536-d). |

**Important:** query-time embeddings must match how the index was built. If you switch embedding modes, rebuild the index.

## RAG index build

`scripts/build_index.py` reads `data/knowledge_base.json`, embeds each chunk, and writes:

- `data/faiss.index`
- `data/faiss_meta.json`

You can commit those files for reproducible deploys, or rely on the **Render `buildCommand`** (see below) to regenerate them on each deploy.

## Deploying on Render

### Option A — Blueprint (`render.yaml`)

1. Push this repository to GitHub/GitLab.
2. In the Render dashboard, create a **Blueprint** and select the repo (Render will read `render.yaml`).
3. When prompted, set **`OPENAI_API_KEY`** (mark as secret). Render will inject **`PORT`** automatically; do not hardcode it. Prefer having the key available **before the first build** so the FAISS index uses the same embedding space as runtime; if the first build ran without a key, trigger a **manual redeploy** after adding the secret.
4. Deploy. The blueprint runs:
   - **Build:** `pip install … && python scripts/build_index.py` (rebuilds the FAISS index; uses OpenAI embeddings only if a key is present at build time, otherwise **pseudo** embeddings).
   - **Start:** `uvicorn api.index:app --host 0.0.0.0 --port $PORT`
5. Health checks use **`GET /health`**.

### Option B — Web Service (dashboard only)

Create a **Web Service**, link the repo, then set:

| Setting | Value |
| --- | --- |
| **Runtime** | Python 3 |
| **Build Command** | `pip install --upgrade pip && pip install -r requirements.txt && python scripts/build_index.py` |
| **Start Command** | `uvicorn api.index:app --host 0.0.0.0 --port $PORT` |

Add environment variable **`OPENAI_API_KEY`** (secret). Python version follows **`.python-version`** (or set **`PYTHON_VERSION`** in the dashboard if you prefer an explicit patch, e.g. `3.11.11`).

The included **`Procfile`** matches the start command above; Render will use it if you leave “Start Command” empty in some setups—when in doubt, paste the `uvicorn` line explicitly.

## Tests

```bash
pytest
```

## Project layout

```
Makefile                  # Local: `make dev` (uvicorn --reload)
api/index.py              # FastAPI entrypoint (ASGI app: app)
Procfile                  # Render: web process (uvicorn + $PORT)
render.yaml               # Render Blueprint (optional IaC)
app/agents/               # Analyzer, decision maker, formatter (OpenAI JSON)
app/rag/                  # Embeddings + FAISS vector store + retriever
app/services/orchestrator.py
data/knowledge_base.json  # Retrieval corpus (edit + rebuild index)
scripts/build_index.py
tests/test_health.py
```

## Notes and limitations

- This MVP intentionally avoids external databases; the “knowledge base” is versioned JSON plus a small on-disk FAISS index.
- On Render, each instance loads the index at startup; keep the corpus small for fast boots.
- Agents require an OpenAI key; retrieval can run in `pseudo` mode for local experimentation without embeddings API access.
