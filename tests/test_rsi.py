from pool_calculations.rsi import calculate_saturation_ph, calculate_rsi, categorize_rsi


def test_calculate_saturation_ph():
    phs = calculate_saturation_ph(temp_c=25, hardness=200, alkalinity=100)
    assert round(phs, 2) == 7.69, f"pHs calculation off: {phs}"


def test_calculate_rsi():
    rsi = calculate_rsi(ph=7.4, temp_c=25, hardness=200, alkalinity=100)
    assert round(rsi, 2) == 7.97, f"RSI calculation off: {rsi}"


def test_categorize_rsi():
    assert categorize_rsi(5.5) == "stark kalkausfällend"
    assert categorize_rsi(6.5) == "leicht kalkausfällend"
    assert categorize_rsi(7.2) == "stabil"
    assert categorize_rsi(8.0) == "leicht korrosiv"
    assert categorize_rsi(9.0) == "stark korrosiv"
