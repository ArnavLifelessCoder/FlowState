from __future__ import annotations

from fastapi import Header, HTTPException, Query, WebSocketException, status

from config import get_settings


def _is_authorized(token: str | None) -> bool:
    """Check auth via legacy API token OR valid JWT access token."""
    settings = get_settings()
    if not settings.enable_auth:
        return True
    if token is None:
        return False
    # Legacy static token
    if token == settings.api_token:
        return True
    # JWT access token
    try:
        import jwt
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload.get("type") == "access" and payload.get("sub") is not None
    except Exception:
        return False


def require_api_token(authorization: str | None = Header(default=None)) -> None:
    token = authorization.removeprefix("Bearer ").strip() if authorization else None
    if not _is_authorized(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )


def require_ws_token(token: str | None = Query(default=None)) -> None:
    if not _is_authorized(token):
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
