# Pool Water Balance - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Streamlit web app that calculates pool water balance (LSI/RSI) and recommends chemical dosing for the user's specific Lay-Z-Spa Ibiza hot tub.

**Architecture:** Single-user multi-page Streamlit app with a standalone `pool_calculations/` module, SQLite persistence via SQLAlchemy, and pool configuration in `config.toml`. DevContainer for reproducible dev environment.

**Tech Stack:** Python 3.11, Streamlit, SQLAlchemy, Plotly, Pillow, pytest, SQLite

---

### Task 1: Project Scaffold and DevContainer

**Files:**
- Create: `.devcontainer/devcontainer.json`
- Create: `.devcontainer/Dockerfile`
- Create: `requirements.txt`
- Create: `config.toml`
- Create: `pyproject.toml`

- [ ] **Create `.devcontainer/devcontainer.json`**

```json
{
  "name": "Pool Water Balance",
  "build": { "dockerfile": "Dockerfile" },
  "customizations": {
    "vscode": {
      "extensions": ["ms-python.python", "ms-python.pylance"]
    }
  },
  "forwardPorts": [8501],
  "postCreateCommand": "pip install -r requirements.txt",
  "remoteUser": "vscode"
}
```

- [ ] **Create `.devcontainer/Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /workspace
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
```

- [ ] **Create `requirements.txt`**

```
streamlit>=1.35
sqlalchemy>=2.0
plotly>=5.20
pillow>=10.0
pandas>=2.1
pytest>=7.4
```

- [ ] **Create `config.toml`**

```toml
[pool]
name = "Lay-Z-Spa Ibiza"
volume_liter = 1000
pool_type = "chlorine"

[targets]
ph_min = 7.2
ph_max = 7.6
chlorine_min = 0.5
chlorine_max = 3.0
alkalinity_min = 80
alkalinity_max = 120
hardness_min = 150
hardness_max = 250
temperature_default = 35

[products]
  [products.ph_minus]
  name = "Summer Fun pH-Minus Granulat"
  factor = 1.4
  unit = "g"

  [products.ph_plus]
  name = "Summer Fun pH-Plus Granulat"
  factor = 0.74
  unit = "g"

  [products.chlorine_tabs]
  name = "Summer Fun Perfect Care Tabs 20g"
  active_chlorine_per_tab = 18.0
  unit = "Tabletten"
```

- [ ] **Create `pyproject.toml`**

```toml
[project]
name = "pool-water-balance"
version = "0.1.0"
description = "Pool Water Balance Calculator"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Commit**

```bash
git add .devcontainer/ requirements.txt config.toml pyproject.toml
git commit -m "feat: add devcontainer, config, and project scaffold"
```

---

### Task 2: Calculation Module - Models

**Files:**
- Create: `pool_calculations/__init__.py`
- Create: `pool_calculations/models.py`

- [ ] **Create `pool_calculations/__init__.py`** -- empty file

- [ ] **Create `pool_calculations/models.py`**

```python
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PoolConfig:
    name: str = "Lay-Z-Spa Ibiza"
    volume_liter: float = 1000
    pool_type: str = "chlorine"
    ph_min: float = 7.2
    ph_max: float = 7.6
    chlorine_min: float = 0.5
    chlorine_max: float = 3.0
    alkalinity_min: float = 80
    alkalinity_max: float = 120
    hardness_min: float = 150
    hardness_max: float = 250
    temperature_default: float = 35


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


@dataclass
class WaterBalanceResult:
    lsi: float
    rsi: float
    lsi_category: str
    rsi_category: str
    is_balanced: bool
    dosing: list[DosingRecommendation] = field(default_factory=list)
```

- [ ] **Commit**

```bash
git add pool_calculations/
git commit -m "feat: add calculation data models"
```

---

### Task 3: Calculation Module - LSI

**Files:**
- Create: `pool_calculations/lsi.py`
- Create: `tests/test_lsi.py`

- [ ] **Create `tests/` directory** via `mkdir -p tests`

- [ ] **Create `pool_calculations/lsi.py`**

```python
import math


