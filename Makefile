# Local development only. Production (e.g. Render) uses native: uvicorn api.index:app --host 0.0.0.0 --port $PORT
.PHONY: dev build-index

PORT ?= 8000
SHELL := /bin/bash

# Resolve Python: project .venv first, then python3 / python on PATH. Uses CURDIR so paths with spaces work.
define resolve_py
root="$(CURDIR)"; \
py="$$root/.venv/bin/python"; \
if [[ ! -x "$$py" ]]; then py=$$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true); fi; \
if [[ -z "$$py" ]] || ! "$$py" -c "import uvicorn" 2>/dev/null; then \
 echo >&2 "Cannot import uvicorn. From the repo root run:"; \
  echo >&2 "  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"; \
  exit 1; \
fi
endef

dev:
	@$(resolve_py); \
	if command -v lsof >/dev/null 2>&1 && lsof -iTCP:$(PORT) -sTCP:LISTEN >/dev/null 2>&1; then \
	  echo >&2 "Port $(PORT) is already in use. Try: make dev PORT=8010"; \
	  exit 1; \
	fi; \
	exec "$$py" -m uvicorn api.index:app --reload --host 0.0.0.0 --port $(PORT)

build-index:
	@$(resolve_py); \
	exec "$$py" scripts/build_index.py
