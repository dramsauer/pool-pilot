import datetime
from database.db import get_engine, init_db, get_session
from database.models import Reading, MaintenanceTask, Photo


def test_create_readings_table():
    engine = get_engine(":memory:")
    init_db(engine)
    session = get_session(engine)

    reading = Reading(
        ph=7.4, chlorine=1.5, alkalinity=100,
        hardness=200, temperature_c=35,
        lsi_value=0.5, rsi_value=7.0,
    )
    session.add(reading)
    session.commit()

    saved = session.query(Reading).first()
    assert saved.ph == 7.4
    assert saved.lsi_value == 0.5
    session.close()


def test_create_maintenance_task():
    engine = get_engine(":memory:")
    init_db(engine)
    session = get_session(engine)

    task = MaintenanceTask(
        task_type="wasserwechsel",
        title="Wasserwechsel",
        due_date=datetime.date.today(),
        interval_days=3,
    )
    session.add(task)
    session.commit()

    saved = session.query(MaintenanceTask).first()
    assert saved.task_type == "wasserwechsel"
    assert saved.interval_days == 3
    session.close()


def test_create_photo():
    engine = get_engine(":memory:")
    init_db(engine)
    session = get_session(engine)

    photo = Photo(image_path="photos/test.jpg", caption="Pool")
    session.add(photo)
    session.commit()

    saved = session.query(Photo).first()
    assert saved.image_path == "photos/test.jpg"
    session.close()
