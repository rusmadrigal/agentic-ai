# Agentic AI Decision Engine

![Vista del MVP — capa de decisión e inteligencia](docs/images/mvp.png)

## ¿Qué hace esta herramienta?

**Agentic AI Decision Engine** es una aplicación de demostración orientada a negocio que **transforma datos de producto y competidores en decisiones de pricing accionables**. Está pensada para presentaciones, entrevistas o workshops (por ejemplo, estilo consultoría / Accenture-level positioning en la UI).

En la práctica el flujo es:

1. **Ingesta de datos** — Producto desde [DummyJSON](https://dummyjson.com) (simulación de catálogo externo) o **producto manual** (SKU / what-if).
2. **Benchmark de competidores** — Filas de título + precio (a mano, o **competidores de ejemplo** cargados desde el mismo catálogo DummyJSON vía API).
3. **Motor de decisión** — Con `OPENAI_API_KEY` puedes usar **razonamiento LLM** (`use_llm: true` o por defecto cuando la clave existe); sin clave o con **modo simulado**, se aplican **reglas deterministas** (pricing, promoción, inventario) con la misma estructura de salida.
4. **Capa de presentación** — Interfaz HTML en `/` con hero de decisión, **confianza**, insight, contexto de producto y comparación visual de precios; contrato JSON estable en **`POST /v1/decisions`**.

No sustituye un ERP ni un pricing intelligence productivo; sirve para **mostrar cómo la IA estructura datos reales (o simulados) en outputs listos para negocio**.

## Para revisores

1. Arranca la API (véase **Inicio rápido**), abre **`http://127.0.0.1:8000/`**, introduce un **Product ID**, **Fetch product**, revisa competidores (o **Load example competitors**), elige **Use AI (LLM)** o **Simulated logic** y pulsa **Get Pricing Recommendation**. El tour guiado está en la cabecera.
2. **`/docs`** — OpenAPI; ejemplo **`POST /v1/decisions`** con `product_id` o `product` + `competitors` y opcional **`use_llm`**.
3. **`GET /api/readiness`** — `openai_configured`, `llm_decisions_ready`, `rag_ready`, etc. (sin secretos).

## Inicio rápido (local)

Usa **Python 3.10+** (recomendado 3.11; el repo puede incluir **`.python-version`**).

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Índice FAISS opcional (demos / extensión RAG)
python scripts/build_index.py

# Opcional: embeddings OpenAI al construir el índice
export OPENAI_API_KEY=...
export EMBEDDING_MODE=embedding-3-small
python scripts/build_index.py

make dev
# o: uvicorn api.index:app --reload --host 0.0.0.0 --port 8000
```

Abre `http://localhost:8000/docs` para la documentación interactiva.

### Ejemplo `POST /v1/decisions`

```bash
curl -s http://localhost:8000/v1/decisions \
  -H 'content-type: application/json' \
  -d @- <<'JSON'
{
  "product_id": 1,
  "use_llm": false,
  "competitors": [
    { "title": "Brand A", "price": 100 },
    { "title": "Brand B", "price": 130 }
  ]
}
JSON
```

La respuesta incluye `product`, `competitors`, `decisions` (estrategia, precio recomendado, promoción, inventario, razonamiento, `confidence` si aplica), `source` (`dummyjson API` | `manual`) y **`decision_engine`** (`llm` | `simulated`).

### Competidores de ejemplo (DummyJSON)

```http
GET /api/example-competitors/{product_id}?limit=3
```

Devuelve filas sugeridas desde el mismo catálogo (misma categoría cuando es posible).

## Configuración

Ver **`.env.example`**. Variables relevantes:

| Variable | Uso |
| --- | --- |
| `OPENAI_API_KEY` | Habilita el modo LLM en `/v1/decisions` (cuando `use_llm` no fuerza lo contrario). |
| `OPENAI_CHAT_MODEL` | Por defecto `gpt-4o-mini`. |
| `EMBEDDING_MODE` | `embedding-3-small` o `pseudo` (offline). |
| `OPENAI_EMBEDDING_MODEL` | Por defecto `text-embedding-3-small`. |

Los embeddings en tiempo de consulta deben ser coherentes con cómo se construyó el índice FAISS.

## Despliegue (Render)

- **Blueprint:** `render.yaml` — build con `pip` + `scripts/build_index.py`, start `uvicorn` con `$PORT`.
- **Health:** `GET /health`.
- Definir **`OPENAI_API_KEY`** como secreto si usar LLM/embeddings en build.

## Tests

```bash
pytest
```

## Estructura del proyecto

```
api/index.py              # FastAPI (demo HTML, decisiones, DummyJSON)
app/services/             # ai_decision_engine (LLM), rule_decisions (simulado)
app/integrations/         # dummyjson.py
app/rag/                  # FAISS + retriever (extensión)
app/static/demo.html      # UI demo
docs/images/mvp.png       # Captura del MVP
```

## Notas

- El MVP no depende de base de datos externa; el corpus RAG es JSON versionado + índice en disco.
- DummyJSON es **datos de ejemplo**; en producción se conectarían fuentes y políticas reales.

---

## Creador

**Rusben Madrigal**  
San José, Costa Rica  

- Correo: [rusbenmadrigal@gmail.com](mailto:rusbenmadrigal@gmail.com)  
- GitHub: [@rusmadrigal](https://github.com/rusmadrigal)  
- Web: [www.rusmadrigal.com](https://www.rusmadrigal.com)  
