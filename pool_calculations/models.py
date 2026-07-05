from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WaterTest:
    ph: float
    chlorine: float
    alkalinity: float
    hardness: float
    temperature_c: float
    cya: float = 0
    notes: str = ""


@dataclass
class DosingRecommendation:
    product: str
    amount: float
    unit: str
    reason: str
    product_id: int | None = None
    follow_up_days: int = 0
    priority: int = 0
    instruction: str = ""
    wait_minutes: int = 30


@dataclass
class WaterBalanceResult:
    lsi: float
    rsi: float
    lsi_category: str
    rsi_category: str
    csi: float = 0.0
    csi_category: str = ""
    ccpp: float = 0.0
    is_balanced: bool = False
    consensus: str = ""
    consensus_detail: str = ""
    primary_driver: str = ""
    dosing: list[DosingRecommendation] = field(default_factory=list)
