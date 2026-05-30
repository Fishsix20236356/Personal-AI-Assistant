"""Security helpers: API key auth and user identity extraction."""

import re
import secrets

from fastapi import HTTPException, Request, status

from config.settings import settings

_USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:@-]{1,64}$")


def validate_security_settings() -> None:
    """Fail fast on insecure configuration."""
    if settings.AUTH_ENABLED and not settings.APP_API_KEY:
        raise RuntimeError(
            "AUTH_ENABLED=true but APP_API_KEY is empty. "
            "Please set APP_API_KEY in .env."
        )


def _extract_api_key(request: Request) -> str:
    key = request.headers.get(settings.API_KEY_HEADER, "").strip()
    if key:
        return key

    authorization = request.headers.get("Authorization", "").strip()
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()

    return ""


def require_api_key(request: Request) -> None:
    """Dependency to enforce API key authentication."""
    if not settings.AUTH_ENABLED:
        return

    provided = _extract_api_key(request)
    if not provided or not secrets.compare_digest(provided, settings.APP_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )


def get_current_user_id(request: Request) -> str:
    """
    Resolve current user id from trusted header.
    Falls back to DEFAULT_USER_ID for single-user deployments.
    """
    user_id = request.headers.get(settings.USER_ID_HEADER, "").strip()
    if not user_id:
        return settings.DEFAULT_USER_ID

    if not _USER_ID_PATTERN.fullmatch(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {settings.USER_ID_HEADER}",
        )

    return user_id
