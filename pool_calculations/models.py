from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WaterTest:
    ph: float
    chlorine: float
    alkalinity: float
    hardness: float
    temperature_c: float
    notes: str = ""


@dataclass
class DosingRecommendation:
    product: str
    amount: float
    unit: str
    reason: str
    product_id: int | None = None
    follow_up_days: int = 0


@dataclass
class WaterBalanceResult:
    lsi: float
    rsi: float
    lsi_category: str
    rsi_category: str
    is_balanced: bool
    dosing: list[DosingRecommendation] = field(default_factory=list)
