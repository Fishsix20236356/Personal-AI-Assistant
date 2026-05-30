# Project: Agno Personal Assistant

## Architecture Reference
- 完整技术架构见 technical-architecture.md
- 基于 Agno 框架（Agent/Tool/Storage/Knowledge）
- FastAPI + PostgreSQL(pgvector) + SQLite(FTS5)

## Critical Design Rules
1. **会话存储分离**：Agno 管 session/runs/history，app_meta.db 管业务元数据
2. **session_id 是唯一贯穿主键**：格式 "{mode}_{uuid}"
3. **Knowledge 先删后插**：更新文档必须先 delete 旧内容再 load 新内容
4. **Tool 不用全局变量**：所有依赖通过 agent.dependencies 注入（Agno v2.5 API）
5. **SOP 会话隔离**：所有 todo CRUD 必须按 session_id 过滤
6. **线程安全**：watchdog 回调必须通过 loop.call_soon_threadsafe 入队
7. **模型选择**：统一使用 agno.models.openai.like.OpenAILike，不用 OpenAIChat

## Agno v2.5 API Mapping
- `agno.storage.sqlite.SqliteStorage` (not `agno.db.sqlite.SqliteDb`)
- `agno.knowledge.agent.AgentKnowledge` (not `agno.knowledge.knowledge.Knowledge`)
- `agno.embedder.openai.OpenAIEmbedder` (not `agno.knowledge.embedder.openai.OpenAIEmbedder`)
- `agno.document.chunking.fixed.FixedSizeChunking` / `.semantic.SemanticChunking`
- Agent constructor: `storage=` (not `db=`), `add_history_to_messages=` (not `add_history_to_context=`)
- Agent.run/arun: `message=` (not `input=`)
- Tool functions receive `agent: Agent`, access `agent.dependencies` and `agent.session_id`

## Tech Stack
- Python 3.12+
- agno v2.5 (Agent framework)
- FastAPI + uvicorn
- PostgreSQL + pgvector (知识库向量存储)
- SQLite (sessions, app metadata, wechat search with FTS5)
- watchdog (文件监听)
- APScheduler (定时任务)
- chonkie (语义分块)

## Code Style
- 原生 sqlite3（不用 SQLAlchemy ORM）
- 参数化 SQL，禁止字符串拼接
- Type hints 用 Python 3.12 语法（str | None 而非 Optional[str]）
- 所有异步操作用 async/await

## Testing
- pytest + pytest-asyncio
- 单元测试用 :memory: SQLite
- Mock LLM 调用，不在测试中真实请求 API

## File Layout
见 technical-architecture.md 第 2 节
