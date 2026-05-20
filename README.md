# Atom MVP Backend

FastAPI backend for the Atom MVP AI workbench.

## Features

- Demo auth with email and nickname
- Session token authentication
- Conversations and messages persisted to SQLite
- SSE assistant streaming
- Mock AI provider when no API key is configured
- Mock search fallback
- Alembic migrations
- Docker-ready Uvicorn runtime

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

API health:

```bash
curl http://localhost:8000/api/health
```

## Environment

See `.env.example`.

## Tests

```bash
pytest
python -m compileall app
```

## Demo Mode

If `OPENAI_API_KEY` or `EXA_API_KEY` is absent, the backend uses mock providers so the complete MVP can still be demonstrated.

