from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class JsonStore:
    def __init__(self, path: Path):
        self.path = path

    def read(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        raw = self.path.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        return json.loads(raw)

    def write(self, data: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")