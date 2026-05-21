# Atom MVP Backend V2 Context Handoff

更新时间：2026-05-21

这份文档用于开启第二版后端开发，记录第一版已经完成的范围、技术选型、仓库状态、部署镜像、验证结果和后续开发注意事项。

## 项目目标

当前项目是一个 GPT-like / AI workbench MVP。第一版后端已经完成，核心目标是提供 demo 登录、用户会话、消息持久化、SSE 流式聊天、mock AI provider、mock search provider、OpenAPI / Apifox 导入、SQLite + Alembic、Docker 构建与阿里云 ACR 镜像推送。

第二版开发应继续围绕后端能力演进，除非用户重新明确要求，否则不要处理前端仓库。

## 用户偏好与约束

默认中文沟通。用户喜欢简洁、具体、可执行的说明，不希望频繁询问。除非涉及密钥、付费服务、破坏性操作、重大产品或架构取舍，否则倾向自主执行。

用户明确不喜欢 Next.js，不希望使用 Tailwind CSS。前端方向曾讨论为 React + Vite + TypeScript + React Router v7 + Ant Design + CSS Modules，但用户后来明确说前端不用继续处理，后续默认只做后端。

后端继续使用 Python、FastAPI、SQLAlchemy 2.x、Alembic、SQLite for MVP。提交前必须跑测试和验证。

## 仓库信息

后端仓库本地路径：

```text
/Users/cloud_prg/Documents/project/github/atom-mvp-backend
```

后端 GitHub：

```text
git@github.com:cloud-prg/atom-mvp-backend.git
```

当前后端分支：

```text
feature-repo-init
```

远端跟踪分支：

```text
origin/feature-repo-init
```

第一版提交：

```text
a37ccac feat: initialize FastAPI backend MVP
```

前端仓库本地路径：

```text
/Users/cloud_prg/Documents/project/github/atom-mvp-frontend
```

前端 GitHub：

```text
git@github.com:cloud-prg/atom-mvp-frontend.git
```

前端仓库里曾因中断前操作生成过一些未提交文件。用户后来明确说前端不用管，所以不要继续处理前端，也不要清理前端文件，除非用户明确要求。

## OpenSpec 与设计文档

OpenSpec change id：

```text
evolve-gpt-like-workbench-mvp
```

设计文档路径：

```text
/Users/cloud_prg/Documents/Codex/2026-05-20/find-skills-users-cloud-prg-agents/openspec/changes/evolve-gpt-like-workbench-mvp/design.md
```

设计方向为前后端分离，后端 FastAPI，SQLite MVP，未来可迁 PostgreSQL，SQLAlchemy + Alembic 管理模型和迁移，SSE 流式输出，Demo Mode 支持无真实 key 演示，OpenAI-compatible AI provider，Exa/mock search provider，Docker Compose 部署并兼容阿里云 ACR。

## 第一版后端能力

第一版已实现以下 API：

```text
GET  /api/health

POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me

GET    /api/conversations
POST   /api/conversations
GET    /api/conversations/{conversation_id}
DELETE /api/conversations/{conversation_id}

GET  /api/conversations/{conversation_id}/messages
POST /api/conversations/{conversation_id}/messages

POST /api/chat/stream
POST /api/search
```

已实现功能包括 demo auth、email + nickname 登录、bearer token、token hash 入库、`/api/auth/me` 校验登录态、会话 CRUD、消息创建与列表、SSE chat stream、mock AI streaming、mock search fallback、SQLite 持久化、Alembic 初始迁移、Dockerfile、docker-compose、OpenAPI 导出和 Apifox 导入文档。

## 后端关键文件

```text
app/main.py
app/core/config.py
app/db.py
app/deps.py
app/models.py
app/schemas.py

app/routers/auth.py
app/routers/conversations.py
app/routers/chat.py
app/routers/search.py

app/services/auth_service.py
app/services/conversation_service.py
app/services/chat_service.py
app/services/ai_provider.py
app/services/search_provider.py

alembic/env.py
alembic/versions/0001_initial_schema.py

tests/conftest.py
tests/test_api.py

Dockerfile
docker-compose.yml
.env.example
.dockerignore
.gitignore
README.md

docs/api-smoke.md
docs/apifox-guide.md
docs/implementation-plan.md
docs/openapi.json
```

## 数据模型

第一版已建表：

```text
users
sessions
conversations
messages
search_runs
search_results
```

`users` 包含 `id`、`email`、`nickname`、`created_at`。

`sessions` 包含 `id`、`user_id`、`token_hash`、`expires_at`、`created_at`。

`conversations` 包含 `id`、`user_id`、`title`、`created_at`、`updated_at`。

`messages` 包含 `id`、`conversation_id`、`role`、`content`、`status`、`client_message_id`、`created_at`、`updated_at`。其中 `unique(conversation_id, client_message_id)` 用于避免重复提交。

`search_runs` 包含 `id`、`conversation_id`、`message_id`、`query`、`provider`、`status`、`created_at`。

`search_results` 包含 `id`、`search_run_id`、`title`、`url`、`snippet`、`source`、`published_at`。

消息状态包括：

```text
pending
streaming
interrupted
completed
failed
```

搜索模式包括：

```text
off
auto
force
```

