try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

from pathlib import Path
from typing import Optional
from pool_calculations.models import PoolConfig


def load_config(path: Optional[str] = None) -> PoolConfig:
    if path is None:
        path = Path(__file__).parent.parent / "config.toml"
    with open(path, "rb") as f:
        data = tomllib.load(f)

    pool = data["pool"]
    targets = data["targets"]

    return PoolConfig(
        name=pool["name"],
        volume_liter=pool["volume_liter"],
        pool_type=pool["pool_type"],
        ph_min=targets["ph_min"],
        ph_max=targets["ph_max"],
        chlorine_min=targets["chlorine_min"],
        chlorine_max=targets["chlorine_max"],
        alkalinity_min=targets["alkalinity_min"],
        alkalinity_max=targets["alkalinity_max"],
        hardness_min=targets["hardness_min"],
        hardness_max=targets["hardness_max"],
        temperature_default=targets["temperature_default"],
    )
