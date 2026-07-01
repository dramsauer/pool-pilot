# Default Tasks für die Wartung — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add default recurring task templates, quick-add presets, auto-measurement follow-ups, and product/dosing tracking to the maintenance system.

**Architecture:** Three new database models (TaskTemplate, PoolTaskDefault) plus column additions to MaintenanceTask and Pool. Templates seeded from config.toml. Recurring instances generated on-the-fly. Quick-add presets in Wartung page pull from templates. Dosing tasks track `recommended_amount` vs `actual_amount`.

**Tech Stack:** Python, Streamlit, SQLAlchemy, SQLite

---

### Task 1: Models — Add TaskTemplate, PoolTaskDefault, extend MaintenanceTask and Pool

**Files:**
- Modify: `database/models.py` (entire file)
- Test: `tests/test_database.py`

- [ ] **Step 1: Add TaskTemplate, PoolTaskDefault models and extend MaintenanceTask/Pool**

Add these classes after `Pool` and `MaintenanceTask` in `database/models.py`:

```python
class TaskTemplate(Base):
    __tablename__ = "task_templates"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(50), default="allgemein")
    interval_days = Column(Integer, default=7)
    default_follow_up_days = Column(Integer, default=0)
    pool_type = Column(String(20), default="all")
    icon = Column(String(10), default="📋")
    product_name = Column(String(200), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)


class PoolTaskDefault(Base):
    __tablename__ = "pool_task_defaults"
    id = Column(Integer, primary_key=True)
    pool_id = Column(Integer, ForeignKey("pools.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("task_templates.id"), nullable=False)
    active = Column(Boolean, default=True)
    custom_interval_days = Column(Integer, nullable=True)
```

Add these columns to `Pool` (after `max_fill_height_cm` line):
```python
    auto_measurement_task_days = Column(Integer, default=7)
```

Add these columns to `MaintenanceTask` (after `follow_up_days`):
```python
    template_id = Column(Integer, ForeignKey("task_templates.id"), nullable=True)
    recommended_amount = Column(Float, nullable=True)
    recommended_unit = Column(String(20), nullable=True)
    actual_amount = Column(Float, nullable=True)
    actual_unit = Column(String(20), nullable=True)
    product_name = Column(String(200), nullable=True)
```

Update the `__all__` list at top (or just ensure the new classes are importable).

- [ ] **Step 2: Add model tests**

Add to `tests/test_database.py`:

```python
def test_task_template_creation():
    session = create_memory_session()
    tmpl = TaskTemplate(
        name="pH prüfen",
        category="chemie",
        interval_days=7,
        pool_type="all",
    )
    session.add(tmpl)
    session.commit()
    saved = session.query(TaskTemplate).first()
    assert saved.name == "pH prüfen"
    assert saved.interval_days == 7
    session.close()


def test_pool_task_default():
    session = create_memory_session()
    pool = Pool(name="Test Pool", volume_liter=500, auto_measurement_task_days=7)
    session.add(pool)
    session.flush()
    tmpl = TaskTemplate(name="Test", category="allgemein", interval_days=7)
    session.add(tmpl)
    session.flush()
    ptd = PoolTaskDefault(pool_id=pool.id, template_id=tmpl.id)
    session.add(ptd)
    session.commit()
    saved = session.query(PoolTaskDefault).first()
    assert saved.pool_id == pool.id
    assert saved.template_id == tmpl.id
    assert saved.active is True
    session.close()


def test_maintenance_task_extended_fields():
    session = create_memory_session()
    task = MaintenanceTask(
        task_type="dosierung",
        title="pH-Minus: 200g",
        recommended_amount=200.0,
        recommended_unit="g",
        product_name="pH-Minus",
    )
    session.add(task)
    session.commit()
    saved = session.query(MaintenanceTask).first()
    assert saved.recommended_amount == 200.0
    assert saved.recommended_unit == "g"
    assert saved.product_name == "pH-Minus"
    session.close()


def test_pool_auto_measurement_default():
    session = create_memory_session()
    pool = Pool(name="Test", volume_liter=500)
    session.add(pool)
    session.commit()
    assert pool.auto_measurement_task_days == 7
    session.close()
```

- [ ] **Step 3: Run model tests**

```bash
cd /app && python -m pytest tests/test_database.py -xvs
```

Expected: 4 new tests pass (total ~9 tests).

- [ ] **Step 4: Commit**

```bash
git add database/models.py tests/test_database.py
git commit -m "feat: add TaskTemplate, PoolTaskDefault models, extend MaintenanceTask and Pool"
```

---

### Task 2: Config + Seeding — Add task_defaults to config.toml and seed in db.py

**Files:**
- Modify: `config.toml`
- Modify: `database/db.py`

- [ ] **Step 1: Add [task_defaults] section to config.toml**

Append at end of `config.toml`:

