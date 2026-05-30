# 技术架构设计文档（修订版）


## 1. 修订后的总体架构

### 1.1 设计原则

1. **Agno 只负责 Agent 会话、历史、状态和推理编排。**
2. **业务元数据和业务表由应用自己管理，不与 Agno Session 表混写职责。**
3. **知识库删改必须走 Contents DB，不能只删向量。**
4. **Tool 不使用全局单例，统一走 `dependencies` / `run_context`。**
5. **面向 API 的可预测性优先于纯 Agentic“全自动”。**

### 1.2 存储分层

| 层 | 存储 | 职责 |
|---|---|---|
| Agno Session 层 | `tmp/agno_sessions.db` | 保存 session、runs、session_state、聊天历史 |
| 应用元数据层 | `tmp/app_meta.db` | 保存 `session_registry`、`todos`、`doc_tracking`、`daily_reports` |
| 知识库层 | PostgreSQL + pgvector | 保存 `knowledge_contents` 和向量 chunks |
| 微信检索层 | `tmp/wechat_search.db` | 保存派生搜索表和 FTS5 索引 |

---

## 2. 工程目录结构

```text
project-root/
├── pyproject.toml
├── .env
├── .env.example
├── config/
│   └── settings.py
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── deps.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── schemas/
│   │   │   ├── chat.py
│   │   │   ├── wechat.py
│   │   │   ├── sop.py
│   │   │   ├── knowledge.py
│   │   │   └── session.py
│   │   └── v1/
│   │       ├── chat.py
│   │       ├── wechat.py
│   │       ├── sop.py
│   │       ├── knowledge.py
│   │       └── session.py
│   │
│   ├── core/
│   │   ├── model_factory.py
│   │   ├── agno_db.py
│   │   ├── agent_factory.py
│   │   ├── session_service.py
│   │   └── prompt_templates.py
│   │
│   ├── knowledge/
│   │   ├── base.py
│   │   ├── reader_factory.py
│   │   ├── loader.py
│   │   ├── service.py
│   │   └── tracker_repository.py
│   │
│   ├── wechat/
│   │   ├── source_reader.py
│   │   ├── search_store.py
│   │   ├── sync.py
│   │   └── tools.py
│   │
│   ├── sop/
│   │   ├── manager.py
│   │   ├── tools.py
│   │   └── models.py
│   │
│   ├── reports/
│   │   └── daily_report.py
│   │
│   ├── db/
│   │   ├── app_meta.py
│   │   ├── pg.py
│   │   └── migrations/
│   │       ├── 001_app_meta.sql
│   │       └── 002_wechat_search.sql
│   │
│   └── background/
│       ├── watcher.py
│       ├── incremental_update.py
│       ├── scheduler.py
│       └── wechat_sync.py
│
├── scripts/
│   ├── init_app_meta.py
│   ├── seed_knowledge.py
│   ├── rebuild_knowledge.py
│   └── build_wechat_search_db.py
│
├── data/
│   ├── documents/
│   └── wechat_db/
│
└── tmp/
    ├── agno_sessions.db
    ├── app_meta.db
    └── wechat_search.db
```

---

## 3. 全局配置

### 3.1 `config/settings.py`

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- LLM ---
    LLM_PROVIDER: str = "qwen"
    LLM_MODEL: str = "qwen-plus"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096

    LLM_FALLBACK_PROVIDER: str | None = "cerebras"
    LLM_FALLBACK_MODEL: str | None = "qwen-3-235b-a22b-instruct-2507"
    LLM_FALLBACK_API_KEY: str | None = None
    LLM_FALLBACK_BASE_URL: str | None = "https://api.cerebras.ai/v1"

    # --- Embedding / Knowledge ---
    EMBED_MODEL: str = "qwen/qwen3-embedding-8b"
    EMBED_API_KEY: str = ""
    EMBED_BASE_URL: str = "https://openrouter.ai/api/v1"
    EMBED_DIMENSIONS: int = 4096
    PG_DSN: str = "postgresql+psycopg://user:pass@localhost:5432/knowledge"
    PG_VECTOR_TABLE: str = "knowledge_vectors"
    PG_CONTENT_TABLE: str = "knowledge_contents"
    KNOWLEDGE_MAX_RESULTS: int = 8

    # --- Local DBs ---
    AGNO_DB_PATH: str = "tmp/agno_sessions.db"
    APP_META_DB_PATH: str = "tmp/app_meta.db"
    WECHAT_SEARCH_DB_PATH: str = "tmp/wechat_search.db"

    # --- File Ingestion ---
    WATCH_DIR: str = "data/documents"
    CHUNKING_STRATEGY: str = "semantic"
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 200
    SEMANTIC_SIMILARITY_THRESHOLD: float = 0.5
    FILE_DEBOUNCE_MS: int = 800

    # --- WeChat ---
    WECHAT_RAW_DB_PATH: str = "data/wechat_db/decrypted.db"
    WECHAT_SYNC_BATCH_SIZE: int = 5000

    # --- Runtime ---
    DEFAULT_TIMEZONE: str = "Asia/Shanghai"
    DAILY_REPORT_CRON: str = "0 8 * * *"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    AGNO_TELEMETRY: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
