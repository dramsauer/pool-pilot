# Data Export / Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add full data export (ZIP download of `data/` directory) and import with per-category merge (Replace / Merge / Skip) with ID remapping for FK dependencies.

**Architecture:** A new Streamlit page `09_Datenverwaltung.py` handles the UI; core logic lives in `utils/export_import.py`. Export uses `zipfile.ZipFile` on `data/`. Import extracts ZIP to temp, opens the imported DB with a separate SQLAlchemy engine, and performs per-category merge in FK-safe order using ID maps.

**Tech Stack:** Python 3.9+, Streamlit, SQLAlchemy 2.0+, SQLite, zipfile, pytest

---

### Task 1: Export utility & tests

**Files:**
- Create: `utils/export_import.py`
- Test: `tests/test_export_import.py`

- [ ] **Step 1: Write the failing test for `create_export_zip`**

  ```python
  # tests/test_export_import.py
  import zipfile
  import io
  import pytest
  from pathlib import Path
  from utils.export_import import create_export_zip
  from database.db import DB_PATH

  def test_create_export_zip_contains_db_and_photos(tmp_path):
      data_dir = tmp_path / "data"
      data_dir.mkdir()
      db_file = data_dir / "pool.db"
      db_file.write_text("fake-db-content")
      photos_dir = data_dir / "photos"
      photos_dir.mkdir()
      photo_file = photos_dir / "test.jpg"
      photo_file.write_text("fake-photo-content")

      zip_bytes = create_export_zip(data_dir)
      with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
          names = zf.namelist()
          assert "pool.db" in names
          assert "photos/test.jpg" in names
          assert zf.read("pool.db") == b"fake-db-content"
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `cd /Users/dominik/Library/CloudStorage/Nextcloud-Dominik@nextcloud․dramsauer․me/Kreativwerkstatt/0 Pool-Wasser-Gleichgewicht && python -m pytest tests/test_export_import.py::test_create_export_zip_contains_db_and_photos -v`
  Expected: `FAILED` with `ModuleNotFoundError: No module named 'utils.export_import'`

- [ ] **Step 3: Write minimal implementation of `create_export_zip`**

  ```python
  # utils/export_import.py
  import io
  import zipfile
  from pathlib import Path


  def create_export_zip(data_dir: Path | str) -> bytes:
      data_dir = Path(data_dir)
      buf = io.BytesIO()
      with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
          db_path = data_dir / "pool.db"
          if db_path.exists():
              zf.write(db_path, "pool.db")
          photos_dir = data_dir / "photos"
          if photos_dir.exists():
              for photo in sorted(photos_dir.iterdir()):
                  if photo.is_file():
                      zf.write(photo, f"photos/{photo.name}")
      return buf.getvalue()
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `python -m pytest tests/test_export_import.py::test_create_export_zip_contains_db_and_photos -v`
  Expected: `PASSED`

- [ ] **Step 5: Commit**

  ```bash
  git add utils/export_import.py tests/test_export_import.py
  git commit -m "feat(export): add create_export_zip utility"
  ```



### Task 2: Export UI page + sidebar link

**Files:**
- Create: `pages/09_Datenverwaltung.py`
- Modify: `Wasserrechner.py:79-87` (sidebar section)

- [ ] **Step 1: Create the export page with download button**

  ```python
  # pages/09_Datenverwaltung.py
  import streamlit as st
  from pathlib import Path
  from utils.export_import import create_export_zip

  st.set_page_config(page_title="Data Export / Import", page_icon="🔐")

  DATA_DIR = Path(__file__).parent.parent / "data"

  st.title("🔐 Data Export / Import")

  st.header("Export")
  st.write("Download a complete ZIP archive of the database and all photos.")

  if st.button("📦 Download full backup (ZIP)"):
      with st.spinner("Creating backup..."):
          zip_bytes = create_export_zip(DATA_DIR)
      st.download_button(
          label="💾 Save ZIP",
          data=zip_bytes,
          file_name=f"poolpilot-backup-{st.context.time if hasattr(st, 'context') else ''}.zip",
          mime="application/zip",
      )
  ```

- [ ] **Step 2: Fix filename with datetime**

  Replace the `file_name` line with:

  ```python
      from datetime import date
      # ...
      file_name=f"poolpilot-backup-{date.today().isoformat()}.zip",
  ```

- [ ] **Step 3: Add sidebar link in `Wasserrechner.py`**

  In `Wasserrechner.py`, after the pool selector block (after line 87), add:

  ```python
  st.sidebar.divider()
  with st.sidebar.expander("Weitere"):
      st.page_link("pages/09_Datenverwaltung.py", label="🔐 Daten-Export/-Import")
  ```

