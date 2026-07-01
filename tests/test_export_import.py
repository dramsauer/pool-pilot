import zipfile
import io
from pathlib import Path
from utils.export_import import create_export_zip


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
