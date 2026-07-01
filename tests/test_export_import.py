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


def test_create_export_zip_empty_data_dir(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    zip_bytes = create_export_zip(data_dir)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        assert zf.namelist() == []


def test_create_export_zip_missing_photos_dir(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_file = data_dir / "pool.db"
    db_file.write_text("fake-db-content")

    zip_bytes = create_export_zip(data_dir)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        assert names == ["pool.db"]
        assert zf.read("pool.db") == b"fake-db-content"


def test_create_export_zip_multiple_photos(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_file = data_dir / "pool.db"
    db_file.write_text("fake-db-content")
    photos_dir = data_dir / "photos"
    photos_dir.mkdir()
    for i in range(3):
        (photos_dir / f"img{i}.jpg").write_text(f"photo-{i}")

    zip_bytes = create_export_zip(data_dir)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        assert "pool.db" in names
        assert "photos/img0.jpg" in names
        assert "photos/img1.jpg" in names
        assert "photos/img2.jpg" in names
        assert zf.read("photos/img0.jpg") == b"photo-0"


def test_create_export_zip_str_path(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_file = data_dir / "pool.db"
    db_file.write_text("fake-db-content")
    photos_dir = data_dir / "photos"
    photos_dir.mkdir()
    (photos_dir / "test.jpg").write_text("fake-photo-content")

    zip_bytes = create_export_zip(str(data_dir))
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        assert "pool.db" in names
        assert "photos/test.jpg" in names


def test_create_export_zip_photo_content_readback(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_file = data_dir / "pool.db"
    db_file.write_text("db-content")
    photos_dir = data_dir / "photos"
    photos_dir.mkdir()
    (photos_dir / "a.jpg").write_text("photo-content-a")
    (photos_dir / "b.jpg").write_text("photo-content-b")

    zip_bytes = create_export_zip(data_dir)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        assert zf.read("pool.db") == b"db-content"
        assert zf.read("photos/a.jpg") == b"photo-content-a"
        assert zf.read("photos/b.jpg") == b"photo-content-b"
