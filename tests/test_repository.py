import datetime
from database.db import get_engine, init_db, get_session
from database.repository import (
    save_reading, get_readings, get_latest_reading, get_readings_since,
    save_task, get_pending_tasks, complete_task,
    save_photo, get_photos, delete_photo,
)


def setup():
    engine = get_engine(":memory:")
    init_db(engine)
    session = get_session(engine)
    return session


def test_save_and_get_readings():
    session = setup()
    save_reading(session, ph=7.4, chlorine=1.5, alkalinity=100, hardness=200,
                 temperature_c=35, lsi=0.5, rsi=7.0)
    readings = get_readings(session)
    assert len(readings) == 1
    assert readings[0].ph == 7.4


def test_latest_reading():
    session = setup()
    save_reading(session, ph=7.4, chlorine=1.5, alkalinity=100, hardness=200,
                 temperature_c=35, lsi=0.5, rsi=7.0)
    save_reading(session, ph=7.6, chlorine=2.0, alkalinity=110, hardness=210,
                 temperature_c=36, lsi=0.6, rsi=7.2)
    latest = get_latest_reading(session)
    assert latest.ph == 7.6


def test_pending_tasks():
    session = setup()
    save_task(session, task_type="wasserwechsel", title="Wasserwechsel",
              due_date=datetime.date.today(), interval_days=3)
    pending = get_pending_tasks(session)
    assert len(pending) == 1


def test_complete_task():
    session = setup()
    task = save_task(session, task_type="wasserwechsel", title="Wasserwechsel",
                     due_date=datetime.date.today())
    complete_task(session, task.id)
    pending = get_pending_tasks(session)
    assert len(pending) == 0


def test_photo_crud():
    session = setup()
    photo = save_photo(session, "photos/test.jpg", "Test")
    assert photo.id is not None
    photos = get_photos(session)
    assert len(photos) == 1
    delete_photo(session, photo.id)
    photos = get_photos(session)
    assert len(photos) == 0
