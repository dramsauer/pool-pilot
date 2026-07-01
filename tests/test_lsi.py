from pool_calculations.lsi import (
    temperature_factor,
    calcium_factor,
    alkalinity_factor,
    calculate_lsi,
    categorize_lsi,
    carbonate_alkalinity,
    tds_correction,
)


def test_temperature_factor():
    result = temperature_factor(25)
    assert round(result, 2) == 1.68


def test_calcium_factor():
    result = calcium_factor(200)
    assert round(result, 2) == 1.90


def test_alkalinity_factor():
    result = alkalinity_factor(100)
    assert round(result, 2) == 2.00


def test_calculate_lsi_balanced():
    result = calculate_lsi(ph=7.4, temp_c=25, hardness=200, alkalinity=100)
    assert round(result, 2) == 0.88


def test_categorize_lsi():
    assert categorize_lsi(-1.0) == "korrosiv"
    assert categorize_lsi(0.0) == "ausgeglichen"
    assert categorize_lsi(0.3) == "ausgeglichen"
    assert categorize_lsi(0.6) == "kalkausfällend"


def test_lsi_with_cya():
    without = calculate_lsi(ph=7.4, temp_c=25, hardness=200, alkalinity=100)
    with_cya = calculate_lsi(
        ph=7.4, temp_c=25, hardness=200, alkalinity=100, cya=50
    )
    assert with_cya < without


def test_lsi_with_tds():
    result = calculate_lsi(
        ph=7.4, temp_c=25, hardness=200, alkalinity=100, tds=3000
    )
    assert result < 0.88


def test_carbonate_alkalinity():
    result = carbonate_alkalinity(100, 50, 7.4)
    assert 80 < result < 90


def test_tds_correction():
    assert tds_correction(500) == 0.0
    assert tds_correction(3000) < 0
