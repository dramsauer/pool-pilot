import math


def temperature_factor(temp_c: float) -> float:
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


def calculate_lsi(
    ph: float,
    temp_c: float,
    hardness: float,
    alkalinity: float,
    cya: float = 0,
    tds: float = 500,
) -> float:
    tf = temperature_factor(temp_c)
    cf = calcium_factor(hardness)
    alk = carbonate_alkalinity(alkalinity, cya, ph)
    af = alkalinity_factor(alk)
    tds_corr = tds_correction(tds)
    return ph + tf + cf + af - 12.1 + tds_corr


def categorize_lsi(lsi: float) -> str:
    if lsi < -0.5:
        return "korrosiv"
    elif lsi <= 0.5:
        return "ausgeglichen"
    else:
        return "kalkausfällend"