```toml
[task_defaults]
templates = [
  { name = "pH prüfen", category = "chemie", interval_days = 7, pool_type = "all", icon = "🧪" },
  { name = "Chlor prüfen", category = "chemie", interval_days = 7, pool_type = "chlorine", icon = "🧪" },
  { name = "pH-Minus zugeben", category = "chemie", interval_days = 0, pool_type = "all", icon = "⚗️", product_name = "Summer Fun pH-Minus Granulat" },
  { name = "Chlor Tablette zugeben", category = "chemie", interval_days = 0, pool_type = "chlorine", icon = "💊", product_name = "Summer Fun Perfect Care Tabs 20g" },
  { name = "Filter rückspülen", category = "technik", interval_days = 14, pool_type = "all", icon = "🔄" },
  { name = "Skimmer reinigen", category = "reinigung", interval_days = 7, pool_type = "all", icon = "🧹" },
  { name = "Pumpenvorsieb reinigen", category = "technik", interval_days = 7, pool_type = "all", icon = "🔧" },
  { name = "Poolboden saugen", category = "reinigung", interval_days = 14, pool_type = "all", icon = "🫧" },
  { name = "Wasserstand prüfen", category = "allgemein", interval_days = 7, pool_type = "all", icon = "📏" },
  { name = "Schockchlorung", category = "chemie", interval_days = 28, pool_type = "chlorine", icon = "⚡" },
  { name = "Vollanalyse (alle Werte)", category = "chemie", interval_days = 14, pool_type = "all", icon = "📊" },
  { name = "CYA prüfen", category = "chemie", interval_days = 30, pool_type = "chlorine", icon = "🧪" },
]
```

- [ ] **Step 2: Add seed logic to db.py**

Import TaskTemplate and PoolTaskDefault at top of `db.py`:
```python
from database.models import Base, Pool, Trinkwasser, Product, Reading, Instrument, TaskTemplate, PoolTaskDefault
```

Add a `_seed_task_templates` function and call it from `init_db()`:

```python
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
    for tmpl_data in templates:
        existing = session.query(TaskTemplate).filter(
            TaskTemplate.name == tmpl_data["name"]
        ).first()
        if existing:
            continue
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
            product_name=product_name,
            product_id=product_id,
        ))
    session.commit()
```

In `init_db()`, call `_seed_task_templates(session)` after `migrate_from_config(session)`.

- [ ] **Step 3: Activate templates for default pool on creation**

In `_seed_task_templates`, after seeding, auto-activate templates for existing pools:

```python
    # Auto-activate matching templates for all pools
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
```

Add schema migration in `_migrate_schema` for the new `maintenance_tasks` columns:

```python
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
```

- [ ] **Step 4: Run existing tests**

```bash
cd /app && python -m pytest tests/test_database.py -xvs
```

Expected: All tests pass (including migration test).

- [ ] **Step 5: Commit**

```bash
git add config.toml database/db.py
git commit -m "feat: add task_defaults config and seeding logic"
```

---

### Task 3: Repository — Template CRUD, pool defaults, extended save_task, completion, recurring generation

**Files:**
- Modify: `database/repository.py` (entire file)
- Test: `tests/test_repository.py`

- [ ] **Step 1: Add template and pool-default query functions**

After existing imports, add new imports:
```python
from database.models import Reading, MaintenanceTask, Photo, Pool, Trinkwasser, Product, Instrument, TaskTemplate, PoolTaskDefault
```

Add after `get_tasks_by_date_range`:

```python
# --- Task Template ---


def get_task_templates(session: Session) -> list[TaskTemplate]:
    return session.query(TaskTemplate).order_by(TaskTemplate.category, TaskTemplate.name).all()


def get_active_templates_for_pool(session: Session, pool_id: int) -> list[TaskTemplate]:
    return (
        session.query(TaskTemplate)
        .join(PoolTaskDefault, TaskTemplate.id == PoolTaskDefault.template_id)
        .filter(
            PoolTaskDefault.pool_id == pool_id,
            PoolTaskDefault.active.is_(True),
        )
        .order_by(TaskTemplate.category, TaskTemplate.name)
        .all()
    )


def set_pool_template_active(
    session: Session, pool_id: int, template_id: int, active: bool
) -> None:
    ptd = session.query(PoolTaskDefault).filter(
        PoolTaskDefault.pool_id == pool_id,
        PoolTaskDefault.template_id == template_id,
    ).first()
    if ptd:
        ptd.active = active
    else:
        session.add(PoolTaskDefault(
            pool_id=pool_id, template_id=template_id, active=active,
        ))
    session.commit()


def get_pool_task_defaults(session: Session, pool_id: int) -> list[PoolTaskDefault]:
    return (
        session.query(PoolTaskDefault)
        .filter(PoolTaskDefault.pool_id == pool_id)
        .all()
    )
```

- [ ] **Step 2: Extend save_task to accept optional fields**

Replace the existing `save_task` function:

```python
def save_task(
    session: Session,
    task_type: str,
    title: str,
    description: str = "",
    due_date: datetime.date | None = None,
    interval_days: int = 0,
    pool_id: int | None = None,
    product_id: int | None = None,
    product_name: str | None = None,
    recommended_amount: float | None = None,
    recommended_unit: str | None = None,
    template_id: int | None = None,
) -> MaintenanceTask:
    task = MaintenanceTask(
        task_type=task_type,
        title=title,
        description=description,
        due_date=due_date,
        interval_days=interval_days,
        pool_id=pool_id,
        product_id=product_id,
        product_name=product_name,
        recommended_amount=recommended_amount,
        recommended_unit=recommended_unit,
        template_id=template_id,
    )
    session.add(task)
    session.commit()
    return task
```

