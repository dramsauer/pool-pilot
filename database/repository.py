from __future__ import annotations

import json
import datetime
from sqlalchemy.orm import Session
from database.models import Reading, MaintenanceTask, Photo, Pool, Trinkwasser, Product


def save_reading(
    session: Session,
    ph: float,
    chlorine: float,
    alkalinity: float,
    hardness: float,
    temperature_c: float,
    lsi: float,
    rsi: float,
    dosing: list | None = None,
    notes: str = "",
) -> Reading:
    reading = Reading(
        ph=ph,
        chlorine=chlorine,
        alkalinity=alkalinity,
        hardness=hardness,
        temperature_c=temperature_c,
        lsi_value=lsi,
        rsi_value=rsi,
        dosing_recommendation=json.dumps(dosing, ensure_ascii=False)
        if dosing
        else None,
        notes=notes,
    )
    session.add(reading)
    session.commit()
    return reading


def get_readings(session: Session, limit: int = 50) -> list[Reading]:
    return session.query(Reading).order_by(Reading.timestamp.desc()).limit(limit).all()


def get_readings_since(session: Session, days: int = 30) -> list[Reading]:
    since = datetime.datetime.now() - datetime.timedelta(days=days)
    return (
        session.query(Reading)
        .filter(Reading.timestamp >= since)
        .order_by(Reading.timestamp.desc())
        .all()
    )


def get_latest_reading(session: Session) -> Reading | None:
    return session.query(Reading).order_by(Reading.timestamp.desc()).first()


def save_task(
    session: Session,
    task_type: str,
    title: str,
    description: str = "",
    due_date: datetime.date | None = None,
    interval_days: int = 0,
) -> MaintenanceTask:
    task = MaintenanceTask(
        task_type=task_type,
        title=title,
        description=description,
        due_date=due_date,
        interval_days=interval_days,
    )
    session.add(task)
    session.commit()
    return task


def get_pending_tasks(session: Session) -> list[MaintenanceTask]:
    return (
        session.query(MaintenanceTask)
        .filter(MaintenanceTask.completed.is_not(True))
        .order_by(MaintenanceTask.due_date)
        .all()
    )


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


# --- Pool CRUD ---


def save_pool(
    session: Session,
    name: str,
    volume_liter: float,
    pool_type: str = "chlorine",
    ph_min: float = 7.2,
    ph_max: float = 7.6,
    chlorine_min: float = 0.5,
    chlorine_max: float = 3.0,
    alkalinity_min: float = 80,
    alkalinity_max: float = 120,
    hardness_min: float = 150,
    hardness_max: float = 250,
    temperature_default: float = 35,
    trinkwasser_id: int | None = None,
) -> Pool:
    pool = Pool(
        name=name,
        volume_liter=volume_liter,
        pool_type=pool_type,
        ph_min=ph_min,
        ph_max=ph_max,
        chlorine_min=chlorine_min,
        chlorine_max=chlorine_max,
        alkalinity_min=alkalinity_min,
        alkalinity_max=alkalinity_max,
        hardness_min=hardness_min,
        hardness_max=hardness_max,
        temperature_default=temperature_default,
        trinkwasser_id=trinkwasser_id,
    )
    session.add(pool)
    session.commit()
    session.refresh(pool)
    return pool


def get_pools(session: Session) -> list[Pool]:
    return session.query(Pool).order_by(Pool.name).all()


def get_pool(session: Session, pool_id: int) -> Pool | None:
    return session.query(Pool).filter(Pool.id == pool_id).first()


def update_pool(session: Session, pool_id: int, **kwargs) -> Pool | None:
    pool = session.query(Pool).filter(Pool.id == pool_id).first()
    if pool:
        for key, value in kwargs.items():
            if hasattr(pool, key):
                setattr(pool, key, value)
        session.commit()
        session.refresh(pool)
    return pool


def delete_pool(session: Session, pool_id: int):
    pool = session.query(Pool).filter(Pool.id == pool_id).first()
    if pool:
        session.delete(pool)
        session.commit()


# --- Trinkwasser CRUD ---


def save_trinkwasser(
    session: Session,
    name: str,
    ph_default: float = 7.5,
    alkalinity_default: float = 145.0,
    calcium_hardness_default: float = 185.0,
    notes: str = "",
) -> Trinkwasser:
    tw = Trinkwasser(
        name=name,
        ph_default=ph_default,
        alkalinity_default=alkalinity_default,
        calcium_hardness_default=calcium_hardness_default,
        notes=notes,
    )
    session.add(tw)
    session.commit()
    session.refresh(tw)
    return tw


def get_trinkwasser_quellen(session: Session) -> list[Trinkwasser]:
    return session.query(Trinkwasser).order_by(Trinkwasser.name).all()


