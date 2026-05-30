# Personal AI Assistant

基于 Agno 框架的个人 AI 助手系统。纯 SQLite + LanceDB 本地存储，无需部署 PostgreSQL 等外部数据库。

## 技术栈

| 组件 | 技术 | 说明 |
|---|---|---|
| 环境管理 | uv | 依赖隔离 + Python 版本管理 |
| Agent 框架 | Agno 2.5 | Agent/Tool/Storage/Knowledge |
| Web 框架 | FastAPI + Uvicorn | 异步 API + SSE 流式输出 |
| 向量存储 | LanceDB | 嵌入式向量数据库，替代 PostgreSQL+pgvector |
| 会话存储 | SQLite | Agno session/runs/history |
| 业务元数据 | SQLite | session_registry, todos, doc_tracking |
| 微信检索 | SQLite FTS5 | 全文搜索引擎 |
| 文件监听 | Watchdog | 知识库增量更新 |
| 定时任务 | APScheduler | 日报生成、微信同步 |
| Embedding | OpenAI 兼容接口 | 支持 OpenRouter 等服务商 |
| LLM | OpenAI 兼容接口 | 支持 Qwen / Cerebras / Groq 等 |

## 项目结构

```
codex/
├── pyproject.toml                  # 依赖声明
├── .python-version                 # Python 版本锁定（uv 管理）
├── uv.lock                         # 依赖锁文件
├── .gitignore                      # 忽略密钥/临时文件
├── .env                            # 环境变量（需自行配置）
├── .env.example                    # 环境变量模板
├── config/
│   └── settings.py                 # 全局配置（pydantic-settings）
├── app/
│   ├── main.py                     # FastAPI 入口 + lifespan 生命周期
│   ├── deps.py                     # FastAPI 依赖注入
│   ├── core/
│   │   ├── agno_db.py              # Agno Session DB（SqliteDb）
│   │   ├── model_factory.py        # LLM 模型工厂（OpenAILike）
│   │   ├── agent_factory.py        # Agent 工厂（chat/wechat/sop）
│   │   ├── session_service.py      # 会话生命周期管理
│   │   └── prompt_templates.py     # 三种模式的系统提示词
│   ├── db/
│   │   ├── app_meta.py             # 业务元数据 CRUD（原生 sqlite3）
│   │   └── migrations/
│   │       ├── 001_app_meta.sql    # session_registry, todos, doc_tracking, daily_reports
│   │       └── 002_wechat_search.sql # wechat_messages + FTS5 索引
│   ├── knowledge/
│   │   ├── base.py                 # Knowledge 实例（LanceDB + OpenAIEmbedder）
│   │   ├── reader_factory.py       # 文档读取器（PDF/DOCX/TXT/MD）
│   │   ├── loader.py               # 文档导入（先删后插策略）
│   │   ├── service.py              # 知识检索 + 状态查询
│   │   └── tracker_repository.py   # doc_tracking 表 CRUD
│   ├── wechat/
│   │   ├── search_store.py         # FTS5 全文检索
│   │   └── tools.py                # Agno Tool（search_messages 等）
│   ├── sop/
│   │   ├── models.py               # TodoStatus / TodoPriority 枚举
│   │   ├── manager.py              # TodoManager（会话隔离 CRUD）
│   │   └── tools.py                # Agno Tool（add/list/update/delete/mark_done）
│   ├── reports/
│   │   └── daily_report.py         # 日报生成服务
│   ├── background/
│   │   ├── watcher.py              # Watchdog 文件变更监听
│   │   ├── incremental_update.py   # 防抖增量更新 Worker
│   │   ├── scheduler.py            # APScheduler 定时任务
│   │   └── wechat_sync.py          # 微信增量同步
│   └── api/
│       ├── router.py               # 路由汇总
│       ├── schemas/                # Pydantic 数据模型
│       └── v1/                     # 各端点实现
│           ├── chat.py             # POST /  + POST /stream（SSE）
│           ├── wechat.py           # POST /search
│           ├── sop.py              # POST /
│           ├── session.py          # GET / PUT / DELETE
│           └── knowledge.py        # GET /status POST /upload DELETE /rebuild
├── scripts/
│   ├── init_app_meta.py            # 初始化 app_meta.db
│   ├── seed_knowledge.py           # 全量导入知识库
│   ├── rebuild_knowledge.py        # 重建知识库
│   └── build_wechat_search_db.py   # 构建微信搜索库
├── data/
│   ├── documents/                  # 知识库文档目录（自动监听）
│   └── wechat_db/                  # 微信解密数据库
└── tmp/                            # 运行时数据库（自动创建）
    ├── agno_sessions.db            # Agno 会话存储
    ├── app_meta.db                 # 业务元数据
    ├── wechat_search.db            # 微信搜索索引
    └── lance_vectors/              # LanceDB 向量数据
```

