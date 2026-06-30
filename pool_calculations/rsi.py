import math


def calculate_saturation_ph(temp_c: float, hardness: float, alkalinity: float, tds: float = 1000) -> float:
    a = (math.log10(tds) - 1) / 10
    b = -13.12 * math.log10(temp_c + 273) + 34.55
    c = math.log10(hardness) - 0.4
    d = math.log10(alkalinity)
    return (9.3 + a + b) - (c + d)


def calculate_rsi(ph: float, temp_c: float, hardness: float, alkalinity: float, tds: float = 1000) -> float:
    phs = calculate_saturation_ph(temp_c, hardness, alkalinity, tds)
    return 2 * phs - ph


def categorize_rsi(rsi: float) -> str:
    if rsi < 6.0:
        return "stark kalkausfällend"
    elif rsi < 7.0:
        return "leicht kalkausfällend"
    elif rsi < 7.5:
        return "stabil"
    elif rsi < 8.5:
        return "leicht korrosiv"
    else:
        return "stark korrosiv"