`auto` 会根据关键词判断是否搜索，例如“最新”“今天”“新闻”“价格”“竞品”“资料”“调研”“today”“latest”“news”“price”。

## SSE 与 Demo Provider

`POST /api/chat/stream` 返回 SSE。已实现事件包括：

```text
message.created
search.completed
search.failed
message.delta
message.completed
message.interrupted
```

Demo mode 下，如果没有真实 key，AI 使用 mock streaming，Search 使用 mock results。

## 本地启动

进入后端目录：

```bash
cd /Users/cloud_prg/Documents/project/github/atom-mvp-backend
```

准备环境文件：

```bash
cp .env.example .env
```

迁移数据库：

```bash
.venv/bin/alembic upgrade head
```

启动服务：

```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

常用地址：

```text
Swagger UI: http://127.0.0.1:8000/docs
OpenAPI:    http://127.0.0.1:8000/openapi.json
Health:     http://127.0.0.1:8000/api/health
```

如果 8000 端口被旧 uvicorn 占用，可以停止旧进程：

```bash
pkill -f "uvicorn app.main:app"
```

## Apifox

已生成 OpenAPI 文件：

```text
/Users/cloud_prg/Documents/project/github/atom-mvp-backend/docs/openapi.json
```

Apifox 可以通过 URL 导入：

```text
http://127.0.0.1:8000/openapi.json
```

也可以通过文件导入：

```text
/Users/cloud_prg/Documents/project/github/atom-mvp-backend/docs/openapi.json
```

Apifox 环境变量建议：

```text
baseUrl = http://127.0.0.1:8000
token =
conversationId =
```

登录接口：

```text
POST /api/auth/login
```

Body：

```json
{
  "email": "demo@example.com",
  "nickname": "Demo"
}
```

拿到 token 后，后续接口 Header：

```text
Authorization: Bearer {{token}}
```

建议测试顺序：

```text
health -> login -> me -> create conversation -> create message -> list messages -> search -> chat stream
```

Apifox 指南文档：

```text
/Users/cloud_prg/Documents/project/github/atom-mvp-backend/docs/apifox-guide.md
```

Apifox MCP 已确认存在，可基于 OpenAPI 启动：

```bash
npx apifox-mcp-server --oas http://127.0.0.1:8000/openapi.json
```

或：

```bash
npx apifox-mcp-server --oas /Users/cloud_prg/Documents/project/github/atom-mvp-backend/docs/openapi.json
```

当前 Codex 环境没有预配置能直接写入用户 Apifox 工作区的 MCP 凭证。

## 验证记录

第一版最终验证通过：

```bash
.venv/bin/pytest -q
# 4 passed
```

```bash
.venv/bin/python -m compileall app
# passed
```

```bash
.venv/bin/alembic upgrade head
# passed
```

```bash
docker compose build backend
# built successfully
```

HTTP 烟测通过：`GET /api/health` 返回 ok，`POST /api/auth/login` 返回 token，`POST /api/chat/stream` 用 Python/httpx 验证 SSE 正常。

OpenAPI 验证通过：

```bash
python3 -m json.tool docs/openapi.json
```

## 已解决问题

一开始 `.venv` 是 Python 3.9，但项目要求 `>=3.11`，已用 `/opt/homebrew/bin/python3.11` 重建 `.venv`。

原先 `uvicorn[standard]>=0.30.0` 导致 pip 解析 `uvloop/watchfiles/websockets` 很慢，已改为 `uvicorn>=0.30.0`。

Pydantic `EmailStr` 需要 `email-validator`，已补依赖 `email-validator>=2.2.0`。

SQLite 读回 datetime 是 naive，和 aware UTC 比较报错，已在 `app/deps.py` 中归一化为 aware UTC。

Docker build 需要提权访问 Docker daemon / buildx 状态。Git 创建分支和 commit 需要提权写 `.git` 元数据。

## Docker 与镜像

已构建并推送阿里云 ACR 镜像：

```text
registry.cn-hangzhou.aliyuncs.com/cloud_prg_hub/atom_mvp:feature-repo-init
```

digest：

```text
sha256:7e2095fc596e6e3736f3bfc97887dbad4b56abb3a7ba0490fcea2d408eb61665
```

阿里云 ACR 信息：

```text
registry: registry.cn-hangzhou.aliyuncs.com
namespace: cloud_prg_hub
repo: atom_mvp
username: yunshangzhou98
vpc endpoint: registry-vpc.cn-hangzhou.aliyuncs.com
```

不要提交 registry 凭证。

## 第二版开发入口

开始第二版前建议执行：

```bash
cd /Users/cloud_prg/Documents/project/github/atom-mvp-backend
git status --short --branch
```

如需从第一版继续开发，可以新建分支：

```bash
git checkout -b feature-v2-xxx
```

第二版开发前应先明确是否涉及新增 API、数据模型变更、Alembic migration、真实 AI provider、真实 Exa provider、demo auth 增强、SSE 恢复/重试增强、Apifox 文档或测试用例增强。

提交前必须跑：

```bash
.venv/bin/pytest -q
.venv/bin/python -m compileall app
.venv/bin/alembic upgrade head
```

如涉及 Docker：

```bash
docker compose build backend
```

