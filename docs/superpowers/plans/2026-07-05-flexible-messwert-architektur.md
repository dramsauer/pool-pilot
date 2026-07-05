# Flexible Messwert-Architektur Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Ersetze hartcodierte Messwert-Spalten in `readings` und Boolean-Flags in `instruments` durch ein flexibles EAV-System (Parameter + ReadingValues + InstrumentCapabilities).

**Architecture:** `parameters`-Tabelle als Register, `reading_values` als EAV-Tabelle, `instrument_capabilities` als Join-Tabelle. Config.toml bekommt `[parameters]`-Sektion. Berechnungen greifen weiterhin über Properties auf Werte zu.

**Tech Stack:** SQLAlchemy, SQLite, Streamlit, Python 3.9+

---

## File Structure

| Datei | Änderung |
|-------|----------|
| `config.toml` | `[parameters]`-Sektion hinzufügen; Instruments `capabilities`-Liste statt Booleans |
| `database/models.py` | 3 neue Modelle: `Parameter`, `ReadingValue`, `InstrumentCapability`; alte Spalten aus `Reading`+`Instrument` entfernen |
| `database/db.py` | `_migrate_schema`: neue Tabellen anlegen, Daten migrieren, alte Spalten droppen |
| `database/repository.py` | CRUD für neue Modelle; `save_reading` nimmt `values: dict`; `get_readings` returned values |
| `pool_calculations/models.py` | `WaterTest.values` als Dict + Properties |
| `Wasserrechner.py` | Dynamische Slider aus Instrument-Capabilities + Parameter-Tabelle |
| `pages/02_Verlauf.py` | Dynamische Chart-Spalten aus vorhandenen Werten |
| `pages/01_Poolverwaltung.py` | Dynamische Checkboxen aus Parameter-Tabelle |
| `utils/export_import.py` | Neue Tabellen in TABLE_CATEGORIES/DEPENDENCY_ORDER/PARENT_DEPENDENCIES aufnehmen |
| `tests/` | Bestehende Tests an neue API anpassen |

---

### Task 1: Neue Modelle + alte anpassen (database/models.py)

**Files:**
- Modify: `database/models.py`

- [ ] **Step 1: Parameter-Modell hinzufügen**

```python
class Parameter(Base):
    __tablename__ = "parameters"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    unit = Column(String(30), default="")
    default_value = Column(Float, default=0.0)
    sort_order = Column(Integer, default=0)
```

- [ ] **Step 2: ReadingValue-Modell hinzufügen**

```python
class ReadingValue(Base):
    __tablename__ = "reading_values"
    id = Column(Integer, primary_key=True)
    reading_id = Column(Integer, ForeignKey("readings.id"), nullable=False)
    parameter_id = Column(Integer, ForeignKey("parameters.id"), nullable=False)
    value = Column(Float, nullable=False)
```

- [ ] **Step 3: InstrumentCapability-Modell hinzufügen**

```python
class InstrumentCapability(Base):
    __tablename__ = "instrument_capabilities"
    id = Column(Integer, primary_key=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    parameter_id = Column(Integer, ForeignKey("parameters.id"), nullable=False)
```

- [ ] **Step 4: Messwert-Spalten aus Reading entfernen**

Entferne: `ph`, `chlorine`, `alkalinity`, `hardness`, `cya`.  
Bleibt: `id`, `pool_id`, `timestamp`, `temperature_c`, `lsi_value`, `rsi_value`, `csi_value`, `ccpp_value`, `dosing_recommendation`, `notes`.

```python
class Reading(Base):
    __tablename__ = "readings"
    id = Column(Integer, primary_key=True)
    pool_id = Column(Integer, ForeignKey("pools.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    temperature_c = Column(Float, nullable=False)
    lsi_value = Column(Float)
    rsi_value = Column(Float)
    csi_value = Column(Float)
    ccpp_value = Column(Float)
    dosing_recommendation = Column(Text)
    notes = Column(Text)
```

- [ ] **Step 5: Boolean-Spalten aus Instrument entfernen**