- [ ] **Step 3: Extend save_pool to accept auto_measurement_task_days**

Add `auto_measurement_task_days` parameter to existing `save_pool` in `repository.py`:

```python
def save_pool(
    session: Session,
    name: str,
    volume_liter: float,
    pool_type: str = "chlorine",
    ph_min: float = 7.2,
    ph_max: float = 7.6,
    chlorine_min: float = 0.5,
    chlorine_max: float = 3.0,
    alkalinity_min: float = 80,
    alkalinity_max: float = 120,
    hardness_min: float = 150,
    hardness_max: float = 250,
    temperature_default: float = 35,
    trinkwasser_id: int | None = None,
    instrument_id: int | None = None,
    shape: str = "rechteckig",
    inner_length_cm: float | None = None,
    inner_width_cm: float | None = None,
    inner_diameter_cm: float | None = None,
    min_fill_height_cm: float = 35.0,
    max_fill_height_cm: float = 45.0,
    auto_measurement_task_days: int = 7,  # ADD THIS
) -> Pool:
    pool = Pool(
        name=name,
        volume_liter=volume_liter,
        pool_type=pool_type,
        ph_min=ph_min,
        ph_max=ph_max,
        chlorine_min=chlorine_min,
        chlorine_max=chlorine_max,
        alkalinity_min=alkalinity_min,
        alkalinity_max=alkalinity_max,
        hardness_min=hardness_min,
        hardness_max=hardness_max,
        temperature_default=temperature_default,
        trinkwasser_id=trinkwasser_id,
        instrument_id=instrument_id,
        shape=shape,
        inner_length_cm=inner_length_cm,
        inner_width_cm=inner_width_cm,
        inner_diameter_cm=inner_diameter_cm,
        min_fill_height_cm=min_fill_height_cm,
        max_fill_height_cm=max_fill_height_cm,
        auto_measurement_task_days=auto_measurement_task_days,  # ADD THIS
    )
    session.add(pool)
    session.commit()
    session.refresh(pool)
    return pool
```

- [ ] **Step 4: Extend complete_task_with_notes to capture actual_amount and generate template follow-ups**

Replace existing `complete_task_with_notes`:

```python
def complete_task_with_notes(
    session: Session,
    task_id: int,
    executed_notes: str = "",
    actual_amount: float | None = None,
    actual_unit: str | None = None,
) -> MaintenanceTask | None:
    task = session.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
    if task:
        task.completed = True
        task.completed_at = datetime.datetime.now()
        task.executed_notes = executed_notes
        if actual_amount is not None:
            task.actual_amount = actual_amount
            task.actual_unit = actual_unit or task.recommended_unit
        session.commit()

        # Generate follow-up from follow_up_days
        if task.follow_up_days > 0:
            follow_up = MaintenanceTask(
                pool_id=task.pool_id,
                reading_id=task.reading_id,
                product_id=task.product_id,
                product_name=task.product_name,
                parent_task_id=task.id,
                task_type=task.task_type,
                title=f"{task.title} (Folge)",
                description=f"Folgeaufgabe — alle {task.follow_up_days} Tage",
                due_date=(
                    datetime.date.today() + datetime.timedelta(days=task.follow_up_days)
                ),
                interval_days=task.interval_days,
                follow_up_days=task.follow_up_days,
                template_id=task.template_id,
            )
            session.add(follow_up)
            session.commit()

        # Generate next template instance if this was a template task
        if task.template_id and task.interval_days > 0:
            _generate_next_template_instance(session, task)

    return task


def _generate_next_template_instance(session: Session, completed_task: MaintenanceTask) -> MaintenanceTask | None:
    """Generate the next recurring instance after completing a template-sourced task."""
    if not completed_task.template_id or completed_task.interval_days <= 0:
        return None
    next_due = datetime.date.today() + datetime.timedelta(days=completed_task.interval_days)
    # Check if an instance already exists for this due date
    existing = session.query(MaintenanceTask).filter(
        MaintenanceTask.template_id == completed_task.template_id,
        MaintenanceTask.pool_id == completed_task.pool_id,
        MaintenanceTask.due_date == next_due,
    ).first()
    if existing:
        return None
    task = MaintenanceTask(
        pool_id=completed_task.pool_id,
        template_id=completed_task.template_id,
        task_type=completed_task.task_type,
        title=completed_task.title,
        description=completed_task.description,
        due_date=next_due,
        interval_days=completed_task.interval_days,
        recommended_amount=completed_task.recommended_amount,
        recommended_unit=completed_task.recommended_unit,
        product_id=completed_task.product_id,
        product_name=completed_task.product_name,
    )
    session.add(task)
    session.commit()
    return task
```

- [ ] **Step 5: Add recurring instance generation for a date range**

Add the function that generates template instances for a visible window:

```python
def ensure_template_instances(
    session: Session,
    pool_id: int | None,
    start_date: datetime.date,
    end_date: datetime.date,
) -> None:
    """Generate missing template task instances for a pool and date range."""
    if pool_id:
        templates = get_active_templates_for_pool(session, pool_id)
        pool_ids = [pool_id]
    else:
        templates = get_task_templates(session)
        pool_ids = [p.id for p in session.query(Pool).all()]

    # Group templates by product_name for dosing calculation
    products = {p.name: p for p in session.query(Product).all()}

    for tmpl in templates:
        for pid in pool_ids:
            tmpl_interval = tmpl.interval_days
            if tmpl_interval <= 0:
                continue

            # Find the last task instance for this template+pool
            last = (
                session.query(MaintenanceTask)
                .filter(
                    MaintenanceTask.template_id == tmpl.id,
                    MaintenanceTask.pool_id == pid,
                )
                .order_by(MaintenanceTask.due_date.desc())
                .first()
            )

            if last:
                ref_date = last.due_date
            else:
                pool_obj = session.query(Pool).filter(Pool.id == pid).first()
                ref_date = pool_obj.created_at.date() if pool_obj and pool_obj.created_at else start_date

            # Generate from ref_date + interval_days forward to end_date
            current = ref_date + datetime.timedelta(days=tmpl_interval)
            while current <= end_date:
                existing = session.query(MaintenanceTask).filter(
                    MaintenanceTask.template_id == tmpl.id,
                    MaintenanceTask.pool_id == pid,
                    MaintenanceTask.due_date == current,
                ).first()
                if not existing:
                    rec_amount = None
                    rec_unit = None
                    if tmpl.product_id and tmpl.product_name:
                        product = session.query(Product).filter(Product.id == tmpl.product_id).first()
                        if product and product.dosage_factor > 0:
                            pool_obj = session.query(Pool).filter(Pool.id == pid).first()
                            if pool_obj:
                                volume_m3 = pool_obj.volume_liter / 1000
                                rec_amount = round(product.dosage_factor * volume_m3, 1)
                                rec_unit = product.unit

                    session.add(MaintenanceTask(
                        pool_id=pid,
                        template_id=tmpl.id,
                        task_type="template",
                        title=tmpl.name,
                        description=tmpl.description or "",
                        due_date=current,
                        interval_days=tmpl_interval,
                        product_id=tmpl.product_id,
                        product_name=tmpl.product_name,
                        recommended_amount=rec_amount,
                        recommended_unit=rec_unit,
                    ))
                current += datetime.timedelta(days=tmpl_interval)
    session.commit()
```

- [ ] **Step 6: Add activate_defaults_for_pool helper**

```python
def activate_defaults_for_pool(session: Session, pool_id: int) -> None:
    """Activate matching task templates for a newly created pool."""
    pool = session.query(Pool).filter(Pool.id == pool_id).first()
    if not pool:
        return
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
                pool_id=pool.id, template_id=tmpl.id, active=True,
            ))
    session.commit()
```

- [ ] **Step 7: Add repository tests**

Add to `tests/test_repository.py`:

```python
from database.repository import (
    save_task,
    get_pending_tasks,
    complete_task,
    complete_task_with_notes,
    get_task_templates,
    get_active_templates_for_pool,
    set_pool_template_active,
    get_pool_task_defaults,
    ensure_template_instances,
    activate_defaults_for_pool,
)
from database.models import TaskTemplate, PoolTaskDefault, MaintenanceTask


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
    assert len(instances) >= 4  # ~30/7 = 4 instances
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
    # Should have generated next instance
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
```

- [ ] **Step 8: Run repository tests**

```bash
cd /app && python -m pytest tests/test_repository.py -xvs
```

Expected: All tests pass (existing + 7 new).

- [ ] **Step 9: Commit**

```bash
git add database/repository.py tests/test_repository.py
git commit -m "feat: add template CRUD, extended task save/complete, recurring generation"
```

---

### Task 4: Quick-add presets + completion with dosing capture (Wartung page)

**Files:**
- Modify: `pages/03_Wartung.py`

- [ ] **Step 1: Add quick-add preset buttons and actual_amount capture**

Replace entire `pages/03_Wartung.py`:

```python
import datetime
import streamlit as st
from database.db import get_engine, init_db, get_session
from database.repository import (
    get_pools,
    get_pending_tasks,
    complete_task_with_notes,
    save_task,
    get_pending_tasks_for_pool,
    get_active_templates_for_pool,
    ensure_template_instances,
)
from database.models import Product

st.set_page_config(
    page_title="PoolPilot - Dein intelligenter Pool-Helfer", page_icon="🏊"
)

engine = get_engine()
init_db(engine)
session = get_session(engine)

st.title("✅ Aufgaben")

# Pool filter
pools = get_pools(session)
pool_filter = None
if len(pools) > 1:
    pool_options = {0: "Alle Pools"} | {p.id: p.name for p in pools}
    selected = st.selectbox(
        "Pool filtern",
        options=list(pool_options.keys()),
        format_func=lambda x: pool_options[x],
    )
    if selected:
        pool_filter = selected

# Ensure template instances for visible window
today = datetime.date.today()
ensure_template_instances(session, pool_filter or 0, today, today + datetime.timedelta(days=90))

# Quick-add presets
st.subheader("⚡ Schnell-Aufgabe")
templates_to_show = get_active_templates_for_pool(session, pool_filter) if pool_filter else []
if not pool_filter and pools:
    templates_to_show = get_active_templates_for_pool(session, pools[0].id)

if templates_to_show:
    categories = {}
    for t in templates_to_show:
        cat = t.category or "allgemein"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(t)

    cat_labels = {"chemie": "🧪 Chemie", "technik": "🔧 Technik", "reinigung": "🧹 Reinigung", "allgemein": "📋 Allgemein"}
    for cat, tmpls in categories.items():
        label = cat_labels.get(cat, cat)
        cols = st.columns(len(tmpls))
        for i, tmpl in enumerate(tmpls):
            with cols[i]:
                if st.button(f"{tmpl.icon} {tmpl.name}", key=f"qa_{tmpl.id}", use_container_width=True):
                    target_pool_id = pool_filter or (pools[0].id if pools else None)
                    rec_amount = None
                    rec_unit = None
                    if tmpl.product_id:
                        product = session.query(Product).filter(Product.id == tmpl.product_id).first()
                        if product and product.dosage_factor > 0 and target_pool_id:
                            p = next((p for p in pools if p.id == target_pool_id), None)
                            if p:
                                volume_m3 = p.volume_liter / 1000
                                rec_amount = round(product.dosage_factor * volume_m3, 1)
                                rec_unit = product.unit
                    save_task(
                        session,
                        task_type="template",
                        title=tmpl.name,
                        description=tmpl.description or "",
                        due_date=today,
                        interval_days=tmpl.interval_days,
                        template_id=tmpl.id,
                        pool_id=target_pool_id,
                        product_id=tmpl.product_id,
                        product_name=tmpl.product_name,
                        recommended_amount=rec_amount,
                        recommended_unit=rec_unit,
                    )
                    st.rerun()
else:
    st.caption("Keine Vorlagen aktiv. In Poolverwaltung aktivieren.")

st.divider()

# Task list
if pool_filter:
    tasks = get_pending_tasks_for_pool(session, pool_filter)
else:
    tasks = get_pending_tasks(session)

if not tasks:
    st.success("✅ Alle Aufgaben erledigt!")
else:
    for task in tasks:
        overdue = task.due_date and task.due_date < today
        is_today = task.due_date == today
        if overdue:
            icon = "🔴"
        elif is_today:
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
                    st.caption(
                        f"✅ Erledigt: {task.completed_at.strftime('%d.%m.%Y %H:%M')}"
                    )
                if task.recommended_amount is not None:
                    st.caption(f"Empfohlen: {task.recommended_amount:g} {task.recommended_unit or ''}")
            with cols[1]:
                if task.due_date:
                    label = (
                        "Überfällig!"
                        if overdue
                        else ("Heute" if is_today else task.due_date.strftime("%d.%m.%Y"))
                    )
                    st.write(f"Fällig: {label}")
                if task.interval_days:
                    st.caption(f"Alle {task.interval_days} Tage")
                if task.follow_up_days:
                    st.caption(f"Folge in {task.follow_up_days} Tagen")
            with cols[2]:
                if not task.completed:
                    exec_notes = st.text_input(
                        "Doku",
                        placeholder="z. B. 100g zugegeben",
                        key=f"exec_{task.id}",
                    )
                    actual_amount = None
                    actual_unit = task.recommended_unit
                    if task.recommended_amount is not None:
                        actual_amount = st.number_input(
                            "Tatsächliche Dosis",
                            value=task.recommended_amount,
                            step=0.1,
                            key=f"amt_{task.id}",
                            label_visibility="collapsed",
                            placeholder=f"Menge ({actual_unit or 'g'})",
                        )
                    if st.button(
                        "✅ Erledigt", key=f"done_{task.id}", use_container_width=True
                    ):
                        complete_task_with_notes(
                            session, task.id,
                            executed_notes=exec_notes,
                            actual_amount=actual_amount,
                            actual_unit=actual_unit,
                        )
                        st.rerun()

st.divider()

# Manual task creation
with st.expander("➕ Manuelle Aufgabe"):
    with st.form("manuelle_aufgabe"):
        pools_for_new = {p.id: p.name for p in pools}
        sel_pool_id = st.selectbox(
            "Pool",
            options=list(pools_for_new.keys()),
            format_func=lambda x: pools_for_new[x],
        )
        title = st.text_input("Titel")
        description = st.text_area("Beschreibung")
        due_date = st.date_input("Fällig am", value=today)
        interval = st.number_input(
            "Wiederholen alle (Tage, 0 = einmalig)", min_value=0, value=0
        )
        follow_up = st.number_input(
            "Folgeaufgabe in (Tagen, 0 = keine)", min_value=0, value=0
        )
        if st.form_submit_button("Speichern"):
            save_task(
                session,
                task_type="custom",
                title=title,
                description=description,
                due_date=due_date,
                interval_days=interval,
            )
            if follow_up > 0:
                save_task(
                    session,
                    task_type="custom",
                    title=f"{title} (Folge)",
                    description=f"Folgeaufgabe in {follow_up} Tagen",
                    due_date=due_date + datetime.timedelta(days=follow_up),
                    interval_days=0,
                )
            st.success("Aufgabe gespeichert!")
            st.rerun()
```

- [ ] **Step 2: Commit**

