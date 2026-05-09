from fastapi import APIRouter, Depends, Header, HTTPException, status

from dependencies import auth_service
from models.user import (
    TokenPair,
    TokenRefresh,
    UserInfo,
    UserLogin,
    UserRecord,
    UserRegister,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
def register(payload: UserRegister) -> UserRecord:
    try:
        return auth_service.register(payload)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/login")
def login(payload: UserLogin) -> TokenPair:
    result = auth_service.login(payload.username, payload.password)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    return result


@router.post("/refresh")
def refresh(payload: TokenRefresh) -> TokenPair:
    result = auth_service.refresh(payload.refresh_token)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    return result


@router.get("/me")
def get_current_user(authorization: str | None = Header(default=None)) -> UserInfo:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    user_id = auth_service.verify_access_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    info = auth_service.get_user_info(user_id)
    if info is None:
        raise HTTPException(status_code=404, detail="User not found")
    return info