Entferne: `can_measure_ph`, `can_measure_chlorine`, `can_measure_bromine`, `can_measure_alkalinity`, `can_measure_hardness`, `can_measure_cya`, `can_measure_salt`, `can_measure_oxygen`.  
Bleibt: `id`, `name`, `brand`, `notes`.

```python
class Instrument(Base):
    __tablename__ = "instruments"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    brand = Column(String(200))
    notes = Column(Text)
```

- [ ] **Step 6: Run: Models importieren ohne Fehler**

```bash
python3 -c "from database.models import Parameter, ReadingValue, InstrumentCapability, Reading, Instrument; print('Models OK')"
```
Expected: `Models OK`

- [ ] **Step 7: Commit**

```bash
git add database/models.py
git commit -m "feat: EAV-Modelle Parameter, ReadingValue, InstrumentCapability; alte Spalten entfernt"
```

---

### Task 2: Config.toml + DB-Migration

**Files:**
- Modify: `config.toml`
- Modify: `database/db.py`

- [ ] **Step 1: Config.toml `[parameters]`-Sektion hinzufügen + Instruments umbauen**

```toml
[parameters]
  [parameters.ph]
  display_name = "pH-Wert"
  unit = ""
  default_value = 7.4
  sort_order = 10
  [parameters.chlorine]
  display_name = "Freies Chlor"
  unit = "mg/L"
  default_value = 1.5
  sort_order = 20
  [parameters.alkalinity]
  display_name = "Gesamtalkalinität"
  unit = "mg/L CaCO₃"
  default_value = 100
  sort_order = 30
  [parameters.hardness]
  display_name = "Gesamthärte"
  unit = "mg/L CaCO₃"
  default_value = 200
  sort_order = 40
  [parameters.cya]
  display_name = "Cyanursäure"
  unit = "mg/L"
  default_value = 0
  sort_order = 50
  [parameters.bromine]
  display_name = "Brom"
  unit = "mg/L"
  default_value = 0
  sort_order = 60
  [parameters.salt]
  display_name = "Salzgehalt (TDS)"
  unit = "mg/L NaCl"
  default_value = 500
  sort_order = 70
  [parameters.oxygen]
  display_name = "Sauerstoff"
  unit = "mg/L"
  default_value = 0
  sort_order = 80

[instruments]
  [instruments.summer_fun_teststreifen]
  name = "Summer Fun Teststreifen"
  brand = "Summer Fun"
  capabilities = ["ph", "chlorine", "bromine"]
  notes = "3-in-1: pH, Chlor, Brom"
  [instruments.pool_total_5in1]
  name = "POOL Total 5 in 1"
  brand = "POOL"
  capabilities = ["ph", "chlorine", "alkalinity", "hardness", "cya"]
  notes = "5 Parameter: pH, Chlor, Alk, CYA, Härte"
```

- [ ] **Step 2: Migration in `_migrate_schema`**

Füge in `_migrate_schema()` nach dem bestehenden Code ein:

```python
# Neue Tabellen anlegen (create_all macht das, aber migration braucht sie
# explizit für bestehende DBs)
from sqlalchemy import Table, MetaData
meta = MetaData()
existing_tables = inspector.get_table_names()

if "parameters" not in existing_tables:
    session.execute(text("""
        CREATE TABLE parameters (
            id INTEGER PRIMARY KEY,
            name VARCHAR(50) UNIQUE NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            unit VARCHAR(30) DEFAULT '',
            default_value FLOAT DEFAULT 0.0,
            sort_order INTEGER DEFAULT 0
        )
    """))

if "reading_values" not in existing_tables:
    session.execute(text("""
        CREATE TABLE reading_values (
            id INTEGER PRIMARY KEY,
            reading_id INTEGER NOT NULL REFERENCES readings(id),
            parameter_id INTEGER NOT NULL REFERENCES parameters(id),
            value FLOAT NOT NULL,
            UNIQUE(reading_id, parameter_id)
        )
    """))

if "instrument_capabilities" not in existing_tables:
    session.execute(text("""
        CREATE TABLE instrument_capabilities (
            id INTEGER PRIMARY KEY,
            instrument_id INTEGER NOT NULL REFERENCES instruments(id),
            parameter_id INTEGER NOT NULL REFERENCES parameters(id),
            UNIQUE(instrument_id, parameter_id)
        )
    """))
```

