from __future__ import annotations

from typing import List, Optional

from src.domain.company import Company
from src.infra.storage.fs_layout import ensure_company_folders
from src.infra.storage.json_store import JsonStore
from src.infra.storage.paths import COMPANIES_JSON, PROJECT_ROOT


class CompanyRegistry:
    """
    Armazena empresas em configs/companies.json no formato:
    {
        "<company_id>": { ... dados ... },
        ...
    }
    """

    def __init__(self, store: Optional[JsonStore] = None):
        self.store = store or JsonStore(COMPANIES_JSON)

    def list(self) -> List[Company]:
        data = self.store.read()
        companies = [Company.from_dict(payload) for payload in data.values()]
        companies.sort(key=lambda c: c.company_id)
        return companies

    def get(self, company_id: str) -> Optional[Company]:
        data = self.store.read()
        payload = data.get(company_id)
        return Company.from_dict(payload) if payload else None

    def upsert(self, company: Company) -> None:
        data = self.store.read()
        data[company.company_id] = company.to_dict()
        self.store.write(data)

        # ✅ garante pastas padrão da empresa após salvar cadastro
        ensure_company_folders(PROJECT_ROOT, company.company_id)

    def delete(self, company_id: str) -> bool:
        data = self.store.read()
        if company_id not in data:
            return False
        del data[company_id]
        self.store.write(data)
        return True