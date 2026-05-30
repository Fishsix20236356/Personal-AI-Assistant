"""FastAPI dependency injection."""

from fastapi import Request

from app.core.security import get_current_user_id as _get_current_user_id


def get_session_service(request: Request):
    return request.app.state.session_service


def get_knowledge_service(request: Request):
    return request.app.state.knowledge_service


def get_knowledge_loader(request: Request):
    return request.app.state.knowledge_loader


def get_todo_manager(request: Request):
    return request.app.state.todo_manager


def get_wechat_search(request: Request):
    return request.app.state.wechat_search


def get_current_user_id(request: Request) -> str:
    return _get_current_user_id(request)
