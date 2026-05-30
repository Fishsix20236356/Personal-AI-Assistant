## 二、Claude Code 提示词：分阶段完整版

以下提示词设计为**直接复制粘贴到 Claude Code 中使用**，每个阶段是一个独立的 prompt。

---

### 阶段 0：项目初始化

```
我要基于附件的技术架构文档构建一个 Agno 个人助理项目。

请先阅读 technical-architecture.md 全文，然后执行以下初始化步骤：

1. 创建项目目录结构（严格按文档第 2 节的工程目录）
2. 创建 pyproject.toml（按文档第 11 节的依赖列表）
3. 创建 config/settings.py（按文档第 3.1 节完整复制）
4. 创建 .env.example（列出所有环境变量的示例值）
5. 创建 tmp/ 目录和 data/documents/、data/wechat_db/ 目录
6. 所有 __init__.py 文件先创建为空文件

不要写任何业务代码，只搭骨架。完成后列出创建的文件清单。
```

---

### 阶段 1：数据层

```
参考 technical-architecture.md 的第 4 节"数据存储与表结构"，实现数据层：

## 任务 1：app_meta.db 初始化
- 创建 app/db/app_meta.py，实现 AppMetaRepository 类
- 包含：upsert_session, touch_session, rename_session, delete_session_cascade,
  list_sessions, get_session 方法
- 创建 app/db/migrations/001_app_meta.sql（按文档 4.1 节的 4 张表）
- 创建 scripts/init_app_meta.py 执行迁移脚本

## 任务 2：Agno Session Storage
- 创建 app/core/agno_db.py（按文档 4.2 节，使用 agno.db.sqlite.SqliteDb）

## 任务 3：PostgreSQL 知识库
- 创建 app/knowledge/base.py（按文档 4.3 节，使用 agno Knowledge + PgVector + OpenAIEmbedder）

## 任务 4：微信搜索库
- 创建 app/db/migrations/002_wechat_search.sql（按文档 4.4 节的 FTS5 表结构）

## 关键约束
- AppMetaRepository 使用原生 sqlite3，不用 SQLAlchemy
- 所有 SQL 必须参数化，禁止字符串拼接
- session_id 是贯穿所有层的唯一主键
- 每个 Repository 方法都要写 docstring 说明职责边界

## 测试
- 为 AppMetaRepository 写单元测试（用内存 SQLite :memory:）
- 测试 session 的 CRUD 和级联删除
- 测试 todos 的 session_id 隔离
```

---

### 阶段 2：核心基础设施

```
参考 technical-architecture.md 第 6.1-6.3 节，实现核心基础设施：

## 任务 1：模型工厂 (app/core/model_factory.py)
- 按文档 6.1 节实现，使用 agno.models.openai.like.OpenAILike
- 包含 ModelConfig dataclass、get_primary_model_config、get_fallback_model_config、build_model
- 不要用 OpenAIChat，架构文档明确要求用 OpenAILike

## 任务 2：Agent 工厂 (app/core/agent_factory.py)
- 按文档 6.2 节实现 create_chat_agent、create_wechat_agent、create_sop_agent
- 注意：session_id 不在工厂里固定，在 arun() 时传入
- read_chat_history=False, search_session_history=False（chat agent）
- tool_call_limit 分别设为：chat 无限制、wechat 6、sop 8

## 任务 3：Session Service (app/core/session_service.py)
- 按文档 6.3 节实现
- ensure_session：生成 "{mode}_{uuid}" 格式的 session_id
- delete_session：必须同时删 Agno session 和 app_meta 记录（双删闭环）
- rename_session：同时同步到 Agno session name

## 任务 4：Prompt Templates (app/core/prompt_templates.py)
- 创建 CHAT_INSTRUCTIONS、WECHAT_INSTRUCTIONS、SOP_INSTRUCTIONS 三个常量
- Chat：你是一个知识助手，基于提供的参考资料回答问题，如果资料不足要明确说明
- WeChat：你是微信聊天记录搜索助手，使用提供的工具搜索和分析聊天记录
- SOP：你是待办事项管理助手，使用提供的工具管理当前会话的待办事项

## 测试
- model_factory：测试 primary 和 fallback 配置生成
- session_service：测试 ensure_session 幂等性、delete_session 双删
```

---

### 阶段 3：知识库模块

