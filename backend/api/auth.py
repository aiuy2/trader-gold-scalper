"""auth.py - register / login / refresh / logout. Issues a short-lived JWT
access token plus a long-lived refresh token (security/token_manager.py)
so the mobile app doesn't force a re-login every JWT_EXPIRE_MINUTES."""
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database.database import get_db
from database.repositories import users as users_repo
from app.security import (
    hash_password, verify_password, create_access_token,
    decode_access_token_payload,
)
from security import token_manager
from services.license_service import LicenseService

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


def _issue_tokens(email: str, user_id: int, device_id: str | None) -> TokenResponse:
    access_token = create_access_token(subject=email)
    refresh_token = token_manager.issue_refresh_token(user_id, email, device_id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db), x_device_id: str = Header(default=None)):
    if users_repo.get_by_email(db, payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = users_repo.create(db, payload.email, hash_password(payload.password), payload.full_name)
    # New accounts start on a trial license so the bot can be tried
    # immediately without a separate "activate" step.
    LicenseService.issue_trial(user.id)
    return _issue_tokens(user.email, user.id, x_device_id)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db), x_device_id: str = Header(default=None)):
    user = users_repo.get_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return _issue_tokens(user.email, user.id, x_device_id)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest):
    result = token_manager.redeem_refresh_token(payload.refresh_token)
    if result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")
    access_token = create_access_token(subject=result["email"])
    return TokenResponse(access_token=access_token, refresh_token=result["new_refresh_token"])


@router.post("/logout")
def logout(payload: RefreshRequest, authorization: str = Header(default=None)):
    token_manager.revoke_refresh_token(payload.refresh_token)
    # Also denylist the current access token so it stops working immediately
    # rather than lingering until its natural expiry.
    if authorization and authorization.lower().startswith("bearer "):
        access_token = authorization.split(" ", 1)[1]
        claims = decode_access_token_payload(access_token)
        if claims and claims.get("jti"):
            from datetime import datetime, timezone
            expires_at = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
            token_manager.denylist_access_token(claims["jti"], expires_at)
    return {"success": True}
