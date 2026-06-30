from pool_calculations.dosing import recommend_dosing
from pool_calculations.models import PoolConfig, WaterTest


def test_recommend_ph_plus():
    config = PoolConfig()
    test = WaterTest(ph=6.8, chlorine=2.0, alkalinity=100, hardness=200, temperature_c=35)
    result = recommend_dosing(test, config)
    assert len(result) == 1
    assert "pH-Plus" in result[0].product
    assert result[0].amount > 0


def test_recommend_ph_minus():
    config = PoolConfig()
    test = WaterTest(ph=8.0, chlorine=2.0, alkalinity=100, hardness=200, temperature_c=35)
    result = recommend_dosing(test, config)
    assert len(result) == 1
    assert "pH-Minus" in result[0].product
    assert result[0].amount > 0


def test_recommend_chlorine():
    config = PoolConfig()
    test = WaterTest(ph=7.4, chlorine=0.0, alkalinity=100, hardness=200, temperature_c=35)
    result = recommend_dosing(test, config)
    assert len(result) == 1
    assert "Perfect Care" in result[0].product
    assert result[0].amount >= 1


def test_no_recommendation_needed():
    config = PoolConfig()
    test = WaterTest(ph=7.4, chlorine=1.5, alkalinity=100, hardness=200, temperature_c=35)
    result = recommend_dosing(test, config)
    assert len(result) == 0


def test_chlorine_and_ph():
    config = PoolConfig()
    test = WaterTest(ph=6.8, chlorine=0.0, alkalinity=100, hardness=200, temperature_c=35)
    result = recommend_dosing(test, config)
    assert len(result) == 2
