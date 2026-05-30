(() => {
  const STORAGE_KEYS = {
    settings: "personal-assistant.ui.settings",
    transcripts: "personal-assistant.ui.transcripts",
  };

  const MODE_CONFIG = {
    knowledge: {
      label: "知识库",
      apiMode: "chat",
      requestKey: "message",
      maxLength: 4000,
      description: "面向资料库的问答模式。优先调用 SSE 流式接口，先接收 citations，再逐 token 渲染答案。",
      placeholder: "向知识库提问，例如：总结计划文档里的关键事项",
      intro: "知识库模式会调用 /api/v1/chat/stream，返回 citations、token、done 三类核心事件；如果浏览器无法读取流，会退回 /api/v1/chat/。",
      hint: "知识库模式将优先使用流式接口。",
    },
    sop: {
      label: "SOP",
      apiMode: "sop",
      requestKey: "message",
      maxLength: 2000,
      description: "面向待办和 SOP 执行的模式。返回 reply、actions、todos_snapshot，适合做任务拆解和状态追踪。",
      placeholder: "输入 SOP 指令，例如：添加一个待办，上线前检查，优先级高",
      intro: "SOP 模式会调用 /api/v1/sop/，前端会把 actions 和 todos_snapshot 展开成可读的执行记录。",
      hint: "SOP 返回会包含工具动作和待办快照。",
    },
    wechat: {
      label: "微信",
      apiMode: "wechat",
      requestKey: "query",
      maxLength: 2000,
      description: "面向微信消息检索的模式。前端发送 query，展示 answer、messages 和 total_count。",
      placeholder: "搜索微信，例如：最近谁提到过上线检查？",
      intro: "微信模式会调用 /api/v1/wechat/search，当前后端主要返回 answer；如果 messages 有数据，前端会自动展开消息列表。",
      hint: "微信模式使用 query 字段提交检索问题。",
    },
  };

  const API_MODE_TO_UI_MODE = {
    chat: "knowledge",
    sop: "sop",
    wechat: "wechat",
  };

  const PRIORITY_LABELS = {
    0: "紧急",
    1: "高",
    2: "普通",
    3: "低",
  };

  const STATUS_LABELS = {
    pending: "待处理",
    doing: "进行中",
    done: "已完成",
    cancelled: "已取消",
  };

  const state = {
    mode: "knowledge",
    sessionId: null,
    sessions: [],
    messages: [],
    pending: false,
    knowledgeStatus: null,
    settings: loadJson(STORAGE_KEYS.settings, {}),
    transcripts: loadJson(STORAGE_KEYS.transcripts, {}),
  };

  const els = {};

  document.addEventListener("DOMContentLoaded", init);

  function init() {
    bindElements();
    bindEvents();
    hydrateSettings();
    setMode("knowledge", { reset: true });
    refreshFromBackend();
  }

  function bindElements() {
    els.modeDescription = document.querySelector("#modeDescription");
    els.connectionStatus = document.querySelector("#connectionStatus");
    els.activeSessionLabel = document.querySelector("#activeSessionLabel");
    els.knowledgeStatus = document.querySelector("#knowledgeStatus");
    els.refreshKnowledge = document.querySelector("#refreshKnowledge");
    els.messages = document.querySelector("#messages");
    els.composer = document.querySelector("#composer");
    els.messageInput = document.querySelector("#messageInput");
    els.inputHint = document.querySelector("#inputHint");
    els.sendButton = document.querySelector("#sendButton");
    els.newSession = document.querySelector("#newSession");
    els.baseUrlInput = document.querySelector("#baseUrlInput");
    els.apiKeyInput = document.querySelector("#apiKeyInput");
    els.userIdInput = document.querySelector("#userIdInput");
    els.saveSettings = document.querySelector("#saveSettings");
    els.refreshSessions = document.querySelector("#refreshSessions");
    els.sessionsList = document.querySelector("#sessionsList");
    els.sessionCount = document.querySelector("#sessionCount");
    els.modeButtons = Array.from(document.querySelectorAll("[data-mode]"));
  }

  function bindEvents() {
    els.modeButtons.forEach((button) => {
      button.addEventListener("click", () => {
        if (state.pending) return;
        setMode(button.dataset.mode, { reset: true });
      });
    });

    els.composer.addEventListener("submit", (event) => {
      event.preventDefault();
      sendCurrentMessage();
    });

    els.messageInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        els.composer.requestSubmit();
      }
    });

    els.newSession.addEventListener("click", () => {
      if (state.pending) return;
      startNewSession();
    });

    els.saveSettings.addEventListener("click", () => {
      saveSettingsFromForm();
      refreshFromBackend();
    });

    els.refreshSessions.addEventListener("click", loadSessions);
    els.refreshKnowledge.addEventListener("click", refreshKnowledgeStatus);
  }

  function hydrateSettings() {
    els.baseUrlInput.value = state.settings.baseUrl || defaultBaseUrl();
    els.apiKeyInput.value = state.settings.apiKey || "";
    els.userIdInput.value = state.settings.userId || "local-user";
  }

  function saveSettingsFromForm() {
    state.settings = {
      baseUrl: els.baseUrlInput.value.trim(),
      apiKey: els.apiKeyInput.value.trim(),
      userId: els.userIdInput.value.trim() || "local-user",
    };
    localStorage.setItem(STORAGE_KEYS.settings, JSON.stringify(state.settings));
    setConnectionStatus("连接信息已保存", "ok");
  }

  function setMode(mode, options = {}) {
    if (!MODE_CONFIG[mode]) return;

    if (state.sessionId) persistCurrentTranscript();
    state.mode = mode;
    state.sessionId = options.keepSession ? state.sessionId : null;

    if (options.reset) {
      state.messages = [createMessage("system", MODE_CONFIG[mode].intro)];
    }

    els.modeButtons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.mode === mode);
    });

    els.modeDescription.textContent = MODE_CONFIG[mode].description;
    els.messageInput.placeholder = MODE_CONFIG[mode].placeholder;
    els.messageInput.maxLength = MODE_CONFIG[mode].maxLength;
    els.inputHint.textContent = MODE_CONFIG[mode].hint;

    renderMessages();
    renderActiveSession();
  }

  function startNewSession() {
    if (state.sessionId) persistCurrentTranscript();
    state.sessionId = null;
    state.messages = [createMessage("system", MODE_CONFIG[state.mode].intro)];
    renderMessages();
    renderActiveSession();
  }

  async function refreshFromBackend() {
    await refreshHealth();
    await Promise.allSettled([loadSessions(), refreshKnowledgeStatus()]);
  }

  async function refreshHealth() {
    try {
      await fetch(urlFor("/health"));
      setConnectionStatus("后端在线", "ok");
    } catch (error) {
      setConnectionStatus(`后端不可达：${error.message}`, "error");
    }
  }

  async function loadSessions() {
    try {
      const sessions = await apiFetch("/api/v1/sessions/");
      state.sessions = Array.isArray(sessions) ? sessions : [];
      renderSessions();
      setConnectionStatus("会话已同步", "ok");
    } catch (error) {
      renderSessionError(error);
      setConnectionStatus(readableError(error), "error");
    }
  }

  async function refreshKnowledgeStatus() {
    try {
      state.knowledgeStatus = await apiFetch("/api/v1/knowledge/status");
      renderKnowledgeStatus();
    } catch (error) {
      state.knowledgeStatus = null;
      els.knowledgeStatus.textContent = readableError(error);
    }
  }

  async function sendCurrentMessage() {
    const text = els.messageInput.value.trim();
    if (!text || state.pending) return;

    const wasNewSession = !state.sessionId;
    const assistantMessage = createMessage("assistant", "", { streaming: true });

    state.messages.push(createMessage("user", text));
    state.messages.push(assistantMessage);
    els.messageInput.value = "";
    setPending(true);
    renderMessages();

    try {
      if (state.mode === "knowledge") {
        await sendKnowledgeMessage(text, assistantMessage);
      } else if (state.mode === "sop") {
        await sendSopMessage(text, assistantMessage);
      } else {
        await sendWechatMessage(text, assistantMessage);
      }

      assistantMessage.streaming = false;
      if (!assistantMessage.text.trim()) {
        assistantMessage.text = "后端返回成功，但没有文本内容。";
      }

      await autoRenameSession(wasNewSession, text);
      persistCurrentTranscript();
      await loadSessions();
    } catch (error) {
      assistantMessage.streaming = false;
      assistantMessage.error = true;
      assistantMessage.text = `请求失败：${readableError(error)}`;
      setConnectionStatus(readableError(error), "error");
      persistCurrentTranscript();
    } finally {
      setPending(false);
      renderMessages();
      renderActiveSession();
      els.messageInput.focus();
    }
  }

  async function sendKnowledgeMessage(text, assistantMessage) {
    const payload = buildPayload(text);
    const response = await fetch(urlFor("/api/v1/chat/stream"), {
      method: "POST",
      headers: authHeaders(true),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw await httpError(response);
    }

    if (!response.body) {
      await sendKnowledgeMessageFallback(text, assistantMessage);
      return;
    }

    await readSseStream(response, ({ event, data }) => {
      if (event === "citations") {
        assistantMessage.citations = parseJson(data, []);
      } else if (event === "token") {
        assistantMessage.text += data;
      } else if (event === "tool_call_started") {
        assistantMessage.streamingLabel = "工具调用中";
      } else if (event === "tool_call_completed") {
        assistantMessage.streamingLabel = "工具调用完成";
      } else if (event === "done") {
        const donePayload = parseJson(data, {});
        applySessionId(donePayload.session_id);
      } else if (event === "error") {
        const errPayload = parseJson(data, {});
        throw new Error(errPayload.error || data || "SSE error");
      }
      renderMessages();
    });
  }

  async function sendKnowledgeMessageFallback(text, assistantMessage) {
    const data = await apiFetch("/api/v1/chat/", {
      method: "POST",
      body: JSON.stringify(buildPayload(text)),
    });
    applySessionId(data.session_id);
    assistantMessage.text = data.message || "";
    assistantMessage.citations = data.citations || [];
    assistantMessage.grounded = Boolean(data.grounded);
    assistantMessage.uncertainPoints = data.uncertain_points || [];
    assistantMessage.nextSteps = data.next_steps || [];
  }

  async function sendSopMessage(text, assistantMessage) {
    const data = await apiFetch("/api/v1/sop/", {
      method: "POST",
      body: JSON.stringify(buildPayload(text)),
    });
    applySessionId(data.session_id);
    assistantMessage.text = data.reply || "";
    assistantMessage.actions = data.actions || [];
    assistantMessage.todos = data.todos_snapshot || [];
  }

  async function sendWechatMessage(text, assistantMessage) {
    const data = await apiFetch("/api/v1/wechat/search", {
      method: "POST",
      body: JSON.stringify(buildPayload(text)),
    });
    applySessionId(data.session_id);
    assistantMessage.text = data.answer || "";
    assistantMessage.wechatMessages = data.messages || [];
    assistantMessage.totalCount = data.total_count || 0;
  }

  function buildPayload(text) {
    const config = MODE_CONFIG[state.mode];
    const payload = {
      session_id: state.sessionId,
    };
    payload[config.requestKey] = text;
    return payload;
  }

  function applySessionId(sessionId) {
    if (sessionId) {
      state.sessionId = sessionId;
      renderActiveSession();
    }
  }

  async function autoRenameSession(wasNewSession, firstMessage) {
    if (!wasNewSession || !state.sessionId) return;

    const title = firstMessage.replace(/\s+/g, " ").slice(0, 28);
    if (!title) return;

    try {
      await apiFetch(
        `/api/v1/sessions/${encodeURIComponent(state.sessionId)}/rename?title=${encodeURIComponent(title)}`,
        { method: "PUT" },
      );
    } catch (error) {
      console.warn("Session auto rename failed:", error);
    }
  }

  async function renameSession(session) {
    const currentTitle = session.title || shortSessionId(session.session_id);
    const nextTitle = window.prompt("会话新名称", currentTitle);
    if (!nextTitle || nextTitle.trim() === currentTitle) return;

    try {
      await apiFetch(
        `/api/v1/sessions/${encodeURIComponent(session.session_id)}/rename?title=${encodeURIComponent(nextTitle.trim())}`,
        { method: "PUT" },
      );
      await loadSessions();
    } catch (error) {
      setConnectionStatus(readableError(error), "error");
    }
  }

  async function deleteSession(session) {
    const title = session.title || shortSessionId(session.session_id);
    if (!window.confirm(`删除会话「${title}」？此操作会同步删除后端会话记录。`)) return;

    try {
      await apiFetch(`/api/v1/sessions/${encodeURIComponent(session.session_id)}`, {
        method: "DELETE",
      });
      delete state.transcripts[session.session_id];
      persistTranscripts();

      if (state.sessionId === session.session_id) {
        state.sessionId = null;
        state.messages = [createMessage("system", MODE_CONFIG[state.mode].intro)];
        renderMessages();
        renderActiveSession();
      }
      await loadSessions();
    } catch (error) {
      setConnectionStatus(readableError(error), "error");
    }
  }

  function selectSession(session) {
    if (state.pending) return;

    if (state.sessionId) persistCurrentTranscript();
    const uiMode = API_MODE_TO_UI_MODE[session.mode] || "knowledge";
    setMode(uiMode, { reset: false, keepSession: true });
    state.sessionId = session.session_id;

    const transcript = state.transcripts[session.session_id];
    if (transcript && Array.isArray(transcript.messages) && transcript.messages.length) {
      state.messages = transcript.messages;
    } else {
      state.messages = [
        createMessage(
          "system",
          `已接入后端会话 ${shortSessionId(session.session_id)}。后端可继续使用该 session_id 的上下文；当前接口未提供历史消息读取，所以这里只展示本地新产生的消息。`,
        ),
      ];
    }

    renderMessages();
    renderActiveSession();
    renderSessions();
  }

  async function apiFetch(path, options = {}) {
    const response = await fetch(urlFor(path), {
      ...options,
      headers: {
        ...authHeaders(Boolean(options.body)),
        ...(options.headers || {}),
      },
    });

    if (!response.ok) {
      throw await httpError(response);
    }

    if (options.raw) return response;

    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      return response.json();
    }
    return response.text();
  }

  async function readSseStream(response, onEvent) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      buffer = buffer.replace(/\r\n/g, "\n");

      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const event = parseSseBlock(block);
        if (event) onEvent(event);
        boundary = buffer.indexOf("\n\n");
      }

      if (done) break;
    }

    if (buffer.trim()) {
      const event = parseSseBlock(buffer);
      if (event) onEvent(event);
    }
  }

  function parseSseBlock(block) {
    const lines = block.split("\n");
    const dataLines = [];
    let event = "message";

    lines.forEach((line) => {
      if (!line || line.startsWith(":")) return;
      if (line.startsWith("event:")) {
        event = line.slice("event:".length).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice("data:".length).replace(/^ /, ""));
      }
    });

    if (!dataLines.length && event === "message") return null;
    return { event, data: dataLines.join("\n") };
  }

  function authHeaders(includeJson) {
    const settings = currentSettings();
    const headers = {};
    if (includeJson) headers["Content-Type"] = "application/json";
    if (settings.apiKey) headers["X-API-Key"] = settings.apiKey;
    if (settings.userId) headers["X-User-Id"] = settings.userId;
    return headers;
  }

  function urlFor(path) {
    const settings = currentSettings();
    const baseUrl = (settings.baseUrl || defaultBaseUrl()).replace(/\/+$/, "");
    return `${baseUrl}${path}`;
  }

  function currentSettings() {
    if (els.baseUrlInput && els.apiKeyInput && els.userIdInput) {
      return {
        baseUrl: els.baseUrlInput.value.trim() || defaultBaseUrl(),
        apiKey: els.apiKeyInput.value.trim(),
        userId: els.userIdInput.value.trim() || "local-user",
      };
    }

    return {
      baseUrl: state.settings.baseUrl || defaultBaseUrl(),
      apiKey: state.settings.apiKey || "",
      userId: state.settings.userId || "local-user",
    };
  }

  function defaultBaseUrl() {
    if (window.location.protocol === "http:" || window.location.protocol === "https:") {
      return window.location.origin;
    }
    return "http://localhost:8000";
  }

  async function httpError(response) {
    const text = await response.text();
    let detail = text;
    try {
      const json = JSON.parse(text);
      detail = json.detail || json.error || text;
    } catch {
      detail = text || response.statusText;
    }
    return new Error(`${response.status} ${detail}`);
  }

  function readableError(error) {
    if (!error) return "未知错误";
    return error.message || String(error);
  }

  function parseJson(raw, fallback) {
    try {
      return JSON.parse(raw);
    } catch {
      return fallback;
    }
  }

  function setPending(isPending) {
    state.pending = isPending;
    els.sendButton.disabled = isPending;
    els.messageInput.disabled = isPending;
    els.modeButtons.forEach((button) => {
      button.disabled = isPending;
    });
    els.sendButton.textContent = isPending ? "发送中" : "发送";
  }

  function setConnectionStatus(text, status) {
    els.connectionStatus.textContent = text;
    els.connectionStatus.classList.toggle("is-ok", status === "ok");
    els.connectionStatus.classList.toggle("is-error", status === "error");
  }

  function renderKnowledgeStatus() {
    if (!state.knowledgeStatus) {
      els.knowledgeStatus.textContent = "未加载";
      return;
    }

    const status = state.knowledgeStatus;
    els.knowledgeStatus.textContent = `${status.total_documents} 文档 / ${status.total_chunks} chunks`;
  }

  function renderActiveSession() {
    els.activeSessionLabel.textContent = state.sessionId
      ? `${MODE_CONFIG[state.mode].label} · ${shortSessionId(state.sessionId)}`
      : `${MODE_CONFIG[state.mode].label} · 新会话`;
  }

  function renderMessages() {
    els.messages.replaceChildren(...state.messages.map(renderMessage));
    renderActiveSession();
    requestAnimationFrame(() => {
      els.messages.scrollTop = els.messages.scrollHeight;
    });
  }

  function renderMessage(message) {
    const article = document.createElement("article");
    article.className = `message ${message.role}`;
    if (message.error) article.classList.add("error");

    const meta = document.createElement("div");
    meta.className = "message-meta";
    meta.textContent = metaTextForMessage(message);

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = message.streaming
      ? `${message.text}${message.text ? "" : "正在等待后端响应"}${message.streamingLabel ? `\n${message.streamingLabel}` : ""}`
      : message.text;

    article.append(meta, bubble);

    const details = renderMessageDetails(message);
    if (details) article.append(details);

    return article;
  }

  function metaTextForMessage(message) {
    if (message.role === "user") return "You";
    if (message.role === "system") return "System";
    return MODE_CONFIG[message.mode || state.mode].label;
  }

  function renderMessageDetails(message) {
    const fragment = document.createDocumentFragment();
    let hasDetails = false;

    if (Array.isArray(message.citations) && message.citations.length) {
      fragment.append(renderDetailList("Citations", message.citations.map(renderCitation)));
      hasDetails = true;
    }

    if (Array.isArray(message.actions) && message.actions.length) {
      fragment.append(renderDetailList("Actions", message.actions.map(renderAction)));
      hasDetails = true;
    }

    if (Array.isArray(message.todos) && message.todos.length) {
      fragment.append(renderDetailList("Todo Snapshot", message.todos.map(renderTodo)));
      hasDetails = true;
    }

    if (Array.isArray(message.wechatMessages) && message.wechatMessages.length) {
      fragment.append(renderDetailList(`WeChat Messages · ${message.totalCount}`, message.wechatMessages.map(renderWechatMessage)));
      hasDetails = true;
    } else if (typeof message.totalCount === "number" && message.totalCount > 0) {
      fragment.append(renderDetailList("WeChat Messages", [textCard(`共 ${message.totalCount} 条匹配，后端未返回 message 明细。`)]));
      hasDetails = true;
    }

    return hasDetails ? fragment : null;
  }

  function renderDetailList(title, children) {
    const wrapper = document.createElement("div");
    wrapper.className = "detail-block";

    const heading = document.createElement("p");
    heading.className = "detail-title";
    heading.textContent = title;

    wrapper.append(heading, ...children);
    return wrapper;
  }

  function renderCitation(citation) {
    const node = document.createElement("div");
    node.className = "citation";

    const source = document.createElement("strong");
    source.textContent = citation.source || citation.content_id || "未知来源";

    const snippet = document.createElement("span");
    const score = typeof citation.score === "number" ? ` · score ${citation.score.toFixed(3)}` : "";
    snippet.textContent = `${citation.snippet || "无片段"}${score}`;

    node.append(source, snippet);
    return node;
  }

  function renderAction(action) {
    const node = document.createElement("div");
    node.className = "action-row";

    const name = document.createElement("strong");
    name.textContent = action.action || "action";

    const status = document.createElement("span");
    status.className = "tag";
    status.textContent = action.ok ? "ok" : "failed";

    const payload = document.createElement("span");
    payload.textContent = JSON.stringify(action.payload || {});

    node.append(name, status, payload);
    return node;
  }

  function renderTodo(todo) {
    const node = document.createElement("div");
    node.className = "todo";

    const title = document.createElement("strong");
    title.textContent = `${todo.id ? `#${todo.id} ` : ""}${todo.title || "未命名待办"}`;

    const meta = document.createElement("span");
    const priority = PRIORITY_LABELS[todo.priority] || todo.priority;
    const status = STATUS_LABELS[todo.status] || todo.status;
    const dueDate = todo.due_date ? ` · 截止 ${todo.due_date}` : "";
    meta.textContent = `${status} · 优先级 ${priority}${dueDate}`;

    const detail = document.createElement("span");
    detail.textContent = todo.detail ? `\n${todo.detail}` : "";

    node.append(title, meta, detail);
    return node;
  }

  function renderWechatMessage(message) {
    const node = document.createElement("div");
    node.className = "wechat-message";

    const title = document.createElement("strong");
    title.textContent = `${message.talker_name || "未知联系人"}${message.room_name ? ` · ${message.room_name}` : ""}`;

    const content = document.createElement("span");
    content.textContent = `${message.date_str || ""}\n${message.content || ""}`;

    node.append(title, content);
    return node;
  }

  function textCard(text) {
    const node = document.createElement("div");
    node.className = "citation";
    node.textContent = text;
    return node;
  }

  function renderSessions() {
    els.sessionCount.textContent = state.sessions.length;
    els.sessionsList.replaceChildren();

    if (!state.sessions.length) {
      const empty = document.createElement("div");
      empty.className = "empty-state";
      empty.textContent = "还没有会话。发送第一条消息后，后端会返回 session_id，右侧会自动同步。";
      els.sessionsList.append(empty);
      return;
    }

    state.sessions.forEach((session) => {
      els.sessionsList.append(renderSessionItem(session));
    });
  }

  function renderSessionItem(session) {
    const item = document.createElement("article");
    item.className = "session-item";
    if (session.session_id === state.sessionId) item.classList.add("is-active");

    const main = document.createElement("button");
    main.type = "button";
    main.className = "session-main";
    main.addEventListener("click", () => selectSession(session));

    const title = document.createElement("span");
    title.className = "session-title";
    title.textContent = session.title || shortSessionId(session.session_id);

    const meta = document.createElement("span");
    meta.className = "session-meta";
    const uiMode = API_MODE_TO_UI_MODE[session.mode] || "knowledge";
    meta.textContent = `${MODE_CONFIG[uiMode].label} · ${formatDate(session.updated_at || session.created_at)}`;

    main.append(title, meta);

    const controls = document.createElement("div");
    controls.className = "session-controls";

    const renameButton = document.createElement("button");
    renameButton.type = "button";
    renameButton.textContent = "重命名";
    renameButton.addEventListener("click", () => renameSession(session));

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.textContent = "删除";
    deleteButton.addEventListener("click", () => deleteSession(session));

    controls.append(renameButton, deleteButton);
    item.append(main, controls);
    return item;
  }

  function renderSessionError(error) {
    els.sessionCount.textContent = "!";
    els.sessionsList.replaceChildren();
    const node = document.createElement("div");
    node.className = "empty-state";
    node.textContent = `会话同步失败：${readableError(error)}。请确认后端地址与 API Key。`;
    els.sessionsList.append(node);
  }

  function createMessage(role, text, extra = {}) {
    return {
      id:
        window.crypto && typeof window.crypto.randomUUID === "function"
          ? window.crypto.randomUUID()
          : `${Date.now()}-${Math.random()}`,
      role,
      mode: state.mode,
      text,
      ...extra,
    };
  }

  function persistCurrentTranscript() {
    if (!state.sessionId) return;
    state.transcripts[state.sessionId] = {
      mode: state.mode,
      updatedAt: new Date().toISOString(),
      messages: state.messages.slice(-80),
    };
    persistTranscripts();
  }

  function persistTranscripts() {
    localStorage.setItem(STORAGE_KEYS.transcripts, JSON.stringify(state.transcripts));
  }

  function loadJson(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch {
      return fallback;
    }
  }

  function shortSessionId(sessionId) {
    if (!sessionId) return "新会话";
    const parts = sessionId.split("_");
    const prefix = parts[0] || "session";
    const suffix = (parts[1] || sessionId).slice(0, 8);
    return `${prefix}_${suffix}`;
  }

  function formatDate(raw) {
    if (!raw) return "未知时间";
    return raw.replace("T", " ").slice(0, 19);
  }
})();
