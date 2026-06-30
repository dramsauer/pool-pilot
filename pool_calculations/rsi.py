import math


def calculate_saturation_ph(
    temp_c: float, hardness: float, alkalinity: float, tds: float = 1000
) -> float:
    a = (math.log10(tds) - 1) / 10
    b = -13.12 * math.log10(temp_c + 273) + 34.55
    c = math.log10(hardness) - 0.4
    d = math.log10(alkalinity)
    return (9.3 + a + b) - (c + d)


def calculate_rsi(
    ph: float, temp_c: float, hardness: float, alkalinity: float, tds: float = 1000
) -> float:
    phs = calculate_saturation_ph(temp_c, hardness, alkalinity, tds)
    return 2 * phs - ph


def categorize_rsi(rsi: float) -> str:
    """RSI: < 6.0 kalkend, 6.0–7.0 ausgeglichen, > 7.0 korrosiv."""
    if rsi < 6.0:
        return "kalkend"
    elif rsi <= 7.0:
        return "ausgeglichen"
    else:
        return "korrosiv"