```
参考 technical-architecture.md 第 6.4-6.6 节，实现知识库相关模块：

## 任务 1：Reader 工厂 (app/knowledge/reader_factory.py)
- 按文档 6.5.1 节实现
- SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".md", ".txt", ".html"}
- build_docling_reader()：根据 settings.CHUNKING_STRATEGY 选择 SemanticChunking 或 FixedSizeChunking

## 任务 2：Tracker Repository (app/knowledge/tracker_repository.py)
- 操作 doc_tracking 表
- 方法：get(file_path), upsert(...), delete(file_path), delete_all(),
  count_by_status(status), get_last_sync_time()

## 任务 3：Knowledge Loader (app/knowledge/loader.py)
- 按文档 6.5.2 节完整实现
- 关键："先删后插"策略——ingest 时如果已有 content_id，先 remove_content_by_id 再 insert
- rebuild_all()：先 remove_all_content + delete_all tracking，再全量重新 ingest
- _hash_file：SHA256

## 任务 4：Knowledge Service (app/knowledge/service.py)
- 按文档 6.6 节实现
- search_references(query) -> list[Citation]
- get_status() -> dict（文档数来自 knowledge.get_content，chunk 数来自 pgvector 表）

## 任务 5：初始化脚本
- scripts/seed_knowledge.py：扫描 data/documents/ 下所有支持格式的文件，调用 loader.ingest
- scripts/rebuild_knowledge.py：调用 loader.rebuild_all

## 关键约束
- knowledge.insert() 必须传 metadata={"source_path": ..., "file_hash": ...}
- 文档删除必须走 remove_content_by_id，不能只删向量
- tracker_repository 用原生 sqlite3 操作 app_meta.db
```

---

### 阶段 4：微信检索模块

```
参考 technical-architecture.md 第 6.7 节和第 4.4 节，实现微信检索模块：

## 任务 1：WeChatSearchStore (app/wechat/search_store.py)
按文档 6.7.1 节实现，核心方法：
- sync_incremental()：从 raw_db 增量抽取到 search_db，用 msg_id/ts 做水位
- search_messages(query, contact, room, start_date, end_date, limit)：
  query 非空时走 FTS5 MATCH + 条件过滤；为空时走普通条件过滤
- get_message_context(msg_id, window=5)：定位消息后取同会话前后 N 条
- list_contacts(keyword)：按 talker_name 模糊搜索，返回最近活跃
- list_rooms(keyword)：按 room_name 模糊搜索

## 任务 2：WeChat Tools (app/wechat/tools.py)
按文档 6.7.2 节实现 4 个 tool：
- search_messages、get_message_context、list_contacts、list_rooms
- 所有 tool 通过 run_context.dependencies["wechat_search"] 获取 store
- 不使用任何模块级全局变量

## 任务 3：构建脚本 (scripts/build_wechat_search_db.py)
- 执行 002_wechat_search.sql 创建表
- 全量从 WECHAT_RAW_DB_PATH 抽取到 WECHAT_SEARCH_DB_PATH
- 同步构建 FTS5 索引

## 关键约束
- 所有 SQL 必须参数化
- FTS5 查询要处理特殊字符转义
- 检索只走 wechat_search.db，不允许启动时全量构建内存索引
- sync_incremental 要幂等，重复执行不产生重复数据

## 测试
- 用 fixture 创建临时 SQLite 测试 search_messages 的 FTS5 查询
- 测试日期范围过滤、联系人过滤的组合条件
- 测试 get_message_context 的窗口边界
```

---

### 阶段 5：SOP 模块

```
参考 technical-architecture.md 第 6.8 节，实现 SOP 待办管理模块：

## 任务 1：TodoManager (app/sop/manager.py)
按文档 6.8.1 节完整实现：
- add(session_id, title, detail, priority, due_date, tags) -> dict
- update(session_id, todo_id, updates) -> bool（白名单字段更新）
- delete(session_id, todo_id) -> bool
- set_status(session_id, todo_id, status) -> bool
- list(session_id, status=None) -> list[dict]

## 任务 2：SOP Models (app/sop/models.py)
- TodoStatus enum: pending, doing, done, cancelled
- TodoPriority enum: 0=urgent, 1=high, 2=normal, 3=low

## 任务 3：SOP Tools (app/sop/tools.py)
按文档 6.8.2 节实现：
- add_todo, list_todos, update_todo, delete_todo, mark_done
- 所有 tool 从 run_context.session_id 获取会话作用域
- 所有 tool 从 run_context.dependencies["todo_manager"] 获取 manager
- 每个 tool 执行后调用 _audit() 记录到 run_context.dependencies["executed_actions"]
- tags 参数用逗号分隔字符串，tool 内部转 list

## 关键约束
- 所有 CRUD 操作必须按 session_id 过滤，绝对禁止跨会话操作
- update 方法用白名单过滤允许更新的字段
- 不使用模块级全局 _manager

## 测试
- TodoManager：测试 CRUD 完整流程
- 测试 session_id 隔离：session_a 的 todo 不能被 session_b 更新或删除
- 测试 priority 排序和 status 过滤
```

---

### 阶段 6：API 路由层

