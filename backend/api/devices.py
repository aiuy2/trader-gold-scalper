"""devices.py - list/register/revoke devices bound to the user's license."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from database.models.user import User
from app.dependencies import get_current_user
from services.device_service import DeviceService

router = APIRouter(prefix="/devices", tags=["devices"])


class RegisterDeviceRequest(BaseModel):
    device_id: str
    device_name: str | None = None
    platform: str | None = None


@router.get("")
def list_devices(user: User = Depends(get_current_user)):
    return DeviceService.list_devices(user.id)


@router.post("")
def register_device(payload: RegisterDeviceRequest, user: User = Depends(get_current_user)):
    return DeviceService.register_device(user.id, payload.device_id, payload.device_name, payload.platform)


@router.delete("/{device_id}")
def revoke_device(device_id: str, user: User = Depends(get_current_user)):
    return {"success": DeviceService.revoke_device(user.id, device_id)}
