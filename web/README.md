# 简洁问答前端

这个目录是独立于现有 `frontend` 的轻量静态前端，由 FastAPI 挂载到 `/ui/`。

## 模式到接口的映射

| 前端模式 | 后端会话 mode | 请求接口 | 请求字段 | 主要返回字段 |
|---|---|---|---|---|
| SOP | `sop` | `POST /api/v1/sop/` | `message`, `session_id` | `session_id`, `reply`, `actions`, `todos_snapshot` |
| 微信 | `wechat` | `POST /api/v1/wechat/search` | `query`, `session_id` | `session_id`, `answer`, `messages`, `total_count` |
| 知识库 | `chat` | `POST /api/v1/chat/stream` | `message`, `session_id` | SSE: `citations`, `token`, `done`, `error` |

知识库模式优先走流式接口。浏览器原生 `EventSource` 无法携带 `X-API-Key` 请求头，所以这里使用 `fetch` 读取 `text/event-stream` 并手动解析 SSE 块。

## 会话交互过程

1. 打开 `/ui/` 后，前端读取后端地址、`APP_API_KEY`、`User ID`，并调用 `/health`、`/api/v1/sessions/`、`/api/v1/knowledge/status` 初始化状态。
2. 用户选择 `SOP / 微信 / 知识库` 三种模式之一，前端按模式决定请求路径和请求字段名。
3. 如果当前没有 `session_id`，第一次发送时不传会话，后端创建会话并返回 `session_id`。
4. 前端拿到新的 `session_id` 后，自动调用 `PUT /api/v1/sessions/{id}/rename?title=...`，用首条消息生成会话标题。
5. 右侧会话管理通过 `GET /api/v1/sessions/` 刷新列表，支持点击继续、重命名和删除。
6. 后端当前只暴露会话元数据，不暴露完整历史消息读取接口；前端会把当前浏览器内看过的消息按 `session_id` 存入 `localStorage`，旧会话仍可用同一个 `session_id` 继续后端上下文。

## 返回处理

- 知识库：`citations` 渲染为引用卡片，`token` 逐段拼接为助手回答，`done.session_id` 绑定当前会话。
- SOP：`reply` 渲染为回答，`actions` 渲染为工具动作记录，`todos_snapshot` 渲染为待办快照。
- 微信：`answer` 渲染为回答，`messages` 有值时展开消息明细，`total_count` 用于显示匹配数量。
