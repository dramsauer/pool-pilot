# Pool Water Balance Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild app with workflow-gesteuerter Wasserrechner as landing page, DB-backed pools/products/trinkwasser, execution documentation, and follow-up tasks.

**Architecture:** Streamlit app with SQLite via SQLAlchemy. Config.toml is migrated to DB on first run (no longer runtime source). The Wasserrechner becomes app.py with a live 4-step workflow: measure → calculate → task → document. Four sidebar pages: Poolverwaltung, Verlauf, Wartung.

**Tech Stack:** Python 3.9+, Streamlit, SQLAlchemy 2.0, Plotly, Pillow

---

### Task 1: Update DB Models (Pool, Trinkwasser, Product + extend existing)

**Files:**
- Modify: `database/models.py`
- Test: `tests/test_database.py`

- [ ] **Step 1: Write failing tests for new models**

```python
# Add to tests/test_database.py
import datetime
from database.db import get_engine, init_db, get_session
from database.models import Base, Pool, Trinkwasser, Product, MaintenanceTask, Photo


def create_memory_session():
    engine = get_engine(":memory:")
    init_db(engine)
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_database.py -v 2>&1 | tail -20
```

Expected: ImportError for Pool, Trinkwasser, Product + 4 FAILED

- [ ] **Step 3: Write new models in `database/models.py`**

Replace entire file with:

```python
import datetime
from sqlalchemy import Column, Integer, Float, String, Text, DateTime, Boolean, Date, LargeBinary, ForeignKey
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Pool(Base):
    __tablename__ = "pools"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    volume_liter = Column(Float, nullable=False)
    pool_type = Column(String(20), default="chlorine")
    ph_min = Column(Float, default=7.2)
    ph_max = Column(Float, default=7.6)
    chlorine_min = Column(Float, default=0.5)
    chlorine_max = Column(Float, default=3.0)
    alkalinity_min = Column(Float, default=80)
    alkalinity_max = Column(Float, default=120)
    hardness_min = Column(Float, default=150)
    hardness_max = Column(Float, default=250)
    temperature_default = Column(Float, default=35)
    trinkwasser_id = Column(Integer, ForeignKey("trinkwasser.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)


class Trinkwasser(Base):
    __tablename__ = "trinkwasser"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    ph_default = Column(Float, default=7.5)
    alkalinity_default = Column(Float, default=145.0)
    calcium_hardness_default = Column(Float, default=185.0)
    notes = Column(Text)


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    typ = Column(String(20), nullable=False)
    dosage_factor = Column(Float, default=0)
    unit = Column(String(20), default="g")
    active_chlorine_per_tab = Column(Float, nullable=True)
    interval_days = Column(Integer, default=0)
    notes = Column(Text)


class Reading(Base):
    __tablename__ = "readings"
    id = Column(Integer, primary_key=True)
    pool_id = Column(Integer, ForeignKey("pools.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    ph = Column(Float, nullable=False)
    chlorine = Column(Float, nullable=False)
    alkalinity = Column(Float, nullable=False)
    hardness = Column(Float, nullable=False)
    temperature_c = Column(Float, nullable=False)
    lsi_value = Column(Float)
    rsi_value = Column(Float)
    dosing_recommendation = Column(Text)
    notes = Column(Text)


class Photo(Base):
    __tablename__ = "photos"
    id = Column(Integer, primary_key=True)
    reading_id = Column(Integer, ForeignKey("readings.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    image_path = Column(String(500))
    image_data = Column(LargeBinary, nullable=True)
    caption = Column(Text)


class MaintenanceTask(Base):
    __tablename__ = "maintenance_tasks"
    id = Column(Integer, primary_key=True)
    pool_id = Column(Integer, ForeignKey("pools.id"), nullable=True)
    reading_id = Column(Integer, ForeignKey("readings.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    parent_task_id = Column(Integer, ForeignKey("maintenance_tasks.id"), nullable=True)
    task_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    due_date = Column(Date)
    interval_days = Column(Integer, default=0)
    follow_up_days = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    executed_notes = Column(Text, nullable=True)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_database.py -v 2>&1 | tail -20
```

Expected: 7 PASSED

- [ ] **Step 5: Commit**

```bash
git add database/models.py tests/test_database.py
git commit -m "feat: add Pool, Trinkwasser, Product models; extend Reading/Photo/MaintenanceTask"
```

---

### Task 2: Update Repository (CRUD for new tables)

**Files:**
- Modify: `database/repository.py`
- Modify: `tests/test_repository.py`

- [ ] **Step 1: Write failing tests for new repo functions**

Add to `tests/test_repository.py`:

```python
from database.repository import (
    save_pool, get_pools, update_pool, delete_pool,
    save_trinkwasser, get_trinkwasser_quellen, delete_trinkwasser,
    save_product, get_products, update_product, delete_product,
    get_readings_for_pool, save_task_with_follow_up,
)
from database.models import Pool, Trinkwasser, Product


def make_session():
    from database.db import get_engine, init_db, get_session
    engine = get_engine(":memory:")
    init_db(engine)
    return get_session(engine)


def test_pool_crud():
    session = make_session()
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
    session = make_session()
    tw = save_trinkwasser(session, name="Stamsried", ph_default=7.5, alkalinity_default=145.0)
    assert tw.id is not None

    quellen = get_trinkwasser_quellen(session)
    assert len(quellen) == 1

    delete_trinkwasser(session, tw.id)
    assert len(get_trinkwasser_quellen(session)) == 0
    session.close()


def test_product_crud():
    session = make_session()
    prod = save_product(session, name="pH-Minus", typ="ph_minus", dosage_factor=1.4, unit="g")
    assert prod.id is not None

    products = get_products(session)
    assert len(products) == 1

    prod2 = update_product(session, prod.id, name="New pH-Minus")
    assert prod2.name == "New pH-Minus"

    delete_product(session, prod.id)
    assert len(get_products(session)) == 0
    session.close()


def test_readings_for_pool():
    session = make_session()
    pool = save_pool(session, name="Pool A", volume_liter=1000)
    readings = get_readings_for_pool(session, pool.id)
    assert len(readings) == 0
    session.close()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_repository.py -v 2>&1 | tail -20
```

