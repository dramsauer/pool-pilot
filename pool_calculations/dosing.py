import math
from pool_calculations.models import WaterTest, DosingRecommendation
from database.models import Product, Pool


_INSTRUCTIONS = {
    "ph_minus": (
        "In 5 L Wasser auflösen und langsam am Skimmer oder "
        "an der Stelle mit dem stärksten Wasserzufluss zugeben. "
        "Filter mindestens 30 Minuten laufen lassen."
    ),
    "ph_plus": (
        "In 5 L Wasser auflösen und langsam am Skimmer oder "
        "an der Stelle mit dem stärksten Wasserzufluss zugeben. "
        "Filter mindestens 30 Minuten laufen lassen."
    ),
    "chlorine": (
        "Tablette in den Skimmer oder Dosierschwimmer geben. "
        "Nicht direkt ins Becken werfen."
    ),
    "alk_plus": (
        "Natriumhydrogencarbonat (Natron) in einem Eimer Wasser auflösen "
        "und langsam im Becken verteilen. pH nach 2 Stunden prüfen."
    ),
    "alk_minus": (
        "pH-Minus Produkt verwenden bei laufender Pumpe. "
        "Alkalinität senkt sich indirekt über pH-Senkung."
    ),
    "hardness_plus": (
        "Calciumchlorid in einem Eimer Wasser auflösen "
        "und langsam am Skimmer zugeben."
    ),
    "hardness_minus": (
        "Calciumhärte kann nur durch Teilwasserwechsel (Verdünnung) "
        "reduziert werden."
    ),
}


def _instruction(typ: str) -> str:
    return _INSTRUCTIONS.get(typ, "")


def recommend_dosing_from_db(
    test: WaterTest, pool: Pool, products: list[Product]
) -> list[DosingRecommendation]:
    volume_m3 = pool.volume_liter / 1000
    recommendations = []

    ph_minus = next((p for p in products if p.typ == "ph_minus"), None)
    ph_plus = next((p for p in products if p.typ == "ph_plus"), None)
    chlorine_prod = next((p for p in products if p.typ == "chlorine"), None)

    # --- Priority 1: Alkalinity (buffer first) ---
    if test.alkalinity < pool.alkalinity_min:
        delta = pool.alkalinity_min - test.alkalinity
        amount = math.ceil(delta * volume_m3 * 1.5 * 10) / 10
        recommendations.append(
            DosingRecommendation(
                product="Alkalinität erhöhen (Natron)",
                amount=amount,
                unit="g",
                reason=(
                    f"Alkalinität {test.alkalinity} mg/L zu niedrig "
                    f"(Ziel {pool.alkalinity_min}–{pool.alkalinity_max})"
                ),
                priority=1,
                instruction=_instruction("alk_plus"),
                wait_minutes=120,
            )
        )
    elif test.alkalinity > pool.alkalinity_max:
        delta = test.alkalinity - pool.alkalinity_max
        amount = math.ceil(delta * volume_m3 * 0.7 * 10) / 10
        advice = DosingRecommendation(
            product="Alkalinität senken",
            amount=amount,
            unit="g",
            reason=(
                f"Alkalinität {test.alkalinity} mg/L zu hoch "
                f"(Ziel {pool.alkalinity_min}–{pool.alkalinity_max})"
            ),
            priority=1,
            instruction=_instruction("alk_minus"),
            wait_minutes=60,
        )
        if ph_minus:
            advice.product = ph_minus.name
            advice.product_id = ph_minus.id
            advice.amount = math.ceil(delta * volume_m3 * ph_minus.dosage_factor * 0.3 * 10) / 10
        recommendations.append(advice)

    # --- Priority 2: pH ---
    if test.ph < pool.ph_min and ph_plus:
        delta = pool.ph_min - test.ph
        amount = math.ceil(delta * volume_m3 * ph_plus.dosage_factor * 10) / 10
        recommendations.append(
            DosingRecommendation(
                product=ph_plus.name,
                amount=amount,
                unit=ph_plus.unit,
                reason=f"pH zu niedrig ({test.ph} → Ziel {pool.ph_min})",
                product_id=ph_plus.id,
                follow_up_days=ph_plus.interval_days,
                priority=2,
                instruction=_instruction("ph_plus"),
                wait_minutes=30,
            )
        )

    elif test.ph > pool.ph_max and ph_minus:
        delta = test.ph - pool.ph_max
        amount = math.ceil(delta * volume_m3 * ph_minus.dosage_factor * 10) / 10
        recommendations.append(
            DosingRecommendation(
                product=ph_minus.name,
                amount=amount,
                unit=ph_minus.unit,
                reason=f"pH zu hoch ({test.ph} → Ziel {pool.ph_max})",
                product_id=ph_minus.id,
                follow_up_days=ph_minus.interval_days,
                priority=2,
                instruction=_instruction("ph_minus"),
                wait_minutes=30,
            )
        )

    # --- Priority 3: Calcium Hardness ---
    if test.hardness < pool.hardness_min:
        delta = pool.hardness_min - test.hardness
        amount = math.ceil(delta * volume_m3 * 2.5 * 10) / 10
        recommendations.append(
            DosingRecommendation(
                product="Calciumhärte erhöhen (Calciumchlorid)",
                amount=amount,
                unit="g",
                reason=(
                    f"Härte {test.hardness} mg/L zu niedrig "
                    f"(Ziel {pool.hardness_min}–{pool.hardness_max})"
                ),
                priority=3,
                instruction=_instruction("hardness_plus"),
                wait_minutes=60,
            )
        )
    elif test.hardness > pool.hardness_max:
        recommendations.append(
            DosingRecommendation(
                product="Calciumhärte senken",
                amount=0,
                unit="",
                reason=(
                    f"Härte {test.hardness} mg/L zu hoch "
                    f"(Ziel {pool.hardness_min}–{pool.hardness_max}). "
                    "Teilwasserwechsel empfohlen."
                ),
                priority=3,
                instruction=_instruction("hardness_minus"),
                wait_minutes=0,
            )
        )

    # --- Priority 4: Chlorine ---
    if (
        test.chlorine < pool.chlorine_min
        and chlorine_prod
        and chlorine_prod.active_chlorine_per_tab
    ):
        delta = pool.chlorine_min - test.chlorine
        tabs_needed = math.ceil(
            delta * volume_m3 / chlorine_prod.active_chlorine_per_tab
        )
        recommendations.append(
            DosingRecommendation(
                product=chlorine_prod.name,
                amount=float(tabs_needed),
                unit=chlorine_prod.unit,
                reason=(
                    f"Chlor zu niedrig ({test.chlorine} "
                    f"→ Ziel {pool.chlorine_min} mg/L)"
                ),
                product_id=chlorine_prod.id,
                follow_up_days=chlorine_prod.interval_days,
                priority=4,
                instruction=_instruction("chlorine"),
                wait_minutes=30,
            )
        )

    recommendations.sort(key=lambda r: r.priority)
    return recommendations