- [ ] **Step 4: Run the app to visually verify**

  Run: `cd /Users/dominik/Library/CloudStorage/Nextcloud-Dominik@nextcloud․dramsauer․me/Kreativwerkstatt/0 Pool-Wasser-Gleichgewicht && streamlit run Wasserrechner.py`
  Expected: Sidebar shows "Weitere" expander → clicking it shows "Daten-Export/-Import" link → navigating shows export page with download button

- [ ] **Step 5: Commit**

  ```bash
  git add pages/09_Datenverwaltung.py Wasserrechner.py
  git commit -m "feat(export): add export page with ZIP download + sidebar link"
  ```



### Task 3: Import analysis utility & tests

**Files:**
- Modify: `utils/export_import.py`
- Modify: `tests/test_export_import.py`

- [ ] **Step 1: Write the failing test for ZIP analysis**

  ```python
  # Add to tests/test_export_import.py
  import tempfile
  import shutil
  from database.db import get_engine, get_session
  from database.models import Base, Pool, Product
  from utils.export_import import analyze_zip, AnalysisResult, TABLE_CATEGORIES

  def make_test_db(path: Path, pools: list[dict], products: list[dict]):
      engine = get_engine(str(path))
      Base.metadata.create_all(engine)
      session = get_session(engine)
      for p in pools:
          session.add(Pool(**p))
      for p in products:
          session.add(Product(**p))
      session.commit()
      session.close()

  def test_analyze_zip_returns_counts(tmp_path):
      # Create a source data dir with a test DB
      data_dir = tmp_path / "data"
      data_dir.mkdir()
      db_path = data_dir / "pool.db"
      make_test_db(db_path, [{"name": "Pool1", "volume_liter": 1000}], [{"name": "Prod1", "typ": "chlorine", "dosage_factor": 10}])

      # Create ZIP from it
      from utils.export_import import create_export_zip
      zip_bytes = create_export_zip(data_dir)

      # Analyze
      result = analyze_zip(zip_bytes)
      assert isinstance(result, AnalysisResult)
      assert result.counts["pools"] == 1
      assert result.counts["products"] == 1
      assert result.counts["readings"] == 0
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `python -m pytest tests/test_export_import.py::test_analyze_zip_returns_counts -v`
  Expected: `FAILED` with `ImportError` or `AttributeError`

- [ ] **Step 3: Add `TABLE_CATEGORIES`, `AnalysisResult`, and `analyze_zip`**

  Add to `utils/export_import.py`:

  ```python
  import tempfile, shutil
  from dataclasses import dataclass
  from database.db import get_engine, get_session

  TABLE_CATEGORIES = {
      "instruments": {"model": "Instrument", "model_class": None},
      "trinkwasser": {"model": "Trinkwasser", "model_class": None},
      "products": {"model": "Product", "model_class": None},
      "task_templates": {"model": "TaskTemplate", "model_class": None},
      "pools": {"model": "Pool", "model_class": None},
      "readings": {"model": "Reading", "model_class": None},
      "photos": {"model": "Photo", "model_class": None},
      "maintenance_tasks": {"model": "MaintenanceTask", "model_class": None},
  }

  USER_CATEGORIES = [
      ("pools", "Pools"),
      ("products", "Products"),
      ("instruments", "Instruments"),
      ("trinkwasser", "Tap Water Sources"),
      ("task_templates", "Task Templates"),
      ("readings", "Measurements"),
      ("maintenance_tasks", "Tasks"),
  ]

  @dataclass
  class AnalysisResult:
      valid: bool
      error: str
      counts: dict
      photo_count: int

  def _resolve_models():
      from database.models import Instrument, Trinkwasser, Product, TaskTemplate, Pool, Reading, Photo, MaintenanceTask
      TABLE_CATEGORIES["instruments"]["model_class"] = Instrument
      TABLE_CATEGORIES["trinkwasser"]["model_class"] = Trinkwasser
      TABLE_CATEGORIES["products"]["model_class"] = Product
      TABLE_CATEGORIES["task_templates"]["model_class"] = TaskTemplate
      TABLE_CATEGORIES["pools"]["model_class"] = Pool
      TABLE_CATEGORIES["readings"]["model_class"] = Reading
      TABLE_CATEGORIES["photos"]["model_class"] = Photo
      TABLE_CATEGORIES["maintenance_tasks"]["model_class"] = MaintenanceTask

  def analyze_zip(zip_bytes: bytes) -> AnalysisResult:
      with tempfile.TemporaryDirectory() as tmp:
          zip_path = Path(tmp) / "import.zip"
          zip_path.write_bytes(zip_bytes)
          extract_dir = Path(tmp) / "extracted"
          shutil.unpack_archive(str(zip_path), str(extract_dir), "zip")
          db_file = extract_dir / "pool.db"
          if not db_file.exists():
              return AnalysisResult(valid=False, error="ZIP does not contain pool.db", counts={}, photo_count=0)
          engine = get_engine(str(db_file))
          session = get_session(engine)
          _resolve_models()
          counts = {}
          for key, info in TABLE_CATEGORIES.items():
              model_cls = info["model_class"]
              if model_cls is not None:
                  counts[key] = session.query(model_cls).count()
          session.close()
          photos_dir = extract_dir / "photos"
          photo_count = len([f for f in photos_dir.iterdir() if f.is_file()]) if photos_dir.exists() else 0
          return AnalysisResult(valid=True, error="", counts=counts, photo_count=photo_count)
  ```

- [ ] **Step 4: Build the correct `TABLE_CATEGORIES` using the proper import**

  The lazy `_resolve_models` pattern is fragile. Replace with direct imports:

  ```python
  from database.models import (
      Instrument, Trinkwasser, Product, TaskTemplate, PoolTaskDefault,
      Pool, Reading, Photo, MaintenanceTask,
  )

  TABLE_CATEGORIES = {
      "instruments": {"model": Instrument, "label": "Instruments"},
      "trinkwasser": {"model": Trinkwasser, "label": "Tap Water Sources"},
      "products": {"model": Product, "label": "Products"},
      "task_templates": {"model": TaskTemplate, "label": "Task Templates"},
      "pools": {"model": Pool, "label": "Pools"},
      "pool_task_defaults": {"model": PoolTaskDefault, "label": "Pool Task Defaults"},
      "readings": {"model": Reading, "label": "Measurements"},
      "photos": {"model": Photo, "label": "Photos"},
      "maintenance_tasks": {"model": MaintenanceTask, "label": "Tasks"},
  }

  DEPENDENCY_ORDER = [
      "instruments", "trinkwasser", "products", "task_templates",
      "pools",
      "pool_task_defaults",
      "readings",
      "photos",
      "maintenance_tasks",
  ]

  def analyze_zip(zip_bytes: bytes) -> AnalysisResult:
      try:
          with tempfile.TemporaryDirectory() as tmp:
              extract_dir = Path(tmp) / "extracted"
              zip_path = Path(tmp) / "import.zip"
              zip_path.write_bytes(zip_bytes)
              shutil.unpack_archive(str(zip_path), str(extract_dir), "zip")
              db_file = extract_dir / "pool.db"
              if not db_file.exists():
                  return AnalysisResult(valid=False, error="ZIP does not contain pool.db", counts={}, photo_count=0)
              engine = get_engine(str(db_file))
              session = get_session(engine)
              counts = {}
              for key, info in TABLE_CATEGORIES.items():
                  counts[key] = session.query(info["model"]).count()
              session.close()
              photos_dir = extract_dir / "photos"
              photo_count = len([f for f in photos_dir.iterdir() if f.is_file()]) if photos_dir.exists() else 0
              return AnalysisResult(valid=True, error="", counts=counts, photo_count=photo_count)
      except Exception as e:
          return AnalysisResult(valid=False, error=str(e), counts={}, photo_count=0)
  ```

- [ ] **Step 5: Update `AnalysisResult` with `tmp_path` for later use**

  ```python
  @dataclass
  class AnalysisResult:
      valid: bool
      error: str
      counts: dict
      photo_count: int
      tmp_path: str = ""
      imported_db_path: str = ""
      extract_dir: str = ""
  ```

  Update `analyze_zip` to store `tmp_path` and `imported_db_path`:

  ```python
  def analyze_zip(zip_bytes: bytes) -> AnalysisResult:
      tmp = tempfile.mkdtemp()
      try:
          extract_dir = Path(tmp) / "extracted"
          zip_path = Path(tmp) / "import.zip"
          zip_path.write_bytes(zip_bytes)
          shutil.unpack_archive(str(zip_path), str(extract_dir), "zip")
          db_file = extract_dir / "pool.db"
          if not db_file.exists():
              shutil.rmtree(tmp)
              return AnalysisResult(valid=False, error="ZIP does not contain pool.db", counts={}, photo_count=0)
          engine = get_engine(str(db_file))
          session = get_session(engine)
          counts = {}
          for key, info in TABLE_CATEGORIES.items():
              counts[key] = session.query(info["model"]).count()
          session.close()
          photos_dir = extract_dir / "photos"
          photo_count = len([f for f in photos_dir.iterdir() if f.is_file()]) if photos_dir.exists() else 0
          return AnalysisResult(valid=True, error="", counts=counts, photo_count=photo_count, tmp_path=tmp, imported_db_path=str(db_file), extract_dir=str(extract_dir))
      except Exception as e:
          shutil.rmtree(tmp, ignore_errors=True)
          return AnalysisResult(valid=False, error=str(e), counts={}, photo_count=0)
  ```

- [ ] **Step 6: Run tests to verify**

  Run: `python -m pytest tests/test_export_import.py -v`
  Expected: Both tests `PASSED`

- [ ] **Step 7: Commit**

  ```bash
  git add utils/export_import.py tests/test_export_import.py
  git commit -m "feat(import): add analyze_zip utility with tests"
  ```



### Task 4: Import analysis UI

**Files:**
- Modify: `pages/09_Datenverwaltung.py`

- [ ] **Step 1: Add the upload + analyze section below export**

  ```python
  # pages/09_Datenverwaltung.py — add after export section
  import json

  st.header("Import")
  st.write("Upload a backup ZIP to restore or merge data into the current database.")

  uploaded_zip = st.file_uploader("⬆ Upload backup ZIP", type="zip")

  if uploaded_zip is not None:
      zip_bytes = uploaded_zip.getvalue()

      if st.button("🔍 Analyze ZIP"):
          with st.spinner("Analyzing..."):
              result = analyze_zip(zip_bytes)
          if not result.valid:
              st.error(f"Invalid ZIP: {result.error}")
              st.stop()
          st.success("ZIP analysis complete!")

          col1, col2 = st.columns(2)
          col1.metric("Database entries", sum(result.counts.values()))
          col2.metric("Photos", result.photo_count)

          # Show table comparison (placeholder for merge UI)
          st.subheader("Contents")
          for key, label in [
              ("pools", "Pools"), ("products", "Products"),
              ("instruments", "Instruments"), ("trinkwasser", "Tap Water"),
              ("task_templates", "Task Templates"),
              ("readings", "Measurements"), ("maintenance_tasks", "Tasks"),
          ]:
              c = result.counts.get(key, 0)
              if c > 0:
                  st.write(f"- {label}: **{c}**")
  ```

- [ ] **Step 2: Run the app to visually verify**

  Run: `streamlit run Wasserrechner.py` → navigate to Data Export / Import → upload a manually created test ZIP → click "Analyze ZIP"
  Expected: ZIP analysis succeeds and shows contents

- [ ] **Step 3: Commit**

  ```bash
  git add pages/09_Datenverwaltung.py
  git commit -m "feat(import): add import analysis UI"
  ```



### Task 5: Import merge execution utility & tests

**Files:**
- Modify: `utils/export_import.py`
- Modify: `tests/test_export_import.py`

- [ ] **Step 1: Write the failing test for `execute_import` with Replace mode**

  ```python
  # Add to tests/test_export_import.py
  from utils.export_import import execute_import
  from database.db import get_engine as get_current_engine
  from sqlalchemy import create_engine

  def test_execute_import_replace_pools(tmp_path):
      # Create current DB with 1 pool
      current_db = tmp_path / "current.db"
      current_engine = create_engine(f"sqlite:///{current_db}")
      Base.metadata.create_all(current_engine)
      s = get_session(current_engine)
      s.add(Pool(name="OldPool", volume_liter=500))
      s.commit()
      s.close()

      # Create imported DB with 1 pool
      imported_db = tmp_path / "imported.db"
      imported_engine = create_engine(f"sqlite:///{imported_db}")
      Base.metadata.create_all(imported_engine)
      s = get_session(imported_engine)
      s.add(Pool(name="NewPool", volume_liter=1000))
      s.commit()
      s.close()

      # Execute import: replace pools
      current_sesh = get_session(current_engine)
      result = execute_import(
          current_session=current_sesh,
          imported_db_path=str(imported_db),
          strategies={"pools": "replace"},
          id_maps={},
      )
      current_sesh.close()

      assert result["pools"]["status"] == "ok"
      assert result["pools"]["count"] == 1
      assert result["pools"]["action"] == "replaced"

      # Verify
      s = get_session(current_engine)
      pools = s.query(Pool).all()
      assert len(pools) == 1
      assert pools[0].name == "NewPool"
      s.close()
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `python -m pytest tests/test_export_import.py::test_execute_import_replace_pools -v`
  Expected: `FAILED` with `AttributeError: module has no attribute 'execute_import'`