Expected: 4 FAILED (ImportError for new functions)

- [ ] **Step 3: Add new CRUD functions to `database/repository.py`**

Append before the EOF:

```python
# --- Pool CRUD ---

def save_pool(session: Session, name: str, volume_liter: float,
              pool_type: str = "chlorine", ph_min: float = 7.2,
              ph_max: float = 7.6, chlorine_min: float = 0.5,
              chlorine_max: float = 3.0, alkalinity_min: float = 80,
              alkalinity_max: float = 120, hardness_min: float = 150,
              hardness_max: float = 250, temperature_default: float = 35,
              trinkwasser_id: int | None = None) -> Pool:
    pool = Pool(name=name, volume_liter=volume_liter, pool_type=pool_type,
                ph_min=ph_min, ph_max=ph_max,
                chlorine_min=chlorine_min, chlorine_max=chlorine_max,
                alkalinity_min=alkalinity_min, alkalinity_max=alkalinity_max,
                hardness_min=hardness_min, hardness_max=hardness_max,
                temperature_default=temperature_default,
                trinkwasser_id=trinkwasser_id)
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

def save_trinkwasser(session: Session, name: str, ph_default: float = 7.5,
                     alkalinity_default: float = 145.0,
                     calcium_hardness_default: float = 185.0,
                     notes: str = "") -> Trinkwasser:
    tw = Trinkwasser(name=name, ph_default=ph_default,
                     alkalinity_default=alkalinity_default,
                     calcium_hardness_default=calcium_hardness_default,
                     notes=notes)
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

def save_product(session: Session, name: str, typ: str,
                 dosage_factor: float = 0, unit: str = "g",
                 active_chlorine_per_tab: float | None = None,
                 interval_days: int = 0, notes: str = "") -> Product:
    prod = Product(name=name, typ=typ, dosage_factor=dosage_factor,
                   unit=unit, active_chlorine_per_tab=active_chlorine_per_tab,
                   interval_days=interval_days, notes=notes)
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

def save_reading_for_pool(session: Session, pool_id: int, ph: float, chlorine: float,
                           alkalinity: float, hardness: float, temperature_c: float,
                           lsi: float, rsi: float, dosing: list | None = None,
                           notes: str = "") -> Reading:
    reading = Reading(
        pool_id=pool_id,
        ph=ph, chlorine=chlorine, alkalinity=alkalinity,
        hardness=hardness, temperature_c=temperature_c,
        lsi_value=lsi, rsi_value=rsi,
        dosing_recommendation=json.dumps(dosing, ensure_ascii=False) if dosing else None,
        notes=notes,
    )
    session.add(reading)
    session.commit()
    session.refresh(reading)
    return reading


def get_readings_for_pool(session: Session, pool_id: int, limit: int = 50) -> list[Reading]:
    return session.query(Reading).filter(
        Reading.pool_id == pool_id
    ).order_by(Reading.timestamp.desc()).limit(limit).all()


def get_latest_reading_for_pool(session: Session, pool_id: int) -> Reading | None:
    return session.query(Reading).filter(
        Reading.pool_id == pool_id
    ).order_by(Reading.timestamp.desc()).first()


# --- Extended Task functions ---

def get_pending_tasks_for_pool(session: Session, pool_id: int) -> list[MaintenanceTask]:
    return session.query(MaintenanceTask).filter(
        MaintenanceTask.pool_id == pool_id,
        MaintenanceTask.completed == False,
    ).order_by(MaintenanceTask.due_date).all()


def get_task(session: Session, task_id: int) -> MaintenanceTask | None:
    return session.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()


def complete_task_with_notes(session: Session, task_id: int, executed_notes: str = "") -> MaintenanceTask | None:
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
```

- [ ] **Step 4: Run repository tests**

```bash
python3 -m pytest tests/test_repository.py -v 2>&1 | tail -20
```

Expected: 4 PASSED + existing tests PASSED (total 8-9)

- [ ] **Step 5: Commit**

```bash
git add database/repository.py tests/test_repository.py
git commit -m "feat: add CRUD for Pool, Trinkwasser, Product; extended Reading/Task functions"
```

---

### Task 3: Migration (config.toml → DB on first run)

**Files:**
- Modify: `database/db.py`
- Modify: `tests/test_database.py`

- [ ] **Step 1: Write failing migration test**

Add to `tests/test_database.py`:

```python
from database.db import migrate_from_config


def test_migration_creates_default_pool():
    session = create_memory_session()
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_database.py::test_migration_creates_default_pool -v 2>&1
```

Expected: FAIL (ImportError for migrate_from_config)

- [ ] **Step 3: Add migration function to `database/db.py`**

Replace `database/db.py` with:

```python
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
    migrate_from_config(session)
    session.close()


def get_session(engine=None) -> Session:
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine)()


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
```

- [ ] **Step 4: Run migration test**

```bash
python3 -m pytest tests/test_database.py::test_migration_creates_default_pool -v 2>&1
```

Expected: PASS

- [ ] **Step 5: Run all tests**

```bash
python3 -m pytest tests/ -v 2>&1 | tail -25
```

Expected: all passing

- [ ] **Step 6: Commit**

```bash
git add database/db.py tests/test_database.py
git commit -m "feat: add config.toml to DB migration in init_db"
```

---

### Task 4: Update Dosing Module to Read Products from DB

**Files:**
- Modify: `pool_calculations/dosing.py`
- Modify: `pool_calculations/models.py`
- Modify: `tests/test_dosing.py`

- [ ] **Step 1: Write failing tests for DB-backed dosing**

Replace `tests/test_dosing.py` with:

