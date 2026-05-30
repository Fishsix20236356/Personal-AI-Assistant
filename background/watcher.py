"""DocChangeHandler — watchdog 文件变更处理器。"""

import asyncio
from pathlib import Path

from watchdog.events import FileSystemEventHandler

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
