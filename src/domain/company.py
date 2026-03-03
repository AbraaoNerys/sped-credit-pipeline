from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, Optional

from .value_objects import CNPJ


class TaxRegime(str, Enum):
    SIMPLES = "SIMPLES"
    PRESUMIDO = "PRESUMIDO"
    REAL = "REAL"


@dataclass(frozen=True)
class Company:
    company_id: str
    razao_social: str
    cnpj: CNPJ
    regime: TaxRegime
    estabelecimento: str
    ativo: bool = True
    observacoes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["cnpj"] = self.cnpj.value
        d["regime"] = self.regime.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Company":
        return cls(
            company_id=str(data["company_id"]),
            razao_social=str(data["razao_social"]),
            cnpj=CNPJ.from_raw(str(data["cnpj"])),
            regime=TaxRegime(str(data["regime"]).upper()),
            estabelecimento=str(data["estabelecimento"]),
            ativo=bool(data.get("ativo", True)),
            observacoes=data.get("observacoes"),
        )