```
参考 technical-architecture.md 第 5 节（API 契约）和第 7 节（路由），实现 API 层：

## 任务 1：Schemas (app/api/schemas/)
按文档第 5 节创建所有 Pydantic 模型：
- chat.py：ChatRequest, Citation, ChatResponse, ChatAgentOutput
- wechat.py：WeChatSearchRequest, WeChatMessageOut, WeChatSearchResponse
- sop.py：TodoStatus, TodoPriority, TodoItem, SopAction, SopRequest, SopResponse
- knowledge.py：KnowledgeStatusResponse
- session.py：SessionInfo

## 任务 2：依赖注入 (app/deps.py)
按文档 6.9 节实现 FastAPI 依赖函数：
- get_session_service, get_knowledge_service
- get_chat_agent, get_wechat_agent, get_sop_agent

## 任务 3：Chat 路由 (app/api/v1/chat.py)
- POST /：调用 ChatService.run_chat（文档 6.4.2 节的完整流程）
- POST /stream：SSE 流式，映射 Agno RunOutputEvent（文档 6.4.3 节）

## 任务 4：WeChat 路由 (app/api/v1/wechat.py)
- POST /search：ensure_session -> Agent.arun(dependencies={"wechat_search": store})

## 任务 5：SOP 路由 (app/api/v1/sop.py)
- POST /：ensure_session -> executed_actions=[] -> Agent.arun -> manager.list 生成 snapshot

## 任务 6：Session 路由 (app/api/v1/session.py)
- GET /：list sessions（支持 mode 过滤）
- GET /{session_id}：get session
- PUT /{session_id}/rename：rename
- DELETE /{session_id}：delete（双删闭环）

## 任务 7：Knowledge 路由 (app/api/v1/knowledge.py)
- GET /status
- POST /upload（接收文件 -> 保存到 data/documents -> loader.ingest）
- DELETE /files/{file_path:path}
- POST /rebuild

## 任务 8：Router 汇总 (app/api/router.py)
- 前缀：/api/v1/chat, /api/v1/wechat, /api/v1/sop, /api/v1/sessions, /api/v1/knowledge

## 关键约束
- ChatResponse 中 grounded=bool(citations)，不要用数值 confidence
- SopResponse 的 actions 来自真实执行的 tool 动作，不是 LLM 生成的 JSON
- 所有端点的错误处理要返回标准 HTTPException
```

---

### 阶段 7：后台任务 & 应用生命周期

```
参考 technical-architecture.md 第 8-9 节，实现后台任务和应用入口：

## 任务 1：文件监听 (app/background/watcher.py)
按文档 8.1.1 节实现 DocChangeHandler：
- 继承 watchdog.events.FileSystemEventHandler
- 构造函数接收 loop 和 enqueue_change 回调
- 通过 loop.call_soon_threadsafe() 将事件安全入队到主事件循环
- 只处理 SUPPORTED_EXTENSIONS 中的文件

## 任务 2：增量更新 Worker (app/background/incremental_update.py)
按文档 8.1.2 节实现 IncrementalUpdateWorker：
- debounce 机制：用 pending dict 合并短时间内的重复事件
- run() 循环：每 debounce_ms 毫秒检查一次 pending，批量处理

## 任务 3：微信增量同步 (app/background/wechat_sync.py)
- 封装 WeChatSearchStore.sync_incremental 为可调度任务

## 任务 4：日报生成 (app/reports/daily_report.py)
按文档 8.3 节实现 DailyReportService：
- 从 Agno Session Storage 获取指定日期的会话历史
- 用 Agent 生成摘要
- 保存到 daily_reports 表

## 任务 5：调度器 (app/background/scheduler.py)
- 使用 APScheduler
- 两个定时任务：daily_report（按 DAILY_REPORT_CRON）、wechat_incremental_sync

## 任务 6：应用入口 (app/main.py)
按文档第 9 节实现 lifespan：
- 初始化所有 Repository 和 Service
- 启动 IncrementalUpdateWorker（asyncio.create_task）
- 启动 watchdog Observer
- 启动 APScheduler
- 将服务实例挂到 app.state
- finally 中优雅关闭：scheduler.shutdown -> observer.stop -> worker_task.cancel

## 关键约束
- watchdog 的回调线程不能直接操作 asyncio，必须通过 loop.call_soon_threadsafe
- Worker 的 debounce 要处理同一文件短时间内多次修改只触发一次 ingest
- lifespan 的 finally 必须完整清理资源
```

---

### 阶段 8：集成测试 & 质量检查

```
项目主要模块已完成，执行最终质量检查：

## 1. 集成测试
- 测试完整的 Chat 链路：创建 session -> 发送消息 -> 获取响应（mock LLM）
- 测试完整的 SOP 链路：创建 session -> 添加 todo -> 列出 -> 标记完成
- 测试 Session 删除闭环：删除后 agno_sessions 和 app_meta 都不应有残留
- 测试知识库的"先删后插"：同一文件导入两次后 chunk 数不应翻倍

## 2. 安全检查
- 检查所有 SQLite 操作是否使用参数化查询
- 检查是否有硬编码的 API key 或密码
- 检查 FTS5 查询是否正确转义用户输入

## 3. 代码审查
- 确认没有模块级全局变量用于依赖注入（所有 tool 都走 run_context）
- 确认所有 SOP CRUD 都按 session_id 过滤
- 确认 Knowledge 删除走 contents_db 而非只删向量
- 确认 watchdog 回调使用 call_soon_threadsafe

## 4. 启动验证
- 运行 scripts/init_app_meta.py 验证数据库创建
- 运行 uvicorn app.main:app 验证服务启动不报错
- 调用 GET /api/v1/knowledge/status 验证端点可达
```
