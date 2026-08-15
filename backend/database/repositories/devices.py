"""devices.py - registered device CRUD (used by license device-binding)."""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from database.models.device import Device


def list_for_user(db: Session, user_id: int):
    return db.query(Device).filter(Device.user_id == user_id).all()


def get_by_device_id(db: Session, user_id: int, device_id: str):
    return db.query(Device).filter(Device.user_id == user_id, Device.device_id == device_id).first()


def create(db: Session, user_id: int, device_id: str, device_name: str = None, platform: str = None):
    device = Device(
        user_id=user_id, device_id=device_id, device_name=device_name,
        platform=platform, last_seen=datetime.now(timezone.utc),
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def touch(db: Session, device: Device):
    device.last_seen = datetime.now(timezone.utc)
    db.commit()
    db.refresh(device)
    return device


def delete(db: Session, user_id: int, device_id: str) -> bool:
    deleted = db.query(Device).filter(
        Device.user_id == user_id, Device.device_id == device_id
    ).delete()
    db.commit()
    return deleted > 0