- [ ] **Step 3: Seed-Logik für Parameter in `migrate_from_config`**

Nach dem Seed der Instruments, füge Parameter-Seed ein:

```python
# Seed parameters from config
if session.query(Parameter).count() == 0:
    for key, pdata in data.get("parameters", {}).items():
        session.add(Parameter(
            name=key,
            display_name=pdata["display_name"],
            unit=pdata.get("unit", ""),
            default_value=pdata.get("default_value", 0.0),
            sort_order=pdata.get("sort_order", 0),
        ))
    session.commit()
```

- [ ] **Step 4: Instrument-Seed auf Capabilities umstellen**

Ändere den Instrument-Seed-Block in `migrate_from_config`:

```python
if session.query(Instrument).count() == 0:
    for key, inst in data.get("instruments", {}).items():
        instrument = Instrument(
            name=inst["name"],
            brand=inst.get("brand", ""),
            notes=inst.get("notes", ""),
        )
        session.add(instrument)
        session.flush()
        for cap_name in inst.get("capabilities", []):
            param = session.query(Parameter).filter(Parameter.name == cap_name).first()
            if param:
                session.add(InstrumentCapability(
                    instrument_id=instrument.id,
                    parameter_id=param.id,
                ))
    session.commit()
```

- [ ] **Step 5: Alte Spalten aus Readings migrieren + droppen**

Nach dem Parameters-Seed (wenn Daten existieren):

```python
# Migrate old columns to reading_values
reading_cols = {c["name"] for c in inspector.get_columns("readings")}
for col in ["ph", "chlorine", "alkalinity", "hardness", "cya"]:
    if col in reading_cols:
        # Copy data to reading_values
        param = session.query(Parameter).filter(Parameter.name == col).first()
        if param:
            session.execute(text(f"""
                INSERT OR IGNORE INTO reading_values (reading_id, parameter_id, value)
                SELECT id, {param.id}, {col} FROM readings WHERE {col} IS NOT NULL
            """))
        # Drop column
        session.execute(text(f"ALTER TABLE readings DROP COLUMN {col}"))

# Drop old boolean columns from instruments
inst_cols = {c["name"] for c in inspector.get_columns("instruments")}
for col in ["can_measure_ph", "can_measure_chlorine", "can_measure_bromine",
            "can_measure_alkalinity", "can_measure_hardness", "can_measure_cya",
            "can_measure_salt", "can_measure_oxygen"]:
    if col in inst_cols:
        # Migrate capabilities from booleans
        if col.startswith("can_measure_"):
            param_name = col.replace("can_measure_", "")
            param = session.query(Parameter).filter(Parameter.name == param_name).first()
            if param:
                session.execute(text(f"""
                    INSERT OR IGNORE INTO instrument_capabilities (instrument_id, parameter_id)
                    SELECT id, {param.id} FROM instruments WHERE {col} = 1
                """))
        session.execute(text(f"ALTER TABLE instruments DROP COLUMN {col}"))
```

- [ ] **Step 6: Run: init_db erstellt korrektes Schema**

```bash
python3 -c "
from database.db import get_engine, init_db, get_session
engine = get_engine()
init_db(engine)
session = get_session(engine)
from database.models import Parameter
params = session.query(Parameter).all()
print(f'{len(params)} parameters')
for p in params:
    print(f'  {p.name}: {p.display_name} ({p.unit})')
from database.models import InstrumentCapability
for i in session.query(InstrumentCapability).all():
    print(f'  Instrument {i.instrument_id} -> Parameter {i.parameter_id}')
"
```
Expected: 8 parameters seeded, 2 instruments with correct capabilities

- [ ] **Step 7: Commit**

```bash
git add config.toml database/db.py
git commit -m "feat: config.toml [parameters]-Sektion; DB-Migration neuer Tabellen"
```