def temperature_factor(temp_c: float) -> float:
    return -13.12 * math.log10(temp_c + 273) + 34.55


def calcium_factor(hardness_mgl: float) -> float:
    return math.log10(hardness_mgl) - 0.4


def alkalinity_factor(alkalinity_mgl: float) -> float:
    return math.log10(alkalinity_mgl)


def calculate_lsi(ph: float, temp_c: float, hardness: float, alkalinity: float) -> float:
    tf = temperature_factor(temp_c)
    cf = calcium_factor(hardness)
    af = alkalinity_factor(alkalinity)
    return ph + tf + cf + af - 12.1


def categorize_lsi(lsi: float) -> str:
    if lsi < -0.5:
        return "korrosiv"
    elif lsi <= 0.5:
        return "ausgeglichen"
    else:
        return "kalkausfällend"
```

- [ ] **Create `tests/test_lsi.py`**

```python
from pool_calculations.lsi import (
    temperature_factor,
    calcium_factor,
    alkalinity_factor,
    calculate_lsi,
    categorize_lsi,
)


def test_temperature_factor():
    result = temperature_factor(25)
    assert round(result, 2) == 1.68, f"Expected ~1.68, got {result}"


def test_calcium_factor():
    result = calcium_factor(200)
    assert round(result, 2) == 1.90, f"Expected ~1.90, got {result}"


def test_alkalinity_factor():
    result = alkalinity_factor(100)
    assert round(result, 2) == 2.00, f"Expected ~2.00, got {result}"


def test_calculate_lsi_balanced():
    result = calculate_lsi(ph=7.4, temp_c=25, hardness=200, alkalinity=100)
    assert round(result, 2) == 0.88, f"LSI calculation off: {result}"


def test_categorize_lsi():
    assert categorize_lsi(-1.0) == "korrosiv"
    assert categorize_lsi(0.0) == "ausgeglichen"
    assert categorize_lsi(0.3) == "ausgeglichen"
    assert categorize_lsi(0.6) == "kalkausfällend"
```

- [ ] **Run tests**

Run: `python -m pytest tests/test_lsi.py -v`
Expected: 5 passed

- [ ] **Commit**

```bash
git add pool_calculations/lsi.py tests/test_lsi.py
git commit -m "feat: add LSI calculation with tests"
```

---

### Task 4: Calculation Module - RSI

**Files:**
- Create: `pool_calculations/rsi.py`
- Create: `tests/test_rsi.py`

- [ ] **Create `pool_calculations/rsi.py`**

```python
import math


def calculate_saturation_ph(temp_c: float, hardness: float, alkalinity: float, tds: float = 1000) -> float:
    a = (math.log10(tds) - 1) / 10
    b = -13.12 * math.log10(temp_c + 273) + 34.55
    c = math.log10(hardness) - 0.4
    d = math.log10(alkalinity)
    return (9.3 + a + b) - (c + d)


def calculate_rsi(ph: float, temp_c: float, hardness: float, alkalinity: float, tds: float = 1000) -> float:
    phs = calculate_saturation_ph(temp_c, hardness, alkalinity, tds)
    return 2 * phs - ph


def categorize_rsi(rsi: float) -> str:
    if rsi < 6.0:
        return "stark kalkausfällend"
    elif rsi < 7.0:
        return "leicht kalkausfällend"
    elif rsi < 7.5:
        return "stabil"
    elif rsi < 8.5:
        return "leicht korrosiv"
    else:
        return "stark korrosiv"
```

- [ ] **Create `tests/test_rsi.py`**

```python
from pool_calculations.rsi import calculate_saturation_ph, calculate_rsi, categorize_rsi


def test_calculate_saturation_ph():
    phs = calculate_saturation_ph(temp_c=25, hardness=200, alkalinity=100)
    assert round(phs, 2) == 7.29, f"pHs calculation off: {phs}"


def test_calculate_rsi():
    rsi = calculate_rsi(ph=7.4, temp_c=25, hardness=200, alkalinity=100)
    assert round(rsi, 2) == 7.18, f"RSI calculation off: {rsi}"


