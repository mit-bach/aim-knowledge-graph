from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

SCHEMA = Path(__file__).resolve().parent.parent / "schema"


def trail_settings() -> dict[str, Any]:
    return yaml.safe_load((SCHEMA / "trail.yaml").read_text())


def fact_types() -> dict[str, dict[str, Any]]:
    return yaml.safe_load((SCHEMA / "fact_types.yaml").read_text())
