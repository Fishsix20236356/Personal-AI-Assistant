"""Knowledge loader — 文档导入与管理（先删后插策略）。"""

import hashlib
from pathlib import Path

from app.knowledge.base import get_shared_knowledge
from app.knowledge.reader_factory import SUPPORTED_EXTENSIONS, build_reader
from app.knowledge.tracker_repository import TrackerRepository
from config.settings import settings


class KnowledgeLoader:
    def __init__(self, tracker_repo: TrackerRepository):
        self.knowledge = get_shared_knowledge()
        self.tracker_repo = tracker_repo

    def ingest(self, file_path: str) -> dict:
        path = Path(file_path).resolve()
        file_hash = self._hash_file(path)
        record = self.tracker_repo.get(str(path))

        if record and record["file_hash"] == file_hash and record["status"] == "synced":
            return {"status": "skipped", "file_path": str(path)}

        # 先删旧内容（先删后插策略）
        if record and record.get("content_id"):
            try:
                self.knowledge.remove_content_by_id(record["content_id"])
            except Exception:
                pass

        # 使用 Knowledge.insert（内部会调用 reader 读取并 chunk）
        reader = build_reader(path.suffix)
        metadata = {
            "source_path": self._public_source_path(path),
            "file_hash": file_hash,
        }
        self.knowledge.insert(
            name=path.stem,
            path=str(path),
            metadata=metadata,
            reader=reader,
        )

        # 获取导入后的 content_id
        content_id = path.stem
        # 尝试获取 chunk 数量
        chunk_count = 0
        try:
            contents, _ = self.knowledge.get_content(limit=1000)
            for c in contents:
                if c.name == path.stem:
                    content_id = c.id
                    break
            chunk_count = len(contents)  # approximate
        except Exception:
            pass

        self.tracker_repo.upsert(
            file_path=str(path),
            content_id=content_id,
            file_hash=file_hash,
            file_size=path.stat().st_size,
            chunk_count=chunk_count,
            status="synced",
            last_error="",
        )
        return {
            "status": "synced",
            "file_path": str(path),
            "content_id": content_id,
            "chunk_count": chunk_count,
        }

    def delete(self, file_path: str) -> None:
        path = str(Path(file_path).resolve())
        record = self.tracker_repo.get(path)
        if record and record.get("content_id"):
            try:
                self.knowledge.remove_content_by_id(record["content_id"])
            except Exception:
                pass
        self.tracker_repo.delete(path)

    def rebuild_all(self) -> None:
        # 清空所有内容
        try:
            self.knowledge.remove_all_content()
        except Exception:
            pass
        self.tracker_repo.delete_all()
        # 全量重新导入
        for path in Path("data/documents").rglob("*"):
            if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                try:
                    self.ingest(str(path))
                except Exception as e:
                    print(f"[rebuild_all] Error ingesting {path}: {e}")

    @staticmethod
    def _hash_file(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _public_source_path(path: Path) -> str:
        watch_root = Path(settings.WATCH_DIR).resolve()
        resolved = path.resolve()
        try:
            return resolved.relative_to(watch_root).as_posix()
        except ValueError:
            return resolved.name
