"""users.py - current user's profile."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from database.models.user import User
from app.dependencies import get_current_user
from services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return UserService.get_profile(user.id)


@router.patch("/me")
def update_me(payload: UpdateProfileRequest, user: User = Depends(get_current_user)):
    return UserService.update_profile(user.id, payload.full_name)


@router.post("/me/change-password")
def change_password(payload: ChangePasswordRequest, user: User = Depends(get_current_user)):
    return UserService.change_password(user.id, payload.old_password, payload.new_password)
