from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIGS_DIR = PROJECT_ROOT / "configs"
COMPANIES_JSON = CONFIGS_DIR / "companies.json"

DATA_DIR = PROJECT_ROOT / "data"