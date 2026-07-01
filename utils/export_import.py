import io
import zipfile
from pathlib import Path
from typing import Union


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
