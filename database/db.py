from pathlib import Path
from typing import Optional
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base, Pool, Trinkwasser, Product, Reading, Instrument, TaskTemplate, PoolTaskDefault


DB_PATH = Path(__file__).parent.parent / "data" / "pool.db"


def get_engine(db_path: Optional[str] = None):
    if db_path is None:
        DB_PATH.parent.mkdir(exist_ok=True)
        db_path = str(DB_PATH)
    return create_engine(f"sqlite:///{db_path}")


def init_db(engine=None):
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)
    session = get_session(engine)
    _migrate_schema(session)
    migrate_from_config(session)
    _seed_task_templates(session)
    session.close()


def get_session(engine=None) -> Session:
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine)()


def _migrate_schema(session: Session):
    """Add missing columns to existing tables for schema upgrades."""
    from sqlalchemy import text

    inspector = inspect(session.bind)

    existing = {c["name"] for c in inspector.get_columns("readings")}
    for col in ["pool_id"]:
        if col not in existing:
            session.execute(text(f"ALTER TABLE readings ADD COLUMN {col} INTEGER"))

    for col, t in [
        ("csi_value", "FLOAT"),
        ("ccpp_value", "FLOAT"),
    ]:
        if col not in existing:
            session.execute(text(f"ALTER TABLE readings ADD COLUMN {col} {t}"))

    existing = {c["name"] for c in inspector.get_columns("photos")}
    for col in ["reading_id", "image_data"]:
        if col not in existing:
            t = "BLOB" if col == "image_data" else "INTEGER"
            session.execute(text(f"ALTER TABLE photos ADD COLUMN {col} {t}"))

    existing_pool_cols = {c["name"] for c in inspector.get_columns("pools")}
    if "instrument_id" not in existing_pool_cols:
        session.execute(text("ALTER TABLE pools ADD COLUMN instrument_id INTEGER"))

    for col, t in [
        ("shape", "VARCHAR(10) DEFAULT 'rechteckig'"),
        ("inner_length_cm", "FLOAT"),
        ("inner_width_cm", "FLOAT"),
        ("inner_diameter_cm", "FLOAT"),
        ("min_fill_height_cm", "FLOAT DEFAULT 35.0"),
        ("max_fill_height_cm", "FLOAT DEFAULT 45.0"),
    ]:
        if col not in existing_pool_cols:
            session.execute(text(f"ALTER TABLE pools ADD COLUMN {col} {t}"))

    existing = {c["name"] for c in inspector.get_columns("maintenance_tasks")}
    for col, t in [
        ("pool_id", "INTEGER"),
        ("reading_id", "INTEGER"),
        ("product_id", "INTEGER"),
        ("parent_task_id", "INTEGER"),
        ("follow_up_days", "INTEGER DEFAULT 0"),
        ("executed_at", "DATETIME"),
        ("executed_notes", "TEXT"),
    ]:
        if col not in existing:
            session.execute(text(f"ALTER TABLE maintenance_tasks ADD COLUMN {col} {t}"))

    existing_task = {c["name"] for c in inspector.get_columns("maintenance_tasks")}
    for col, t in [
        ("template_id", "INTEGER"),
        ("recommended_amount", "FLOAT"),
        ("recommended_unit", "VARCHAR(20)"),
        ("actual_amount", "FLOAT"),
        ("actual_unit", "VARCHAR(20)"),
        ("product_name", "VARCHAR(200)"),
    ]:
        if col not in existing_task:
            session.execute(text(f"ALTER TABLE maintenance_tasks ADD COLUMN {col} {t}"))

    existing_pool_cols = {c["name"] for c in inspector.get_columns("pools")}
    for col, t in [
        ("auto_measurement_task_days", "INTEGER DEFAULT 7"),
    ]:
        if col not in existing_pool_cols:
            session.execute(text(f"ALTER TABLE pools ADD COLUMN {col} {t}"))

    # Migration for task_templates
    try:
        existing_tmpl = {c["name"] for c in inspector.get_columns("task_templates")}
        for col, t in [
            ("preferred_weekday", "INTEGER"),
        ]:
            if col not in existing_tmpl:
                session.execute(text(f"ALTER TABLE task_templates ADD COLUMN {col} {t}"))
    except Exception:
        pass  # table might not exist yet

    session.commit()