- [ ] **Step 3: Implement `execute_import` — core function**

  Add to `utils/export_import.py`:

  ```python
  from sqlalchemy import create_engine
  from database.db import get_session

  CATEGORY_MERGE_KEYS = {
      "pools": ["name"],
      "products": ["name"],
      "instruments": ["name"],
      "trinkwasser": ["name"],
      "task_templates": ["name"],
      "pool_task_defaults": ["pool_id", "template_id"],
      "readings": ["timestamp", "pool_id"],
      "photos": ["reading_id", "image_path"],
      "maintenance_tasks": ["title", "due_date"],
  }

  PARENT_DEPENDENCIES = {
      "pool_task_defaults": ["pools", "task_templates"],
      "readings": ["pools"],
      "photos": ["readings"],
      "maintenance_tasks": ["pools", "readings", "products"],
  }

  PHOTO_AUTO_PARENT = "readings"

  def _get_row_dict(row) -> dict:
      return {c.name: getattr(row, c.name) for c in row.__table__.columns}

  # Explicit FK column mappings: (child_category, parent_category) -> fk_column_name
  _FK_MAP = {
      ("pool_task_defaults", "pools"): "pool_id",
      ("pool_task_defaults", "task_templates"): "template_id",
      ("readings", "pools"): "pool_id",
      ("photos", "readings"): "reading_id",
      ("maintenance_tasks", "pools"): "pool_id",
      ("maintenance_tasks", "readings"): "reading_id",
      ("maintenance_tasks", "products"): "product_id",
  }

  def _remap_fk(row_dict: dict, id_maps: dict, category: str) -> dict:
      """Remap FK columns using accumulated ID maps."""
      deps = PARENT_DEPENDENCIES.get(category, [])
      for dep in deps:
          fk_col = _FK_MAP.get((category, dep), f"{dep.rstrip('s')}_id")
          if fk_col in row_dict and row_dict[fk_col] is not None:
              if dep in id_maps and row_dict[fk_col] in id_maps[dep]:
                  row_dict[fk_col] = id_maps[dep][row_dict[fk_col]]
      return row_dict

  def execute_import(
      current_session,
      imported_db_path: str,
      strategies: dict[str, str],
      id_maps: dict[str, dict[int, int]],
      photos_extract_dir: str = "",
      data_photos_dir: str = "",
  ) -> dict:
      imported_engine = create_engine(f"sqlite:///{imported_db_path}")
      imported_session = get_session(imported_engine)

      result = {}

      # Auto-link photos strategy to readings strategy
      if "photos" not in strategies and PHOTO_AUTO_PARENT in strategies:
          strategies["photos"] = strategies[PHOTO_AUTO_PARENT]

      # Auto-handle pool_task_defaults: only import if both pools and task_templates are imported
      pool_strat = strategies.get("pools", "skip")
      template_strat = strategies.get("task_templates", "skip")
      if pool_strat != "skip" and template_strat != "skip":
          strategies.setdefault("pool_task_defaults", "replace")

      for category in DEPENDENCY_ORDER:
          strategy = strategies.get(category, "skip")
          if strategy == "skip":
              result[category] = {"status": "skipped", "count": 0, "action": "skipped"}
              continue

          model_cls = TABLE_CATEGORIES[category]["model"]
          imported_records = list(imported_session.query(model_cls).all())

          if strategy == "replace":
              # Delete existing records
              current_session.query(model_cls).delete()
              current_session.flush()

              count = 0
              for rec in imported_records:
                  rd = _get_row_dict(rec)
                  imported_id = rd.pop("id")
                  rd.pop("created_at", None)
                  rd = _remap_fk(rd, id_maps, category)
                  new_obj = model_cls(**rd)
                  current_session.add(new_obj)
                  current_session.flush()
                  id_maps.setdefault(category, {})[imported_id] = new_obj.id
                  count += 1

              current_session.commit()
              result[category] = {"status": "ok", "count": count, "action": "replaced"}

          elif strategy == "merge":
              merge_keys = CATEGORY_MERGE_KEYS.get(category, ["name"])
              count = 0
              for rec in imported_records:
                  rd = _get_row_dict(rec)
                  imported_id = rd.pop("id")
                  rd.pop("created_at", None)
                  rd = _remap_fk(rd, id_maps, category)

                  # Build filter for merge key
                  filters = {}
                  for k in merge_keys:
                      if k in rd and rd[k] is not None:
                          filters[k] = rd[k]
                  existing = None
                  if filters:
                      existing = current_session.query(model_cls).filter_by(**filters).first()

                  if existing is not None:
                      id_maps.setdefault(category, {})[imported_id] = existing.id
                  else:
                      new_obj = model_cls(**rd)
                      current_session.add(new_obj)
                      current_session.flush()
                      id_maps.setdefault(category, {})[imported_id] = new_obj.id
                      count += 1

              current_session.commit()
              result[category] = {"status": "ok", "count": count, "action": "merged"}

      imported_session.close()

      # Handle photos file copy (separate key to avoid overwriting DB import result)
      if strategies.get("photos", "skip") != "skip" and photos_extract_dir and data_photos_dir:
          photos_result = _handle_photo_files(
              photos_extract_dir, data_photos_dir,
              strategy=strategies.get("photos", "merge")
          )
          result["photo_files"] = photos_result

      return result


  def _handle_photo_files(src_dir: str, dst_dir: str, strategy: str) -> dict:
      import shutil, os
      src = Path(src_dir) / "photos"
      dst = Path(dst_dir)
      dst.mkdir(parents=True, exist_ok=True)

      if not src.exists():
          return {"status": "skipped", "count": 0, "action": "no_photos_found"}

      if strategy == "replace":
          for f in dst.iterdir():
              if f.is_file():
                  f.unlink()

      count = 0
      for f in sorted(src.iterdir()):
          if f.is_file():
              target = dst / f.name
              if target.exists() and strategy == "merge":
                  # Skip duplicates in merge mode
                  continue
              shutil.copy2(str(f), str(target))
              count += 1

      return {"status": "ok", "count": count, "action": strategy}
  ```