---

### Task 3: Repository anpassen

**Files:**
- Modify: `database/repository.py`

- [ ] **Step 1: Neue CRUD-Funktionen für Parameter**

```python
def get_parameters(session: Session) -> list[Parameter]:
    return session.query(Parameter).order_by(Parameter.sort_order).all()

def get_parameter_by_name(session: Session, name: str) -> Parameter | None:
    return session.query(Parameter).filter(Parameter.name == name).first()
```

- [ ] **Step 2: `save_reading` auf values-Dict umstellen**

```python
def save_reading(
    session: Session,
    values: dict[str, float],
    temperature_c: float,
    lsi: float | None = None,
    rsi: float | None = None,
    csi: float | None = None,
    ccpp: float | None = None,
    dosing: list | None = None,
    notes: str = "",
) -> Reading:
    reading = Reading(
        temperature_c=temperature_c,
        lsi_value=lsi,
        rsi_value=rsi,
        csi_value=csi,
        ccpp_value=ccpp,
        dosing_recommendation=json.dumps(dosing, ensure_ascii=False) if dosing else None,
        notes=notes,
    )
    session.add(reading)
    session.flush()
    for param_name, val in values.items():
        param = get_parameter_by_name(session, param_name)
        if param:
            session.add(ReadingValue(reading_id=reading.id, parameter_id=param.id, value=val))
    session.commit()
    session.refresh(reading)
    return reading
```

- [ ] **Step 3: `save_reading_for_pool` analog umstellen**

```python
def save_reading_for_pool(
    session: Session,
    pool_id: int,
    values: dict[str, float],
    temperature_c: float,
    lsi: float | None = None,
    rsi: float | None = None,
    csi: float | None = None,
    ccpp: float | None = None,
    dosing: list | None = None,
    notes: str = "",
) -> Reading:
    reading = Reading(
        pool_id=pool_id,
        temperature_c=temperature_c,
        lsi_value=lsi,
        rsi_value=rsi,
        csi_value=csi,
        ccpp_value=ccpp,
        dosing_recommendation=json.dumps(dosing, ensure_ascii=False) if dosing else None,
        notes=notes,
    )
    session.add(reading)
    session.flush()
    for param_name, val in values.items():
        param = get_parameter_by_name(session, param_name)
        if param:
            session.add(ReadingValue(reading_id=reading.id, parameter_id=param.id, value=val))
    session.commit()
    session.refresh(reading)
    return reading
```

- [ ] **Step 4: `get_readings` / `get_readings_for_pool` / `get_latest_reading` – values attached**

Füge eine Hilfsfunktion hinzu, die Reading-Objekte mit values anreichert:

```python
def _attach_values(session: Session, reading: Reading) -> Reading:
    rvs = (
        session.query(ReadingValue, Parameter)
        .join(Parameter, ReadingValue.parameter_id == Parameter.id)
        .filter(ReadingValue.reading_id == reading.id)
        .all()
    )
    reading._values = {p.name: rv.value for rv, p in rvs}
    return reading

def _attach_values_many(session: Session, readings: list[Reading]) -> list[Reading]:
    if not readings:
        return readings
    ids = [r.id for r in readings]
    rows = (
        session.query(ReadingValue, Parameter)
        .join(Parameter, ReadingValue.parameter_id == Parameter.id)
        .filter(ReadingValue.reading_id.in_(ids))
        .all()
    )
    mapping: dict[int, dict] = {rid: {} for rid in ids}
    for rv, p in rows:
        mapping[rv.reading_id][p.name] = rv.value
    for r in readings:
        r._values = mapping.get(r.id, {})
    return readings
```

Ändere `get_readings`, `get_readings_for_pool`, `get_latest_reading`, `get_readings_since` um `_attach_values_many` bzw. `_attach_values` aufzurufen.

- [ ] **Step 5: Instrument-Capability CRUD**

