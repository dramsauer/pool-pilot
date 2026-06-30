import datetime
from database.db import get_engine, init_db, get_session, migrate_from_config
from database.models import Base, Pool, Trinkwasser, Product, Reading, MaintenanceTask, Photo


def create_memory_session():
    engine = get_engine(":memory:")
    Base.metadata.create_all(engine)
    return get_session(engine)


def test_create_pool():
    session = create_memory_session()
    pool = Pool(name="Test Pool", volume_liter=500)
    session.add(pool)
    session.commit()
    saved = session.query(Pool).first()
    assert saved.name == "Test Pool"
    assert saved.volume_liter == 500
    session.close()


def test_create_trinkwasser():
    session = create_memory_session()
    tw = Trinkwasser(name="Stamsried", ph_default=7.5, alkalinity_default=145.0, calcium_hardness_default=185.0)
    session.add(tw)
    session.commit()
    saved = session.query(Trinkwasser).first()
    assert saved.name == "Stamsried"
    assert saved.alkalinity_default == 145.0
    session.close()


def test_create_product():
    session = create_memory_session()
    prod = Product(name="pH-Minus", typ="ph_minus", dosage_factor=1.4, unit="g")
    session.add(prod)
    session.commit()
    saved = session.query(Product).first()
    assert saved.name == "pH-Minus"
    assert saved.typ == "ph_minus"
    session.close()


def test_maintenance_task_with_follow_up():
    session = create_memory_session()
    task = MaintenanceTask(
        task_type="custom", title="Chlor prüfen",
        follow_up_days=7,
    )
    session.add(task)
    session.commit()
    saved = session.query(MaintenanceTask).first()
    assert saved.follow_up_days == 7
    session.close()


def test_create_readings_table():
    session = create_memory_session()
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
    session = create_memory_session()
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
    session = create_memory_session()
    photo = Photo(image_path="photos/test.jpg", caption="Pool")
    session.add(photo)
    session.commit()
    saved = session.query(Photo).first()
    assert saved.image_path == "photos/test.jpg"
    session.close()


def test_migration_creates_default_pool():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    pool_count_before = session.query(Pool).count()
    assert pool_count_before == 0

    migrate_from_config(session)

    pool_count_after = session.query(Pool).count()
    assert pool_count_after == 1
    pool = session.query(Pool).first()
    assert pool.name == "Lay-Z-Spa Ibiza"
    assert pool.volume_liter == 1000

    product_count = session.query(Product).count()
    assert product_count == 3

    tw_count = session.query(Trinkwasser).count()
    assert tw_count == 1
    session.close()
