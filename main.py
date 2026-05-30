"""Application entry point — FastAPI app with lifespan."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.background.incremental_update import IncrementalUpdateWorker
from app.background.scheduler import create_scheduler
from app.background.watcher import DocChangeHandler
from app.core.session_service import SessionService
from app.db.app_meta import AppMetaRepository
from app.knowledge.loader import KnowledgeLoader
from app.knowledge.service import KnowledgeService
from app.knowledge.tracker_repository import TrackerRepository
from app.reports.daily_report import DailyReportService
from app.sop.manager import TodoManager
from app.sop.tools import add_todo, list_todos, update_todo, delete_todo, mark_done
from app.wechat.search_store import WeChatSearchStore
from app.core.security import validate_security_settings
from config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_security_settings()
    loop = asyncio.get_running_loop()

    # ── 初始化 Repository / Service ─────────────────────
    app_meta_repo = AppMetaRepository(settings.APP_META_DB_PATH)
    tracker_repo = TrackerRepository(settings.APP_META_DB_PATH)
    session_service = SessionService(app_meta_repo)
    knowledge_service = KnowledgeService(tracker_repo)
    knowledge_loader = KnowledgeLoader(tracker_repo)
    todo_manager = TodoManager(settings.APP_META_DB_PATH)
    wechat_search = WeChatSearchStore(
        raw_db_path=settings.WECHAT_RAW_DB_PATH,
        search_db_path=settings.WECHAT_SEARCH_DB_PATH,
    )

    # ── 增量同步微信数据 ─────────────────────────────────
    try:
        wechat_search.sync_incremental()
    except Exception as e:
        print(f"[lifespan] WeChat sync warning: {e}")

    # ── 启动 IncrementalUpdateWorker ──────────────────────
    worker = IncrementalUpdateWorker(
        loader=knowledge_loader,
        debounce_ms=settings.FILE_DEBOUNCE_MS,
    )
    worker_task = asyncio.create_task(worker.run())

    # ── 启动 watchdog 文件监听 ────────────────────────────
    observer = None
    try:
        from watchdog.observers import Observer

        observer = Observer()
        handler = DocChangeHandler(loop=loop, enqueue_change=worker.enqueue)
        observer.schedule(handler, settings.WATCH_DIR, recursive=True)
        observer.start()
    except Exception as e:
        print(f"[lifespan] Watchdog warning: {e}")

    # ── 启动调度器 ───────────────────────────────────────
    report_service = DailyReportService(app_meta_repo, settings.APP_META_DB_PATH)
    scheduler = create_scheduler(wechat_search, report_service)
    scheduler.start()

    # ── 挂载到 app.state ─────────────────────────────────
    app.state.session_service = session_service
    app.state.knowledge_service = knowledge_service
    app.state.knowledge_loader = knowledge_loader
    app.state.todo_manager = todo_manager
    app.state.wechat_search = wechat_search
    app.state.worker = worker
    app.state.sop_tools = [add_todo, list_todos, update_todo, delete_todo, mark_done]

    print("[lifespan] Application started successfully.")

    try:
        yield
    finally:
        # ── 优雅关闭 ──────────────────────────────────────
        print("[lifespan] Shutting down...")
        scheduler.shutdown(wait=False)
        if observer:
            observer.stop()
            await asyncio.to_thread(observer.join, 5)
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
        print("[lifespan] Shutdown complete.")


app = FastAPI(
    title="Personal AI Assistant",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins_list,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.cors_allow_methods_list,
    allow_headers=settings.cors_allow_headers_list,
)

app.include_router(api_router)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
if WEB_DIR.exists():
    app.mount("/ui", StaticFiles(directory=WEB_DIR, html=True), name="ui")


@app.get("/")
async def root():
    return RedirectResponse(url="/ui/")


@app.get("/health")
async def health():
    return {"status": "ok"}