```python
def get_instrument(session: Session, instrument_id: int) -> Instrument | None:
    return session.query(Instrument).filter(Instrument.id == instrument_id).first()

def get_instruments(session: Session) -> list[Instrument]:
    return session.query(Instrument).all()

def get_instrument_capabilities(session: Session, instrument_id: int) -> list[Parameter]:
    return (
        session.query(Parameter)
        .join(InstrumentCapability)
        .filter(InstrumentCapability.instrument_id == instrument_id)
        .order_by(Parameter.sort_order)
        .all()
    )

def save_instrument(
    session: Session,
    name: str,
    brand: str = "",
    capabilities: list[str] | None = None,
    notes: str = "",
) -> Instrument:
    inst = Instrument(name=name, brand=brand, notes=notes)
    session.add(inst)
    session.flush()
    for cap_name in (capabilities or []):
        param = get_parameter_by_name(session, cap_name)
        if param:
            session.add(InstrumentCapability(instrument_id=inst.id, parameter_id=param.id))
    session.commit()
    session.refresh(inst)
    return inst

def update_instrument_capabilities(
    session: Session,
    instrument_id: int,
    capabilities: list[str],
) -> None:
    session.query(InstrumentCapability).filter(
        InstrumentCapability.instrument_id == instrument_id
    ).delete()
    for cap_name in capabilities:
        param = get_parameter_by_name(session, cap_name)
        if param:
            session.add(InstrumentCapability(
                instrument_id=instrument_id, parameter_id=param.id
            ))
    session.commit()
```

- [ ] **Step 6: Tests anpassen und ausführen**

Aktualisiere `tests/test_repository.py`: `save_reading`-Aufrufe ändern von Einzelparametern zu `values=dict`.

```python
reading = save_reading(
    session,
    values={"ph": 7.4, "chlorine": 1.5, "alkalinity": 100, "hardness": 200},
    temperature_c=25,
    lsi=0.5,
    rsi=6.5,
)
```

```bash
python3 -m pytest tests/test_repository.py -v
```
Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add database/repository.py tests/test_repository.py
git commit -m "feat: Repository auf values-Dict + Capability-CRUD umgestellt"
```

---

### Task 4: WaterTest + Berechnungen

**Files:**
- Modify: `pool_calculations/models.py`

- [ ] **Step 1: WaterTest auf Dict umstellen**

```python
@dataclass
class WaterTest:
    values: dict[str, float] = field(default_factory=dict)
    temperature_c: float = 25
    notes: str = ""

    @property
    def ph(self) -> float:
        return self.values.get("ph", 0.0)

    @property
    def chlorine(self) -> float:
        return self.values.get("chlorine", 0.0)

    @property
    def alkalinity(self) -> float:
        return self.values.get("alkalinity", 0.0)

    @property
    def hardness(self) -> float:
        return self.values.get("hardness", 0.0)

    @property
    def cya(self) -> float:
        return self.values.get("cya", 0.0)

    def get(self, name: str, default: float = 0.0) -> float:
        return self.values.get(name, default)
```

- [ ] **Step 2: Bestehende Tests laufen lassen**

```bash
python3 -m pytest tests/test_lsi.py tests/test_csi.py tests/test_dosing.py -v
```
Expected: All pass (WaterTest properties liefern gleiche Werte wie vorher)

- [ ] **Step 3: Commit**

```bash
git add pool_calculations/models.py
git commit -m "feat: WaterTest auf values-Dict + Properties umgestellt"
```

---

### Task 5: Wasserrechner.py dynamisch

**Files:**
- Modify: `Wasserrechner.py`

- [ ] **Step 1: Help-Texte dynamisch aus Parameter-Tabelle generieren**

```python
all_parameters = get_parameters(session)
help_texts = {p.name: f"{p.display_name} ({p.unit})" for p in all_parameters}
```

- [ ] **Step 2: Capability-Dict dynamisch aus DB laden**

```python
cap_params = get_instrument_capabilities(session, selected_inst_id) if selected_inst_id else all_parameters
```

- [ ] **Step 3: Slider dynamisch rendern**

```python
user_values = {}
col1, col2 = st.columns(2)
for i, param in enumerate(cap_params):
    col = col1 if i % 2 == 0 else col2
    default = tw_defaults.get(param.name, param.default_value)
    with col:
        if hasattr(pool, f"{param.name}_min") and hasattr(pool, f"{param.name}_max"):
            # Has pool targets → use them for range
            pmin = getattr(pool, f"{param.name}_min", 0)
            pmax = getattr(pool, f"{param.name}_max", 10)
            user_values[param.name] = st.slider(
                param.display_name, float(pmin), float(pmax), float(default),
                help=help_texts.get(param.name, ""),
            )
        else:
            # No pool targets → use reasonable range
            user_values[param.name] = st.slider(
                param.display_name, 0.0, 500.0, float(default),
                help=help_texts.get(param.name, ""),
            )
