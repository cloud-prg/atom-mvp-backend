# Atom MVP Backend Implementation Plan

Goal: deliver a FastAPI backend for the GPT-like MVP with demo auth, conversations, messages, SSE streaming, mock/real provider boundaries, SQLite persistence, Alembic, tests, and Docker support.

Architecture:

- FastAPI routers expose auth, conversations, messages, chat stream, search, and health APIs.
- SQLAlchemy models own persistence and avoid SQLite-only assumptions where practical.
- Services own auth/session, message state, AI streaming, and search fallback behavior.
- Demo mode works without external API keys.

Verification:

- `pytest`
- `python -m compileall app`
- Docker build where available.

