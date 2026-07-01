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
    complete_task_with_notes,
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
    get_task_templates,
    get_active_templates_for_pool,
    set_pool_template_active,
    get_pool_task_defaults,
    ensure_template_instances,
    activate_defaults_for_pool,
)
from database.models import TaskTemplate, PoolTaskDefault, MaintenanceTask


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


def test_save_task_with_optional_fields():
    session = setup()
    task = save_task(
        session,
        task_type="dosierung",
        title="pH-Minus: 200g",
        pool_id=1,
        product_id=1,
        product_name="pH-Minus",
        recommended_amount=200.0,
        recommended_unit="g",
    )
    assert task.pool_id == 1
    assert task.product_id == 1
    assert task.product_name == "pH-Minus"
    assert task.recommended_amount == 200.0
    assert task.recommended_unit == "g"
    session.close()


def test_complete_task_with_actual_amount():
    session = setup()
    pool = save_pool(session, name="Test", volume_liter=1000)
    task = save_task(
        session, task_type="dosierung", title="Chlor: 1 Tab",
        recommended_amount=1.0, recommended_unit="Stk",
        product_name="Chlortabs",
    )
    completed = complete_task_with_notes(
        session, task.id, executed_notes="Nur eine halbe",
        actual_amount=0.5, actual_unit="Stk",
    )
    assert completed.completed is True
    assert completed.actual_amount == 0.5
    assert completed.actual_unit == "Stk"
    assert completed.executed_notes == "Nur eine halbe"
    session.close()


def test_get_task_templates():
    session = setup()
    tmpl = TaskTemplate(name="Test", category="chemie", interval_days=7)
    session.add(tmpl)
    session.commit()
    templates = get_task_templates(session)
    assert len(templates) == 1
    session.close()


def test_active_templates_for_pool():
    session = setup()
    pool = save_pool(session, name="Test", volume_liter=500)
    tmpl = TaskTemplate(name="Test", category="chemie", interval_days=7)
    session.add(tmpl)
    session.flush()
    ptd = PoolTaskDefault(pool_id=pool.id, template_id=tmpl.id, active=True)
    session.add(ptd)
    session.commit()
    active = get_active_templates_for_pool(session, pool.id)
    assert len(active) == 1
    assert active[0].name == "Test"
    session.close()


def test_ensure_template_instances():
    session = setup()
    pool = save_pool(session, name="Test", volume_liter=500)
    tmpl = TaskTemplate(name="Weekly", category="test", interval_days=7)
    session.add(tmpl)
    session.flush()
    session.add(PoolTaskDefault(pool_id=pool.id, template_id=tmpl.id, active=True))
    session.commit()

    today = datetime.date.today()
    end = today + datetime.timedelta(days=30)
    ensure_template_instances(session, pool.id, today, end)

    instances = session.query(MaintenanceTask).filter(
        MaintenanceTask.pool_id == pool.id,
        MaintenanceTask.template_id == tmpl.id,
    ).all()
    assert len(instances) >= 4
    session.close()


def test_template_follow_up_on_complete():
    session = setup()
    pool = save_pool(session, name="Test", volume_liter=500)
    tmpl = TaskTemplate(name="Weekly", category="test", interval_days=7)
    session.add(tmpl)
    session.flush()
    task = save_task(
        session, task_type="template", title="Weekly",
        pool_id=pool.id, template_id=tmpl.id,
        interval_days=7, due_date=datetime.date.today(),
    )
    complete_task_with_notes(session, task.id)
    instances = session.query(MaintenanceTask).filter(
        MaintenanceTask.template_id == tmpl.id,
    ).all()
    assert len(instances) == 2
    session.close()


def test_activate_defaults_for_pool():
    session = setup()
    tmpl = TaskTemplate(name="Generic", category="test", interval_days=7, pool_type="all")
    session.add(tmpl)
    session.flush()
    pool = save_pool(session, name="Test", volume_liter=500, pool_type="chlorine")
    activate_defaults_for_pool(session, pool.id)
    defaults = get_pool_task_defaults(session, pool.id)
    assert len(defaults) == 1
    assert defaults[0].active is True
    session.close()


def test_ensure_template_instances_snaps_to_preferred_weekday():
    session = setup()
    # Create a pool on a Wednesday (weekday=2)
    pool = save_pool(session, name="Test", volume_liter=500)
    # preferred_weekday=4 means Friday
    tmpl = TaskTemplate(name="FridayTask", category="test", interval_days=7, preferred_weekday=4)
    session.add(tmpl)
    session.flush()
    session.add(PoolTaskDefault(pool_id=pool.id, template_id=tmpl.id, active=True))
    session.commit()

    # Override pool.created_at to a Wednesday
    pool.created_at = datetime.datetime(2026, 7, 1)  # Wednesday
    session.commit()

    start = datetime.date(2026, 7, 1)   # Wednesday
    end = datetime.date(2026, 7, 31)     # end of July
    ensure_template_instances(session, pool.id, start, end)

    instances = session.query(MaintenanceTask).filter(
        MaintenanceTask.pool_id == pool.id,
        MaintenanceTask.template_id == tmpl.id,
    ).order_by(MaintenanceTask.due_date).all()

    assert len(instances) >= 4
    # All instances should fall on a Friday (weekday=4)
    for inst in instances:
        assert inst.due_date.weekday() == 4, f"{inst.due_date} is not a Friday"
    session.close()