```python
from database.db import get_engine, init_db, get_session
from database.models import Product, Pool
from database.repository import save_product, save_pool
from pool_calculations.dosing import recommend_dosing_from_db
from pool_calculations.models import WaterTest


def make_session():
    engine = get_engine(":memory:")
    init_db(engine)
    return get_session(engine)


def test_recommend_ph_plus_from_db():
    session = make_session()
    pool = save_pool(session, name="Test", volume_liter=1000)
    save_product(session, name="pH-Plus Granulat", typ="ph_plus", dosage_factor=0.74, unit="g")
    products = session.query(Product).all()

    test = WaterTest(ph=6.8, chlorine=2.0, alkalinity=100, hardness=200, temperature_c=35)
    result = recommend_dosing_from_db(test, pool, products)
    assert len(result) == 1
    assert "pH-Plus" in result[0].product
    assert result[0].amount > 0
    session.close()


def test_recommend_chlorine_from_db():
    session = make_session()
    pool = save_pool(session, name="Test", volume_liter=1000)
    save_product(session, name="Chlor Tabs", typ="chlorine",
                 unit="Tablette(n)", active_chlorine_per_tab=18.0)
    products = session.query(Product).all()

    test = WaterTest(ph=7.4, chlorine=0.0, alkalinity=100, hardness=200, temperature_c=35)
    result = recommend_dosing_from_db(test, pool, products)
    assert len(result) == 1
    assert result[0].amount >= 1
    session.close()


def test_no_recommendation_needed_from_db():
    session = make_session()
    pool = save_pool(session, name="Test", volume_liter=1000)
    save_product(session, name="pH-Plus", typ="ph_plus", dosage_factor=0.74, unit="g")
    save_product(session, name="pH-Minus", typ="ph_minus", dosage_factor=1.4, unit="g")
    save_product(session, name="Chlor Tabs", typ="chlorine",
                 unit="Tablette(n)", active_chlorine_per_tab=18.0)
    products = session.query(Product).all()

    test = WaterTest(ph=7.4, chlorine=1.5, alkalinity=100, hardness=200, temperature_c=35)
    result = recommend_dosing_from_db(test, pool, products)
    assert len(result) == 0
    session.close()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_dosing.py -v 2>&1 | tail -20
```

Expected: 3 FAILED (ImportError for recommend_dosing_from_db)

- [ ] **Step 3: Update `pool_calculations/dosing.py`**

Replace with:

```python
import math
from pool_calculations.models import WaterTest, DosingRecommendation
from database.models import Product, Pool


def recommend_dosing_from_db(test: WaterTest, pool: Pool, products: list[Product]) -> list[DosingRecommendation]:
    volume_m3 = pool.volume_liter / 1000
    recommendations = []

    ph_minus = next((p for p in products if p.typ == "ph_minus"), None)
    ph_plus = next((p for p in products if p.typ == "ph_plus"), None)
    chlorine_prod = next((p for p in products if p.typ == "chlorine"), None)

    if test.ph < pool.ph_min and ph_plus:
        delta = pool.ph_min - test.ph
        amount = delta * volume_m3 * ph_plus.dosage_factor
        amount = math.ceil(amount * 10) / 10
        recommendations.append(DosingRecommendation(
            product=ph_plus.name,
            amount=amount,
            unit=ph_plus.unit,
            reason=f"pH zu niedrig ({test.ph} → Ziel {pool.ph_min})",
            product_id=ph_plus.id,
            follow_up_days=ph_plus.interval_days,
        ))

    elif test.ph > pool.ph_max and ph_minus:
        delta = test.ph - pool.ph_max
        amount = delta * volume_m3 * ph_minus.dosage_factor
        amount = math.ceil(amount * 10) / 10
        recommendations.append(DosingRecommendation(
            product=ph_minus.name,
            amount=amount,
            unit=ph_minus.unit,
            reason=f"pH zu hoch ({test.ph} → Ziel {pool.ph_max})",
            product_id=ph_minus.id,
            follow_up_days=ph_minus.interval_days,
        ))

    if test.chlorine < pool.chlorine_min and chlorine_prod and chlorine_prod.active_chlorine_per_tab:
        delta = pool.chlorine_min - test.chlorine
        tabs_needed = math.ceil(delta * volume_m3 / chlorine_prod.active_chlorine_per_tab)
        recommendations.append(DosingRecommendation(
            product=chlorine_prod.name,
            amount=float(tabs_needed),
            unit=chlorine_prod.unit,
            reason=f"Chlor zu niedrig ({test.chlorine} → Ziel {pool.chlorine_min} mg/L)",
            product_id=chlorine_prod.id,
            follow_up_days=chlorine_prod.interval_days,
        ))

    return recommendations
```

- [ ] **Step 4: Update models to include product_id + follow_up_days**

Update `pool_calculations/models.py`:

```python
from dataclasses import dataclass, field


@dataclass
class WaterTest:
    ph: float
    chlorine: float
    alkalinity: float
    hardness: float
    temperature_c: float
    notes: str = ""


@dataclass
class DosingRecommendation:
    product: str
    amount: float
    unit: str
    reason: str
    product_id: int | None = None
    follow_up_days: int = 0


@dataclass
class WaterBalanceResult:
    lsi: float
    rsi: float
    lsi_category: str
    rsi_category: str
    is_balanced: bool
    dosing: list[DosingRecommendation] = field(default_factory=list)
```

Remove the `PoolConfig` class (no longer needed — Pool from DB is used directly).

- [ ] **Step 5: Run dosing tests**

```bash
python3 -m pytest tests/test_dosing.py -v 2>&1 | tail -20
```

Expected: 3 PASSED

- [ ] **Step 6: Run all tests**

```bash
python3 -m pytest tests/ -v 2>&1 | tail -25
```

Expected: all passing (some existing tests referencing PoolConfig may need update)

- [ ] **Step 7: Remove `PoolConfig` usage from tests**