def test_categorize_rsi():
    assert categorize_rsi(5.5) == "stark kalkausfällend"
    assert categorize_rsi(6.5) == "leicht kalkausfällend"
    assert categorize_rsi(7.2) == "stabil"
    assert categorize_rsi(8.0) == "leicht korrosiv"
    assert categorize_rsi(9.0) == "stark korrosiv"
```

- [ ] **Run tests**

Run: `python -m pytest tests/test_rsi.py tests/test_lsi.py -v`
Expected: 10 passed

- [ ] **Commit**

```bash
git add pool_calculations/rsi.py tests/test_rsi.py
git commit -m "feat: add RSI calculation with tests"
```

---

### Task 5: Calculation Module - Dosing

**Files:**
- Create: `pool_calculations/dosing.py`
- Create: `tests/test_dosing.py`

- [ ] **Create `pool_calculations/dosing.py`**

```python
import math
from pool_calculations.models import PoolConfig, WaterTest, DosingRecommendation


def get_product_config(config: PoolConfig) -> dict:
    return {
        "ph_minus": {"name": "Summer Fun pH-Minus Granulat", "factor": 1.4, "unit": "g"},
        "ph_plus": {"name": "Summer Fun pH-Plus Granulat", "factor": 0.74, "unit": "g"},
        "chlorine_tabs": {"name": "Summer Fun Perfect Care Tabs 20g", "active_cl_per_tab": 18.0, "unit": "Tablette(n)"},
    }


def recommend_dosing(test: WaterTest, config: PoolConfig) -> list[DosingRecommendation]:
    products = get_product_config(config)
    volume_m3 = config.volume_liter / 1000
    recommendations = []

    if test.ph < config.ph_min:
        delta = config.ph_min - test.ph
        amount = delta * volume_m3 * products["ph_plus"]["factor"]
        amount = math.ceil(amount * 10) / 10
        recommendations.append(DosingRecommendation(
            product=products["ph_plus"]["name"],
            amount=amount,
            unit=products["ph_plus"]["unit"],
            reason=f"pH zu niedrig ({test.ph} -> Ziel {config.ph_min})",
        ))

    elif test.ph > config.ph_max:
        delta = test.ph - config.ph_max
        amount = delta * volume_m3 * products["ph_minus"]["factor"]
        amount = math.ceil(amount * 10) / 10
        recommendations.append(DosingRecommendation(
            product=products["ph_minus"]["name"],
            amount=amount,
            unit=products["ph_minus"]["unit"],
            reason=f"pH zu hoch ({test.ph} -> Ziel {config.ph_max})",
        ))

    if test.chlorine < config.chlorine_min:
        delta = config.chlorine_min - test.chlorine
        tabs_needed = math.ceil(delta * volume_m3 / products["chlorine_tabs"]["active_cl_per_tab"])
        recommendations.append(DosingRecommendation(
            product=products["chlorine_tabs"]["name"],
            amount=float(tabs_needed),
            unit=products["chlorine_tabs"]["unit"],
            reason=f"Chlor zu niedrig ({test.chlorine} -> Ziel {config.chlorine_min} mg/L)",
        ))

    return recommendations
```

- [ ] **Create `tests/test_dosing.py`**

```python
from pool_calculations.dosing import recommend_dosing
from pool_calculations.models import PoolConfig, WaterTest


def test_recommend_ph_plus():
    config = PoolConfig()
    test = WaterTest(ph=6.8, chlorine=2.0, alkalinity=100, hardness=200, temperature_c=35)
    result = recommend_dosing(test, config)
    assert len(result) == 1
    assert "pH-Plus" in result[0].product
    assert result[0].amount > 0


def test_recommend_ph_minus():
    config = PoolConfig()
    test = WaterTest(ph=8.0, chlorine=2.0, alkalinity=100, hardness=200, temperature_c=35)
    result = recommend_dosing(test, config)
    assert len(result) == 1
    assert "pH-Minus" in result[0].product
    assert result[0].amount > 0


