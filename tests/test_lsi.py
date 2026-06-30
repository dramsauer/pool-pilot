from pool_calculations.lsi import (
    temperature_factor,
    calcium_factor,
    alkalinity_factor,
    calculate_lsi,
    categorize_lsi,
)


def test_temperature_factor():
    result = temperature_factor(25)
    assert round(result, 2) == 1.68, f"Expected ~1.68, got {result}"


def test_calcium_factor():
    result = calcium_factor(200)
    assert round(result, 2) == 1.90, f"Expected ~1.90, got {result}"


def test_alkalinity_factor():
    result = alkalinity_factor(100)
    assert round(result, 2) == 2.00, f"Expected ~2.00, got {result}"


def test_calculate_lsi_balanced():
    result = calculate_lsi(ph=7.4, temp_c=25, hardness=200, alkalinity=100)
    assert round(result, 2) == 0.88, f"LSI calculation off: {result}"


def test_categorize_lsi():
    assert categorize_lsi(-1.0) == "korrosiv"
    assert categorize_lsi(0.0) == "ausgeglichen"
    assert categorize_lsi(0.3) == "ausgeglichen"
    assert categorize_lsi(0.6) == "kalkausfällend"
