import io
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union
from database.db import get_engine, get_session
from database.models import (
    Instrument, Trinkwasser, Product, TaskTemplate, PoolTaskDefault,
    Pool, Reading, Photo, MaintenanceTask,
    Parameter, ReadingValue, InstrumentCapability,
)


def create_export_zip(data_dir: Union[Path, str]) -> bytes:
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


TABLE_CATEGORIES = {
    "parameters": {"model": Parameter, "label": "Parameters"},
    "instruments": {"model": Instrument, "label": "Instruments"},
    "instrument_capabilities": {"model": InstrumentCapability, "label": "Instrument Capabilities"},
    "trinkwasser": {"model": Trinkwasser, "label": "Tap Water Sources"},
    "products": {"model": Product, "label": "Products"},
    "task_templates": {"model": TaskTemplate, "label": "Task Templates"},
    "pools": {"model": Pool, "label": "Pools"},
    "pool_task_defaults": {"model": PoolTaskDefault, "label": "Pool Task Defaults"},
    "readings": {"model": Reading, "label": "Measurements"},
    "reading_values": {"model": ReadingValue, "label": "Measurement Values"},
    "photos": {"model": Photo, "label": "Photos"},
    "maintenance_tasks": {"model": MaintenanceTask, "label": "Tasks"},
}

DEPENDENCY_ORDER = [
    "parameters",
    "instruments", "instrument_capabilities",
    "trinkwasser", "products", "task_templates",
    "pools",
    "pool_task_defaults",
    "readings", "reading_values",
    "photos",
    "maintenance_tasks",
]

USER_CATEGORIES = [
    ("pools", "Pools"),
    ("products", "Products"),
    ("instruments", "Instruments"),
    ("trinkwasser", "Tap Water Sources"),
    ("task_templates", "Task Templates"),
    ("readings", "Measurements"),
    ("maintenance_tasks", "Tasks"),
]

CATEGORY_MERGE_KEYS = {
    "parameters": ["name"],
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
    "instrument_capabilities": ["parameters", "instruments"],
    "pool_task_defaults": ["pools", "task_templates"],
    "readings": ["pools"],
    "reading_values": ["readings", "parameters"],
    "photos": ["readings"],
    "maintenance_tasks": ["pools", "readings", "products"],
}

PHOTO_AUTO_PARENT = "readings"


@dataclass
class AnalysisResult:
    valid: bool
    error: str
    counts: dict
    photo_count: int
    tmp_path: str = ""
    imported_db_path: str = ""
    extract_dir: str = ""


def analyze_zip(zip_bytes: bytes) -> AnalysisResult:
    tmp = tempfile.mkdtemp()
    try:
        extract_dir = Path(tmp) / "extracted"
        zip_path = Path(tmp) / "import.zip"
        zip_path.write_bytes(zip_bytes)
        with zipfile.ZipFile(str(zip_path), "r") as zf:
            for member in zf.namelist():
                target = (extract_dir / member).resolve()
                if not str(target).startswith(str(extract_dir.resolve())):
                    raise ValueError("Path traversal detected in ZIP")
            zf.extractall(str(extract_dir))
        db_file = extract_dir / "pool.db"
        if not db_file.exists():
            shutil.rmtree(tmp)
            return AnalysisResult(valid=False, error="ZIP enthält keine pool.db", counts={}, photo_count=0)
        engine = get_engine(str(db_file))
        session = get_session(engine)
        counts = {}
        for key, info in TABLE_CATEGORIES.items():
            counts[key] = session.query(info["model"]).count()
        session.close()
        photos_dir = extract_dir / "photos"
        photo_count = len([f for f in photos_dir.iterdir() if f.is_file()]) if photos_dir.exists() else 0
        return AnalysisResult(
            valid=True, error="", counts=counts, photo_count=photo_count,
            tmp_path=tmp, imported_db_path=str(db_file), extract_dir=str(extract_dir),
        )
    except Exception as e:
        shutil.rmtree(tmp, ignore_errors=True)
        return AnalysisResult(valid=False, error=str(e), counts={}, photo_count=0)