def test_recommend_chlorine():
    config = PoolConfig()
    test = WaterTest(ph=7.4, chlorine=0.0, alkalinity=100, hardness=200, temperature_c=35)
    result = recommend_dosing(test, config)
    assert len(result) == 1
    assert "Perfect Care" in result[0].product
    assert result[0].amount >= 1


def test_no_recommendation_needed():
    config = PoolConfig()
    test = WaterTest(ph=7.4, chlorine=1.5, alkalinity=100, hardness=200, temperature_c=35)
    result = recommend_dosing(test, config)
    assert len(result) == 0


def test_chlorine_and_ph():
    config = PoolConfig()
    test = WaterTest(ph=6.8, chlorine=0.0, alkalinity=100, hardness=200, temperature_c=35)
    result = recommend_dosing(test, config)
    assert len(result) == 2
```

- [ ] **Run tests**

Run: `python -m pytest tests/ -v`
Expected: 15+ passed

- [ ] **Commit**

```bash
git add pool_calculations/dosing.py tests/test_dosing.py
git commit -m "feat: add dosing calculation with tests"
```

---

### Task 6: Config Loader

**Files:**
- Create: `utils/__init__.py`
- Create: `utils/config_loader.py`
- Create: `tests/test_config_loader.py`

- [ ] **Create `utils/config_loader.py`**

```python
import tomllib
from pathlib import Path
from pool_calculations.models import PoolConfig


def load_config(path: str | None = None) -> PoolConfig:
    if path is None:
        path = Path(__file__).parent.parent / "config.toml"
    with open(path, "rb") as f:
        data = tomllib.load(f)

    pool = data["pool"]
    targets = data["targets"]

    return PoolConfig(
        name=pool["name"],
        volume_liter=pool["volume_liter"],
        pool_type=pool["pool_type"],
        ph_min=targets["ph_min"],
        ph_max=targets["ph_max"],
        chlorine_min=targets["chlorine_min"],
        chlorine_max=targets["chlorine_max"],
        alkalinity_min=targets["alkalinity_min"],
        alkalinity_max=targets["alkalinity_max"],
        hardness_min=targets["hardness_min"],
        hardness_max=targets["hardness_max"],
        temperature_default=targets["temperature_default"],
    )
```

- [ ] **Create `tests/test_config_loader.py`**

```python
from pathlib import Path
from utils.config_loader import load_config


def test_load_config():
    config_path = Path(__file__).parent.parent / "config.toml"
    config = load_config(str(config_path))
    assert config.name == "Lay-Z-Spa Ibiza"
    assert config.volume_liter == 1000
    assert config.ph_min == 7.2
    assert config.ph_max == 7.6
```

- [ ] **Run tests**

Run: `python -m pytest tests/test_config_loader.py -v`
Expected: 1 passed

- [ ] **Commit**

```bash
git add utils/ tests/test_config_loader.py
git commit -m "feat: add TOML config loader with test"
```

---

### Task 7: Database Module

**Files:**
- Create: `database/__init__.py`
- Create: `database/models.py`
- Create: `database/db.py`
- Create: `tests/test_database.py`

- [ ] **Create `database/models.py`**

```python
import datetime
from sqlalchemy import Column, Integer, Float, String, Text, DateTime, Boolean, Date
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Reading(Base):
    __tablename__ = "readings"
    id = Column(Integer, primary_key=True)
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


class MaintenanceTask(Base):
    __tablename__ = "maintenance_tasks"
    id = Column(Integer, primary_key=True)
    task_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    due_date = Column(Date)
    interval_days = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)


class Photo(Base):
    __tablename__ = "photos"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    image_path = Column(String(500), nullable=False)
    caption = Column(Text)
```

- [ ] **Create `database/db.py`**

```python
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base


DB_PATH = Path(__file__).parent.parent / "data" / "pool.db"


def get_engine(db_path: str | None = None):
    if db_path is None:
        DB_PATH.parent.mkdir(exist_ok=True)
        db_path = str(DB_PATH)
    return create_engine(f"sqlite:///{db_path}")


def init_db(engine=None):
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)