- [ ] **Step 4: Fix the `remap_fk` for readings merge key**

  The merge key for readings is `["timestamp", "pool_id"]` but pool_id needs remapping before matching. Add a helper to remap merge keys:

  ```python
  from sqlalchemy import inspect as sa_inspect

  def _remap_merge_filters(filters: dict, id_maps: dict, category: str) -> dict:
      """Remap FK values in merge key filters."""
      deps = PARENT_DEPENDENCIES.get(category, [])
      for dep in deps:
          fk_col = _FK_MAP.get((category, dep), f"{dep.rstrip('s')}_id")
          if fk_col in filters and filters[fk_col] is not None:
              if dep in id_maps and filters[fk_col] in id_maps[dep]:
                  filters[fk_col] = id_maps[dep][filters[fk_col]]
      return filters
  ```

  Add the call to `_remap_merge_filters` in the merge block, right after building `filters`:

  ```python
  filters = _remap_merge_filters(filters, id_maps, category)
  ```

- [ ] **Step 5: Write tests for Merge mode**

  ```python
  def test_execute_import_merge_pools(tmp_path):
      current_db = tmp_path / "current.db"
      current_engine = create_engine(f"sqlite:///{current_db}")
      Base.metadata.create_all(current_engine)
      s = get_session(current_engine)
      s.add(Pool(name="ExistingPool", volume_liter=500))
      s.commit()
      s.close()

      imported_db = tmp_path / "imported.db"
      imported_engine = create_engine(f"sqlite:///{imported_db}")
      Base.metadata.create_all(imported_engine)
      s = get_session(imported_engine)
      s.add(Pool(name="ExistingPool", volume_liter=500))  # duplicate
      s.add(Pool(name="NewPool", volume_liter=1000))       # new
      s.commit()
      s.close()

      current_sesh = get_session(current_engine)
      result = execute_import(
          current_session=current_sesh,
          imported_db_path=str(imported_db),
          strategies={"pools": "merge"},
          id_maps={},
      )
      current_sesh.close()

      assert result["pools"]["status"] == "ok"
      assert result["pools"]["count"] == 1  # only 1 new
      assert result["pools"]["action"] == "merged"

      s = get_session(current_engine)
      pools = s.query(Pool).all()
      assert len(pools) == 2  # existing + new
      names = {p.name for p in pools}
      assert names == {"ExistingPool", "NewPool"}
      s.close()
  ```

