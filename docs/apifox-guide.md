# Apifox Import And Manual Test Guide

This backend is a FastAPI service, so it exposes OpenAPI automatically.

## Files

- Static OpenAPI export: `docs/openapi.json`
- Runtime OpenAPI URL: `http://127.0.0.1:8000/openapi.json`
- Swagger UI: `http://127.0.0.1:8000/docs`

## Start Backend Locally

```bash
cd /Users/cloud_prg/Documents/project/github/atom-mvp-backend
cp .env.example .env
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

Expected:

```json
{
  "status": "ok",
  "env": "development",
  "demo_mode": true,
  "mock_ai": true,
  "mock_search": true
}
```

## Import Into Apifox

Recommended import source:

```text
/Users/cloud_prg/Documents/project/github/atom-mvp-backend/docs/openapi.json
```

Alternative runtime import source:

```text
http://127.0.0.1:8000/openapi.json
```

In Apifox:

1. Create or open a project.
2. Choose Import.
3. Select OpenAPI / Swagger.
4. Import `docs/openapi.json`, or paste the runtime OpenAPI URL.
5. Set environment base URL:

```text
http://127.0.0.1:8000
```

## Authentication Setup

Call login:

```http
POST /api/auth/login
Content-Type: application/json
```

Body:

```json
{
  "email": "demo@example.com",
  "nickname": "Demo"
}
```

Copy `token` from the response.

Set Apifox environment variable:

```text
token=<copied token>
```

For authenticated requests, add header:

```text
Authorization: Bearer {{token}}
```

## Suggested Manual Test Order

### 1. Health

```http
GET /api/health
```

Expected: `status` is `ok`.

### 2. Login

```http
POST /api/auth/login
```

Expected:

- Returns `token`.
- Returns normalized user email.

### 3. Me

```http
GET /api/auth/me
Authorization: Bearer {{token}}
```

Expected:

- Returns current user.
- Returns `401` if token is missing or invalid.

### 4. Create Conversation

```http
POST /api/conversations
Authorization: Bearer {{token}}
Content-Type: application/json
```

Body:

```json
{
  "title": "Manual Apifox Test"
}
```

Expected:

- Returns conversation `id`.
- Returns title.

Save `id` as Apifox variable:

```text
conversationId=<created id>
```

### 5. Create Message

```http
POST /api/conversations/{{conversationId}}/messages
Authorization: Bearer {{token}}
Content-Type: application/json
```

Body:

```json
{
  "role": "user",
  "content": "hello from Apifox",
  "client_message_id": "apifox-message-1"
}
```

Expected:

- Message is persisted.
- `status` is `completed`.

### 6. List Messages

```http
GET /api/conversations/{{conversationId}}/messages
Authorization: Bearer {{token}}
```

Expected:

- Contains the message created in step 5.

### 7. Search Fallback

```http
POST /api/search
Authorization: Bearer {{token}}
Content-Type: application/json
```

Body:

```json
{
  "query": "latest AI workbench patterns",
  "mode": "force"
}
```

Expected in demo mode:

- `provider` is `mock`.
- `status` is `completed`.
- `results` has mock search results.

### 8. Chat Stream

```http
POST /api/chat/stream
Authorization: Bearer {{token}}
Content-Type: application/json
```

Body:

```json
{
  "conversation_id": "{{conversationId}}",
  "content": "今天的 AI 工作台怎么做？",
  "client_message_id": "apifox-stream-1",
  "search_mode": "auto"
}
```

Expected SSE events:

```text
message.created
search.completed
message.delta
message.completed
```

If Apifox does not render SSE incrementally, verify the same endpoint with:

```bash
TOKEN="<copied token>"
curl -N http://127.0.0.1:8000/api/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"今天的 AI 工作台怎么做？","client_message_id":"curl-stream-1","search_mode":"auto"}'
```

## Apifox MCP

Apifox does have MCP support. This Codex environment does not currently have an Apifox MCP server configured with workspace credentials, but the generated OpenAPI file can be used as an MCP data source.

Official Apifox MCP server examples support OpenAPI input:

```bash
npx apifox-mcp-server --oas http://127.0.0.1:8000/openapi.json
```

or:

```bash
npx apifox-mcp-server --oas /Users/cloud_prg/Documents/project/github/atom-mvp-backend/docs/openapi.json
```

For an MCP-compatible client, configure a local stdio server roughly like this:

```json
{
  "mcpServers": {
    "atom-mvp-api": {
      "command": "npx",
      "args": [
        "apifox-mcp-server",
        "--oas",
        "/Users/cloud_prg/Documents/project/github/atom-mvp-backend/docs/openapi.json"
      ]
    }
  }
}
```

This lets an AI coding tool query the backend API definitions from the exported OpenAPI document.

If you want the MCP server to read an existing Apifox project directly, configure it with the Apifox project/API access settings required by your Apifox account. Do not commit those tokens to this repository.

The reliable workflow is:

1. Export OpenAPI from FastAPI.
2. Import `docs/openapi.json` into Apifox.
3. Use Apifox environments for `baseUrl`, `token`, and `conversationId`.

Do not put Apifox tokens, registry passwords, or production secrets into the repository.