def get_session(engine=None) -> Session:
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine)()
```

- [ ] **Create `tests/test_database.py`**

```python
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
```

- [ ] **Run tests**

Run: `python -m pytest tests/test_database.py -v`
Expected: 3 passed

- [ ] **Commit**

```bash
git add database/ tests/test_database.py
git commit -m "feat: add database models and initialization"
```

---

### Task 8: Database Repository (CRUD operations)

**Files:**
- Create: `database/repository.py`
- Create: `tests/test_repository.py`

- [ ] **Create `database/repository.py`**

```python
import json
import datetime
from sqlalchemy.orm import Session
from database.models import Reading, MaintenanceTask, Photo


def save_reading(session: Session, ph: float, chlorine: float, alkalinity: float,
                 hardness: float, temperature_c: float, lsi: float, rsi: float,
                 dosing: list | None = None, notes: str = "") -> Reading:
    reading = Reading(
        ph=ph, chlorine=chlorine, alkalinity=alkalinity,
        hardness=hardness, temperature_c=temperature_c,
        lsi_value=lsi, rsi_value=rsi,
        dosing_recommendation=json.dumps(dosing, ensure_ascii=False) if dosing else None,
        notes=notes,
    )
    session.add(reading)
    session.commit()
    return reading


def get_readings(session: Session, limit: int = 50) -> list[Reading]:
    return session.query(Reading).order_by(Reading.timestamp.desc()).limit(limit).all()


def get_readings_since(session: Session, days: int = 30) -> list[Reading]:
    since = datetime.datetime.now() - datetime.timedelta(days=days)
    return session.query(Reading).filter(Reading.timestamp >= since).order_by(Reading.timestamp.desc()).all()


def get_latest_reading(session: Session) -> Reading | None:
    return session.query(Reading).order_by(Reading.timestamp.desc()).first()


def save_task(session: Session, task_type: str, title: str, description: str = "",
              due_date: datetime.date | None = None, interval_days: int = 0) -> MaintenanceTask:
    task = MaintenanceTask(
        task_type=task_type, title=title, description=description,
        due_date=due_date, interval_days=interval_days,
    )
    session.add(task)
    session.commit()
    return task


def get_pending_tasks(session: Session) -> list[MaintenanceTask]:
    return session.query(MaintenanceTask).filter(MaintenanceTask.completed == False).order_by(MaintenanceTask.due_date).all()


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
```

- [ ] **Create `tests/test_repository.py`**

```python
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
```

- [ ] **Run tests**

Run: `python -m pytest tests/test_repository.py -v`
Expected: 5 passed

- [ ] **Commit**

```bash
git add database/repository.py tests/test_repository.py
git commit -m "feat: add database repository with CRUD operations"
```

---

### Task 9: Main Wasserrechner Page (Core UI)

**Files:**
- Create: `app.py`
- Create: `pages/`
- Create: `pages/1_Wasserrechner.py`

- [ ] **Create `pages/` directory** via `mkdir -p pages`

- [ ] **Create `app.py` (Dashboard)**

```python
import streamlit as st
from database.db import get_engine, init_db, get_session
from database.repository import get_latest_reading, get_pending_tasks
from utils.config_loader import load_config

st.set_page_config(page_title="Pool Wasser-Gleichgewicht", page_icon=":droplet:", layout="centered")

engine = get_engine()
init_db(engine)

config = load_config()
session = get_session(engine)

st.title(":droplet: Pool Wasser-Gleichgewicht")
st.caption(f":large_blue_circle: {config.name} - {config.volume_liter} Liter")

col1, col2 = st.columns(2)
with col1:
    latest = get_latest_reading(session)
    if latest:
        st.metric("Letzte Messung", latest.timestamp.strftime("%d.%m.%Y %H:%M"))
        st.metric("pH", f"{latest.ph:.1f}")
        st.metric("Chlor", f"{latest.chlorine:.1f} mg/L")
    else:
        st.info("Noch keine Messungen erfasst.")