```

- [ ] **Step 4: save_reading_for_pool mit Dict statt Einzelwerten**

```python
reading = save_reading_for_pool(
    session,
    pool_id=selected_pool_id,
    values=user_values,
    temperature_c=temperature,
    lsi=lsi,
    rsi=rsi,
    csi=csi,
    ccpp=ccpp,
    dosing=dosing_data,
    notes=notes,
)
```

- [ ] **Step 5: Commit**

```bash
git add Wasserrechner.py
git commit -m "feat: Wasserrechner dynamische Slider aus Parameter-Tabelle"
```

---

### Task 6: 02_Verlauf.py dynamisch

**Files:**
- Modify: `pages/02_Verlauf.py`

- [ ] **Step 1: DataFrame dynamisch aus vorhandenen Values**

```python
def _build_row(reading, param_names):
    row = {"Datum": reading.timestamp}
    for n in param_names:
        row[n] = getattr(reading, '_values', {}).get(n, None)
    row["Temperatur"] = reading.temperature_c
    row["LSI"] = reading.lsi_value
    row["RSI"] = reading.rsi_value
    row["CSI"] = reading.csi_value if reading.csi_value is not None else None
    row["CCPP"] = reading.ccpp_value if reading.ccpp_value is not None else None
    return row

# Collect all unique parameter names across readings
all_param_names = set()
for r in readings:
    all_param_names.update(getattr(r, '_values', {}).keys())
all_param_names = sorted(all_param_names)

df = pd.DataFrame([_build_row(r, all_param_names) for r in readings])
```

- [ ] **Step 2: Commit**

```bash
git add pages/02_Verlauf.py
git commit -m "feat: Verlauf dynamische Spalten aus reading_values"
```

---

### Task 7: 01_Poolverwaltung.py dynamisch

**Files:**
- Modify: `pages/01_Poolverwaltung.py`

- [ ] **Step 1: Instrument-Edit dynamische Checkboxen aus Parameter-Tabelle**

```python
all_params = get_parameters(session)
current_caps = {p.name for p in get_instrument_capabilities(session, inst.id)}

for param in all_params:
    checked = st.checkbox(param.display_name, value=param.name in current_caps)
```

- [ ] **Step 2: Save/Update mit capabilities-Liste**

```python
selected_caps = [p.name for p in all_params if st.checkbox(p.display_name, value=False)]
save_instrument(session, name=name, brand=brand, capabilities=selected_caps, notes=notes)
```

- [ ] **Step 3: Commit**

```bash
git add pages/01_Poolverwaltung.py
git commit -m "feat: Poolverwaltung dynamische Parameter-Checkboxen"
```

---

### Task 8: Export/Import erweitern

**Files:**
- Modify: `utils/export_import.py`

- [ ] **Step 1: Neue Tabellen in TABLE_CATEGORIES**

```python
TABLE_CATEGORIES = {
    "parameters": {"model": Parameter, "label": "Parameters"},
    ...
    "instrument_capabilities": {"model": InstrumentCapability, "label": "Instrument Capabilities"},
    "readings": {"model": Reading, "label": "Measurements"},
    "reading_values": {"model": ReadingValue, "label": "Measurement Values"},
    ...
}
```

- [ ] **Step 2: DEPENDENCY_ORDER + PARENT_DEPENDENCIES aktualisieren**

```python
DEPENDENCY_ORDER = [
    "parameters",
    "instruments", "instrument_capabilities",
    "trinkwasser", "products", "task_templates",
    "pools", "pool_task_defaults",
    "readings", "reading_values",
    "photos",
    "maintenance_tasks",
]