def get_trinkwasser(session: Session, tw_id: int) -> Trinkwasser | None:
    return session.query(Trinkwasser).filter(Trinkwasser.id == tw_id).first()


def delete_trinkwasser(session: Session, tw_id: int):
    tw = session.query(Trinkwasser).filter(Trinkwasser.id == tw_id).first()
    if tw:
        session.delete(tw)
        session.commit()


# --- Product CRUD ---


def save_product(
    session: Session,
    name: str,
    typ: str,
    dosage_factor: float = 0,
    unit: str = "g",
    active_chlorine_per_tab: float | None = None,
    interval_days: int = 0,
    notes: str = "",
) -> Product:
    prod = Product(
        name=name,
        typ=typ,
        dosage_factor=dosage_factor,
        unit=unit,
        active_chlorine_per_tab=active_chlorine_per_tab,
        interval_days=interval_days,
        notes=notes,
    )
    session.add(prod)
    session.commit()
    session.refresh(prod)
    return prod


def get_products(session: Session) -> list[Product]:
    return session.query(Product).order_by(Product.name).all()


def get_product(session: Session, product_id: int) -> Product | None:
    return session.query(Product).filter(Product.id == product_id).first()


def update_product(session: Session, product_id: int, **kwargs) -> Product | None:
    prod = session.query(Product).filter(Product.id == product_id).first()
    if prod:
        for key, value in kwargs.items():
            if hasattr(prod, key):
                setattr(prod, key, value)
        session.commit()
        session.refresh(prod)
    return prod


def delete_product(session: Session, product_id: int):
    prod = session.query(Product).filter(Product.id == product_id).first()
    if prod:
        session.delete(prod)
        session.commit()


# --- Extended Reading functions ---


def save_reading_for_pool(
    session: Session,
    pool_id: int,
    ph: float,
    chlorine: float,
    alkalinity: float,
    hardness: float,
    temperature_c: float,
    lsi: float,
    rsi: float,
    dosing: list | None = None,
    notes: str = "",
) -> Reading:
    reading = Reading(
        pool_id=pool_id,
        ph=ph,
        chlorine=chlorine,
        alkalinity=alkalinity,
        hardness=hardness,
        temperature_c=temperature_c,
        lsi_value=lsi,
        rsi_value=rsi,
        dosing_recommendation=json.dumps(dosing, ensure_ascii=False)
        if dosing
        else None,
        notes=notes,
    )
    session.add(reading)
    session.commit()
    session.refresh(reading)
    return reading


def get_readings_for_pool(
    session: Session, pool_id: int, limit: int = 50
) -> list[Reading]:
    return (
        session.query(Reading)
        .filter(Reading.pool_id == pool_id)
        .order_by(Reading.timestamp.desc())
        .limit(limit)
        .all()
    )


def get_latest_reading_for_pool(session: Session, pool_id: int) -> Reading | None:
    return (
        session.query(Reading)
        .filter(Reading.pool_id == pool_id)
        .order_by(Reading.timestamp.desc())
        .first()
    )


# --- Extended Task functions ---


def get_pending_tasks_for_pool(session: Session, pool_id: int) -> list[MaintenanceTask]:
    return (
        session.query(MaintenanceTask)
        .filter(
            MaintenanceTask.pool_id == pool_id,
            MaintenanceTask.completed.is_not(True),
        )
        .order_by(MaintenanceTask.due_date)
        .all()
    )


def get_task(session: Session, task_id: int) -> MaintenanceTask | None:
    return session.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()


def complete_task_with_notes(
    session: Session, task_id: int, executed_notes: str = ""
) -> MaintenanceTask | None:
    task = session.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
    if task:
        task.completed = True
        task.completed_at = datetime.datetime.now()
        task.executed_notes = executed_notes
        session.commit()

        if task.follow_up_days > 0:
            follow_up = MaintenanceTask(
                pool_id=task.pool_id,
                reading_id=task.reading_id,
                product_id=task.product_id,
                parent_task_id=task.id,
                task_type=task.task_type,
                title=f"{task.title} (Folge)",
                description=f"Folgeaufgabe — alle {task.follow_up_days} Tage",
                due_date=(
                    datetime.date.today() + datetime.timedelta(days=task.follow_up_days)
                ),
                interval_days=task.interval_days,
                follow_up_days=task.follow_up_days,
            )
            session.add(follow_up)
            session.commit()

    return task


def get_tasks_by_date_range(
    session: Session, start_date: datetime.date, end_date: datetime.date, pool_id: int | None = None
) -> list[MaintenanceTask]:
    q = session.query(MaintenanceTask).filter(
        MaintenanceTask.due_date >= start_date,
        MaintenanceTask.due_date <= end_date,
    )
    if pool_id is not None:
        q = q.filter(MaintenanceTask.pool_id == pool_id)
    return q.order_by(MaintenanceTask.due_date, MaintenanceTask.completed).all()
