from __future__ import annotations

import json
import datetime
from sqlalchemy.orm import Session
from database.models import Reading, MaintenanceTask, Photo, Pool, Trinkwasser, Product, Instrument, TaskTemplate, PoolTaskDefault


def save_reading(
    session: Session,
    ph: float,
    chlorine: float,
    alkalinity: float,
    hardness: float,
    temperature_c: float,
    lsi: float,
    rsi: float,
    csi: float = 0.0,
    ccpp: float = 0.0,
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
        csi_value=csi,
        ccpp_value=ccpp,
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
    pool_id: int | None = None,
    product_id: int | None = None,
    product_name: str | None = None,
    recommended_amount: float | None = None,
    recommended_unit: str | None = None,
    template_id: int | None = None,
) -> MaintenanceTask:
    task = MaintenanceTask(
        task_type=task_type,
        title=title,
        description=description,
        due_date=due_date,
        interval_days=interval_days,
        pool_id=pool_id,
        product_id=product_id,
        product_name=product_name,
        recommended_amount=recommended_amount,
        recommended_unit=recommended_unit,
        template_id=template_id,
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
    instrument_id: int | None = None,
    shape: str = "rechteckig",
    inner_length_cm: float | None = None,
    inner_width_cm: float | None = None,
    inner_diameter_cm: float | None = None,
    min_fill_height_cm: float = 35.0,
    max_fill_height_cm: float = 45.0,
    auto_measurement_task_days: int = 7,
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
        instrument_id=instrument_id,
        shape=shape,
        inner_length_cm=inner_length_cm,
        inner_width_cm=inner_width_cm,
        inner_diameter_cm=inner_diameter_cm,
        min_fill_height_cm=min_fill_height_cm,
        max_fill_height_cm=max_fill_height_cm,
        auto_measurement_task_days=auto_measurement_task_days,
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
    csi: float = 0.0,
    ccpp: float = 0.0,
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
        csi_value=csi,
        ccpp_value=ccpp,
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
    session: Session,
    task_id: int,
    executed_notes: str = "",
    actual_amount: float | None = None,
    actual_unit: str | None = None,
) -> MaintenanceTask | None:
    task = session.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
    if task:
        task.completed = True
        task.completed_at = datetime.datetime.now()
        task.executed_notes = executed_notes
        if actual_amount is not None:
            task.actual_amount = actual_amount
            task.actual_unit = actual_unit or task.recommended_unit
        session.commit()

        # Generate follow-up from follow_up_days
        if task.follow_up_days > 0:
            follow_up = MaintenanceTask(
                pool_id=task.pool_id,
                reading_id=task.reading_id,
                product_id=task.product_id,
                product_name=task.product_name,
                parent_task_id=task.id,
                task_type=task.task_type,
                title=f"{task.title} (Folge)",
                description=f"Folgeaufgabe — alle {task.follow_up_days} Tage",
                due_date=(
                    datetime.date.today() + datetime.timedelta(days=task.follow_up_days)
                ),
                interval_days=task.interval_days,
                follow_up_days=task.follow_up_days,
                template_id=task.template_id,
            )
            session.add(follow_up)
            session.commit()

        # Generate next template instance if this was a template task
        if task.template_id and task.interval_days > 0:
            _generate_next_template_instance(session, task)

    return task


def _generate_next_template_instance(session: Session, completed_task: MaintenanceTask) -> MaintenanceTask | None:
    """Generate the next recurring instance after completing a template-sourced task."""
    if not completed_task.template_id or completed_task.interval_days <= 0:
        return None
    next_due = datetime.date.today() + datetime.timedelta(days=completed_task.interval_days)
    existing = session.query(MaintenanceTask).filter(
        MaintenanceTask.template_id == completed_task.template_id,
        MaintenanceTask.pool_id == completed_task.pool_id,
        MaintenanceTask.due_date == next_due,
    ).first()
    if existing:
        return None
    task = MaintenanceTask(
        pool_id=completed_task.pool_id,
        template_id=completed_task.template_id,
        task_type=completed_task.task_type,
        title=completed_task.title,
        description=completed_task.description,
        due_date=next_due,
        interval_days=completed_task.interval_days,
        recommended_amount=completed_task.recommended_amount,
        recommended_unit=completed_task.recommended_unit,
        product_id=completed_task.product_id,
        product_name=completed_task.product_name,
    )
    session.add(task)
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


# --- Task Template ---


def get_task_templates(session: Session) -> list[TaskTemplate]:
    return session.query(TaskTemplate).order_by(TaskTemplate.category, TaskTemplate.name).all()


def get_active_templates_for_pool(session: Session, pool_id: int) -> list[TaskTemplate]:
    return (
        session.query(TaskTemplate)
        .join(PoolTaskDefault, TaskTemplate.id == PoolTaskDefault.template_id)
        .filter(
            PoolTaskDefault.pool_id == pool_id,
            PoolTaskDefault.active.is_(True),
        )
        .order_by(TaskTemplate.category, TaskTemplate.name)
        .all()
    )


def set_pool_template_active(
    session: Session, pool_id: int, template_id: int, active: bool
) -> None:
    ptd = session.query(PoolTaskDefault).filter(
        PoolTaskDefault.pool_id == pool_id,
        PoolTaskDefault.template_id == template_id,
    ).first()
    if ptd:
        ptd.active = active
    else:
        session.add(PoolTaskDefault(
            pool_id=pool_id, template_id=template_id, active=active,
        ))
    session.commit()


def get_pool_task_defaults(session: Session, pool_id: int) -> list[PoolTaskDefault]:
    return (
        session.query(PoolTaskDefault)
        .filter(PoolTaskDefault.pool_id == pool_id)
        .all()
    )


