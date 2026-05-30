"""Knowledge service — 知识检索与状态查询。"""

from pathlib import Path

from app.api.schemas.chat import Citation
from app.knowledge.base import get_shared_knowledge
from app.knowledge.tracker_repository import TrackerRepository
from config.settings import settings


class KnowledgeService:
    def __init__(self, tracker_repo: TrackerRepository):
        self.knowledge = get_shared_knowledge()
        self.tracker_repo = tracker_repo

    async def search_references(self, query: str) -> list[Citation]:
        results = self.knowledge.search(query=query)
        citations = []
        for doc in results:
            meta = doc.meta_data or {}
            citations.append(
                Citation(
                    content_id=doc.id or "",
                    source=self._public_source(meta.get("source_path", "")),
                    snippet=doc.content[:500] if doc.content else "",
                    score=None,
                )
            )
        return citations

    async def get_status(self) -> dict:
        all_records = self.tracker_repo.list_all()
        total_documents = len(all_records)
        total_chunks = sum(r.get("chunk_count", 0) for r in all_records)

        return {
            "total_documents": total_documents,
            "total_chunks": total_chunks,
            "pending_files": self.tracker_repo.count_by_status("pending"),
            "error_files": self.tracker_repo.count_by_status("error"),
            "last_sync_time": self.tracker_repo.get_last_sync_time(),
        }

    @staticmethod
    def _public_source(raw_source: str) -> str:
        if not raw_source:
            return ""

        source = Path(raw_source)
        if not source.is_absolute():
            return source.as_posix()

        watch_root = Path(settings.WATCH_DIR).resolve()
        resolved = source.resolve()
        try:
            return resolved.relative_to(watch_root).as_posix()
        except ValueError:
            return resolved.name
