"""authentication.py - device-aware auth layered on top of the base JWT
auth in app/security.py + app/dependencies.py. Records a session touch
(for the 'active devices' list and license device limits) whenever a
request carries an X-Device-Id header."""
from fastapi import Depends, Header
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.user import User
from app.dependencies import get_current_user
from security import session_manager


def get_current_user_with_device(
    x_device_id: str = Header(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if x_device_id:
        session_manager.touch(user.id, x_device_id)
    return user