# --- Instrument CRUD ---


def get_instruments(session: Session) -> list[Instrument]:
    return session.query(Instrument).order_by(Instrument.name).all()


def get_instrument(session: Session, instrument_id: int) -> Instrument | None:
    return session.query(Instrument).filter(Instrument.id == instrument_id).first()


def save_instrument(
    session: Session,
    name: str,
    brand: str = "",
    can_measure_ph: bool = False,
    can_measure_chlorine: bool = False,
    can_measure_bromine: bool = False,
    can_measure_alkalinity: bool = False,
    can_measure_hardness: bool = False,
    can_measure_cya: bool = False,
    can_measure_salt: bool = False,
    can_measure_oxygen: bool = False,
    notes: str = "",
) -> Instrument:
    inst = Instrument(
        name=name,
        brand=brand,
        can_measure_ph=can_measure_ph,
        can_measure_chlorine=can_measure_chlorine,
        can_measure_bromine=can_measure_bromine,
        can_measure_alkalinity=can_measure_alkalinity,
        can_measure_hardness=can_measure_hardness,
        can_measure_cya=can_measure_cya,
        can_measure_salt=can_measure_salt,
        can_measure_oxygen=can_measure_oxygen,
        notes=notes,
    )
    session.add(inst)
    session.commit()
    session.refresh(inst)
    return inst


def update_instrument(session: Session, instrument_id: int, **kwargs) -> Instrument | None:
    inst = session.query(Instrument).filter(Instrument.id == instrument_id).first()
    if inst:
        for key, value in kwargs.items():
            if hasattr(inst, key):
                setattr(inst, key, value)
        session.commit()
        session.refresh(inst)
    return inst


def delete_instrument(session: Session, instrument_id: int):
    inst = session.query(Instrument).filter(Instrument.id == instrument_id).first()
    if inst:
        session.delete(inst)
        session.commit()


def ensure_template_instances(
    session: Session,
    pool_id: int | None,
    start_date: datetime.date,
    end_date: datetime.date,
) -> None:
    """Generate missing template task instances for a pool and date range."""
    if pool_id:
        templates = get_active_templates_for_pool(session, pool_id)
        pool_ids = [pool_id]
    else:
        templates = get_task_templates(session)
        pool_ids = [p.id for p in session.query(Pool).all()]

    for tmpl in templates:
        for pid in pool_ids:
            tmpl_interval = tmpl.interval_days
            if tmpl_interval <= 0:
                continue

            last = (
                session.query(MaintenanceTask)
                .filter(
                    MaintenanceTask.template_id == tmpl.id,
                    MaintenanceTask.pool_id == pid,
                )
                .order_by(MaintenanceTask.due_date.desc())
                .first()
            )

            if last:
                ref_date = last.due_date
            else:
                pool_obj = session.query(Pool).filter(Pool.id == pid).first()
                ref_date = pool_obj.created_at.date() if pool_obj and pool_obj.created_at else start_date

            # Snap to preferred weekday (e.g., Friday = 4)
            if tmpl.preferred_weekday is not None:
                days_ahead = tmpl.preferred_weekday - ref_date.weekday()
                if days_ahead != 0:
                    if days_ahead < 0:
                        days_ahead += 7
                    ref_date = ref_date + datetime.timedelta(days=days_ahead)

            if last:
                current = ref_date + datetime.timedelta(days=tmpl_interval)
            else:
                current = ref_date
            while current <= end_date:
                existing = session.query(MaintenanceTask).filter(
                    MaintenanceTask.template_id == tmpl.id,
                    MaintenanceTask.pool_id == pid,
                    MaintenanceTask.due_date == current,
                ).first()
                if not existing:
                    rec_amount = None
                    rec_unit = None
                    if tmpl.product_id and tmpl.product_name:
                        product = session.query(Product).filter(Product.id == tmpl.product_id).first()
                        if product and product.dosage_factor > 0:
                            pool_obj = session.query(Pool).filter(Pool.id == pid).first()
                            if pool_obj:
                                volume_m3 = pool_obj.volume_liter / 1000
                                rec_amount = round(product.dosage_factor * volume_m3, 1)
                                rec_unit = product.unit

                    session.add(MaintenanceTask(
                        pool_id=pid,
                        template_id=tmpl.id,
                        task_type="template",
                        title=tmpl.name,
                        description=tmpl.description or "",
                        due_date=current,
                        interval_days=tmpl_interval,
                        product_id=tmpl.product_id,
                        product_name=tmpl.product_name,
                        recommended_amount=rec_amount,
                        recommended_unit=rec_unit,
                    ))
                current += datetime.timedelta(days=tmpl_interval)
    session.commit()


def activate_defaults_for_pool(session: Session, pool_id: int) -> None:
    """Activate matching task templates for a newly created pool."""
    pool = session.query(Pool).filter(Pool.id == pool_id).first()
    if not pool:
        return
    templates = session.query(TaskTemplate).filter(
        (TaskTemplate.pool_type == pool.pool_type) | (TaskTemplate.pool_type == "all")
    ).all()
    for tmpl in templates:
        existing = session.query(PoolTaskDefault).filter(
            PoolTaskDefault.pool_id == pool.id,
            PoolTaskDefault.template_id == tmpl.id,
        ).first()
        if not existing:
            session.add(PoolTaskDefault(
                pool_id=pool.id, template_id=tmpl.id, active=True,
            ))
    session.commit()


def update_task(session: Session, task_id: int, **kwargs) -> MaintenanceTask | None:
    task = session.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
    if task:
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        session.commit()
        session.refresh(task)
    return task


def delete_task(session: Session, task_id: int) -> None:
    task = session.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
    if task:
        session.delete(task)
        session.commit()