Edit `tests/test_lsi.py` and `tests/test_rsi.py` — they should not reference PoolConfig (they don't need it). Check and remove import if present.

- [ ] **Step 8: Commit**

```bash
git add pool_calculations/dosing.py pool_calculations/models.py tests/test_dosing.py
git commit -m "feat: dosing module reads products from DB instead of hardcoded config"
```

---

### Task 5: Poolverwaltung Page (CRUD UI)

**Files:**
- Create: `pages/01_Poolverwaltung.py`
- Delete: `pages/1_Wasserrechner.py` (will be replaced by app.py in Task 6)

- [ ] **Step 1: Create `pages/01_Poolverwaltung.py`**

```python
import streamlit as st
from database.db import get_engine, init_db, get_session
from database.repository import (
    save_pool, get_pools, get_pool, update_pool, delete_pool,
    save_trinkwasser, get_trinkwasser_quellen, get_trinkwasser, delete_trinkwasser,
    save_product, get_products, update_product, delete_product,
)

st.set_page_config(page_title="Pools & Produkte", page_icon="🏊")

engine = get_engine()
init_db(engine)
session = get_session(engine)

st.title("🏊 Pools & Produkte")

tab1, tab2, tab3 = st.tabs(["Pools", "Trinkwasser-Quellen", "Produkte"])

with tab1:
    st.subheader("Pool verwalten")
    pools = get_pools(session)
    if pools:
        pool_names = {p.id: p.name for p in pools}
        selected_id = st.selectbox("Pool auswählen", options=list(pool_names.keys()),
                                   format_func=lambda x: pool_names[x])
        pool = get_pool(session, selected_id)
    else:
        pool = None

    with st.form("pool_form"):
        name = st.text_input("Name", value=pool.name if pool else "")
        col1, col2 = st.columns(2)
        with col1:
            volume = st.number_input("Volumen (L)", min_value=1, value=int(pool.volume_liter) if pool else 1000)
        with col2:
            ptype = st.selectbox("Typ", ["chlorine", "bromine"],
                                 index=0 if not pool or pool.pool_type == "chlorine" else 1)
        col1, col2 = st.columns(2)
        with col1:
            ph_min = st.number_input("pH min", 0.0, 14.0, value=pool.ph_min if pool else 7.2, step=0.1)
        with col2:
            ph_max = st.number_input("pH max", 0.0, 14.0, value=pool.ph_max if pool else 7.6, step=0.1)
        col1, col2 = st.columns(2)
        with col1:
            chl_min = st.number_input("Chlor min (mg/L)", 0.0, 10.0, value=pool.chlorine_min if pool else 0.5, step=0.1)
        with col2:
            chl_max = st.number_input("Chlor max (mg/L)", 0.0, 10.0, value=pool.chlorine_max if pool else 3.0, step=0.1)
        col1, col2 = st.columns(2)
        with col1:
            alk_min = st.number_input("Alkalinität min", 0, 500, value=int(pool.alkalinity_min if pool else 80))
        with col2:
            alk_max = st.number_input("Alkalinität max", 0, 500, value=int(pool.alkalinity_max if pool else 120))
        col1, col2 = st.columns(2)
        with col1:
            hard_min = st.number_input("Härte min", 0, 500, value=int(pool.hardness_min if pool else 150))
        with col2:
            hard_max = st.number_input("Härte max", 0, 500, value=int(pool.hardness_max if pool else 250))
        temp_default = st.number_input("Standard-Temperatur (°C)", 0, 45, value=int(pool.temperature_default if pool else 35))

        tw_quellen = get_trinkwasser_quellen(session)
        tw_options = {0: "Keine"} | {tw.id: tw.name for tw in tw_quellen}
        tw_id = st.selectbox("Trinkwasser-Quelle", options=list(tw_options.keys()),
                             format_func=lambda x: tw_options[x],
                             index=list(tw_options.keys()).index(pool.trinkwasser_id) if pool and pool.trinkwasser_id in tw_options else 0)

        submitted = st.form_submit_button("Speichern")
        if submitted:
            if pool:
                update_pool(session, pool.id, name=name, volume_liter=volume,
                            pool_type=ptype, ph_min=ph_min, ph_max=ph_max,
                            chlorine_min=chl_min, chlorine_max=chl_max,
                            alkalinity_min=alk_min, alkalinity_max=alk_max,
                            hardness_min=hard_min, hardness_max=hard_max,
                            temperature_default=temp_default,
                            trinkwasser_id=tw_id if tw_id else None)
                st.success("Pool aktualisiert!")
            else:
                save_pool(session, name=name, volume_liter=volume, pool_type=ptype,
                          ph_min=ph_min, ph_max=ph_max,
                          chlorine_min=chl_min, chlorine_max=chl_max,
                          alkalinity_min=alk_min, alkalinity_max=alk_max,
                          hardness_min=hard_min, hardness_max=hard_max,
                          temperature_default=temp_default,
                          trinkwasser_id=tw_id if tw_id else None)
                st.success("Pool angelegt!")

    st.divider()
    if pool:
        if st.button("Pool löschen", type="secondary"):
            delete_pool(session, pool.id)
            st.rerun()
    st.button("Neuen Pool anlegen", on_click=lambda: None)

with tab2:
    st.subheader("Trinkwasser-Quellen")
    for tw in get_trinkwasser_quellen(session):
        with st.expander(f"📡 {tw.name}"):
            st.write(f"pH: {tw.ph_default}")
            st.write(f"Alkalinität: {tw.alkalinity_default} mg/L")
            st.write(f"Calciumhärte: {tw.calcium_hardness_default} mg/L")
            if tw.notes:
                st.caption(tw.notes)
            if st.button("Löschen", key=f"del_tw_{tw.id}"):
                delete_trinkwasser(session, tw.id)
                st.rerun()

    st.divider()
    with st.form("new_trinkwasser"):
        st.subheader("Neue Quelle")
        tw_name = st.text_input("Name", value="Stamsried – Kreiswerke Cham")
        col1, col2, col3 = st.columns(3)
        with col1:
            tw_ph = st.number_input("pH", 0.0, 14.0, value=7.5, step=0.1)
        with col2:
            tw_alk = st.number_input("Alkalinität (mg/L)", 0, 500, value=145)
        with col3:
            tw_hard = st.number_input("Calciumhärte (mg/L)", 0, 500, value=185)
        tw_notes = st.text_area("Notizen", value="Trinkwasseranalyse 27.03.2025, Labor Kneißler")
        if st.form_submit_button("Speichern"):
            save_trinkwasser(session, name=tw_name, ph_default=tw_ph,
                             alkalinity_default=tw_alk, calcium_hardness_default=tw_hard,
                             notes=tw_notes)
            st.rerun()

with tab3:
    st.subheader("Produkte")
    for prod in get_products(session):
        with st.expander(f"🧪 {prod.name}"):
            with st.form(key=f"prod_{prod.id}"):
                p_name = st.text_input("Name", value=prod.name)
                p_typ = st.selectbox("Typ", ["ph_minus", "ph_plus", "chlorine"],
                                     index=["ph_minus", "ph_plus", "chlorine"].index(prod.typ))
                col1, col2 = st.columns(2)
                with col1:
                    p_factor = st.number_input("Dosierfaktor", value=prod.dosage_factor, step=0.01)
                with col2:
                    p_unit = st.text_input("Einheit", value=prod.unit)
                p_chlorine = st.number_input("Aktives Chlor pro Tablette (mg)", value=prod.active_chlorine_per_tab or 0.0, step=0.5)
                p_interval = st.number_input("Wiederholintervall (Tage, 0 = einmalig)", min_value=0, value=prod.interval_days)
                p_notes = st.text_area("Notizen", value=prod.notes or "")
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Speichern"):
                        update_product(session, prod.id, name=p_name, typ=p_typ,
                                       dosage_factor=p_factor, unit=p_unit,
                                       active_chlorine_per_tab=p_chlorine if p_typ == "chlorine" and p_chlorine > 0 else None,
                                       interval_days=p_interval, notes=p_notes)
                        st.rerun()
                with col2:
                    if st.form_submit_button("Löschen"):
                        delete_product(session, prod.id)
                        st.rerun()

    st.divider()
    with st.form("new_product"):
        st.subheader("Neues Produkt")
        col1, col2 = st.columns(2)
        with col1:
            np_name = st.text_input("Name")
        with col2:
            np_typ = st.selectbox("Typ", ["ph_minus", "ph_plus", "chlorine"])
        col1, col2 = st.columns(2)
        with col1:
            np_factor = st.number_input("Dosierfaktor", value=0.0, step=0.1)
        with col2:
            np_unit = st.text_input("Einheit", value="g")
        col1, col2 = st.columns(2)
        with col1:
            np_chlorine = st.number_input("Aktives Chlor pro Tablette (mg)", value=0.0, step=0.5)
        with col2:
            np_interval = st.number_input("Wiederholintervall (Tage)", min_value=0, value=0)
        np_notes = st.text_area("Notizen")
        if st.form_submit_button("Speichern"):
            save_product(session, name=np_name, typ=np_typ,
                         dosage_factor=np_factor, unit=np_unit,
                         active_chlorine_per_tab=np_chlorine if np_typ == "chlorine" and np_chlorine > 0 else None,
                         interval_days=np_interval, notes=np_notes)
            st.rerun()
```

- [ ] **Step 2: Delete old page files**

```bash
git rm pages/1_Wasserrechner.py
```

- [ ] **Step 3: Commit**

```bash
git add pages/01_Poolverwaltung.py
git rm pages/1_Wasserrechner.py
git commit -m "feat: add Poolverwaltung page with Pool/Trinkwasser/Product CRUD"
```

---

### Task 6: Wasserrechner (app.py — new landing page with live workflow)

**Files:**
- Rewrite: `app.py`

This is the core of the redesign. The page has:
1. Pool selector (top)
2. Live measurement sliders with help tooltips
3. LSI/RSI gauge + text ampel (auto-updates on slider change)
4. Dosing recommendations
5. Task creation + execution documentation
6. Photo upload / camera input
7. Save button

```python
import datetime
import os
import json
import io
import streamlit as st
import plotly.graph_objects as go
from PIL import Image
from database.db import get_engine, init_db, get_session
from database.repository import (
    get_pools, get_pool, get_products,
    save_reading_for_pool, save_task, save_photo,
    complete_task_with_notes,
    get_readings_for_pool,
)
from pool_calculations.lsi import calculate_lsi, categorize_lsi
from pool_calculations.rsi import calculate_rsi, categorize_rsi
from pool_calculations.dosing import recommend_dosing_from_db
from pool_calculations.models import WaterTest

st.set_page_config(page_title="Wasserrechner", page_icon="💧", layout="centered")

engine = get_engine()
init_db(engine)
session = get_session(engine)

# Pool selector
pools = get_pools(session)
if not pools:
    st.warning("Kein Pool konfiguriert. Bitte lege unter 'Pools & Produkte' einen Pool an.")
    st.page_link("pages/01_Poolverwaltung.py", label="→ Pools & Produkte")
    st.stop()

pool_options = {p.id: f"{p.name} ({p.volume_liter} L)" for p in pools}
selected_pool_id = st.selectbox(
    "Pool", options=list(pool_options.keys()),
    format_func=lambda x: pool_options[x],
    key="pool_selector",
)
pool = get_pool(session, selected_pool_id)

# Load products for dosing
products = get_products(session)

# Load trinkwasser defaults if linked
tw_defaults = {"alkalinity": 100, "hardness": 200}
if pool.trinkwasser_id:
    from database.repository import get_trinkwasser
    tw = get_trinkwasser(session, pool.trinkwasser_id)
    if tw:
        tw_defaults = {"alkalinity": tw.alkalinity_default,
                       "hardness": tw.calcium_hardness_default}

st.title("💧 Wasserrechner")
st.caption(f"{pool.name} · {pool.volume_liter} Liter · {pool.pool_type}")

st.divider()

# Initialize session state
if "last_dosing" not in st.session_state:
    st.session_state.last_dosing = []
if "task_created" not in st.session_state:
    st.session_state.task_created = False

# Step 1: Measurement input with live calculation
st.subheader("1️⃣ Messwerte erfassen")

help_texts = {
    "ph": "Der pH-Wert beeinflusst Chlorwirkung und Wasserbalance. "
          "Teststreifen messen von 6,2 bis 8,4. Ziel: 7,2–7,6.",
    "chlorine": "Freies Chlor in mg/L. "
                "Teststreifen messen freies Chlor. Ziel: 0,5–3,0 mg/L.",
    "temp": "Wassertemperatur in °C. Beeinflusst LSI/RSI direkt.",
    "alk": "Säurepufferkapazität (mg/L CaCO₃). "
           "Verhindert pH-Schwankungen. Wird NICHT mit Teststreifen gemessen. "
           "Trinkwasser-Default: {} mg/L".format(tw_defaults["alkalinity"]),
    "hard": "Calcium-Ionen (mg/L CaCO₃, NICHT Gesamthärte). "
            "Wichtig für LSI-Berechnung. Wird NICHT mit Teststreifen gemessen. "
            "Trinkwasser-Default: {} mg/L".format(tw_defaults["hardness"]),
}

col1, col2 = st.columns(2)

with col1:
    ph = st.slider("pH-Wert ⓘ", 6.2, 8.4, 7.4, 0.1,
                    help=help_texts["ph"])
    chlorine = st.slider("Chlor (mg/L) ⓘ", 0.0, 10.0, 1.5, 0.1,
                          help=help_texts["chlorine"])
    temperature = st.slider("Wassertemperatur (°C) ⓘ", 0, 45,
                              int(pool.temperature_default), 1,
                              help=help_texts["temp"])

with col2:
    alkalinity = st.slider("Alkalinität (mg/L CaCO₃) ⓘ", 0, 500,
                             int(tw_defaults["alkalinity"]), 10,
                             help=help_texts["alk"])
    hardness = st.slider("Calciumhärte (mg/L CaCO₃) ⓘ", 0, 500,
                           int(tw_defaults["hardness"]), 10,
                           help=help_texts["hard"])
    notes = st.text_input("📝 Notizen (optional)", placeholder="z. B. Wetter, Wasserstand...")

# Live calculation
lsi = calculate_lsi(ph, temperature, hardness, alkalinity)
rsi = calculate_rsi(ph, temperature, hardness, alkalinity)
lsi_cat = categorize_lsi(lsi)
rsi_cat = categorize_rsi(rsi)

test = WaterTest(ph=ph, chlorine=chlorine, alkalinity=alkalinity,
                 hardness=hardness, temperature_c=temperature)
dosing = recommend_dosing_from_db(test, pool, products)

st.divider()

# Step 2: Results display (auto-updated)
st.subheader("2️⃣ Wasserbalance")

col_lsi, col_rsi, col_status = st.columns(3)

with col_lsi:
    lsi_color = "green" if lsi_cat == "ausgeglichen" else ("red" if lsi_cat == "korrosiv" else "orange")
    st.markdown(f"### LSI: <span style='color:{lsi_color}'>{lsi:+.2f}</span>",
                unsafe_allow_html=True)
    st.caption(f"→ {lsi_cat}")

with col_rsi:
    st.markdown(f"### RSI: {rsi:.1f}")
    st.caption(f"→ {rsi_cat}")

with col_status:
    if lsi_cat == "ausgeglichen" and rsi_cat == "neutral":
        st.success("✅ Wasser im Gleichgewicht")
    else:
        st.warning("⚡ Handlungsbedarf")

# Plotly gauge
gauge_fig = go.Figure()
gauge_fig.add_trace(go.Indicator(
    mode="gauge+number",
    value=lsi,
    title={"text": "LSI – Live"},
    gauge={
        "axis": {"range": [-2, 2]},
        "bar": {"color": "darkblue"},
        "steps": [
            {"range": [-2, -0.5], "color": "red"},
            {"range": [-0.5, 0.5], "color": "green"},
            {"range": [0.5, 2], "color": "orange"},
        ],
    },
))
st.plotly_chart(gauge_fig, use_container_width=True)

# pH / Chlor leiste
ph_ok = pool.ph_min <= ph <= pool.ph_max
chl_ok = pool.chlorine_min <= chlorine <= pool.chlorine_max
ph_icon = "✅" if ph_ok else "⚠️"
chl_icon = "✅" if chl_ok else "⚠️"
col_a, col_b = st.columns(2)
col_a.metric("pH", f"{ph:.1f}", delta="✅ i.O." if ph_ok else f"⚠️ Ziel {pool.ph_min}–{pool.ph_max}")
col_b.metric("Chlor", f"{chlorine:.1f} mg/L", delta="✅ i.O." if chl_ok else f"⚠️ Ziel {pool.chlorine_min}–{pool.chlorine_max}")

st.divider()

# Step 3: Dosing recommendations
st.subheader("3️⃣ Dosierempfehlung")

if dosing:
    for d in dosing:
        with st.container(border=True):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.warning(f"**{d.product}**: {d.amount:g} {d.unit}")
                st.caption(d.reason)
            with col_b:
                if st.button("📋 Aufgabe", key=f"task_{d.product}_{d.amount}", use_container_width=True):
                    save_task(
                        session,
                        task_type="dosierung",
                        title=f"{d.product}: {d.amount:g} {d.unit}",
                        description=d.reason,
                        due_date=datetime.date.today(),
                        interval_days=0,
                    )
                    st.session_state.task_created = True
                    st.rerun()

        # Step 4: Execution documentation
        st.caption("Ausführung dokumentieren:")
        exec_col1, exec_col2 = st.columns([3, 1])
        with exec_col1:
            exec_notes = st.text_input(
                "Was wurde gemacht?",
                placeholder=f"z. B. {d.amount:g} {d.unit} zugegeben um ...",
                key=f"exec_{d.product}",
            )
        with exec_col2:
            if st.button("✅ Erledigt", key=f"done_{d.product}", use_container_width=True):
                task_data = {
                    "date": datetime.date.today().isoformat(),
                    "time": datetime.datetime.now().strftime("%H:%M"),
                    "action": exec_notes or f"{d.amount:g} {d.unit} zugegeben",
                    "product": d.product,
                    "amount": d.amount,
                    "unit": d.unit,
                    "reason": d.reason,
                }
                if "executed_actions" not in st.session_state:
                    st.session_state.executed_actions = []
                st.session_state.executed_actions.append(task_data)

                if d.follow_up_days > 0:
                    save_task(
                        session,
                        task_type="nachkontrolle",
                        title=f"{d.product} – Nachkontrolle",
                        description=f"Folgeaufgabe in {d.follow_up_days} Tagen "
                                    f"(automatisch erzeugt am {datetime.date.today().isoformat()})",
                        due_date=datetime.date.today() + datetime.timedelta(days=d.follow_up_days),
                        interval_days=d.follow_up_days,
                    )
                st.rerun()
else:
    st.success("✅ Keine Dosierung erforderlich — alle Werte im Zielbereich.")

st.divider()

# Photo section
st.subheader("📸 Foto")
photo_col1, photo_col2 = st.columns(2)
with photo_col1:
    uploaded_file = st.file_uploader("📁 Vom Gerät hochladen", type=["jpg", "jpeg", "png"])
with photo_col2:
    camera_file = st.camera_input("📸 Mit Kamera aufnehmen")

photo_path = None
photo_data = None
if camera_file:
    photo_data = camera_file.getvalue()
    img = Image.open(io.BytesIO(photo_data))
    photo_dir = os.path.join(os.path.dirname(__file__), "data", "photos")
    os.makedirs(photo_dir, exist_ok=True)
    fname = f"reading_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    photo_path = os.path.join(photo_dir, fname)
    img.save(photo_path)
    st.image(photo_data, caption="Kamera-Aufnahme", width=300)
elif uploaded_file:
    photo_data = uploaded_file.getvalue()
    img = Image.open(uploaded_file)
    photo_dir = os.path.join(os.path.dirname(__file__), "data", "photos")
    os.makedirs(photo_dir, exist_ok=True)
    fname = f"reading_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    photo_path = os.path.join(photo_dir, fname)
    img.save(photo_path)
    st.image(photo_data, caption="Hochgeladenes Foto", width=300)

st.divider()

# Save button
if st.button("💾 Messung speichern", type="primary", use_container_width=True):
    dosing_data = [{"product": d.product, "amount": d.amount, "unit": d.unit, "reason": d.reason}
                   for d in dosing] if dosing else []

    reading = save_reading_for_pool(
        session, pool_id=selected_pool_id,
        ph=ph, chlorine=chlorine, alkalinity=alkalinity, hardness=hardness,
        temperature_c=temperature, lsi=lsi, rsi=rsi,
        dosing=dosing_data, notes=notes,
    )

    # Link photo if taken
    if photo_path:
        save_photo(session, image_path=photo_path,
                   caption=f"Messung {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}")

    # Create tasks for dosing if not already done
    if not st.session_state.get("task_created"):
        for d in dosing:
            save_task(
                session,
                task_type="dosierung",
                title=f"{d.product}: {d.amount:g} {d.unit}",
                description=d.reason,
                due_date=datetime.date.today(),
                interval_days=0,
            )

    st.success("✅ Messung gespeichert!")
    st.session_state.last_dosing = dosing
    st.session_state.task_created = False
    if "executed_actions" in st.session_state:
        del st.session_state.executed_actions

# Show last saved result
if st.session_state.last_dosing:
    with st.expander("Letzte gespeicherte Messung"):
        st.json([{"product": d.product, "amount": d.amount, "unit": d.unit, "reason": d.reason}
                 for d in st.session_state.last_dosing])
```

- [ ] **Step 1: Write file**

Write the content above to `app.py`.

- [ ] **Step 2: Quick check app starts**

```bash
python3 -m streamlit run app.py 2>&1 &
sleep 5
curl -s http://localhost:8501 | head -20
kill %1 2>/dev/null
```

Expected: Streamlit app starts, HTML returned

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: rewrite app.py as workflow-gesteuerter Wasserrechner with live LSI/RSI, dosing, photo, tasks"
```

---

### Task 7: Update Wartung Page (execution docs + follow-ups + pool filter)

**Files:**
- Rewrite: `pages/3_Wartung.py`

```python
import datetime
import streamlit as st
from database.db import get_engine, init_db, get_session
from database.repository import (
    get_pools, get_pending_tasks, complete_task_with_notes,
    save_task, get_pending_tasks_for_pool,
)

st.set_page_config(page_title="Wartung", page_icon="✅")

engine = get_engine()
init_db(engine)
session = get_session(engine)

st.title("✅ Aufgaben")

# Pool filter
pools = get_pools(session)
pool_filter = None
if len(pools) > 1:
    pool_options = {0: "Alle Pools"} | {p.id: p.name for p in pools}
    selected = st.selectbox("Pool filtern", options=list(pool_options.keys()),
                            format_func=lambda x: pool_options[x])
    if selected:
        pool_filter = selected

if pool_filter:
    tasks = get_pending_tasks_for_pool(session, pool_filter)
else:
    tasks = get_pending_tasks(session)

if not tasks:
    st.success("✅ Alle Aufgaben erledigt!")
else:
    for task in tasks:
        overdue = task.due_date and task.due_date < datetime.date.today()
        today = task.due_date == datetime.date.today()
        if overdue:
            icon = "🔴"
        elif today:
            icon = "🟡"
        else:
            icon = "🟢"

        with st.container(border=True):
            cols = st.columns([3, 1, 2])
            with cols[0]:
                st.write(f"{icon} **{task.title}**")
                if task.description:
                    st.caption(task.description)
                if task.completed_at:
                    st.caption(f"✅ Erledigt: {task.completed_at.strftime('%d.%m.%Y %H:%M')}")
            with cols[1]:
                if task.due_date:
                    label = "Überfällig!" if overdue else ("Heute" if today else task.due_date.strftime("%d.%m.%Y"))
                    st.write(f"Fällig: {label}")
                if task.interval_days:
                    st.caption(f"Alle {task.interval_days} Tage")
                if task.follow_up_days:
                    st.caption(f"Folge in {task.follow_up_days} Tagen")
            with cols[2]:
                if not task.completed:
                    exec_notes = st.text_input("Doku", placeholder="z. B. 100g zugegeben",
                                               key=f"exec_{task.id}")
                    if st.button("✅ Erledigt", key=f"done_{task.id}", use_container_width=True):
                        complete_task_with_notes(session, task.id, executed_notes=exec_notes)
                        st.rerun()

st.divider()

# Manual task creation
with st.expander("➕ Manuelle Aufgabe"):
    with st.form("manuelle_aufgabe"):
        pools_for_new = {p.id: p.name for p in pools}
        sel_pool_id = st.selectbox("Pool", options=list(pools_for_new.keys()),
                                   format_func=lambda x: pools_for_new[x])
        title = st.text_input("Titel")
        description = st.text_area("Beschreibung")
        due_date = st.date_input("Fällig am", value=datetime.date.today())
        interval = st.number_input("Wiederholen alle (Tage, 0 = einmalig)", min_value=0, value=0)
        follow_up = st.number_input("Folgeaufgabe in (Tagen, 0 = keine)", min_value=0, value=0)
        if st.form_submit_button("Speichern"):
            save_task(session, task_type="custom", title=title,
                      description=description, due_date=due_date,
                      interval_days=interval)
            if follow_up > 0:
                save_task(session, task_type="custom",
                          title=f"{title} (Folge)",
                          description=f"Folgeaufgabe in {follow_up} Tagen",
                          due_date=due_date + datetime.timedelta(days=follow_up),
                          interval_days=0)
            st.success("Aufgabe gespeichert!")
            st.rerun()
```

- [ ] **Step 1: Write file**

Write content above to `pages/3_Wartung.py`.

- [ ] **Step 2: Commit**

```bash
git add pages/3_Wartung.py
git commit -m "feat: update Wartung page with pool filter, execution docs, follow-up tasks"
```

---

### Task 8: Update Verlauf Page (pool filter)

**Files:**
- Rewrite: `pages/2_Verlauf.py`

```python
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from database.db import get_engine, init_db, get_session
from database.repository import get_pools, get_readings_since, get_readings_for_pool

st.set_page_config(page_title="Verlauf", page_icon="📈")

engine = get_engine()
init_db(engine)
session = get_session(engine)

st.title("📈 Verlauf & Trends")

pools = get_pools(session)
if len(pools) > 1:
    pool_options = {0: "Alle Pools"} | {p.id: p.name for p in pools}
    selected = st.selectbox("Pool filtern", options=list(pool_options.keys()),
                            format_func=lambda x: pool_options[x])
else:
    selected = pools[0].id if pools else None

days = st.segmented_control("Zeitraum", ["7", "14", "30", "90"], default="30")

if selected and selected != 0:
    readings = get_readings_for_pool(session, selected, limit=200)
else:
    readings = get_readings_since(session, days=int(days))
    readings = [r for r in readings]

if not readings:
    st.info("Noch keine Messwerte vorhanden.")
    st.stop()

df = pd.DataFrame([{
    "Datum": r.timestamp,
    "pH": r.ph,
    "Chlor": r.chlorine,
    "Alkalinität": r.alkalinity,
    "Härte": r.hardness,
    "LSI": r.lsi_value,
    "RSI": r.rsi_value,
} for r in readings])

fig = make_subplots(rows=3, cols=1,
                    subplot_titles=["pH & Chlor", "Alkalinität & Calciumhärte", "LSI & RSI"],
                    row_heights=[0.33, 0.33, 0.33])

fig.add_trace(go.Scatter(x=df["Datum"], y=df["pH"], name="pH", mode="lines+markers"), row=1, col=1)
fig.add_trace(go.Scatter(x=df["Datum"], y=df["Chlor"], name="Chlor", mode="lines+markers"), row=1, col=1)
fig.add_trace(go.Scatter(x=df["Datum"], y=df["Alkalinität"], name="Alkalinität", mode="lines+markers"), row=2, col=1)
fig.add_trace(go.Scatter(x=df["Datum"], y=df["Härte"], name="Härte", mode="lines+markers"), row=2, col=1)
fig.add_trace(go.Scatter(x=df["Datum"], y=df["LSI"], name="LSI", mode="lines+markers"), row=3, col=1)
fig.add_trace(go.Scatter(x=df["Datum"], y=df["RSI"], name="RSI", mode="lines+markers"), row=3, col=1)

fig.update_layout(height=700, hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

st.subheader("📋 Alle Messwerte")
display_df = df.sort_values("Datum", ascending=False)
st.dataframe(display_df, use_container_width=True)

csv = display_df.to_csv(index=False, decimal=",", sep=";")
st.download_button("📥 Als CSV exportieren", data=csv, file_name="messwerte.csv", mime="text/csv")
```

- [ ] **Step 1: Write file**

Write content above to `pages/2_Verlauf.py`.

- [ ] **Step 2: Commit**

```bash
git add pages/2_Verlauf.py
git commit -m "feat: update Verlauf page with pool filter and alkalinity/hardness charts"
```

---

### Task 9: Cleanup & Final Testing

**Files:**
- Delete: `pages/4_Fotos.py` (merged into app.py workflow)
- Remove: `config_loader.py` references (no longer needed at runtime)
- Verify: all tests pass

- [ ] **Step 1: Remove old Fotos page**

```bash
git rm pages/4_Fotos.py
```

- [ ] **Step 2: Remove stale config_loader import from any remaining page**

Check if any file still imports from `utils.config_loader`:
```bash
rg "from utils.config_loader" pages/ app.py
```

If found, remove or update those imports.

- [ ] **Step 3: Run all tests**

```bash
python3 -m pytest tests/ -v 2>&1 | tail -30
```

Expected: all passing

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove old pages, final cleanup"
```

---

### Task 10: Verify App Starts and Workflow Works

- [ ] **Step 1: Start the app**

```bash
python3 -m streamlit run app.py --server.address=0.0.0.0 --server.port=8501 &
sleep 8
curl -s http://localhost:8501 | head -5
```

Expected: HTML output with "Wasserrechner" title

- [ ] **Step 2: Quick functional check with curl**

Check that pages are accessible:
```bash
curl -s http://localhost:8501/Poolverwaltung | head -3
curl -s http://localhost:8501/Verlauf | head -3
curl -s http://localhost:8501/Wartung | head -3
```

Expected: All return HTML

- [ ] **Step 3: Stop test server**

```bash
kill %1 2>/dev/null
```

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A && git commit -m "fix: final adjustments after verification"
```
