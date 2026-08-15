"""positions.py - open positions CRUD (mirrors current broker state)."""
from sqlalchemy.orm import Session
from database.models.position import Position


def list_for_user(db: Session, user_id: int):
    return db.query(Position).filter(Position.user_id == user_id).all()


def create(db: Session, **kwargs):
    position = Position(**kwargs)
    db.add(position)
    db.commit()
    db.refresh(position)
    return position


def delete_by_ticket(db: Session, user_id: int, ticket: int):
    db.query(Position).filter(Position.user_id == user_id, Position.ticket == ticket).delete()
    db.commit()


def clear_for_worker(db: Session, worker_id: int):
    db.query(Position).filter(Position.worker_id == worker_id).delete()
    db.commit()