- [ ] **Step 6: Write tests for Skip mode**

  ```python
  def test_execute_import_skip_pools(tmp_path):
      current_db = tmp_path / "current.db"
      current_engine = create_engine(f"sqlite:///{current_db}")
      Base.metadata.create_all(current_engine)
      s = get_session(current_engine)
      s.add(Pool(name="ExistingPool", volume_liter=500))
      s.commit()
      s.close()

      imported_db = tmp_path / "imported.db"
      imported_engine = create_engine(f"sqlite:///{imported_db}")
      Base.metadata.create_all(imported_engine)
      s = get_session(imported_engine)
      s.add(Pool(name="NewPool", volume_liter=1000))
      s.commit()
      s.close()

      current_sesh = get_session(current_engine)
      result = execute_import(
          current_session=current_sesh,
          imported_db_path=str(imported_db),
          strategies={"pools": "skip"},
          id_maps={},
      )
      current_sesh.close()

      assert result["pools"]["status"] == "skipped"

      s = get_session(current_engine)
      pools = s.query(Pool).all()
      assert len(pools) == 1
      assert pools[0].name == "ExistingPool"
      s.close()
  ```

- [ ] **Step 7: Write ID remapping test**

  ```python
  def test_execute_import_remaps_readings_fk(tmp_path):
      current_db = tmp_path / "current.db"
      current_engine = create_engine(f"sqlite:///{current_db}")
      Base.metadata.create_all(current_engine)
      s = get_session(current_engine)
      s.add(Pool(name="OldPool", volume_liter=500))
      s.commit()
      s.close()

      imported_db = tmp_path / "imported.db"
      imported_engine = create_engine(f"sqlite:///{imported_db}")
      Base.metadata.create_all(imported_engine)
      s = get_session(imported_engine)
      p = Pool(name="NewPool", volume_liter=1000)
      s.add(p)
      s.flush()
      from datetime import datetime
      s.add(Reading(pool_id=p.id, timestamp=datetime(2026, 6, 1, 12, 0, 0),
                    ph=7.2, chlorine=1.0, alkalinity=100, hardness=200, temperature_c=30))
      s.commit()
      s.close()

      current_sesh = get_session(current_engine)

      # First import pool (replace), build id_map
      result_pools = execute_import(
          current_session=current_sesh,
          imported_db_path=str(imported_db),
          strategies={"pools": "replace"},
          id_maps={},
      )

      # Now import readings (merge) using the id_maps from pool import
      result_readings = execute_import(
          current_session=current_sesh,
          imported_db_path=str(imported_db),
          strategies={"readings": "merge"},
          id_maps=result_pools.get("_id_maps", {}),
      )
      current_sesh.close()

      assert result_readings["readings"]["status"] == "ok"

      s = get_session(current_engine)
      readings = s.query(Reading).all()
      assert len(readings) == 1
      # Verify the reading's pool_id references the newly inserted pool
      new_pool = s.query(Pool).first()
      assert readings[0].pool_id == new_pool.id
      s.close()
  ```

  Fix `execute_import` to return `id_maps`:

  At the end of `execute_import`, just before `return result`:

  ```python
      result["_id_maps"] = id_maps
      return result
  ```

