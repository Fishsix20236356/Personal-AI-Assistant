"""Knowledge route — 状态、上传、删除、重建。"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from app.api.schemas.knowledge import KnowledgeStatusResponse
from app.deps import get_knowledge_service, get_knowledge_loader
from app.knowledge.service import KnowledgeService
from app.knowledge.loader import KnowledgeLoader
from app.knowledge.reader_factory import SUPPORTED_EXTENSIONS
from config.settings import settings

router = APIRouter()


def _watch_root() -> Path:
    root = Path(settings.WATCH_DIR).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _resolve_under_watch_dir(path_or_name: str) -> Path:
    root = _watch_root()
    normalized = path_or_name.replace("\\", "/")
    target = (root / normalized).resolve()
    try:
        target.relative_to(root)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid file path") from e
    return target


def _sanitize_upload_filename(raw_name: str) -> str:
    if not raw_name:
        raise HTTPException(status_code=400, detail="Missing file name")

    normalized = raw_name.replace("\\", "/").strip()
    if "/" in normalized:
        raise HTTPException(status_code=400, detail="Invalid file name")

    safe_name = Path(normalized).name.strip()
    if safe_name in {"", ".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid file name")
    if safe_name != normalized:
        raise HTTPException(status_code=400, detail="Invalid file name")
    return safe_name


@router.get("/status", response_model=KnowledgeStatusResponse)
async def knowledge_status(
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    status = await knowledge_service.get_status()
    return KnowledgeStatusResponse(**status)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    knowledge_loader: KnowledgeLoader = Depends(get_knowledge_loader),
):
    safe_name = _sanitize_upload_filename(file.filename or "")
    ext = Path(safe_name).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: {SUPPORTED_EXTENSIONS}",
        )

    dest = _resolve_under_watch_dir(safe_name)
    max_upload_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    written = 0

    try:
        with dest.open("wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_upload_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Max size is {settings.MAX_UPLOAD_SIZE_MB}MB",
                    )
                f.write(chunk)
    except Exception:
        if dest.exists():
            dest.unlink()
        raise

    result = knowledge_loader.ingest(str(dest))
    return result


@router.delete("/files/{file_path:path}")
async def delete_document(
    file_path: str,
    knowledge_loader: KnowledgeLoader = Depends(get_knowledge_loader),
):
    full_path = _resolve_under_watch_dir(file_path)
    if full_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    if full_path.is_dir():
        raise HTTPException(status_code=400, detail="Invalid file path")
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    knowledge_loader.delete(str(full_path))
    full_path.unlink()
    return {"ok": True}


@router.post("/rebuild")
async def rebuild_knowledge(
    knowledge_loader: KnowledgeLoader = Depends(get_knowledge_loader),
):
    knowledge_loader.rebuild_all()
    return {"ok": True}
