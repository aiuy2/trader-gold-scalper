"""notifications.py - in-app notification inbox."""
from fastapi import APIRouter, Depends

from database.models.user import User
from app.dependencies import get_current_user
from services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(unread_only: bool = False, user: User = Depends(get_current_user)):
    return NotificationService.list_for_user(user.id, unread_only=unread_only)


@router.post("/{notification_id}/read")
def mark_read(notification_id: int, user: User = Depends(get_current_user)):
    return {"success": NotificationService.mark_read(user.id, notification_id)}
