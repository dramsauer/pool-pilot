from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WaterTest:
    values: dict[str, float] = field(default_factory=dict)
    temperature_c: float = 25
    notes: str = ""

    @property
    def ph(self) -> float:
        return self.values.get("ph", 0.0)

    @property
    def chlorine(self) -> float:
        return self.values.get("chlorine", 0.0)

    @property
    def alkalinity(self) -> float:
        return self.values.get("alkalinity", 0.0)

    @property
    def hardness(self) -> float:
        return self.values.get("hardness", 0.0)

    @property
    def cya(self) -> float:
        return self.values.get("cya", 0.0)

    def get(self, name: str, default: float = 0.0) -> float:
        return self.values.get(name, default)


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
