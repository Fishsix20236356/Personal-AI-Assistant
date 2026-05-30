"""IncrementalUpdateWorker — 防抖增量更新。"""

import asyncio
import time


class IncrementalUpdateWorker:
    def __init__(self, loader, debounce_ms: int = 800):
        self.loader = loader
        self.debounce_ms = debounce_ms
        self.pending: dict[str, tuple[str, float]] = {}

    def enqueue(self, action: str, file_path: str) -> None:
        self.pending[file_path] = (action, time.monotonic())

    async def run(self) -> None:
        while True:
            await asyncio.sleep(self.debounce_ms / 1000)
            if not self.pending:
                continue
            ready = list(self.pending.items())
            self.pending.clear()
            for file_path, (action, _) in ready:
                await self._handle(action, file_path)

    async def _handle(self, action: str, file_path: str) -> None:
        try:
            if action == "upsert":
                await asyncio.to_thread(self.loader.ingest, file_path)
            elif action == "delete":
                await asyncio.to_thread(self.loader.delete, file_path)
        except Exception as e:
            print(f"[IncrementalUpdateWorker] Error processing {action} {file_path}: {e}")