with col2:
    if latest:
        lsi_cat = ":green_circle:" if -0.5 <= latest.lsi_value <= 0.5 else (":red_circle:" if latest.lsi_value < -0.5 else ":yellow_circle:")
        st.metric("LSI", f"{latest.lsi_value:+.2f}")
        st.metric("RSI", f"{latest.rsi_value:.1f}")
    else:
        st.write("")

st.divider()
st.subheader(":clipboard: Wartung")
tasks = get_pending_tasks(session)
if tasks:
    for task in tasks:
        st.write(f"- {task.title}")
else:
    st.success("Keine offenen Aufgaben")

st.divider()
st.page_link("pages/1_Wasserrechner.py", label=":microscope: Neue Messung & Berechnung", use_container_width=True)
```

- [ ] **Create `pages/1_Wasserrechner.py`**

```python
import streamlit as st
import plotly.graph_objects as go
from database.db import get_engine, init_db, get_session
from database.repository import save_reading
from pool_calculations.lsi import calculate_lsi, categorize_lsi
from pool_calculations.rsi import calculate_rsi, categorize_rsi
from pool_calculations.dosing import recommend_dosing
from pool_calculations.models import WaterTest
from utils.config_loader import load_config

st.set_page_config(page_title="Wasserrechner", page_icon=":microscope:")

engine = get_engine()
init_db(engine)
session = get_session(engine)
config = load_config()

st.title(":microscope: Wasserrechner & Dosierung")
st.caption(f"Pool: {config.name} ({config.volume_liter} L)")

with st.form("messung"):
    col1, col2 = st.columns(2)
    with col1:
        ph = st.slider("pH-Wert", 6.2, 8.4, 7.4, 0.1)
        chlorine = st.slider("Chlor (mg/L)", 0.0, 10.0, 1.5, 0.5)
        alkalinity = st.slider("Alkalinitat (mg/L CaCO3)", 0, 300, 100, 10)
    with col2:
        hardness = st.slider("Calciumharte (mg/L CaCO3)", 0, 500, 200, 10)
        temperature = st.slider("Wassertemperatur (C)", 0, 45, config.temperature_default, 1)
        notes = st.text_input("Notizen")
    submitted = st.form_submit_button("Berechnen & Speichern", type="primary", use_container_width=True)

    if submitted:
        lsi = calculate_lsi(ph, temperature, hardness, alkalinity)
        rsi = calculate_rsi(ph, temperature, hardness, alkalinity)
        lsi_cat = categorize_lsi(lsi)
        rsi_cat = categorize_rsi(rsi)

        test = WaterTest(ph=ph, chlorine=chlorine, alkalinity=alkalinity,
                         hardness=hardness, temperature_c=temperature)
        dosing = recommend_dosing(test, config)

        dosing_data = [{"product": d.product, "amount": d.amount, "unit": d.unit, "reason": d.reason} for d in dosing]

        save_reading(session, ph=ph, chlorine=chlorine, alkalinity=alkalinity,
                     hardness=hardness, temperature_c=temperature,
                     lsi=lsi, rsi=rsi, dosing=dosing_data, notes=notes)
        st.session_state["last_result"] = {
            "ph": ph, "chlorine": chlorine, "alkalinity": alkalinity,
            "hardness": hardness, "temperature": temperature,
            "lsi": lsi, "lsi_cat": lsi_cat, "rsi": rsi, "rsi_cat": rsi_cat,
            "dosing": dosing,
        }
        st.rerun()

if "last_result" in st.session_state:
    r = st.session_state["last_result"]
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        color = "green" if r["lsi_cat"] == "ausgeglichen" else ("red" if r["lsi_cat"] == "korrosiv" else "orange")
        st.markdown(f"### <span style='color:{color}'>LSI: {r['lsi']:+.2f}</span>", unsafe_allow_html=True)
        st.caption(f"-> {r['lsi_cat']}")
    with col2:
        st.markdown(f"### RSI: {r['rsi']:.1f}")
        st.caption(f"-> {r['rsi_cat']}")
    with col3:
        if r["dosing"]:
            st.warning(":zap: Handlungsbedarf!")
        else:
            st.success(":white_check_mark: Wasser ist im Gleichgewicht")

    fig = go.Figure()
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=r["lsi"],
        title={"text": "LSI"},
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
    st.plotly_chart(fig, use_container_width=True)

    if r["dosing"]:
        st.subheader(":clipboard: Dosierempfehlung")
        for d in r["dosing"]:
            st.info(f"**{d.product}**: {d.amount:g} {d.unit}")
            st.caption(d.reason)

    st.page_link("app.py", label="<- Zuruck zum Dashboard", use_container_width=True)
