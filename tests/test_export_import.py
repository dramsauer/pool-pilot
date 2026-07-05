import zipfile
import io
import shutil
from pathlib import Path
from sqlalchemy import create_engine
from database.db import get_engine, get_session
from database.models import Base, Pool, Product, Reading
from utils.export_import import analyze_zip, AnalysisResult, create_export_zip, execute_import


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
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "pool.db"
    make_test_db(db_path, [{"name": "Pool1", "volume_liter": 1000}], [{"name": "Prod1", "typ": "chlorine", "dosage_factor": 10}])

    zip_bytes = create_export_zip(data_dir)

    result = analyze_zip(zip_bytes)
    assert isinstance(result, AnalysisResult)
    assert result.valid
    assert result.counts["pools"] == 1
    assert result.counts["products"] == 1
    assert result.counts["readings"] == 0
    assert result.photo_count == 0

    shutil.rmtree(result.tmp_path, ignore_errors=True)


def test_execute_import_replace_pools(tmp_path):
    current_db = tmp_path / "current.db"
    current_engine = get_engine(str(current_db))
    Base.metadata.create_all(current_engine)
    s = get_session(current_engine)
    s.add(Pool(name="OldPool", volume_liter=500))
    s.commit()
    s.close()

    imported_db = tmp_path / "imported.db"
    imported_engine = get_engine(str(imported_db))
    Base.metadata.create_all(imported_engine)
    s = get_session(imported_engine)
    s.add(Pool(name="NewPool", volume_liter=1000))
    s.commit()
    s.close()

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

    s = get_session(current_engine)
    pools = s.query(Pool).all()
    assert len(pools) == 1
    assert pools[0].name == "NewPool"
    s.close()


def test_execute_import_merge_pools(tmp_path):
    current_db = tmp_path / "current.db"
    current_engine = get_engine(str(current_db))
    Base.metadata.create_all(current_engine)
    s = get_session(current_engine)
    s.add(Pool(name="ExistingPool", volume_liter=500))
    s.commit()
    s.close()

    imported_db = tmp_path / "imported.db"
    imported_engine = get_engine(str(imported_db))
    Base.metadata.create_all(imported_engine)
    s = get_session(imported_engine)
    s.add(Pool(name="ExistingPool", volume_liter=500))
    s.add(Pool(name="NewPool", volume_liter=1000))
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
    assert result["pools"]["count"] == 1
    assert result["pools"]["action"] == "merged"

    s = get_session(current_engine)
    pools = s.query(Pool).all()
    assert len(pools) == 2
    names = {p.name for p in pools}
    assert names == {"ExistingPool", "NewPool"}
    s.close()


def test_execute_import_skip_pools(tmp_path):
    current_db = tmp_path / "current.db"
    current_engine = get_engine(str(current_db))
    Base.metadata.create_all(current_engine)
    s = get_session(current_engine)
    s.add(Pool(name="ExistingPool", volume_liter=500))
    s.commit()
    s.close()

    imported_db = tmp_path / "imported.db"
    imported_engine = get_engine(str(imported_db))
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


def test_execute_import_remaps_readings_fk(tmp_path):
    from datetime import datetime

    current_db = tmp_path / "current.db"
    current_engine = get_engine(str(current_db))
    Base.metadata.create_all(current_engine)
    s = get_session(current_engine)
    s.add(Pool(name="OldPool", volume_liter=500))
    s.commit()
    s.close()

    imported_db = tmp_path / "imported.db"
    imported_engine = get_engine(str(imported_db))
    Base.metadata.create_all(imported_engine)
    s = get_session(imported_engine)
    p = Pool(name="NewPool", volume_liter=1000)
    s.add(p)
    s.flush()
    s.add(Reading(
        pool_id=p.id, timestamp=datetime(2026, 6, 1, 12, 0, 0), temperature_c=30,
    ))
    s.commit()
    s.close()

    current_sesh = get_session(current_engine)

    result_pools = execute_import(
        current_session=current_sesh,
        imported_db_path=str(imported_db),
        strategies={"pools": "replace"},
        id_maps={},
    )

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
    new_pool = s.query(Pool).first()
    assert readings[0].pool_id == new_pool.id
    s.close()


def test_execute_import_merge_preserves_timestamp(tmp_path):
    from datetime import datetime

    current_db = tmp_path / "current.db"
    current_engine = create_engine(f"sqlite:///{current_db}")
    Base.metadata.create_all(current_engine)
    s = get_session(current_engine)
    s.add(Pool(name="TestPool", volume_liter=1000))
    s.commit()
    s.close()

    imported_db = tmp_path / "imported.db"
    imported_engine = create_engine(f"sqlite:///{imported_db}")
    Base.metadata.create_all(imported_engine)
    s = get_session(imported_engine)
    p = Pool(name="TestPool", volume_liter=1000)
    s.add(p)
    s.flush()
    ts = datetime(2026, 7, 1, 10, 30, 0)
    s.add(Reading(
        pool_id=p.id, timestamp=ts, temperature_c=30,
    ))
    s.commit()
    s.close()

    current_sesh = get_session(current_engine)

    r1 = execute_import(current_session=current_sesh, imported_db_path=str(imported_db), strategies={"pools": "merge"}, id_maps={})
    r2 = execute_import(current_session=current_sesh, imported_db_path=str(imported_db), strategies={"readings": "merge"}, id_maps=r1.get("_id_maps", {}))

    current_sesh.close()

    s = get_session(current_engine)
    readings = s.query(Reading).all()
    assert len(readings) == 1
    assert readings[0].timestamp == ts
    s.close()
