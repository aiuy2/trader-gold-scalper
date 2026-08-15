"""authorization.py - gate endpoints behind an active (non-expired) license."""
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.database import get_db
from database.models.user import User
from database.repositories import licenses as licenses_repo
from app.dependencies import get_current_user


def require_active_license(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lic = licenses_repo.get_active_for_user(db, user.id)
    if not lic:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active license.")
    if lic.expires_at and lic.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="License expired.")
    return user
