from __future__ import annotations

import json
import datetime
from sqlalchemy.orm import Session
from database.models import Reading, MaintenanceTask, Photo


def save_reading(session: Session, ph: float, chlorine: float, alkalinity: float,
                 hardness: float, temperature_c: float, lsi: float, rsi: float,
                 dosing: list | None = None, notes: str = "") -> Reading:
    reading = Reading(
        ph=ph, chlorine=chlorine, alkalinity=alkalinity,
        hardness=hardness, temperature_c=temperature_c,
        lsi_value=lsi, rsi_value=rsi,
        dosing_recommendation=json.dumps(dosing, ensure_ascii=False) if dosing else None,
        notes=notes,
    )
    session.add(reading)
    session.commit()
    return reading


def get_readings(session: Session, limit: int = 50) -> list[Reading]:
    return session.query(Reading).order_by(Reading.timestamp.desc()).limit(limit).all()


def get_readings_since(session: Session, days: int = 30) -> list[Reading]:
    since = datetime.datetime.now() - datetime.timedelta(days=days)
    return session.query(Reading).filter(Reading.timestamp >= since).order_by(Reading.timestamp.desc()).all()


def get_latest_reading(session: Session) -> Reading | None:
    return session.query(Reading).order_by(Reading.timestamp.desc()).first()


def save_task(session: Session, task_type: str, title: str, description: str = "",
              due_date: datetime.date | None = None, interval_days: int = 0) -> MaintenanceTask:
    task = MaintenanceTask(
        task_type=task_type, title=title, description=description,
        due_date=due_date, interval_days=interval_days,
    )
    session.add(task)
    session.commit()
    return task


def get_pending_tasks(session: Session) -> list[MaintenanceTask]:
    return session.query(MaintenanceTask).filter(MaintenanceTask.completed == False).order_by(MaintenanceTask.due_date).all()


def complete_task(session: Session, task_id: int):
    task = session.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
    if task:
        task.completed = True
        task.completed_at = datetime.datetime.now()
        session.commit()


def save_photo(session: Session, image_path: str, caption: str = "") -> Photo:
    photo = Photo(image_path=image_path, caption=caption)
    session.add(photo)
    session.commit()
    return photo


def get_photos(session: Session) -> list[Photo]:
    return session.query(Photo).order_by(Photo.timestamp.desc()).all()


def delete_photo(session: Session, photo_id: int):
    photo = session.query(Photo).filter(Photo.id == photo_id).first()
    if photo:
        session.delete(photo)
        session.commit()