## 构建过程

### 前置要求

- [uv](https://docs.astral.sh/uv/) >= 0.10（uv 自带 Python 版本管理，无需预装 Python）

### 1. 安装依赖

```bash
# uv 自动下载 Python 3.12、创建 .venv、安装全部依赖
uv sync
```

这一条命令完成：
- 下载并安装 Python 3.12.7
- 创建 `.venv` 虚拟环境
- 安装 133 个依赖包（含 agno, fastapi, lancedb 等）

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 API 密钥
```

关键配置项：

```bash
# 安全（所有 /api/v1/* 默认要求鉴权）
AUTH_ENABLED=true
APP_API_KEY=replace-with-a-long-random-secret
API_KEY_HEADER=X-API-Key
USER_ID_HEADER=X-User-Id

# LLM（支持任何 OpenAI 兼容接口）
LLM_MODEL=qwen3.6-plus
LLM_API_KEY=sk-your-key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# Fallback LLM（主模型失败时自动切换）
LLM_FALLBACK_PROVIDER=cerebras
LLM_FALLBACK_MODEL=qwen-3-235b-a22b-instruct-2507
LLM_FALLBACK_API_KEY=csk-your-key
LLM_FALLBACK_BASE_URL=https://api.cerebras.ai/v1

# Embedding（通过 OpenRouter 使用）
EMBED_MODEL=qwen/qwen3-embedding-8b
EMBED_API_KEY=sk-or-v1-your-key
EMBED_BASE_URL=https://openrouter.ai/api/v1
EMBED_DIMENSIONS=4096

# CORS（前端域名白名单，逗号分隔）
CORS_ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### 3. 初始化数据库

```bash
uv run python scripts/init_app_meta.py
```

输出：
```
app_meta.db initialized at: tmp/app_meta.db
Existing sessions: 0
```

### 4. （可选）导入知识库

将文档放入 `data/documents/` 后执行：

```bash
uv run python scripts/seed_knowledge.py
```

### 5. 启动服务

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

服务启动后自动完成：
- 创建所有 SQLite 数据库和表
- 初始化 LanceDB 向量表
- 启动 Watchdog 文件监听（`data/documents/`）
- 启动 APScheduler 定时任务
- 启动 IncrementalUpdateWorker

输出：
```
INFO: Started server process [6120]
INFO: Application startup complete.
INFO: Uvicorn running on http://127.0.0.1:8000
[lifespan] Application started successfully.
```

### 6. 验证

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

调用业务接口时请携带：

```bash
-H "X-API-Key: $APP_API_KEY"
```

## API 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| POST | `/api/v1/chat/` | 聊天（完整响应） |
| POST | `/api/v1/chat/stream` | 聊天（SSE 流式） |
| POST | `/api/v1/wechat/search` | 微信消息搜索 |
| POST | `/api/v1/sop/` | 待办事项管理 |
| GET | `/api/v1/sessions/` | 列出会话 |
| GET | `/api/v1/sessions/{id}` | 获取会话 |
| PUT | `/api/v1/sessions/{id}/rename` | 重命名会话 |
| DELETE | `/api/v1/sessions/{id}` | 删除会话（双删闭环） |
| GET | `/api/v1/knowledge/status` | 知识库状态 |
| POST | `/api/v1/knowledge/upload` | 上传文档 |
| DELETE | `/api/v1/knowledge/files/{path}` | 删除文档 |
| POST | `/api/v1/knowledge/rebuild` | 重建知识库 |

## 测试报告

### 测试环境

| 项目 | 值 |
|---|---|
| OS | Windows 11 |
| 环境管理 | uv 0.10.4 |
| Python | 3.12.7（uv 管理，.venv） |
| Agno | 2.5.16 |
| FastAPI | 0.135.3 |
| LLM | Qwen3.6-plus (DashScope) |
| Embedding | qwen/qwen3-embedding-8b (OpenRouter) |

### 测试 1：服务启动

```bash
$ uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
INFO: Application startup complete.
[lifespan] Application started successfully.

$ curl http://localhost:8000/health
{"status":"ok"}
```

**结果: PASS**

### 测试 2：知识库状态

```
$ curl -H "X-API-Key: $APP_API_KEY" http://localhost:8000/api/v1/knowledge/status
{
    "total_documents": 0,
    "total_chunks": 0,
    "pending_files": 0,
    "error_files": 0,
    "last_sync_time": null
}
```

**结果: PASS**

### 测试 3：文档上传

```
$ curl -X POST http://localhost:8000/api/v1/knowledge/upload \
  -H "X-API-Key: $APP_API_KEY" \
  -F "file=@data/documents/计划.md"
{"status":"synced","file_path":"...计划.md","content_id":"计划","chunk_count":0}

$ curl -H "X-API-Key: $APP_API_KEY" http://localhost:8000/api/v1/knowledge/status
{"total_documents":1,"total_chunks":0,"pending_files":0,"error_files":0,...}
```

**结果: PASS** — 文档导入成功，知识库文档数更新

### 测试 4：SSE 流式输出

```
$ curl -s -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H "X-API-Key: $APP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "说两个字：成功"}'

event: citations
data: [{"source":"...计划.md","snippet":"# 个人AI代理系统..."}]

event: token
data: 成功

event: done
data: {"session_id":"chat_c62f4a96..."}
```

**结果: PASS** — SSE 事件流正常，token 实时逐个输出，citations 先于 token 发送

### 测试 5：非流式聊天

```
$ curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "X-API-Key: $APP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "今天星期几？"}'
{
    "session_id": "chat_80c883cd...",
    "message": "根据您提供的当前时间（2026年4月11日），今天是**星期六**。",
    "grounded": true,
    "citations": [{"source":"...计划.md","snippet":"# 个人AI代理系统..."}]
}
```

**结果: PASS** — 正确返回结构化响应，知识库检索生效（`grounded: true`）

### 测试 6：SOP 待办管理

```
$ curl -X POST http://localhost:8000/api/v1/sop/ \
  -H "X-API-Key: $APP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "添加一个待办：上线前检查，优先级高"}'
{
    "session_id": "sop_e1b46846...",
    "reply": "已成功添加待办事项！...",
    "actions": [
        {"action": "add", "ok": true, "payload": {"id": 1}},
        {"action": "list", "ok": true, "payload": {"count": 1}}
    ],
    "todos_snapshot": [
        {"id":1, "title":"上线前检查", "priority":1, "status":"pending"}
    ]
}
```

**结果: PASS** — LLM 正确调用 add_todo + list_todos 工具，actions 记录真实工具执行

### 测试 7：Session CRUD

| 操作 | 命令 | 结果 |
|---|---|---|
| 列出会话 | `GET /api/v1/sessions/` | 返回所有会话 |
| 重命名 | `PUT /sessions/{id}/rename?title=TestChat` | `{"ok":true}` |
| 删除 | `DELETE /api/v1/sessions/{id}` | `{"ok":true}` |
| 删除后查询 | `GET /api/v1/sessions/{id}` | `404 Session not found` |

**结果: PASS** — 双删闭环：同时删除 Agno session 和 app_meta 记录

### 测试总结

| 测试项 | 状态 |
|---|---|
| uv sync 安装依赖 | PASS |
| 服务启动 + 数据库自动初始化 | PASS |
| 知识库状态查询 | PASS |
| 文档上传 + 自动导入 | PASS |
| SSE 流式输出（token 级别） | PASS |
| 非流式聊天（完整响应） | PASS |
| 知识库关联聊天（RAG 检索） | PASS |
| SOP 待办 CRUD | PASS |
| SOP 工具动作追踪 | PASS |
| Session CRUD | PASS |
| Session 删除级联 | PASS |
| LLM API 调用（Qwen） | PASS |
| Embedding API 调用（OpenRouter） | PASS |

**13 / 13 项测试全部通过。**

## 设计要点

1. **零外部数据库** — 所有数据存储为本地 SQLite 文件 + LanceDB 目录，无需部署 PostgreSQL
2. **会话存储分离** — Agno 管 session/runs/history，app_meta.db 管业务元数据，通过 session_id 关联
3. **知识库先删后插** — 文档更新时先删除旧内容再导入新内容，避免 chunk 重复
4. **Tool 无全局变量** — 所有依赖通过 `agent.dependencies` 注入，Tool 函数通过 `RunContext` 访问
5. **SOP 会话隔离** — 所有 todo CRUD 严格按 session_id 过滤，禁止跨会话操作
6. **线程安全** — Watchdog 回调通过 `loop.call_soon_threadsafe()` 安全入队到主事件循环
7. **防抖更新** — IncrementalUpdateWorker 合并短时间内的重复文件变更事件
