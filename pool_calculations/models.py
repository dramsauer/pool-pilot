from dataclasses import dataclass, field


@dataclass
class PoolConfig:
    name: str = "Lay-Z-Spa Ibiza"
    volume_liter: float = 1000
    pool_type: str = "chlorine"
    ph_min: float = 7.2
    ph_max: float = 7.6
    chlorine_min: float = 0.5
    chlorine_max: float = 3.0
    alkalinity_min: float = 80
    alkalinity_max: float = 120
    hardness_min: float = 150
    hardness_max: float = 250
    temperature_default: float = 35


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


@dataclass
class WaterBalanceResult:
    lsi: float
    rsi: float
    lsi_category: str
    rsi_category: str
    is_balanced: bool
    dosing: list[DosingRecommendation] = field(default_factory=list)
