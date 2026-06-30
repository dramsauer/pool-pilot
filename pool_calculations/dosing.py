import math
from pool_calculations.models import PoolConfig, WaterTest, DosingRecommendation


def get_product_config(config: PoolConfig) -> dict:
    return {
        "ph_minus": {"name": "Summer Fun pH-Minus Granulat", "factor": 1.4, "unit": "g"},
        "ph_plus": {"name": "Summer Fun pH-Plus Granulat", "factor": 0.74, "unit": "g"},
        "chlorine_tabs": {"name": "Summer Fun Perfect Care Tabs 20g", "active_cl_per_tab": 18.0, "unit": "Tablette(n)"},
    }


def recommend_dosing(test: WaterTest, config: PoolConfig) -> list[DosingRecommendation]:
    products = get_product_config(config)
    volume_m3 = config.volume_liter / 1000
    recommendations = []

    if test.ph < config.ph_min:
        delta = config.ph_min - test.ph
        amount = delta * volume_m3 * products["ph_plus"]["factor"]
        amount = math.ceil(amount * 10) / 10
        recommendations.append(DosingRecommendation(
            product=products["ph_plus"]["name"],
            amount=amount,
            unit=products["ph_plus"]["unit"],
            reason=f"pH zu niedrig ({test.ph} -> Ziel {config.ph_min})",
        ))

    elif test.ph > config.ph_max:
        delta = test.ph - config.ph_max
        amount = delta * volume_m3 * products["ph_minus"]["factor"]
        amount = math.ceil(amount * 10) / 10
        recommendations.append(DosingRecommendation(
            product=products["ph_minus"]["name"],
            amount=amount,
            unit=products["ph_minus"]["unit"],
            reason=f"pH zu hoch ({test.ph} -> Ziel {config.ph_max})",
        ))

    if test.chlorine < config.chlorine_min:
        delta = config.chlorine_min - test.chlorine
        tabs_needed = math.ceil(delta * volume_m3 / products["chlorine_tabs"]["active_cl_per_tab"])
        recommendations.append(DosingRecommendation(
            product=products["chlorine_tabs"]["name"],
            amount=float(tabs_needed),
            unit=products["chlorine_tabs"]["unit"],
            reason=f"Chlor zu niedrig ({test.chlorine} -> Ziel {config.chlorine_min} mg/L)",
        ))

    return recommendations