def migrate_from_config(session: Session):
    """Import config.toml data into DB tables."""
    config_path = Path(__file__).parent.parent / "config.toml"
    if not config_path.exists():
        return

    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    # Seed instruments from config (if table empty)
    if session.query(Instrument).count() == 0:
        for key, inst in data.get("instruments", {}).items():
            session.add(Instrument(
                name=inst["name"],
                brand=inst.get("brand", ""),
                can_measure_ph=inst.get("can_measure_ph", False),
                can_measure_chlorine=inst.get("can_measure_chlorine", False),
                can_measure_bromine=inst.get("can_measure_bromine", False),
                can_measure_alkalinity=inst.get("can_measure_alkalinity", False),
                can_measure_hardness=inst.get("can_measure_hardness", False),
                can_measure_cya=inst.get("can_measure_cya", False),
                can_measure_salt=inst.get("can_measure_salt", False),
                can_measure_oxygen=inst.get("can_measure_oxygen", False),
                notes=inst.get("notes", ""),
            ))
        session.commit()

    # Seed trinkwasser from config (if table empty)
    if session.query(Trinkwasser).count() == 0:
        for key, tw in data.get("trinkwasser", {}).items():
            session.add(Trinkwasser(
                name=tw["name"],
                ph_default=tw.get("ph_default", 7.5),
                alkalinity_default=tw.get("alkalinity_default", 145.0),
                calcium_hardness_default=tw.get("calcium_hardness_default", 185.0),
                notes=tw.get("notes", ""),
            ))
        session.commit()

    # Seed pool and products (only if pools table empty)
    if session.query(Pool).count() > 0:
        return

    targets = data["targets"]
    first_tw = session.query(Trinkwasser).first()
    summer_fun = session.query(Instrument).filter(
        Instrument.name == "Summer Fun Teststreifen"
    ).first()
    pool = Pool(
        name=data["pool"]["name"],
        volume_liter=data["pool"]["volume_liter"],
        pool_type=data["pool"]["pool_type"],
        ph_min=targets["ph_min"],
        ph_max=targets["ph_max"],
        chlorine_min=targets["chlorine_min"],
        chlorine_max=targets["chlorine_max"],
        alkalinity_min=targets["alkalinity_min"],
        alkalinity_max=targets["alkalinity_max"],
        hardness_min=targets["hardness_min"],
        hardness_max=targets["hardness_max"],
        temperature_default=targets["temperature_default"],
        trinkwasser_id=first_tw.id if first_tw else None,
        instrument_id=summer_fun.id if summer_fun else None,
    )
    session.add(pool)
    session.flush()

    # Seed products from config
    for key, prod in data.get("products", {}).items():
        session.add(Product(
            name=prod["name"],
            typ=prod.get("typ", key),
            dosage_factor=prod.get("dosage_factor", 0),
            unit=prod.get("unit", "g"),
            active_chlorine_per_tab=prod.get("active_chlorine_per_tab"),
            interval_days=prod.get("interval_days", 0),
            notes=prod.get("notes", ""),
        ))
    session.flush()

    # Assign existing readings to default pool
    for reading in session.query(Reading).all():
        reading.pool_id = pool.id

    session.commit()


def _seed_task_templates(session: Session):
    """Seed task_templates from config.toml (upsert by name)."""
    config_path = Path(__file__).parent.parent / "config.toml"
    if not config_path.exists():
        return
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib
    with open(config_path, "rb") as f:
        data = tomllib.load(f)
    templates = data.get("task_defaults", {}).get("templates", [])
    seeded_any = False
    for tmpl_data in templates:
        existing = session.query(TaskTemplate).filter(
            TaskTemplate.name == tmpl_data["name"]
        ).first()
        if existing:
            continue
        seeded_any = True
        product_id = None
        product_name = tmpl_data.get("product_name")
        if product_name:
            product = session.query(Product).filter(
                Product.name == product_name
            ).first()
            if product:
                product_id = product.id
        session.add(TaskTemplate(
            name=tmpl_data["name"],
            category=tmpl_data.get("category", "allgemein"),
            interval_days=tmpl_data.get("interval_days", 7),
            default_follow_up_days=tmpl_data.get("default_follow_up_days", 0),
            pool_type=tmpl_data.get("pool_type", "all"),
            icon=tmpl_data.get("icon", "📋"),
            preferred_weekday=tmpl_data.get("preferred_weekday"),
            product_name=product_name,
            product_id=product_id,
        ))
    session.commit()

    # Auto-activate matching templates for pools (only when new templates were seeded)
    if seeded_any or session.query(PoolTaskDefault).count() == 0:
        for pool in session.query(Pool).all():
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
                        pool_id=pool.id,
                        template_id=tmpl.id,
                        active=True,
                    ))
        session.commit()
