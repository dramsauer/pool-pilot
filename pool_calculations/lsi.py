import math


def temperature_factor(temp_c: float) -> float:
    return -13.12 * math.log10(temp_c + 273) + 34.14


def calcium_factor(hardness_mgl: float) -> float:
    return math.log10(hardness_mgl) - 0.4


def alkalinity_factor(alkalinity_mgl: float) -> float:
    return math.log10(alkalinity_mgl)


def calculate_lsi(ph: float, temp_c: float, hardness: float, alkalinity: float) -> float:
    tf = temperature_factor(temp_c)
    cf = calcium_factor(hardness)
    af = alkalinity_factor(alkalinity)
    return ph + tf + cf + af - 12.1


def categorize_lsi(lsi: float) -> str:
    if lsi < -0.5:
        return "korrosiv"
    elif lsi <= 0.5:
        return "ausgeglichen"
    else:
        return "kalkausfällend"
