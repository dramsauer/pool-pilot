from database.db import get_engine, init_db, get_session
from database.models import Product
from database.repository import save_product, save_pool
from pool_calculations.dosing import recommend_dosing_from_db
from pool_calculations.models import WaterTest


def make_session():
    engine = get_engine(":memory:")
    init_db(engine)
    return get_session(engine)


def test_recommend_ph_plus_from_db():
    session = make_session()
    pool = save_pool(session, name="Test", volume_liter=1000)
    save_product(
        session, name="pH-Plus Granulat", typ="ph_plus", dosage_factor=0.74, unit="g"
    )
    products = session.query(Product).all()

    test = WaterTest(
        ph=6.8, chlorine=2.0, alkalinity=100, hardness=200, temperature_c=35
    )
    result = recommend_dosing_from_db(test, pool, products)
    assert len(result) == 1
    assert "pH-Plus" in result[0].product
    assert result[0].amount > 0
    session.close()


def test_recommend_chlorine_from_db():
    session = make_session()
    pool = save_pool(session, name="Test", volume_liter=1000)
    save_product(
        session,
        name="Chlor Tabs",
        typ="chlorine",
        unit="Tablette(n)",
        active_chlorine_per_tab=18.0,
    )
    products = session.query(Product).all()

    test = WaterTest(
        ph=7.4, chlorine=0.0, alkalinity=100, hardness=200, temperature_c=35
    )
    result = recommend_dosing_from_db(test, pool, products)
    assert len(result) == 1
    assert result[0].amount >= 1
    session.close()


def test_no_recommendation_needed_from_db():
    session = make_session()
    pool = save_pool(session, name="Test", volume_liter=1000)
    save_product(session, name="pH-Plus", typ="ph_plus", dosage_factor=0.74, unit="g")
    save_product(session, name="pH-Minus", typ="ph_minus", dosage_factor=1.4, unit="g")
    save_product(
        session,
        name="Chlor Tabs",
        typ="chlorine",
        unit="Tablette(n)",
        active_chlorine_per_tab=18.0,
    )
    products = session.query(Product).all()

    test = WaterTest(
        ph=7.4, chlorine=1.5, alkalinity=100, hardness=200, temperature_c=35
    )
    result = recommend_dosing_from_db(test, pool, products)
    assert len(result) == 0
    session.close()
