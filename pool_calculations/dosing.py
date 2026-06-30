import math
from pool_calculations.models import WaterTest, DosingRecommendation
from database.models import Product, Pool


def recommend_dosing_from_db(test: WaterTest, pool: Pool, products: list[Product]) -> list[DosingRecommendation]:
    volume_m3 = pool.volume_liter / 1000
    recommendations = []

    ph_minus = next((p for p in products if p.typ == "ph_minus"), None)
    ph_plus = next((p for p in products if p.typ == "ph_plus"), None)
    chlorine_prod = next((p for p in products if p.typ == "chlorine"), None)

    if test.ph < pool.ph_min and ph_plus:
        delta = pool.ph_min - test.ph
        amount = delta * volume_m3 * ph_plus.dosage_factor
        amount = math.ceil(amount * 10) / 10
        recommendations.append(DosingRecommendation(
            product=ph_plus.name,
            amount=amount,
            unit=ph_plus.unit,
            reason=f"pH zu niedrig ({test.ph} \u2192 Ziel {pool.ph_min})",
            product_id=ph_plus.id,
            follow_up_days=ph_plus.interval_days,
        ))

    elif test.ph > pool.ph_max and ph_minus:
        delta = test.ph - pool.ph_max
        amount = delta * volume_m3 * ph_minus.dosage_factor
        amount = math.ceil(amount * 10) / 10
        recommendations.append(DosingRecommendation(
            product=ph_minus.name,
            amount=amount,
            unit=ph_minus.unit,
            reason=f"pH zu hoch ({test.ph} \u2192 Ziel {pool.ph_max})",
            product_id=ph_minus.id,
            follow_up_days=ph_minus.interval_days,
        ))

    if test.chlorine < pool.chlorine_min and chlorine_prod and chlorine_prod.active_chlorine_per_tab:
        delta = pool.chlorine_min - test.chlorine
        tabs_needed = math.ceil(delta * volume_m3 / chlorine_prod.active_chlorine_per_tab)
        recommendations.append(DosingRecommendation(
            product=chlorine_prod.name,
            amount=float(tabs_needed),
            unit=chlorine_prod.unit,
            reason=f"Chlor zu niedrig ({test.chlorine} \u2192 Ziel {pool.chlorine_min} mg/L)",
            product_id=chlorine_prod.id,
            follow_up_days=chlorine_prod.interval_days,
        ))

    return recommendations