- [ ] **Step 8: Run all tests**

  Run: `python -m pytest tests/test_export_import.py -v`
  Expected: All tests `PASSED`

- [ ] **Step 9: Commit**

  ```bash
  git add utils/export_import.py tests/test_export_import.py
  git commit -m "feat(import): add execute_import with replace/merge/skip + ID remapping"
  ```



### Task 6: Import execution UI

**Files:**
- Modify: `pages/09_Datenverwaltung.py`

- [ ] **Step 1: Add category strategy selection UI after analysis**

  In `pages/09_Datenverwaltung.py`, after the analysis section, add:

  ```python
  # Store result in session state
  st.session_state["analyze_result"] = result
  st.session_state["zip_bytes"] = zip_bytes
  ```

  Then add a new section:

  ```python
  if "analyze_result" in st.session_state and st.session_state["analyze_result"].valid:
      result = st.session_state["analyze_result"]

      st.subheader("Import Options")
      st.write("Choose how to handle each category:")

      strategies = {}
      cols = st.columns([3, 1, 1, 2])
      cols[0].markdown("**Category**")
      cols[1].markdown("**Current**")
      cols[2].markdown("**Import**")
      cols[3].markdown("**Action**")

      for key, label in [
          ("pools", "Pools"), ("products", "Products"),
          ("instruments", "Instruments"), ("trinkwasser", "Tap Water"),
          ("task_templates", "Task Templates"),
          ("readings", "Measurements"), ("maintenance_tasks", "Tasks"),
      ]:
          current_count = 0  # TODO: fetch from current DB
          imported_count = result.counts.get(key, 0)
          if imported_count == 0:
              continue

          cols = st.columns([3, 1, 1, 2])
          cols[0].write(label)
          cols[1].write(str(current_count))
          cols[2].write(str(imported_count))
          strategy = cols[3].selectbox(
              "", ["merge", "replace", "skip"],
              index=0,
              key=f"strategy_{key}",
              label_visibility="collapsed",
          )
          strategies[key] = strategy

      st.session_state["strategies"] = strategies
  ```

