"""Router aggregation — 统一注册所有 v1 路由。"""

from fastapi import APIRouter, Depends

from app.api.v1.chat import router as chat_router
from app.api.v1.wechat import router as wechat_router
from app.api.v1.sop import router as sop_router
from app.api.v1.session import router as session_router
from app.api.v1.knowledge import router as knowledge_router
from app.core.security import require_api_key

api_router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)])

api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(wechat_router, prefix="/wechat", tags=["wechat"])
api_router.include_router(sop_router, prefix="/sop", tags=["sop"])
api_router.include_router(session_router, prefix="/sessions", tags=["sessions"])
api_router.include_router(knowledge_router, prefix="/knowledge", tags=["knowledge"])
