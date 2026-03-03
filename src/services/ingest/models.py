from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class DocMeta:
    path: str
    direction: str  # "entrada" | "saida"
    doc_type: str   # "NFE" | "CFE" | "UNKNOWN"
    issued_at: Optional[datetime]
    year: Optional[int]
    month: Optional[int]
    key: Optional[str]
    errors: Optional[str] = None


@dataclass(frozen=True)
class MonthBucket:
    year: int
    month: int
    entrada: int
    saida: int
    nfe: int
    cfe: int
    unknown: int


@dataclass(frozen=True)
class ScanResult:
    company_id: str
    total_files: int
    total_entrada: int
    total_saida: int
    total_nfe: int
    total_cfe: int
    total_unknown: int
    total_with_date: int
    total_without_date: int
    buckets: List[MonthBucket]
    samples_errors: List[DocMeta]

    def to_dict(self) -> Dict:
        return {
            "company_id": self.company_id,
            "total_files": self.total_files,
            "total_entrada": self.total_entrada,
            "total_saida": self.total_saida,
            "total_nfe": self.total_nfe,
            "total_cfe": self.total_cfe,
            "total_unknown": self.total_unknown,
            "total_with_date": self.total_with_date,
            "total_without_date": self.total_without_date,
            "buckets": [
                {
                    "year": b.year,
                    "month": b.month,
                    "entrada": b.entrada,
                    "saida": b.saida,
                    "nfe": b.nfe,
                    "cfe": b.cfe,
                    "unknown": b.unknown,
                }
                for b in self.buckets
            ],
            "samples_errors": [
                {
                    "path": e.path,
                    "direction": e.direction,
                    "doc_type": e.doc_type,
                    "issued_at": e.issued_at.isoformat() if e.issued_at else None,
                    "year": e.year,
                    "month": e.month,
                    "key": e.key,
                    "errors": e.errors,
                }
                for e in self.samples_errors
            ],
        }