PARENT_DEPENDENCIES = {
    "instrument_capabilities": ["parameters", "instruments"],
    "reading_values": ["readings", "parameters"],
    ...
}
```

- [ ] **Step 3: Commit**

```bash
git add utils/export_import.py
git commit -m "feat: Export/Import um neue EAV-Tabellen erweitert"
```

---

### Task 9: Integrationstest

**Files:**
- Delete: `data/pool.db`

- [ ] **Step 1: DB löschen, App frisch starten**

```bash
rm -f "0 Pool-Wasser-Gleichgewicht/data/pool.db"
python3 -c "
from database.db import get_engine, init_db, get_session
from database.repository import (
    get_parameters, get_instruments, get_instrument_capabilities,
    save_reading, get_readings
)
engine = get_engine()
init_db(engine)
session = get_session(engine)

# Verify parameters
params = get_parameters(session)
print(f'Parameters: {len(params)}')
assert len(params) == 8

# Verify instruments
instruments = get_instruments(session)
print(f'Instruments: {len(instruments)}')
assert len(instruments) == 2

# Verify POOL capabilities
from database.models import Instrument
pool_inst = session.query(Instrument).filter(Instrument.name == 'POOL Total 5 in 1').first()
caps = get_instrument_capabilities(session, pool_inst.id)
cap_names = [p.name for p in caps]
print(f'POOL capabilities: {cap_names}')
assert set(cap_names) == {'ph', 'chlorine', 'alkalinity', 'hardness', 'cya'}

# Verify Summer Fun capabilities
sf_inst = session.query(Instrument).filter(Instrument.name == 'Summer Fun Teststreifen').first()
caps = get_instrument_capabilities(session, sf_inst.id)
cap_names = [p.name for p in caps]
print(f'Summer Fun capabilities: {cap_names}')
assert set(cap_names) == {'ph', 'chlorine', 'bromine'}

# Save a reading with new API
reading = save_reading(
    session,
    values={'ph': 7.4, 'chlorine': 1.5, 'alkalinity': 100, 'hardness': 200, 'cya': 30},
    temperature_c=28,
    lsi=0.5,
    rsi=6.5,
)
print(f'Reading saved: id={reading.id}')
print(f'Reading values: {reading._values}')
assert reading._values['ph'] == 7.4
assert reading._values['cya'] == 30

# Verify get_readings
all_r = get_readings(session)
assert len(all_r) == 1
assert all_r[0]._values['ph'] == 7.4

print('ALL INTEGRATION CHECKS PASSED')
"
```

- [ ] **Step 2: Tests durchlaufen lassen**

```bash
python3 -m pytest tests/ -v
```
Expected: 75+ passed

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "feat: Integration – EAV-Messwert-Architektur komplett"
```

---

## Spec Coverage Check

| Spec Requirement | Task |
|-----------------|------|
| `parameters`-Tabelle | Task 1 |
| `reading_values`-Tabelle | Task 1 |
| `instrument_capabilities`-Tabelle | Task 1 |
| Alte Spalten aus Readings entfernt | Task 1 |
| Alte Booleans aus Instruments entfernt | Task 1 |
| Config.toml `[parameters]` + new instrument format | Task 2 |
| DB-Migration + Data-Migration | Task 2 |
| Repository: save_reading mit values-Dict | Task 3 |
| Repository: get_readings mit values | Task 3 |
| Instrument-Capability CRUD | Task 3 |
| WaterTest: dict + Properties | Task 4 |
| UI: dynamische Slider | Task 5 |
| Verlauf: dynamische Spalten | Task 6 |
| Poolverwaltung: dynamische Checkboxen | Task 7 |
| Export/Import: neue Tabellen | Task 8 |
| Integrationstest | Task 9 |