_FK_MAP = {
    ("instrument_capabilities", "parameters"): "parameter_id",
    ("instrument_capabilities", "instruments"): "instrument_id",
    ("pool_task_defaults", "pools"): "pool_id",
    ("pool_task_defaults", "task_templates"): "template_id",
    ("readings", "pools"): "pool_id",
    ("reading_values", "readings"): "reading_id",
    ("reading_values", "parameters"): "parameter_id",
    ("photos", "readings"): "reading_id",
    ("maintenance_tasks", "pools"): "pool_id",
    ("maintenance_tasks", "readings"): "reading_id",
    ("maintenance_tasks", "products"): "product_id",
}


def _get_row_dict(row) -> dict:
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def _remap_fk(row_dict: dict, id_maps: dict, category: str) -> dict:
    deps = PARENT_DEPENDENCIES.get(category, [])
    for dep in deps:
        fk_col = _FK_MAP.get((category, dep), f"{dep.rstrip('s')}_id")
        if fk_col in row_dict and row_dict[fk_col] is not None:
            if dep in id_maps and row_dict[fk_col] in id_maps[dep]:
                row_dict[fk_col] = id_maps[dep][row_dict[fk_col]]
    return row_dict


def _remap_merge_filters(filters: dict, id_maps: dict, category: str) -> dict:
    deps = PARENT_DEPENDENCIES.get(category, [])
    for dep in deps:
        fk_col = _FK_MAP.get((category, dep), f"{dep.rstrip('s')}_id")
        if fk_col in filters and filters[fk_col] is not None:
            if dep in id_maps and filters[fk_col] in id_maps[dep]:
                filters[fk_col] = id_maps[dep][filters[fk_col]]
    return filters


def execute_import(
    current_session,
    imported_db_path: str,
    strategies: dict[str, str],
    id_maps: Optional[dict[str, dict[int, int]]] = None,
    photos_extract_dir: str = "",
    data_photos_dir: str = "",
) -> dict:
    if id_maps is None:
        id_maps = {}

    imported_engine = get_engine(imported_db_path)
    imported_session = get_session(imported_engine)

    try:
        if "photos" not in strategies and PHOTO_AUTO_PARENT in strategies:
            strategies["photos"] = strategies[PHOTO_AUTO_PARENT]

        pool_strat = strategies.get("pools", "skip")
        template_strat = strategies.get("task_templates", "skip")
        if pool_strat != "skip" and template_strat != "skip":
            strategies.setdefault("pool_task_defaults", "replace")

        result = {}

        for category in DEPENDENCY_ORDER:
            strategy = strategies.get(category, "skip")
            if strategy == "skip":
                result[category] = {"status": "skipped", "count": 0, "action": "skipped"}
                continue

            model_cls = TABLE_CATEGORIES[category]["model"]
            imported_records = list(imported_session.query(model_cls).all())

            if strategy == "replace":
                current_session.query(model_cls).delete()
                current_session.flush()

                count = 0
                for rec in imported_records:
                    rd = _get_row_dict(rec)
                    imported_id = rd.pop("id")
                    rd.pop("created_at", None)
                    rd.pop("completed_at", None)
                    rd.pop("executed_at", None)
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
                    rd.pop("completed_at", None)
                    rd.pop("executed_at", None)
                    rd = _remap_fk(rd, id_maps, category)

                    filters = {}
                    for k in merge_keys:
                        if k in rd and rd[k] is not None:
                            filters[k] = rd[k]
                    filters = _remap_merge_filters(filters, id_maps, category)

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

        if strategies.get("photos", "skip") != "skip" and photos_extract_dir and data_photos_dir:
            photos_result = _handle_photo_files(
                photos_extract_dir, data_photos_dir,
                strategy=strategies.get("photos", "merge"),
            )
            result["photo_files"] = photos_result

        result["_id_maps"] = id_maps
        return result
    finally:
        imported_session.close()
        imported_engine.dispose()


def _handle_photo_files(src_dir: str, dst_dir: str, strategy: str) -> dict:
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
                continue
            shutil.copy2(str(f), str(target))
            count += 1

    return {"status": "ok", "count": count, "action": strategy}
