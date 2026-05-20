# Backend API Smoke Test

Start the backend:

```bash
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Health:

```bash
curl http://localhost:8000/api/health
```

Login:

```bash
curl -s http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","nickname":"Demo"}'
```

Chat stream:

```bash
TOKEN="<token from login>"
curl -N http://localhost:8000/api/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"content":"今天的 AI 工作台怎么做","client_message_id":"smoke-1","search_mode":"auto"}'
```