- [ ] **Step 2: Show current DB counts alongside imported counts**

  Need to query the current DB for comparison. Add at the top:

  ```python
  from database.db import get_session, get_engine
  from database.models import Pool, Product, Instrument, Trinkwasser, TaskTemplate, Reading, MaintenanceTask

  def _current_counts():
      session = get_session()
      counts = {
          "pools": session.query(Pool).count(),
          "products": session.query(Product).count(),
          "instruments": session.query(Instrument).count(),
          "trinkwasser": session.query(Trinkwasser).count(),
          "task_templates": session.query(TaskTemplate).count(),
          "readings": session.query(Reading).count(),
          "maintenance_tasks": session.query(MaintenanceTask).count(),
      }
      session.close()
      return counts

  # In the analyze section, store both
  st.session_state["current_counts"] = _current_counts()
  ```

  Replace `current_count = 0` with:

  ```python
  current_counts = st.session_state.get("current_counts", {})
  # ...
  current_count = current_counts.get(key, 0)
  ```

- [ ] **Step 3: Add dependency warning logic**

  After the strategy selection, add:

  ```python
  # Check parent dependencies
  from utils.export_import import PARENT_DEPENDENCIES, DEPENDENCY_ORDER
  warnings = []
  for child, parents in PARENT_DEPENDENCIES.items():
      if strategies.get(child, "skip") != "skip":
          for parent in parents:
              if strategies.get(parent, "skip") == "skip":
                  warnings.append(
                      f"⚠ **{child}** requires **{parent}** to be imported. "
                      f"Please change '{parent}' from 'Skip' to 'Merge' or 'Replace'."
                  )

  if warnings:
      for w in warnings:
          st.warning(w)
      st.session_state["import_blocked"] = True
  else:
      st.session_state["import_blocked"] = False
  ```