```bash
git add pages/03_Wartung.py
git commit -m "feat: quick-add presets and actual dosing capture in Wartung page"
```

---

### Task 5: Auto-measurement task + dosing product capture (Wasserrechner.py)

**Files:**
- Modify: `Wasserrechner.py`

- [ ] **Step 1: Update dosing task creation to capture product data**

In `Wasserrechner.py`, locate the task creation block (around line 391-400) and the follow-up task creation (around line 562-574). Update both to pass `product_id`, `product_name`, `recommended_amount`, `recommended_unit`.

First, add import for `get_pool`:
```python
from database.repository import (
    save_reading,
    save_task,
    save_photo,  # already there
    get_pools,
    get_latest_reading,
    get_readings,
    get_pool,  # ADD THIS
)
```

Update the task creation block (around line 391-400):
```python
    if not st.session_state.get("task_created"):
        for d in dosing:
            save_task(
                session,
                task_type="dosierung",
                title=f"{d.product}: {d.amount:g} {d.unit}",
                description=d.reason,
                due_date=datetime.date.today(),
                interval_days=0,
                product_id=getattr(d, 'product_id', None),
                product_name=d.product,
                recommended_amount=d.amount,
                recommended_unit=d.unit,
            )
```

Update the follow-up block (around line 562-574):
```python
                                if d.follow_up_days > 0:
                                    save_task(
                                        session,
                                        task_type="nachkontrolle",
                                        title=f"{d.product} – Nachkontrolle",
                                        description=(
                                            f"Folgeaufgabe in {d.follow_up_days} Tagen "
                                            f"(auto. {datetime.date.today().isoformat()})"
                                        ),
                                        due_date=datetime.date.today()
                                        + datetime.timedelta(days=d.follow_up_days),
                                        interval_days=d.follow_up_days,
                                        product_id=getattr(d, 'product_id', None),
                                        product_name=d.product,
                                        recommended_amount=d.amount,
                                        recommended_unit=d.unit,
                                    )
```

- [ ] **Step 2: Add auto-measurement follow-up task**

After the existing task creation block (after the `st.session_state.task_created = False` line), add:

```python
    # Auto-create measurement follow-up task
    pool_id = st.session_state.get("selected_pool_id")
    if pool_id:
        pool = get_pool(session, pool_id)
        if pool and pool.auto_measurement_task_days > 0:
            follow_up_date = datetime.date.today() + datetime.timedelta(days=pool.auto_measurement_task_days)
            existing = [t for t in tasks if "Nachkontrolle" in t.title]
            save_task(
                session,
                task_type="nachkontrolle",
                title="Nachkontrolle (Messung)",
                description=f"Automatisch erstellt nach Messung vom {datetime.date.today().isoformat()}",
                due_date=follow_up_date,
                interval_days=pool.auto_measurement_task_days,
                pool_id=pool_id,
            )
```

Find the `tasks` variable to ensure it's accessible. If `tasks` is not in scope, we need to check differently. Let me check what's available in that section of Wasserrechner.py.

Actually, looking at the code flow more carefully, the auto-measurement task should be created unconditionally. The "existing" check was supposed to avoid duplicates but let me keep it simple:

```python
    # Auto-create measurement follow-up task
    pool_id = st.session_state.get("selected_pool_id")
    if pool_id:
        pool = get_pool(session, pool_id)
        if pool and pool.auto_measurement_task_days > 0:
            follow_up_date = datetime.date.today() + datetime.timedelta(days=pool.auto_measurement_task_days)
            save_task(
                session,
                task_type="nachkontrolle",
                title="Nachkontrolle (Messung)",
                description=f"Automatisch erstellt nach Messung vom {datetime.date.today().isoformat()}",
                due_date=follow_up_date,
                interval_days=pool.auto_measurement_task_days,
                pool_id=pool_id,
            )
```

- [ ] **Step 3: Commit**

```bash
git add Wasserrechner.py
git commit -m "feat: auto-measurement follow-up task and product dosing capture"
```

---

### Task 6: Pool configuration — template toggles and auto_measurement_task_days

**Files:**
- Modify: `pages/01_Poolverwaltung.py`

- [ ] **Step 1: Add template toggles and auto_measurement_task_days to pool form**

Add imports at top:
```python
from database.repository import (
    # ... existing imports ...
    get_task_templates,
    get_pool_task_defaults,
    set_pool_template_active,
    activate_defaults_for_pool,
)
```

In the pool form (`with st.form("pool_form")`), after the instrument select (line 181), add:

```python
        st.markdown("##### 📋 Standard-Aufgaben")
        st.caption("Wiederkehrende Aufgaben, die automatisch im Wartung-Kalender erscheinen.")
        templates = get_task_templates(session)
        pool_defaults = {ptd.template_id: ptd for ptd in get_pool_task_defaults(session, pool.id)} if pool else {}
        active_template_ids = set()
        for ptd in pool_defaults.values():
            if ptd.active:
                active_template_ids.add(ptd.template_id)

        cat_labels = {"chemie": "🧪 Chemie", "technik": "🔧 Technik", "reinigung": "🧹 Reinigung", "allgemein": "📋 Allgemein"}
        cats_order = ["chemie", "technik", "reinigung", "allgemein"]
        templates_by_cat: dict[str, list] = {}
        for t in templates:
            cat = t.category if t.category in cats_order else "allgemein"
            templates_by_cat.setdefault(cat, []).append(t)

        selected_templates = set()
        for cat in cats_order:
            if cat in templates_by_cat:
                st.markdown(f"**{cat_labels.get(cat, cat)}**")
                cols = st.columns(2)
                for i, t in enumerate(templates_by_cat[cat]):
                    with cols[i % 2]:
                        default_val = t.id in active_template_ids if pool else True
                        if st.checkbox(
                            f"{t.icon} {t.name} ({t.interval_days} Tage)",
                            value=default_val,
                            key=f"tmpl_{t.id}",
                        ):
                            selected_templates.add(t.id)

        auto_task_days = st.number_input(
            "Auto-Nachkontrolle nach Messung (Tage, 0=aus)",
            min_value=0, max_value=365, value=pool.auto_measurement_task_days if pool else 7,
            key="auto_task_days",
        )
```

In the submit handler, update the `update_pool` / `save_pool` calls to include `auto_measurement_task_days`:

For `update_pool`:
```python
            update_pool(
                ...
                auto_measurement_task_days=auto_task_days,
                ...
            )
            # Update template toggles
            for t in templates:
                is_active = t.id in selected_templates
                set_pool_template_active(session, pool.id, t.id, is_active)
```

For `save_pool` (new pool):
```python
            new_pool = save_pool(
                ...
                auto_measurement_task_days=auto_task_days,
                ...
            )
            activate_defaults_for_pool(session, new_pool.id)
            # Apply template selections
            for t in templates:
                is_active = t.id in selected_templates
                set_pool_template_active(session, new_pool.id, t.id, is_active)
```

- [ ] **Step 2: Commit**

```bash
git add pages/01_Poolverwaltung.py
git commit -m "feat: pool-level template configuration and auto-measurement interval"
```

---

### Task 7: Calendar — show template tasks and capture actual_amount

**Files:**
- Modify: `pages/04_Kalender.py`

- [ ] **Step 1: Integrate template instances and actual_amount capture in calendar**

Replace `pages/04_Kalender.py`:

```python
import datetime
import calendar
import streamlit as st
from database.db import get_engine, init_db, get_session
from database.models import MaintenanceTask
from database.repository import (
    get_pools, get_tasks_by_date_range,
    complete_task_with_notes,
    ensure_template_instances,
)

st.set_page_config(
    page_title="PoolPilot - Dein intelligenter Pool-Helfer", page_icon="🏊"
)

engine = get_engine()
init_db(engine)
session = get_session(engine)

st.title("📅 Aufgaben-Kalender")

pools = get_pools(session)
pool_options = {p.id: p.name for p in pools}
pool_options[0] = "Alle Pools"
selected_pool_id = st.selectbox(
    "Pool filtern",
    options=list(pool_options.keys()),
    format_func=lambda x: pool_options[x],
    key="calendar_pool",
)

now = datetime.date.today()

with st.expander("📝 Aufgabe nachtragen"):
    with st.form("retro_task"):
        retro_pool = st.selectbox(
            "Pool", options=pools, format_func=lambda p: p.name,
            key="retro_pool"
        )
        retro_title = st.text_input("Titel", placeholder="z.B. ½ Chlor-Tablette zugegeben")
        retro_date = st.date_input("Datum", value=now)
        retro_done = st.checkbox("Bereits erledigt", value=True)
        retro_notes = st.text_area("Notiz (optional)", placeholder="Details…")
        if st.form_submit_button("💾 Aufgabe eintragen"):
            if retro_title.strip():
                task = MaintenanceTask(
                    pool_id=retro_pool.id,
                    task_type="manual",
                    title=retro_title.strip(),
                    description=retro_notes,
                    due_date=retro_date,
                    completed=retro_done,
                    completed_at=datetime.datetime.combine(retro_date, datetime.time(12, 0)) if retro_done else None,
                    executed_notes=retro_notes,
                )
                session.add(task)
                session.commit()
                st.success(f"✅ Aufgabe für {retro_date.strftime('%d.%m.%Y')} eingetragen!")
                st.rerun()
            else:
                st.error("Bitte einen Titel eingeben.")

if "cal_year" not in st.session_state:
    st.session_state.cal_year = now.year
if "cal_month" not in st.session_state:
    st.session_state.cal_month = now.month

nav = st.columns([1, 3, 1])
with nav[0]:
    if st.button("◀ Vorheriger"):
        if st.session_state.cal_month == 1:
            st.session_state.cal_month = 12
            st.session_state.cal_year -= 1
        else:
            st.session_state.cal_month -= 1
        st.rerun()

with nav[1]:
    month_name = datetime.date(
        st.session_state.cal_year, st.session_state.cal_month, 1
    ).strftime("%B %Y")
    st.markdown(f"<h3 style='text-align:center'>{month_name}</h3>", unsafe_allow_html=True)

with nav[2]:
    if st.button("Nächster ▶"):
        if st.session_state.cal_month == 12:
            st.session_state.cal_month = 1
            st.session_state.cal_year += 1
        else:
            st.session_state.cal_month += 1
        st.rerun()

# Fetch tasks for the month
first_day = datetime.date(st.session_state.cal_year, st.session_state.cal_month, 1)
last_day = datetime.date(
    st.session_state.cal_year, st.session_state.cal_month,
    calendar.monthrange(st.session_state.cal_year, st.session_state.cal_month)[1]
)
pool_id_arg = None if selected_pool_id == 0 else selected_pool_id

# Ensure template instances for visible month
ensure_template_instances(session, pool_id_arg, first_day, last_day)

tasks = get_tasks_by_date_range(session, first_day, last_day, pool_id_arg)

# Group tasks by date
tasks_by_date: dict[datetime.date, list] = {}
for t in tasks:
    if t.due_date not in tasks_by_date:
        tasks_by_date[t.due_date] = []
    tasks_by_date[t.due_date].append(t)

# Build calendar grid
cal = calendar.Calendar()
month_days = list(cal.itermonthdays(st.session_state.cal_year, st.session_state.cal_month))

html = """
<style>
.cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
.cal-header { text-align: center; font-weight: 700; padding: 6px; background: #f0f2f6; border-radius: 4px; font-size: 0.85rem; }
.cal-day { min-height: 80px; padding: 4px; border-radius: 4px; background: white; border: 1px solid #e0e0e0; font-size: 0.75rem; }
.cal-day.other-month { background: #fafafa; color: #bbb; }
.cal-day.today { border: 2px solid #4CAF50; }
.cal-day-num { font-weight: 600; margin-bottom: 2px; }
.task-dot { display: inline-block; width: 100%; padding: 1px 3px; margin: 1px 0; border-radius: 3px; font-size: 0.65rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; cursor: default; }
.task-dot.pending { background: #ffebee; color: #c62828; }
.task-dot.completed { background: #e8f5e9; color: #2e7d32; text-decoration: line-through; }
.task-dot.followup { background: #fff3e0; color: #e65100; }
.task-dot.template { background: #e3f2fd; color: #1565c0; }
</style>
<div class="cal-grid">
"""

for day_name in ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]:
    html += f"<div class='cal-header'>{day_name}</div>"

for day in month_days:
    if day == 0:
        html += "<div class='cal-day other-month'></div>"
        continue
    d = datetime.date(st.session_state.cal_year, st.session_state.cal_month, day)
    classes = "cal-day"
    if d == now:
        classes += " today"
    html += f"<div class='{classes}'>"
    html += f"<div class='cal-day-num'>{day}</div>"
    if d in tasks_by_date:
        for t in tasks_by_date[d]:
            if t.completed:
                cls = "completed"
            elif t.template_id:
                cls = "template"
            else:
                cls = "pending"
            label = t.title[:20] + ("…" if len(t.title) > 20 else "")
            html += f"<div class='task-dot {cls}' title='{t.title}'>{label}</div>"
    html += "</div>"

html += "</div>"

st.components.v1.html(html, height=600, scrolling=True)

st.divider()
st.subheader("📋 Aufgaben des Monats")
if tasks:
    for t in tasks:
        pool_name = next((p.name for p in pools if p.id == t.pool_id), "—")
        status = "✅ Erledigt" if t.completed else "🔴 Offen"
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{t.title}**")
                details = f"📅 {t.due_date.strftime('%d.%m.%Y')} · {pool_name} · {status}"
                if t.recommended_amount is not None:
                    details += f" · Empfohlen: {t.recommended_amount:g} {t.recommended_unit or ''}"
                if t.actual_amount is not None:
                    details += f" · Gegeben: {t.actual_amount:g} {t.actual_unit or ''}"
                st.caption(details)
            with col2:
                if not t.completed:
                    notes = st.text_input(
                        "Notiz", key=f"notes_{t.id}", label_visibility="collapsed",
                        placeholder="Notiz…"
                    )
                    actual_amount = None
                    actual_unit = t.recommended_unit
                    if t.recommended_amount is not None:
                        actual_amount = st.number_input(
                            "Dosis", value=t.recommended_amount, step=0.1,
                            key=f"amt_cal_{t.id}", label_visibility="collapsed",
                            placeholder=f"Menge ({actual_unit or 'g'})",
                        )
                    if st.button("Erledigt", key=f"done_{t.id}"):
                        complete_task_with_notes(
                            session, t.id, notes,
                            actual_amount=actual_amount,
                            actual_unit=actual_unit,
                        )
                        st.rerun()
else:
    st.info("Keine Aufgaben in diesem Monat.")
```

- [ ] **Step 2: Commit**

```bash
git add pages/04_Kalender.py
git commit -m "feat: calendar shows template tasks and captures actual dosing"
```

---

### Task 8: Run all tests and final verification

- [ ] **Step 1: Run full test suite**

```bash
cd /app && python -m pytest tests/ -xvs
```

Expected: All ~20+ tests pass.

- [ ] **Step 2: Run the app to verify**

```bash
cd /app && streamlit run Wasserrechner.py --server.headless true &
# Check it starts without import errors
```

Expected: Streamlit starts without ImportError or ModuleNotFoundError.

- [ ] **Step 3: Commit any final fixes**

```bash
git add -A && git commit -m "fix: final adjustments after test run"
```
