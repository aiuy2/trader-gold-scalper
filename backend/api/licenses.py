"""licenses.py - view current license + activate a purchased license key."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from database.models.user import User
from app.dependencies import get_current_user
from services.license_service import LicenseService

router = APIRouter(prefix="/licenses", tags=["licenses"])


class ActivateRequest(BaseModel):
    license_key: str
    plan: str = "monthly"


@router.get("/current")
def current_license(user: User = Depends(get_current_user)):
    return LicenseService.current(user.id)


@router.post("/activate")
def activate_license(payload: ActivateRequest, user: User = Depends(get_current_user)):
    return LicenseService.activate(user.id, payload.license_key, payload.plan)
