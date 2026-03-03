from __future__ import annotations

from pathlib import Path


def ensure_company_folders(project_root: Path, company_id: str) -> None:
    """
    Cria a estrutura padrão de pastas para uma empresa, se não existir.

    Estrutura:
        data/input/<company_id>/entrada
        data/input/<company_id>/saida
        data/output/<company_id>
    """
    base = project_root / "data"
    (base / "input" / company_id / "entrada").mkdir(parents=True, exist_ok=True)
    (base / "input" / company_id / "saida").mkdir(parents=True, exist_ok=True)
    (base / "output" / company_id).mkdir(parents=True, exist_ok=True)