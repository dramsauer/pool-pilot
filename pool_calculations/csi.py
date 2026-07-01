import math


def temperature_factor_csi(temp_c: float) -> float:
    return -13.12 * math.log10(temp_c + 273) + 34.14


def calcium_factor(hardness_mgl: float) -> float:
    return math.log10(max(1, hardness_mgl)) - 0.4


def alkalinity_factor(alkalinity_mgl: float) -> float:
    return math.log10(max(1, alkalinity_mgl))


def cyanurate_alkalinity(cya: float, ph: float) -> float:
    if cya <= 0:
        return 0.0
    return cya * 0.38772 / (1 + 10 ** (6.83 - ph))


def carbonate_alkalinity(total_alk: float, cya: float, ph: float) -> float:
    ca = cyanurate_alkalinity(cya, ph)
    return max(0.1, total_alk - ca)


def tds_correction(tds: float) -> float:
    if tds <= 0:
        return 0.0
    return -0.1 * (tds - 500) / 1000


def calculate_csi(
    ph: float,
    temp_c: float,
    hardness: float,
    total_alk: float,
    cya: float = 0,
    tds: float = 500,
) -> float:
    carb_alk = carbonate_alkalinity(total_alk, cya, ph)
    tf = temperature_factor_csi(temp_c)
    cf = calcium_factor(hardness)
    af = alkalinity_factor(carb_alk)
    tds_corr = tds_correction(tds)
    return ph + tf + cf + af - 12.1 + tds_corr


def categorize_csi(csi: float) -> str:
    if csi < -0.5:
        return "stark korrosiv"
    elif csi < -0.3:
        return "korrosiv"
    elif csi <= 0.3:
        return "ausgeglichen"
    elif csi <= 0.5:
        return "kalkend"
    else:
        return "stark kalkend"


def get_csi_urgency(csi: float) -> str:
    if csi < -0.5 or csi > 0.5:
        return "hoch"
    elif csi < -0.3 or csi > 0.3:
        return "mittel"
    return "niedrig"


def _step_precipitate(ph, temp_c, hardness, alk, cya, tds, step):
    h = max(1, hardness - step)
    a = max(0.1, alk - 2 * step)
    return calculate_csi(ph, temp_c, h, a, cya, tds)


def calculate_ccpp(
    ph: float,
    temp_c: float,
    hardness: float,
    total_alk: float,
    cya: float = 0,
    tds: float = 500,
) -> float:
    csi = calculate_csi(ph, temp_c, hardness, total_alk, cya, tds)
    if csi <= 0.3:
        return 0.0
    h = hardness
    a = total_alk
    ccpp = 0.0
    step = 2.0
    max_steps = 500
    for _ in range(max_steps):
        if h < step or a < 2 * step:
            break
        h -= step
        a -= 2 * step
        ccpp += step
        csi_new = calculate_csi(ph, temp_c, h, a, cya, tds)
        if csi_new <= 0.3:
            break
    return round(ccpp, 1)
