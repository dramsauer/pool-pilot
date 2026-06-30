import datetime
from database.db import get_engine, get_session
from database.models import Base
from database.repository import (
    save_reading,
    get_readings,
    get_latest_reading,
    save_task,
    get_pending_tasks,
    complete_task,
    save_photo,
    get_photos,
    delete_photo,
    save_pool,
    get_pools,
    update_pool,
    delete_pool,
    save_trinkwasser,
    get_trinkwasser_quellen,
    delete_trinkwasser,
    save_product,
    get_products,
    update_product,
    delete_product,
    get_readings_for_pool,
)


def setup():
    engine = get_engine(":memory:")
    Base.metadata.create_all(engine)
    session = get_session(engine)
    return session


def test_save_and_get_readings():
    session = setup()
    save_reading(
        session,
        ph=7.4,
        chlorine=1.5,
        alkalinity=100,
        hardness=200,
        temperature_c=35,
        lsi=0.5,
        rsi=7.0,
    )
    readings = get_readings(session)
    assert len(readings) == 1
    assert readings[0].ph == 7.4


def test_latest_reading():
    session = setup()
    save_reading(
        session,
        ph=7.4,
        chlorine=1.5,
        alkalinity=100,
        hardness=200,
        temperature_c=35,
        lsi=0.5,
        rsi=7.0,
    )
    save_reading(
        session,
        ph=7.6,
        chlorine=2.0,
        alkalinity=110,
        hardness=210,
        temperature_c=36,
        lsi=0.6,
        rsi=7.2,
    )
    latest = get_latest_reading(session)
    assert latest.ph == 7.6


def test_pending_tasks():
    session = setup()
    save_task(
        session,
        task_type="wasserwechsel",
        title="Wasserwechsel",
        due_date=datetime.date.today(),
        interval_days=3,
    )
    pending = get_pending_tasks(session)
    assert len(pending) == 1


def test_complete_task():
    session = setup()
    task = save_task(
        session,
        task_type="wasserwechsel",
        title="Wasserwechsel",
        due_date=datetime.date.today(),
    )
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


def test_pool_crud():
    session = setup()
    pool = save_pool(session, name="Test Pool", volume_liter=500)
    assert pool.id is not None
    assert pool.name == "Test Pool"

    pools = get_pools(session)
    assert len(pools) == 1

    pool2 = update_pool(session, pool.id, name="Updated Pool")
    assert pool2.name == "Updated Pool"

    delete_pool(session, pool.id)
    assert len(get_pools(session)) == 0
    session.close()


def test_trinkwasser_crud():
    session = setup()
    tw = save_trinkwasser(
        session, name="Stamsried", ph_default=7.5, alkalinity_default=145.0
    )
    assert tw.id is not None

    quellen = get_trinkwasser_quellen(session)
    assert len(quellen) == 1

    delete_trinkwasser(session, tw.id)
    assert len(get_trinkwasser_quellen(session)) == 0
    session.close()


def test_product_crud():
    session = setup()
    prod = save_product(
        session, name="pH-Minus", typ="ph_minus", dosage_factor=1.4, unit="g"
    )
    assert prod.id is not None

    products = get_products(session)
    assert len(products) == 1

    prod2 = update_product(session, prod.id, name="New pH-Minus")
    assert prod2.name == "New pH-Minus"

    delete_product(session, prod.id)
    assert len(get_products(session)) == 0
    session.close()


def test_readings_for_pool():
    session = setup()
    pool = save_pool(session, name="Pool A", volume_liter=1000)
    readings = get_readings_for_pool(session, pool.id)
    assert len(readings) == 0
    session.close()