```

- [ ] **Verify app starts**

Run: `streamlit run app.py --server.headless=true` (should start without error, then Ctrl+C to stop)

- [ ] **Run all tests to ensure nothing broke**

Run: `python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Commit**

```bash
git add app.py pages/1_Wasserrechner.py
git commit -m "feat: add dashboard and Wasserrechner page with dosing UI"
```

---

### Task 10: Verlauf Page (History & Charts)

**Files:**
- Create: `pages/2_Verlauf.py`

- [ ] **Create `pages/2_Verlauf.py`**

```python
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from database.db import get_engine, init_db, get_session
from database.repository import get_readings_since

st.set_page_config(page_title="Verlauf", page_icon=":chart_with_upwards_trend:")

engine = get_engine()
init_db(engine)
session = get_session(engine)

st.title(":chart_with_upwards_trend: Verlauf & Trends")

days = st.segmented_control("Zeitraum", ["7", "14", "30", "90"], default="30")
readings = get_readings_since(session, days=int(days))

if not readings:
    st.info("Noch keine Messwerte vorhanden.")
    st.stop()

df = pd.DataFrame([{
    "Datum": r.timestamp,
    "pH": r.ph,
    "Chlor": r.chlorine,
    "LSI": r.lsi_value,
    "RSI": r.rsi_value,
} for r in readings])

fig = make_subplots(rows=2, cols=1, subplot_titles=["pH & Chlor", "LSI & RSI"])
fig.add_trace(go.Scatter(x=df["Datum"], y=df["pH"], name="pH", mode="lines+markers"), row=1, col=1)
fig.add_trace(go.Scatter(x=df["Datum"], y=df["Chlor"], name="Chlor", mode="lines+markers"), row=1, col=1)
fig.add_trace(go.Scatter(x=df["Datum"], y=df["LSI"], name="LSI", mode="lines+markers"), row=2, col=1)
fig.add_trace(go.Scatter(x=df["Datum"], y=df["RSI"], name="RSI", mode="lines+markers"), row=2, col=1)

fig.update_layout(height=600, hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

st.subheader(":clipboard: Alle Messwerte")
st.dataframe(df.sort_values("Datum", ascending=False), use_container_width=True)

csv = df.to_csv(index=False, decimal=",", sep=";")
st.download_button(":inbox_tray: Als CSV exportieren", data=csv, file_name="messwerte.csv", mime="text/csv")

st.page_link("app.py", label="<- Zuruck zum Dashboard", use_container_width=True)
```

- [ ] **Check app starts**

Run: `streamlit run app.py --server.headless=true &` then kill it -- just confirm no import errors

- [ ] **Commit**

```bash
git add pages/2_Verlauf.py
git commit -m "feat: add history page with Plotly charts and CSV export"
```

---

### Task 11: Wartung Page

**Files:**
- Create: `pages/3_Wartung.py`

- [ ] **Create `pages/3_Wartung.py`**