```

### 3.2 关键说明

- **将 `assistant.db` 拆为两个文件：**
  - `agno_sessions.db`：只给 Agno Session Storage 使用
  - `app_meta.db`：只给业务表使用
- **将微信检索索引落盘到 `wechat_search.db`**，避免服务每次启动全量重建内存索引。

---

## 4. 数据存储与表结构

### 4.1 `app_meta.db` 表结构

```sql
CREATE TABLE IF NOT EXISTS session_registry (
    session_id    TEXT PRIMARY KEY,
    mode          TEXT NOT NULL CHECK(mode IN ('chat', 'wechat', 'sop')),
    title         TEXT DEFAULT '',
    user_id       TEXT DEFAULT '',
    is_archived   INTEGER NOT NULL DEFAULT 0,
    last_run_at   TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_session_registry_mode
    ON session_registry(mode);

CREATE INDEX IF NOT EXISTS idx_session_registry_updated_at
    ON session_registry(updated_at DESC);


CREATE TABLE IF NOT EXISTS todos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL,
    title         TEXT NOT NULL,
    detail        TEXT DEFAULT '',
    priority      INTEGER NOT NULL DEFAULT 2 CHECK(priority IN (0,1,2,3)),
    status        TEXT NOT NULL DEFAULT 'pending'
                  CHECK(status IN ('pending','doing','done','cancelled')),
    due_date      TEXT,
    tags_json     TEXT NOT NULL DEFAULT '[]',
    created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (session_id) REFERENCES session_registry(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_todos_session_status
    ON todos(session_id, status);

CREATE INDEX IF NOT EXISTS idx_todos_session_priority_due
    ON todos(session_id, priority, due_date);


CREATE TABLE IF NOT EXISTS doc_tracking (
    file_path        TEXT PRIMARY KEY,
    content_id       TEXT,
    file_hash        TEXT NOT NULL,
    file_size        INTEGER NOT NULL,
    chunk_count      INTEGER NOT NULL DEFAULT 0,
    status           TEXT NOT NULL CHECK(status IN ('pending','synced','error')),
    last_synced_at   TEXT,
    last_error       TEXT DEFAULT '',
    created_at       TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);


CREATE TABLE IF NOT EXISTS daily_reports (
    report_date    TEXT PRIMARY KEY,
    summary_md     TEXT NOT NULL,
    source_sessions_json TEXT NOT NULL DEFAULT '[]',
    created_at     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
```

### 4.2 Agno Session Storage

Agno Session Storage 不再手写表结构，统一交给官方 `SqliteDb` 管理：

```python
from agno.db.sqlite import SqliteDb
from config.settings import settings


def build_agno_db() -> SqliteDb:
    return SqliteDb(
        db_file=settings.AGNO_DB_PATH,
        session_table="agent_sessions",
    )
```

**职责边界：**

- `agent_sessions` 是聊天历史、tool 调用、session_state 的真源
- `session_registry` 是 UI/业务元数据的真源
- 二者通过同一个 `session_id` 关联，但不互相代写内部结构

### 4.3 PostgreSQL 知识库结构

```python
from functools import lru_cache

from agno.db.postgres import PostgresDb
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector, SearchType

from config.settings import settings


@lru_cache(maxsize=1)
def get_shared_knowledge() -> Knowledge:
    embedder = OpenAIEmbedder(
        id=settings.EMBED_MODEL,
        api_key=settings.EMBED_API_KEY,
        base_url=settings.EMBED_BASE_URL,
    )

    return Knowledge(
        contents_db=PostgresDb(
            db_url=settings.PG_DSN,
            knowledge_table=settings.PG_CONTENT_TABLE,
        ),
        vector_db=PgVector(
            table_name=settings.PG_VECTOR_TABLE,
            db_url=settings.PG_DSN,
            search_type=SearchType.hybrid,
            embedder=embedder,
        ),
        max_results=settings.KNOWLEDGE_MAX_RESULTS,
    )
```

**修订要点：**

- `contents_db` 必开，因为后续需要列举内容、删除内容、追踪元数据。
- 每次入库必须写 `metadata.source_path` 与 `metadata.file_hash`。
- 文档删除必须优先调用 `knowledge.remove_content_by_id(content_id)`，不能只删向量。

### 4.4 微信搜索库（`wechat_search.db`）

原方案的“启动时构建全量内存倒排索引”被替换为派生搜索库：

```sql
CREATE TABLE IF NOT EXISTS wechat_messages (
    row_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    msg_id         TEXT NOT NULL UNIQUE,
    talker         TEXT NOT NULL,
    talker_name    TEXT NOT NULL,
    room_id        TEXT DEFAULT '',
    room_name      TEXT DEFAULT '',
    content        TEXT NOT NULL,
    msg_type       INTEGER NOT NULL,
    ts             INTEGER NOT NULL,
    date_str       TEXT NOT NULL,
    is_self        INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_wechat_messages_talker_ts
    ON wechat_messages(talker, ts DESC);

CREATE INDEX IF NOT EXISTS idx_wechat_messages_room_ts
    ON wechat_messages(room_id, ts DESC);

CREATE INDEX IF NOT EXISTS idx_wechat_messages_date_ts
    ON wechat_messages(date_str, ts DESC);

CREATE VIRTUAL TABLE IF NOT EXISTS wechat_messages_fts USING fts5(
    content,
    talker_name,
    room_name,
    content='wechat_messages',
    content_rowid='row_id',
    tokenize='unicode61'
);
```

**为什么重写这一块：**

- 不再要求服务启动时全量扫描微信库
- 可增量同步
- 查询语义更稳定，资源占用更可控
- 更适合大数据量聊天记录

---

## 5. API 契约

### 5.1 Chat

```python
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str | None = None
    user_id: str | None = None
    message: str = Field(..., min_length=1, max_length=4000)


class Citation(BaseModel):
    content_id: str
    source: str
    snippet: str
    score: float | None = None


class ChatResponse(BaseModel):
    session_id: str
    message: str
    grounded: bool
    citations: list[Citation] = []
    uncertain_points: list[str] = []
    next_steps: list[str] = []
```

**修订：**

- 删除 `stream` 请求字段，改为独立 `/chat/stream` 路由，避免协议歧义。
- 删除数值型 `confidence`，改为 `grounded: bool`。
  数值置信度在当前方案里没有稳定计算依据，保留只会制造“伪精度”。

### 5.2 WeChat

```python
class WeChatSearchRequest(BaseModel):
    session_id: str | None = None
    user_id: str | None = None
    query: str = Field(..., min_length=1, max_length=2000)


class WeChatMessageOut(BaseModel):
    msg_id: str
    talker_name: str
    room_name: str | None = None
    content: str
    timestamp: int
    date_str: str
    is_self: bool


class WeChatSearchResponse(BaseModel):
    session_id: str
    answer: str
    messages: list[WeChatMessageOut]
    total_count: int
```

### 5.3 SOP

```python
class TodoStatus(str, Enum):
    PENDING = "pending"
    DOING = "doing"
    DONE = "done"
    CANCELLED = "cancelled"


class TodoPriority(int, Enum):
    URGENT = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class TodoItem(BaseModel):
    id: int | None = None
    session_id: str
    title: str
    detail: str = ""
    priority: TodoPriority = TodoPriority.NORMAL
    status: TodoStatus = TodoStatus.PENDING
    due_date: str | None = None
    tags: list[str] = []
    created_at: str | None = None
    updated_at: str | None = None


class SopAction(BaseModel):
    action: str
    ok: bool
    payload: dict = Field(default_factory=dict)


class SopRequest(BaseModel):
    session_id: str | None = None
    user_id: str | None = None
    message: str = Field(..., min_length=1, max_length=2000)


class SopResponse(BaseModel):
    session_id: str
    reply: str
    actions: list[SopAction]
    todos_snapshot: list[TodoItem]
```

**修订：**

- 删除“先让 LLM 输出命令 JSON，再二次解析”的主链路设计。
- SOP 改为标准 Agno Tool 模式，`actions` 直接记录本次真实执行的工具动作。

### 5.4 Session / Knowledge

```python
class SessionInfo(BaseModel):
    session_id: str
    mode: str
    title: str
    is_archived: bool
    last_run_at: str | None = None
    created_at: str
    updated_at: str


class KnowledgeStatusResponse(BaseModel):
    total_documents: int
    total_chunks: int
    pending_files: int
    error_files: int
    last_sync_time: str | None = None
```

---

## 6. 核心模块实现规格

### 6.1 模型工厂：统一改为 `OpenAILike`

依据 Agno 官方文档，OpenAI-compatible 端点优先使用 `OpenAILike`。

```python
from dataclasses import dataclass

from agno.models.openai.like import OpenAILike

from config.settings import settings


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    model: str
    api_key: str
    base_url: str


def get_primary_model_config() -> ModelConfig:
    return ModelConfig(
        provider=settings.LLM_PROVIDER,
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
    )


def get_fallback_model_config() -> ModelConfig | None:
    if not settings.LLM_FALLBACK_PROVIDER:
        return None
    return ModelConfig(
        provider=settings.LLM_FALLBACK_PROVIDER,
        model=settings.LLM_FALLBACK_MODEL or "",
        api_key=settings.LLM_FALLBACK_API_KEY or "",
        base_url=settings.LLM_FALLBACK_BASE_URL or "",
    )


def build_model(cfg: ModelConfig | None = None) -> OpenAILike:
    cfg = cfg or get_primary_model_config()
    return OpenAILike(
        id=cfg.model,
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )
```

**修订要点：**

- 不再直接写 `OpenAIChat(base_url=...)` 作为 OpenAI-compatible 抽象。
- fallback 只在模型调用层触发，不吞掉业务错误和 tool 错误。

### 6.2 Agent 工厂

```python
from agno.agent import Agent

from app.core.agno_db import build_agno_db
from app.core.model_factory import build_model
from app.core.prompt_templates import (
    CHAT_INSTRUCTIONS,
    WECHAT_INSTRUCTIONS,
    SOP_INSTRUCTIONS,
)
from config.settings import settings


def create_chat_agent(model=None) -> Agent:
    return Agent(
        model=model or build_model(),
        db=build_agno_db(),
        instructions=CHAT_INSTRUCTIONS,
        add_history_to_context=True,
        num_history_runs=3,
        read_chat_history=False,
        search_session_history=False,
        add_datetime_to_context=True,
        timezone_identifier=settings.DEFAULT_TIMEZONE,
        markdown=True,
        retries=2,
        delay_between_retries=1,
    )


def create_wechat_agent(model=None) -> Agent:
    return Agent(
        model=model or build_model(),
        db=build_agno_db(),
        instructions=WECHAT_INSTRUCTIONS,
        add_history_to_context=True,
        num_history_runs=2,
        add_datetime_to_context=True,
        timezone_identifier=settings.DEFAULT_TIMEZONE,
        markdown=True,
        tool_call_limit=6,
        retries=2,
        delay_between_retries=1,
    )


def create_sop_agent(model=None, tools=None) -> Agent:
    return Agent(
        model=model or build_model(),
        db=build_agno_db(),
        instructions=SOP_INSTRUCTIONS,
        tools=tools or [],
        add_history_to_context=True,
        num_history_runs=3,
        add_datetime_to_context=True,
        timezone_identifier=settings.DEFAULT_TIMEZONE,
        markdown=True,
        tool_call_limit=8,
        retries=2,
        delay_between_retries=1,
    )
```

**修订要点：**

- `session_id` 不在工厂阶段固定写死，统一在 `run()/arun()` 时传入。
- `read_chat_history`、`search_session_history` 不与常规短历史默认叠加，避免无谓放大上下文。

### 6.3 Session Service

```python
import uuid

from app.db.app_meta import AppMetaRepository
from app.core.agent_factory import (
    create_chat_agent,
    create_wechat_agent,
    create_sop_agent,
)


class SessionService:
    def __init__(self, repo: AppMetaRepository):
        self.repo = repo

    def ensure_session(self, session_id: str | None, mode: str, user_id: str | None) -> str:
        sid = session_id or f"{mode}_{uuid.uuid4().hex}"
        self.repo.upsert_session(session_id=sid, mode=mode, user_id=user_id or "")
        return sid

    def touch_session(self, session_id: str, title: str | None = None) -> None:
        self.repo.touch_session(session_id=session_id, title=title)

    def rename_session(self, session_id: str, title: str, mode: str) -> None:
        self.repo.rename_session(session_id=session_id, title=title)
        # 可选同步到 Agno 的 session name，方便未来接 AgentOS UI。
        agent = self._agent_for_mode(mode)
        agent.set_session_name(session_id=session_id, session_name=title)

    def delete_session(self, session_id: str, mode: str) -> None:
        agent = self._agent_for_mode(mode)
        agent.delete_session(session_id=session_id)
        self.repo.delete_session_cascade(session_id=session_id)

    def _agent_for_mode(self, mode: str):
        if mode == "chat":
            return create_chat_agent()
        if mode == "wechat":
            return create_wechat_agent()
        return create_sop_agent()
```

**修订要点：**

- 会话创建、重命名、删除都必须经过 `SessionService`。
- `agent.delete_session()` 成为删除历史的明确实现，不再写成抽象描述。

### 6.4 Chat 主链路：应用层检索 + Agent 生成

> 架构判断：这是本次最重要的落地优化。
> `search_knowledge=True` 很适合 Agentic RAG，但 API 层如果要求稳定引用、稳定响应结构和可控延迟，更适合应用层先检索、再把上下文交给 Agent 生成。

#### 6.4.1 输出模型

```python
from pydantic import BaseModel, Field


class ChatAgentOutput(BaseModel):
    answer: str = Field(description="给用户的最终回答")
    uncertain_points: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
```

#### 6.4.2 Chat Service

```python
from app.api.schemas.chat import ChatResponse
from app.core.agent_factory import create_chat_agent
from app.core.session_service import SessionService
from app.knowledge.service import KnowledgeService


class ChatService:
    def __init__(
        self,
        session_service: SessionService,
        knowledge_service: KnowledgeService,
    ):
        self.session_service = session_service
        self.knowledge_service = knowledge_service

    async def run_chat(self, req) -> ChatResponse:
        session_id = self.session_service.ensure_session(
            session_id=req.session_id,
            mode="chat",
            user_id=req.user_id,
        )

        citations = await self.knowledge_service.search_references(req.message)
        dependencies = {
            "knowledge_refs": [c.model_dump() for c in citations],
        }

        agent = create_chat_agent()
        response = await agent.arun(
            input=req.message,
            session_id=session_id,
            user_id=req.user_id,
            dependencies=dependencies,
            add_dependencies_to_context=True,
            output_schema=ChatAgentOutput,
        )

        self.session_service.touch_session(session_id=session_id)

        return ChatResponse(
            session_id=session_id,
            message=response.content.answer,
            grounded=bool(citations),
            citations=citations,
            uncertain_points=response.content.uncertain_points,
            next_steps=response.content.next_steps,
        )
```

#### 6.4.3 `/chat/stream`

流式接口改为直接映射 Agno 官方 `RunOutputEvent`：

- `RunEvent.run_content` -> SSE `token`
- `RunEvent.tool_call_started` -> SSE `tool_call_started`
- `RunEvent.tool_call_completed` -> SSE `tool_call_completed`
- `RunEvent.run_completed` -> SSE `done`
- `RunEvent.run_error` -> SSE `error`

这样就不需要自造一套与 Agno 内部事件脱节的流协议。

### 6.5 Knowledge Loader：明确“先删后插”

#### 6.5.1 Reader 工厂

```python
from agno.knowledge.chunking.fixed import FixedSizeChunking
from agno.knowledge.chunking.semantic import SemanticChunking
from agno.knowledge.reader.docling_reader import DoclingReader

from config.settings import settings


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".md", ".txt", ".html"}


def build_docling_reader() -> DoclingReader:
    if settings.CHUNKING_STRATEGY == "semantic":
        chunking_strategy = SemanticChunking(
            chunk_size=settings.CHUNK_SIZE,
            similarity_threshold=settings.SEMANTIC_SIMILARITY_THRESHOLD,
        )
    else:
        chunking_strategy = FixedSizeChunking(
            chunk_size=settings.CHUNK_SIZE,
            overlap=settings.CHUNK_OVERLAP,
        )

    return DoclingReader(chunking_strategy=chunking_strategy)
```

#### 6.5.2 Loader

```python
import hashlib
from pathlib import Path

from app.knowledge.base import get_shared_knowledge


class KnowledgeLoader:
    def __init__(self, tracker_repo):
        self.knowledge = get_shared_knowledge()
        self.tracker_repo = tracker_repo

    def ingest(self, file_path: str) -> dict:
        path = Path(file_path).resolve()
        file_hash = self._hash_file(path)
        record = self.tracker_repo.get(str(path))

        if record and record["file_hash"] == file_hash and record["status"] == "synced":
            return {"status": "skipped", "file_path": str(path)}

        # 先删旧内容，避免重复 chunk / 旧向量残留
        if record and record.get("content_id"):
            self.knowledge.remove_content_by_id(record["content_id"])

        metadata = {
            "source_path": str(path),
            "file_hash": file_hash,
        }
        self.knowledge.insert(
            name=path.name,
            path=str(path),
            metadata=metadata,
            reader=build_docling_reader(),
        )

        content_id = self._find_content_id_by_path(str(path))
        chunk_count = self._count_chunks_by_path(str(path))

        self.tracker_repo.upsert(
            file_path=str(path),
            content_id=content_id,
            file_hash=file_hash,
            file_size=path.stat().st_size,
            chunk_count=chunk_count,
            status="synced",
            last_error="",
        )
        return {"status": "synced", "file_path": str(path), "content_id": content_id}

    def delete(self, file_path: str) -> None:
        path = str(Path(file_path).resolve())
        record = self.tracker_repo.get(path)
        if record and record.get("content_id"):
            self.knowledge.remove_content_by_id(record["content_id"])
        else:
            self._delete_by_metadata_fallback(path)
        self.tracker_repo.delete(path)

    def rebuild_all(self) -> None:
        self.knowledge.remove_all_content()
        self.tracker_repo.delete_all()
        for path in Path("data/documents").rglob("*"):
            if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                self.ingest(str(path))

    def _hash_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
```

**修订要点：**

- `delete()` 不再写成“以 SDK 当前版本为准”。
- `rebuild_all()` 使用官方 `remove_all_content()`。
- 文档版本更新不再残留旧内容。

### 6.6 Knowledge Service

```python
from app.api.schemas.chat import Citation
from app.knowledge.base import get_shared_knowledge
from config.settings import settings


class KnowledgeService:
    def __init__(self, tracker_repo, pg_client):
        self.knowledge = get_shared_knowledge()
        self.tracker_repo = tracker_repo
        self.pg_client = pg_client

    async def search_references(self, query: str) -> list[Citation]:
        raw_results = self.knowledge.search(query=query)
        return [self._to_citation(item) for item in raw_results]

    async def get_status(self) -> dict:
        _, total_documents = self.knowledge.get_content(limit=1, page=1)
        total_chunks = self.pg_client.scalar(
            f"SELECT COUNT(*) FROM {self.pg_client.safe_ident(settings.PG_VECTOR_TABLE)}"
        )
        return {
            "total_documents": total_documents,
            "total_chunks": total_chunks,
            "pending_files": self.tracker_repo.count_by_status("pending"),
            "error_files": self.tracker_repo.count_by_status("error"),
            "last_sync_time": self.tracker_repo.get_last_sync_time(),
        }
```

**修订要点：**

- 文档数来自 `knowledge.get_content(...)`
- chunk 数来自 pgvector 物理表统计
- API 引用统一在这里做 DTO 归一化

### 6.7 微信检索：改为 FTS5 搜索服务

#### 6.7.1 Search Store

```python
class WeChatSearchStore:
    def __init__(self, raw_db_path: str, search_db_path: str):
        self.raw_db_path = raw_db_path
        self.search_db_path = search_db_path

    def sync_incremental(self) -> None:
        """
        从微信原始库增量抽取消息到派生搜索库。
        仅同步新增或变更消息，不在服务启动时全量重建内存索引。
        """
        # 以 msg_id / ts 为水位做增量抽取，并同步更新 FTS5 索引
        ...

    def search_messages(
        self,
        query: str = "",
        contact: str = "",
        room: str = "",
        start_date: str = "",
        end_date: str = "",
        limit: int = 20,
    ) -> list[dict]:
        # query 不为空时走 FTS5 + 过滤；为空时走普通条件过滤
        ...

    def get_message_context(self, msg_id: str, window: int = 5) -> list[dict]:
        # 先定位消息时间戳，再按同会话窗口取前后消息
        ...

    def list_contacts(self, keyword: str = "") -> list[dict]:
        # 按 nickname / remark 模糊匹配并返回最近活跃联系人
        ...

    def list_rooms(self, keyword: str = "") -> list[dict]:
        # 按 room_name 模糊匹配并返回最近活跃群聊
        ...
```

实现约束：

- 检索主路径必须落在 `wechat_search.db` 上
- 不允许服务启动时退回“全量读库 + 全量内存倒排索引”
- 所有查询都必须是参数化 SQL，避免把自然语言直接拼进语句

#### 6.7.2 Tool 设计

原方案的 7 个原子 Tool 被收敛为 4 个更稳定的 Tool：

```python
import json

from agno.run import RunContext
from agno.tools import tool


@tool(name="search_messages", description="按关键词、联系人、群聊、时间范围综合搜索微信消息")
def search_messages(
    run_context: RunContext,
    query: str = "",
    contact: str = "",
    room: str = "",
    start_date: str = "",
    end_date: str = "",
    limit: int = 20,
) -> str:
    store = run_context.dependencies["wechat_search"]
    rows = store.search_messages(
        query=query,
        contact=contact,
        room=room,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return json.dumps(rows, ensure_ascii=False)


@tool(name="get_message_context", description="获取某条微信消息前后上下文")
def get_message_context(run_context: RunContext, msg_id: str, window: int = 5) -> str:
    store = run_context.dependencies["wechat_search"]
    rows = store.get_message_context(msg_id=msg_id, window=window)
    return json.dumps(rows, ensure_ascii=False)


@tool(name="list_contacts", description="搜索联系人列表")
def list_contacts(run_context: RunContext, keyword: str = "") -> str:
    store = run_context.dependencies["wechat_search"]
    return json.dumps(store.list_contacts(keyword=keyword), ensure_ascii=False)


@tool(name="list_rooms", description="搜索群聊列表")
def list_rooms(run_context: RunContext, keyword: str = "") -> str:
    store = run_context.dependencies["wechat_search"]
    return json.dumps(store.list_rooms(keyword=keyword), ensure_ascii=False)
```

**修订要点：**

- 不再使用 `_indexes` 全局变量
- tool 数量下降，减少 prompt 噪声和无意义多跳调用
- 检索能力从“索引组合”变成“一个支持多过滤条件的统一搜索入口”

### 6.8 SOP：改为真正的会话内待办 Agent

#### 6.8.1 TodoManager

```python
import json
import sqlite3


class TodoManager:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def add(self, session_id: str, title: str, detail: str = "", priority: int = 2,
            due_date: str | None = None, tags: list[str] | None = None) -> dict:
        with self._conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO todos (session_id, title, detail, priority, due_date, tags_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, title, detail, priority, due_date, json.dumps(tags or [], ensure_ascii=False)),
            )
        return {"id": cursor.lastrowid}

    def update(self, session_id: str, todo_id: int, updates: dict) -> bool:
        allowed = {"title", "detail", "priority", "status", "due_date", "tags_json"}
        sets = []
        values = []
        for key, value in updates.items():
            if key in allowed:
                sets.append(f"{key} = ?")
                values.append(value)
        if not sets:
            return False
        sets.append("updated_at = datetime('now','localtime')")
        values.extend([session_id, todo_id])
        sql = f"UPDATE todos SET {', '.join(sets)} WHERE session_id = ? AND id = ?"
        with self._conn() as conn:
            cur = conn.execute(sql, values)
        return cur.rowcount > 0

    def delete(self, session_id: str, todo_id: int) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM todos WHERE session_id = ? AND id = ?",
                (session_id, todo_id),
            )
        return cur.rowcount > 0

    def set_status(self, session_id: str, todo_id: int, status: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                """
                UPDATE todos
                   SET status = ?, updated_at = datetime('now','localtime')
                 WHERE session_id = ? AND id = ?
                """,
                (status, session_id, todo_id),
            )
        return cur.rowcount > 0

    def list(self, session_id: str, status: str | None = None) -> list[dict]:
        sql = "SELECT * FROM todos WHERE session_id = ?"
        params: list = [session_id]
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY priority ASC, due_date ASC, created_at DESC"
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
```

#### 6.8.2 Tool 设计

```python
import json

from agno.run import RunContext
from agno.tools import tool


def _audit(run_context: RunContext, action: str, ok: bool, payload: dict) -> None:
    run_context.dependencies["executed_actions"].append(
        {"action": action, "ok": ok, "payload": payload}
    )


@tool(name="add_todo", description="添加当前会话的待办事项")
def add_todo(
    run_context: RunContext,
    title: str,
    detail: str = "",
    priority: int = 2,
    due_date: str = "",
    tags: str = "",
) -> str:
    manager = run_context.dependencies["todo_manager"]
    result = manager.add(
        session_id=run_context.session_id,
        title=title,
        detail=detail,
        priority=priority,
        due_date=due_date or None,
        tags=[t.strip() for t in tags.split(",") if t.strip()],
    )
    _audit(run_context, "add", True, result)
    return json.dumps(result, ensure_ascii=False)


@tool(name="list_todos", description="列出当前会话的待办事项")
def list_todos(run_context: RunContext, status: str = "") -> str:
    manager = run_context.dependencies["todo_manager"]
    rows = manager.list(session_id=run_context.session_id, status=status or None)
    _audit(run_context, "list", True, {"count": len(rows)})
    return json.dumps(rows, ensure_ascii=False)
```

`update_todo`、`delete_todo`、`mark_done` 与上述模式一致：

- 永远从 `run_context.session_id` 取作用域
- 永远通过 `todo_manager` 执行真实数据库操作
- 永远通过 `_audit()` 记录本次动作
- 绝不允许跨会话更新或删除

**修订要点：**

- 不再使用模块级 `_manager`
- 不再使用“全局 todo 列表”
- `session_id` 直接来自当前 Agent run
- `actions` 来源于本次真实工具执行，不再伪造

### 6.9 FastAPI 依赖注入

```python
from fastapi import Request

from app.core.agent_factory import create_chat_agent, create_sop_agent, create_wechat_agent


def get_session_service(request: Request):
    return request.app.state.session_service


def get_knowledge_service(request: Request):
    return request.app.state.knowledge_service


def get_chat_agent():
    return create_chat_agent()


def get_wechat_agent():
    return create_wechat_agent()


def get_sop_agent(request: Request):
    return create_sop_agent(tools=request.app.state.sop_tools)
```

---

## 7. 路由落地方式

### 7.1 `/api/v1/chat`

```python
@router.post("/", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    service: ChatService = Depends(get_chat_service),
):
    return await service.run_chat(req)
```

### 7.2 `/api/v1/chat/stream`

```python
@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    service: ChatStreamService = Depends(get_chat_stream_service),
):
    return StreamingResponse(
        service.stream(req),
        media_type="text/event-stream",
    )
```

### 7.3 `/api/v1/wechat/search`

WeChat 查询仍保留自然语言入口，但底层改为：

1. `SessionService.ensure_session(mode="wechat")`
2. `Agent.arun(..., dependencies={"wechat_search": search_store})`
3. 返回 Agent 总结 + 最终命中的消息列表

### 7.4 `/api/v1/sop`

SOP 执行路径：

1. `SessionService.ensure_session(mode="sop")`
2. `executed_actions = []`
3. `Agent.arun(..., dependencies={"todo_manager": manager, "executed_actions": executed_actions})`
4. `manager.list(session_id)` 生成 `todos_snapshot`

### 7.5 `/api/v1/sessions/{session_id}`

- `GET`：读 `session_registry`
- `PUT /rename`：走 `SessionService.rename_session()`
- `DELETE`：走 `SessionService.delete_session()`

### 7.6 `/api/v1/knowledge`

- `GET /status`：来自 `KnowledgeService.get_status()`
- `POST /upload`：走 `KnowledgeLoader.ingest()`
- `DELETE /files/{file_path:path}`：走 `KnowledgeLoader.delete()`
- `POST /rebuild`：走 `KnowledgeLoader.rebuild_all()`

---

## 8. 后台任务

### 8.1 文件监听与增量更新

#### 8.1.1 Watcher

```python
import asyncio
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from app.knowledge.reader_factory import SUPPORTED_EXTENSIONS


class DocChangeHandler(FileSystemEventHandler):
    def __init__(self, loop: asyncio.AbstractEventLoop, enqueue_change):
        self.loop = loop
        self.enqueue_change = enqueue_change

    def _supported(self, path: str) -> bool:
        return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS

    def _push(self, action: str, path: str) -> None:
        if self._supported(path):
            self.loop.call_soon_threadsafe(self.enqueue_change, action, path)

    def on_created(self, event):
        if not event.is_directory:
            self._push("upsert", event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._push("upsert", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._push("delete", event.src_path)
```

#### 8.1.2 Worker

```python
class IncrementalUpdateWorker:
    def __init__(self, loader, tracker_repo, debounce_ms: int):
        self.loader = loader
        self.tracker_repo = tracker_repo
        self.debounce_ms = debounce_ms
        self.queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()
        self.pending: dict[str, tuple[str, float]] = {}

    def enqueue(self, action: str, file_path: str) -> None:
        import time

        self.pending[file_path] = (action, time.monotonic())

    async def run(self) -> None:
        while True:
            await asyncio.sleep(self.debounce_ms / 1000)
            ready = list(self.pending.items())
            self.pending.clear()
            for file_path, (action, _) in ready:
                await self._handle(action, file_path)
```

**修订要点：**

- 解决线程到事件循环的错误边界
- 增加 debounce，避免一次保存触发多次 upsert

### 8.2 微信增量同步

微信搜索库不再在 app 启动时全量构建，而是：

1. 首次通过脚本 `build_wechat_search_db.py` 全量构建
2. 服务启动后只执行 `sync_incremental()`
3. 可由调度器定期补同步

### 8.3 日报生成

日报不再依赖一个未定义的 `tracker.get_conversations_by_date()`，而是显式从 Agno Session Storage 取会话历史：

```python
class DailyReportService:
    def __init__(self, session_repo, report_repo):
        self.session_repo = session_repo
        self.report_repo = report_repo

    async def generate(self, target_date: str) -> None:
        session_ids = self.session_repo.list_active_session_ids_for_date(target_date)
        transcripts = []

        agent = create_chat_agent()
        for session_id in session_ids:
            session = agent.get_session(session_id=session_id)
            if session is None:
                continue
            transcripts.append(self._extract_messages_for_date(session, target_date))

        if not transcripts:
            return

        report = await self._summarize(transcripts, target_date)
        self.report_repo.upsert(
            report_date=target_date,
            summary_md=report,
            source_sessions_json=session_ids,
        )
```

**修订要点：**

- 日报原始数据来源改为 Agno session/runs
- 不再依赖未定义的业务会话历史表

### 8.4 调度器

继续使用 `APScheduler`，但纳入两个周期性任务：

- `daily_report`
- `wechat_incremental_sync`

---

## 9. 应用生命周期

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()

    app_meta_repo = AppMetaRepository(settings.APP_META_DB_PATH)
    tracker_repo = DocTrackingRepository(settings.APP_META_DB_PATH)
    session_service = SessionService(app_meta_repo)
    knowledge_service = KnowledgeService(tracker_repo=tracker_repo, pg_client=PgClient())
    knowledge_loader = KnowledgeLoader(tracker_repo=tracker_repo)

    todo_manager = TodoManager(settings.APP_META_DB_PATH)
    wechat_search = WeChatSearchStore(
        raw_db_path=settings.WECHAT_RAW_DB_PATH,
        search_db_path=settings.WECHAT_SEARCH_DB_PATH,
    )
    wechat_search.sync_incremental()

    worker = IncrementalUpdateWorker(
        loader=knowledge_loader,
        tracker_repo=tracker_repo,
        debounce_ms=settings.FILE_DEBOUNCE_MS,
    )
    worker_task = asyncio.create_task(worker.run())

    observer = Observer()
    observer.schedule(
        DocChangeHandler(loop=loop, enqueue_change=worker.enqueue),
        settings.WATCH_DIR,
        recursive=True,
    )
    observer.start()

    scheduler = create_scheduler()
    scheduler.start()

    app.state.session_service = session_service
    app.state.knowledge_service = knowledge_service
    app.state.knowledge_loader = knowledge_loader
    app.state.todo_manager = todo_manager
    app.state.wechat_search = wechat_search
    app.state.sop_tools = [add_todo, list_todos, update_todo, delete_todo, mark_done]

    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        observer.stop()
        await asyncio.to_thread(observer.join, 5)
        worker_task.cancel()
```

---

## 10. 关键流程时序

### 10.1 文档问答

```text
Client
  │ POST /api/v1/chat
  ▼
SessionService.ensure_session(mode="chat")
  ▼
KnowledgeService.search_references(query)
  │  ├── Agno Knowledge.search()
  │  └── 统一转换为 Citation DTO
  ▼
Chat Agent.arun(
    dependencies={"knowledge_refs": ...},
    output_schema=ChatAgentOutput
)
  ▼
ChatResponse
```

### 10.2 文档增量更新

```text
watchdog event thread
  ▼
loop.call_soon_threadsafe(worker.enqueue)
  ▼
IncrementalUpdateWorker (debounce)
  ▼
KnowledgeLoader.ingest(path)
  │ 1. 计算 file_hash
  │ 2. 读取 doc_tracking
  │ 3. 如存在旧 content_id -> remove_content_by_id()
  │ 4. knowledge.insert(name/path/metadata/reader)
  │ 5. 回写 doc_tracking(content_id, hash, chunk_count)
  ▼
synced
```

### 10.3 微信检索

```text
Client
  │ POST /api/v1/wechat/search
  ▼
SessionService.ensure_session(mode="wechat")
  ▼
WeChat Agent.arun(
    dependencies={"wechat_search": store}
)
  │  ├── search_messages(...)
  │  ├── list_contacts(...)
  │  └── get_message_context(...)
  ▼
WeChatSearchResponse
```

### 10.4 SOP

```text
Client
  │ POST /api/v1/sop
  ▼
SessionService.ensure_session(mode="sop")
  ▼
SOP Agent.arun(
    dependencies={
      "todo_manager": manager,
      "executed_actions": []
    }
)
  │  ├── add_todo(...)
  │  ├── list_todos(...)
  │  └── mark_done(...)
  ▼
TodoManager.list(session_id)
  ▼
SopResponse(actions, todos_snapshot)
```

---

## 11. 依赖建议

```toml
[project]
name = "personal-assistant"
requires-python = ">=3.12"

dependencies = [
  "agno",
  "fastapi",
  "uvicorn[standard]",
  "pydantic",
  "pydantic-settings",
  "sqlalchemy",
  "psycopg[binary]",
  "pgvector",
  "openai",
  "docling",
  "chonkie",
  "watchdog",
  "apscheduler",
]
```

**说明：**

- 不再单独维护 `todo.db`
- 微信检索使用 SQLite FTS5，不额外引入搜索引擎

---

## 12. 启动与运维

```bash
# 1. 初始化业务库
python scripts/init_app_meta.py

# 2. 首次构建微信搜索库
python scripts/build_wechat_search_db.py

# 3. 首次全量导入知识库
python scripts/seed_knowledge.py

# 4. 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

### 12.1 运维约束

- 知识库重建走 `POST /api/v1/knowledge/rebuild` 或脚本，不允许手工删 pgvector 表
- 会话删除必须走 Session API，不允许只删 `session_registry`
- 微信搜索库损坏时，可以删除 `tmp/wechat_search.db` 后重新执行构建脚本

---

