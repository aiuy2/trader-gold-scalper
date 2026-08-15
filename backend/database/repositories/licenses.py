"""licenses.py - license CRUD."""
from sqlalchemy.orm import Session
from database.models.license import License


def get_active_for_user(db: Session, user_id: int):
    return db.query(License).filter(License.user_id == user_id, License.is_active == True).first()  # noqa: E712


def create(db: Session, user_id: int, license_key: str, plan: str = "trial"):
    lic = License(user_id=user_id, license_key=license_key, plan=plan, is_active=True)
    db.add(lic)
    db.commit()
    db.refresh(lic)
    return lic
