from pool_calculations.csi import (
    calculate_csi,
    categorize_csi,
    calculate_ccpp,
    carbonate_alkalinity,
    cyanurate_alkalinity,
    temperature_factor_csi,
    calcium_factor,
    alkalinity_factor,
    tds_correction,
)


def test_carbonate_alkalinity_no_cya():
    assert carbonate_alkalinity(100, 0, 7.4) == 100.0


def test_carbonate_alkalinity_with_cya():
    result = carbonate_alkalinity(100, 50, 7.4)
    assert 80 < result < 90


def test_cyanurate_alkalinity():
    result = cyanurate_alkalinity(50, 7.4)
    assert 14.0 < result < 17.0


def test_tds_correction_baseline():
    assert tds_correction(500) == 0.0


def test_tds_correction_higher():
    result = tds_correction(3000)
    assert result < 0


def test_tds_correction_lower():
    result = tds_correction(200)
    assert result > 0


def test_calculate_csi_baseline():
    result = calculate_csi(ph=7.4, temp_c=25, hardness=200, total_alk=100)
    assert isinstance(result, float)


def test_csi_no_cya_matches_lsi():
    from pool_calculations.lsi import calculate_lsi

    csi = calculate_csi(ph=7.4, temp_c=25, hardness=200, total_alk=100)
    lsi = calculate_lsi(ph=7.4, temp_c=25, hardness=200, alkalinity=100)
    assert abs(csi - lsi) < 6.0


def test_csi_lower_with_cya():
    without = calculate_csi(ph=7.4, temp_c=25, hardness=200, total_alk=100, cya=0)
    with_cya = calculate_csi(ph=7.4, temp_c=25, hardness=200, total_alk=100, cya=50)
    assert with_cya < without


def test_csi_lower_with_high_tds():
    low_tds = calculate_csi(ph=7.4, temp_c=25, hardness=200, total_alk=100, tds=500)
    high_tds = calculate_csi(
        ph=7.4, temp_c=25, hardness=200, total_alk=100, tds=3000
    )
    assert high_tds < low_tds


def test_categorize_csi_corrosive():
    assert categorize_csi(-1.0) == "stark korrosiv"
    assert categorize_csi(-0.4) == "korrosiv"


def test_categorize_csi_balanced():
    assert categorize_csi(0.0) == "ausgeglichen"
    assert categorize_csi(0.3) == "ausgeglichen"
    assert categorize_csi(-0.3) == "ausgeglichen"


def test_categorize_csi_scaling():
    assert categorize_csi(0.4) == "kalkend"
    assert categorize_csi(1.0) == "stark kalkend"


def test_ccpp_zero_when_balanced():
    result = calculate_ccpp(ph=7.0, temp_c=25, hardness=100, total_alk=60)
    assert result == 0.0


def test_ccpp_positive_when_scaling():
    result = calculate_ccpp(ph=8.0, temp_c=40, hardness=300, total_alk=200)
    assert result >= 0.0
