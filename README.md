# Agentic AI Decision Engine for E-commerce

Production-minded **FastAPI** service that turns product facts into **structured consulting-style decisions**, using a small **agentic workflow** (retrieve → analyze → decide → format) and lightweight **FAISS + JSON RAG**—packaged for **Render** (native Python web service) and local development.

## For reviewers (e.g. hiring panel)

1. Run the API locally (see **Quickstart**), set `OPENAI_API_KEY` in `.env`, and open **`http://127.0.0.1:8000/`** — interactive demo with prefilled product + competitor, one-click “Generate decision brief”, and formatted output (plus raw JSON).
2. Open **`/docs`** for OpenAPI: tagged operations, request **example** on `POST /v1/decisions`, and full schemas.
3. **`GET /api/readiness`** — JSON flags for UI/load checks (`openai_configured`, `rag_ready`) without exposing secrets.

## What it does

- **`GET /`**: reviewer-friendly **HTML demo** (no separate frontend build).
- **POST `/v1/decisions`**: accepts a `ProductBrief` and returns a `DecisionEngineResponse` with retrieval hits plus a `ClientDeliverable` (executive summary, analysis, and explicit decision objects).
- **GET `/health`**: liveness and whether the FAISS artifacts are loaded.

The workflow is intentionally explicit (no heavy orchestration framework) so the repo stays easy to read, test, and deploy.

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

# Run the API
export OPENAI_API_KEY=...   # required for /v1/decisions (LLM agents)
uvicorn api.index:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/docs` for interactive OpenAPI.

### Example request

```bash
curl -s http://localhost:8000/v1/decisions \
  -H 'content-type: application/json' \
  -d @- <<'JSON'
{
  "product": {
    "title": "Merino crewneck sweater — limited colors",
    "description": "Mid-weight merino blend; strong email repeats; sizing content is thin.",
    "category": "Apparel / Knitwear",
    "price_usd": 89,
    "cost_usd": 38,
    "inventory_units": 4200,
    "margin_target_pct": 52,
    "constraints": ["Avoid sitewide 20% coupons", "Premium adjacency"]
  },
  "competitors": [
    {
      "name": "Nordic Knit Co. Crew",
      "price_usd": 78,
      "positioning_notes": "Frequent promos; stronger sizing content."
    }
  ]
}
JSON
```

Sample payloads live in `data/sample_products.json`.

## Configuration

See `.env.example`. Important variables:

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Required for **agents** (`/v1/decisions`). Also used for embeddings when `EMBEDDING_MODE=embedding-3-small`. |
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
3. When prompted, set **`OPENAI_API_KEY`** (mark as secret). Render will inject **`PORT`** automatically; do not hardcode it.
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
