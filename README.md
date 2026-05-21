# Atom MVP Backend

FastAPI backend for the Atom MVP AI workbench.

## Features

- Demo auth with email and nickname
- GitHub OAuth login
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

Local and production configs can be kept separate:

```bash
cp .env.local.example .env.local
cp .env.production.example .env.production
```

The backend loads `.env` first, then an environment-specific file based on `APP_ENV`:

- `APP_ENV=development` loads `.env.local`
- `APP_ENV=production` loads `.env.production`

Real environment variables still override file values. Restart the backend after changing env files.

AI responses use DeepSeek V4 Pro through an OpenAI-compatible endpoint:

```env
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro
```

`OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL` remain as compatibility aliases.

GitHub OAuth needs a GitHub OAuth App. For local development, configure the app callback URL as:

```text
http://127.0.0.1:8000/api/auth/oauth/github/callback
```

Then set:

```env
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
AUTH_REDIRECT_BASE_URL=http://127.0.0.1:8000
FRONTEND_AUTH_CALLBACK_URL=http://127.0.0.1:5173/auth/callback
```

Start login by opening:

```text
http://127.0.0.1:8000/api/auth/oauth/github/login
```

After GitHub authorizes the user, the backend creates or reuses a local user by verified email, creates a local session token, and redirects to `FRONTEND_AUTH_CALLBACK_URL` with the token query parameter. Use a separate GitHub OAuth App for production because the callback URL should use the deployed API domain.

For production, set:

```env
AUTH_REDIRECT_BASE_URL=https://api.jiujiuwarehouse.com
FRONTEND_AUTH_CALLBACK_URL=https://atom.jiujiuwarehouse.com/auth/callback
BACKEND_CORS_ORIGINS=https://atom.jiujiuwarehouse.com
```

Then configure the production GitHub OAuth App callback URL as:

```text
https://api.jiujiuwarehouse.com/api/auth/oauth/github/callback
```

## Tests

```bash
pytest
python -m compileall app
```

## Demo Mode

If `DEEPSEEK_API_KEY`/`OPENAI_API_KEY` or `EXA_API_KEY` is absent, the backend uses mock providers so the complete MVP can still be demonstrated.