```python
import datetime
import streamlit as st
from database.db import get_engine, init_db, get_session
from database.repository import save_task, get_pending_tasks, complete_task

st.set_page_config(page_title="Wartung", page_icon=":clipboard:")

engine = get_engine()
init_db(engine)
session = get_session(engine)

st.title(":clipboard: Wartungsplan")

with st.expander(":heavy_plus_sign: Neue Aufgabe"):
    with st.form("neue_aufgabe"):
        task_type = st.selectbox("Typ", ["wasserwechsel", "filter_reinigen", "chemie_pruefen", "custom"])
        title = st.text_input("Titel")
        if task_type == "wasserwechsel":
            title = title or "Wasserwechsel"
        elif task_type == "filter_reinigen":
            title = title or "Filter reinigen"
        elif task_type == "chemie_pruefen":
            title = title or "Chemie prufen"
        description = st.text_area("Beschreibung")
        due_date = st.date_input("Fallig am", value=datetime.date.today())
        interval_days = st.number_input("Wiederholen alle (Tage, 0 = einmalig)", min_value=0, value=3)
        if st.form_submit_button("Speichern"):
            save_task(session, task_type=task_type, title=title,
                      description=description, due_date=due_date,
                      interval_days=interval_days)
            st.success("Aufgabe gespeichert!")
            st.rerun()

st.subheader("Offene Aufgaben")
tasks = get_pending_tasks(session)
if not tasks:
    st.success("Alle Aufgaben erledigt! :white_check_mark:")
else:
    for task in tasks:
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            overdue = task.due_date and task.due_date < datetime.date.today()
            icon = ":red_circle:" if overdue else ":yellow_circle:"
            st.write(f"{icon} **{task.title}**")
            if task.description:
                st.caption(task.description)
        with col2:
            if task.due_date:
                st.write(f"Fallig: {task.due_date}")
            if task.interval_days:
                st.caption(f"Alle {task.interval_days} Tage")
        with col3:
            if st.button(":white_check_mark: Erledigt", key=f"done_{task.id}"):
                complete_task(session, task.id)
                st.rerun()

st.page_link("app.py", label="<- Zuruck zum Dashboard", use_container_width=True)
```

- [ ] **Commit**

```bash
git add pages/3_Wartung.py
git commit -m "feat: add maintenance task page"
```

---

### Task 12: Fotos Page

**Files:**
- Create: `pages/4_Fotos.py`
- Create: `data/photos/` directory

- [ ] **Create `pages/4_Fotos.py`**

```python
import os
import streamlit as st
from PIL import Image
from database.db import get_engine, init_db, get_session
from database.repository import save_photo, get_photos, delete_photo

st.set_page_config(page_title="Fotos", page_icon=":camera:")

engine = get_engine()
init_db(engine)
session = get_session(engine)

PHOTO_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "photos")
os.makedirs(PHOTO_DIR, exist_ok=True)

st.title(":camera: Foto-Dokumentation")

uploaded = st.file_uploader("Foto hochladen", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
for file in uploaded:
    img = Image.open(file)
    img.thumbnail((800, 800))
    path = os.path.join(PHOTO_DIR, file.name)
    img.save(path)
    caption = st.text_input("Bildunterschrift", key=f"cap_{file.name}")
    save_photo(session, image_path=path, caption=caption or "")
    st.success(f"{file.name} gespeichert!")

st.divider()
st.subheader(":framed_picture: Galerie")

photos = get_photos(session)
if not photos:
    st.info("Noch keine Fotos vorhanden.")
else:
    cols = st.columns(3)
    for i, photo in enumerate(photos):
        with cols[i % 3]:
            if os.path.exists(photo.image_path):
                st.image(photo.image_path, caption=photo.caption, use_container_width=True)
                if st.button(":wastebasket: Loschen", key=f"del_{photo.id}"):
                    if os.path.exists(photo.image_path):
                        os.remove(photo.image_path)
                    delete_photo(session, photo.id)
                    st.rerun()

st.page_link("app.py", label="<- Zuruck zum Dashboard", use_container_width=True)
```

- [ ] **Commit**

```bash
git add pages/4_Fotos.py
git commit -m "feat: add photo documentation page"
```

---

### Task 13: Final Integration & Verification

**Files:**
- Create: `.gitignore`

- [ ] **Create `.gitignore`**

```
__pycache__/
*.pyc
data/*.db
data/photos/
.DS_Store
```

- [ ] **Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All 24+ tests pass

- [ ] **Verify app starts**

Run: `timeout 5 streamlit run app.py --server.headless=true || true` -- should start without import errors

- [ ] **Final commit**

```bash
git add .gitignore
git commit -m "chore: add gitignore and finalize project"
git log --oneline
```
