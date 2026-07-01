import io
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Union
from database.db import get_engine, get_session
from database.models import (
    Instrument, Trinkwasser, Product, TaskTemplate, PoolTaskDefault,
    Pool, Reading, Photo, MaintenanceTask,
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
        shutil.unpack_archive(str(zip_path), str(extract_dir), "zip")
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
