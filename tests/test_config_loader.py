from pathlib import Path
from utils.config_loader import load_config


def test_load_config():
    config_path = Path(__file__).parent.parent / "config.toml"
    config = load_config(str(config_path))
    assert config.name == "Lay-Z-Spa Ibiza"
    assert config.volume_liter == 1000
    assert config.ph_min == 7.2
    assert config.ph_max == 7.6