- [ ] **Step 4: Add execute button with confirmation**

  ```python
  if st.button("🚀 Run Import", disabled=st.session_state.get("import_blocked", True)):
      if not st.session_state.get("import_blocked", True):
          st.session_state["run_import"] = True
  ```

  And add the execution block:

  ```python
  if st.session_state.get("run_import", False):
      result = st.session_state["analyze_result"]
      st.subheader("Result")

      with st.spinner("Importing data..."):
          session = get_session()
          try:
              import_result = execute_import(
                  current_session=session,
                  imported_db_path=result.imported_db_path,
                  strategies=st.session_state["strategies"],
                  id_maps={},
                  photos_extract_dir=result.extract_dir,
                  data_photos_dir=str(DATA_DIR / "photos"),
              )
          except Exception as e:
              st.error(f"Import failed: {e}")
              import_result = {}

          for category in DEPENDENCY_ORDER:
              if category in import_result:
                  r = import_result[category]
                  if r["status"] == "ok":
                      st.success(f"✅ {category}: {r['count']} records {r['action']}")
                  elif r["status"] == "skipped":
                      st.info(f"⏭️ {category}: skipped")

          if "photo_files" in import_result:
              pr = import_result["photo_files"]
              if pr["status"] == "ok":
                  st.success(f"✅ Photo files: {pr['count']} files {pr['action']}")

          session.close()
          st.session_state["run_import"] = False
  ```

  Note: this has a bug — `imported_db_path` from `AnalysisResult` points to the temp dir. By the time the user clicks "Run Import", the temp directory may have been cleaned up. We need to fix this.

- [ ] **Step 5: Fix temp dir persistence**

  The `analyze_zip` function creates a temp dir and returns its path. The UI stores the `AnalysisResult` in session state. But the temp dir from `mkdtemp` is cleaned up by `TemporaryDirectory` only if used as context manager. Since we switched to `mkdtemp`, it persists until manually cleaned. Good.

  But `analyze_zip` is called once on "Analyze" click and `mkdtemp` creates a new dir. The path in `result.tmp_path` stays valid. When "Run Import" is clicked, it uses this path. After import, we need to clean up.

  Add cleanup after import:

  ```python
  import shutil
  # After import
  if result.tmp_path:
      shutil.rmtree(result.tmp_path, ignore_errors=True)
  ```

- [ ] **Step 6: Run the app and verify full flow**

  Run: `streamlit run Wasserrechner.py`
  Expected:
  1. Navigate to Data Export → Download ZIP (works)
  2. Upload the same ZIP → Analyze → shows counts
  3. Select strategies → Run Import → success
  4. Data is merged into current DB

- [ ] **Step 7: Commit**

  ```bash
  git add pages/09_Datenverwaltung.py
  git commit -m "feat(import): add import execution UI with strategy selection"
  ```



### Task 7: Final integration & cleanup

**Files:**
- Modify: `utils/export_import.py`
- Modify: `pages/09_Datenverwaltung.py`

- [ ] **Step 1: Add confirmation dialog before executing import**

  Replace the `st.button("🚀 Run Import")` with a two-step confirmation:

  ```python
  if "confirm_import" not in st.session_state:
      st.session_state["confirm_import"] = False

  if st.button("🚀 Run Import", disabled=st.session_state.get("import_blocked", True)):
      st.session_state["confirm_import"] = True

  if st.session_state["confirm_import"]:
      st.warning("This will modify the database. Are you sure?")
      col1, col2 = st.columns(2)
      if col1.button("✅ Yes, run import"):
          st.session_state["run_import"] = True
          st.session_state["confirm_import"] = False
      if col2.button("❌ Cancel"):
          st.session_state["confirm_import"] = False
  ```

- [ ] **Step 2: Verify all tests pass**

  Run: `python -m pytest tests/test_export_import.py -v`
  Expected: All tests `PASSED`

  Run: `python -m pytest tests/ -v`
  Expected: All existing tests still pass (no regressions)

- [ ] **Step 3: Final commit**

  ```bash
  git add utils/export_import.py pages/09_Datenverwaltung.py tests/test_export_import.py
  git commit -m "feat(import): add confirmation dialog, finalize data export/import feature"
  ```



### Spec Coverage Check

| Spec requirement | Task |
|---|---|
| Export: ZIP of data/ directory (pool.db + photos) | Task 1, 2 |
| Import: ZIP upload → analyze | Task 3, 4 |
| Import: per-category strategy selection (Replace/Merge/Skip) | Task 6 |
| Import: ID remapping for FK dependencies | Task 5 |
| Import: photos file handling | Task 5 |
| Import: dependency warning (parent Skip + child not) | Task 6 |
| Import: partial import (per-category transaction) | Task 5 (per-category commit) |
| Navigation: Sidebar expander "Weitere" | Task 2 |
| Error handling: invalid ZIP, missing pool.db | Task 3 (analyze_zip) |
| Confirmation before import | Task 7 |
