from pathlib import Path
from typing import Optional
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base, Pool, Trinkwasser, Product, Reading


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

    existing = {c["name"] for c in inspector.get_columns("photos")}
    for col in ["reading_id", "image_data"]:
        if col not in existing:
            t = "BLOB" if col == "image_data" else "INTEGER"
            session.execute(text(f"ALTER TABLE photos ADD COLUMN {col} {t}"))

    existing = {c["name"] for c in inspector.get_columns("maintenance_tasks")}
    for col, t in [("pool_id", "INTEGER"), ("reading_id", "INTEGER"),
                   ("product_id", "INTEGER"), ("parent_task_id", "INTEGER"),
                   ("follow_up_days", "INTEGER DEFAULT 0"),
                   ("executed_at", "DATETIME"), ("executed_notes", "TEXT")]:
        if col not in existing:
            session.execute(text(f"ALTER TABLE maintenance_tasks ADD COLUMN {col} {t}"))

    session.commit()


def migrate_from_config(session: Session):
    """Import config.toml data into DB tables if pools table is empty."""
    if session.query(Pool).count() > 0:
        return

    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib

    config_path = Path(__file__).parent.parent / "config.toml"
    if not config_path.exists():
        return

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    # Create default Trinkwasser source
    tw = Trinkwasser(
        name="Stamsried – Kreiswerke Cham (03/2025)",
        ph_default=7.5,
        alkalinity_default=145.0,
        calcium_hardness_default=185.0,
        notes="Quelle: Trinkwasseranalyse 27.03.2025, Labor Kneißler",
    )
    session.add(tw)
    session.flush()

    # Create default pool
    targets = data["targets"]
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
        trinkwasser_id=tw.id,
    )
    session.add(pool)
    session.flush()

    # Create default products
    products_data = [
        Product(name="Summer Fun pH-Minus Granulat", typ="ph_minus",
                dosage_factor=1.4, unit="g", interval_days=0),
        Product(name="Summer Fun pH-Plus Granulat", typ="ph_plus",
                dosage_factor=0.74, unit="g", interval_days=0),
        Product(name="Summer Fun Perfect Care Tabs 20g", typ="chlorine",
                dosage_factor=0, unit="Tablette(n)",
                active_chlorine_per_tab=18.0, interval_days=7),
    ]
    for prod in products_data:
        session.add(prod)
    session.flush()

    # Assign existing readings to default pool
    for reading in session.query(Reading).all():
        reading.pool_id = pool.id

    session.commit()
