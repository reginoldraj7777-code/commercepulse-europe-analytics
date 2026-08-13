from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "profiles.yaml"


@dataclass(frozen=True)
class ScenarioProfile:
    name: str
    start_date: str
    end_date: str
    customers: int
    products: int
    sessions: int
    inventory_frequency: str
    seed: int
    timezone: str
    markets: tuple[str, ...]
    currencies: dict[str, str]


def load_profile(name: str, config_path: Path | None = None) -> ScenarioProfile:
    path = config_path or DEFAULT_CONFIG_PATH
    config: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    profiles = config["profiles"]
    if name not in profiles:
        supported = ", ".join(sorted(k for k in profiles if isinstance(profiles[k], dict)))
        raise ValueError(f"Unknown profile {name!r}. Supported profiles: {supported}")
    selected = profiles[name]
    return ScenarioProfile(
        name=name,
        start_date=str(selected["start_date"]),
        end_date=str(selected["end_date"]),
        customers=int(selected["customers"]),
        products=int(selected["products"]),
        sessions=int(selected["sessions"]),
        inventory_frequency=str(selected["inventory_frequency"]),
        seed=int(profiles["seed"]),
        timezone=str(profiles["timezone"]),
        markets=tuple(profiles["markets"]),
        currencies=dict(profiles["currencies"]),
    )
