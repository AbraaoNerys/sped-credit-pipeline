from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.infra.storage.paths import PROJECT_ROOT
from src.services.company_registry import CompanyRegistry
from src.services.ingest.scanner import _extract_key_and_date_fast, _ensure_staged_xmls
from src.services.process.nfe.parser import parse_nfe_items
from src.infra.excel.writer import write_rows_to_template


@dataclass(frozen=True)
class ProcessConfig:
    company_id: str
    year: int
    month: int
    limit_docs: Optional[int] = None


def _month_key(y: int, m: int) -> str:
    return f"{y:04d}-{m:02d}"


def _select_month_xmls(company_id: str, year: int, month: int) -> List[Tuple[str, Path]]:
    """
    Retorna lista de (direction, xml_path) filtrados por ano/mes e tipo NFE.
    direction: "entrada" | "saida"
    """
    base_input = PROJECT_ROOT / "data" / "input" / company_id
    entrada_dir = base_input / "entrada"
    saida_dir = base_input / "saida"

    entrada_files = _ensure_staged_xmls(company_id, "entrada", entrada_dir)
    saida_files = _ensure_staged_xmls(company_id, "saida", saida_dir)

    selected: List[Tuple[str, Path]] = []

    def filter_files(direction: str, files: List[Path]) -> None:
        for p in files:
            _, issued_at, doc_type, err = _extract_key_and_date_fast(p)
            if err:
                continue
            if doc_type != "NFE":
                continue
            if issued_at is None:
                continue
            if issued_at.year == year and issued_at.month == month:
                selected.append((direction, p))

    filter_files("entrada", entrada_files)
    filter_files("saida", saida_files)

    return selected


def run_month_process(cfg: ProcessConfig) -> Path:
    reg = CompanyRegistry()
    company = reg.get(cfg.company_id)
    if not company:
        raise ValueError(f"Empresa não encontrada: {cfg.company_id}")

    month_str = _month_key(cfg.year, cfg.month)

    template_path = PROJECT_ROOT / "data" / "templates" / "sc_a100_a170_template.xlsx"
    if not template_path.exists():
        raise FileNotFoundError(
            "Template não encontrado. Coloque em: data/templates/sc_a100_a170_template.xlsx"
        )

    out_dir = PROJECT_ROOT / "data" / "output" / cfg.company_id / month_str
    out_path = out_dir / "SC_A100_A170.xlsx"

    files = _select_month_xmls(cfg.company_id, cfg.year, cfg.month)
    if cfg.limit_docs is not None:
        files = files[: cfg.limit_docs]

    rows: List[Dict[str, Any]] = []

    for direction, xml_path in files:
        try:
            doc = parse_nfe_items(xml_path)
        except Exception as exc:
            print(f"⚠️  Erro ao parsear XML ({xml_path.name}): {type(exc).__name__}: {exc}", flush=True)
            continue

        # entrada: contrapartida = emitente
        # saída: contrapartida = destinatário
        if direction == "entrada":
            cod_part = doc.get("EMIT_CNPJ")
            cod_part_nome = doc.get("EMIT_NOME")
            ind_oper = 0
        else:
            cod_part = doc.get("DEST_CNPJ")
            cod_part_nome = doc.get("DEST_NOME")
            ind_oper = 1

        for item in doc["ITENS"]:
            row = {
                # metadados (não necessariamente existem no template; writer ignora o que não existir)
                "LAYOUT": "SC_A100_A170",
                "EMPRESA": company.razao_social,
                "ANO": cfg.year,
                "MES": cfg.month,
                "ESTABELECIMENTO": company.estabelecimento,

                # campos do layout
                "IND_OPER": ind_oper,
                "COD_PART": cod_part,
                "COD_PART_NOME": cod_part_nome,

                "SER": doc.get("SER"),
                "SUB": None,
                "NUM_DOC": doc.get("NUM_DOC"),
                "DT_DOC": doc.get("DT_DOC"),
                "DT_EXE_SERV": None,

                "COD_ITEM": item.get("COD_ITEM"),
                "DESCR_ITEM": item.get("DESCR_ITEM"),
                "DESCR_COMPL": item.get("DESCR_COMPL"),

                "VL_DOC": doc.get("VL_DOC"),
                "VL_ITEM": item.get("VL_ITEM"),
                "VL_DESC": item.get("VL_DESC"),
                "IND_PGTO": doc.get("IND_PGTO"),

                # opcionais
                "NAT_BC_CRED": None,
                "IND_ORIG_CRED": None,
                "COD_CTA": None,
                "COD_CCUS": None,
                "COD_NBS": None,
                "VL_ISS": None,
                "PIS_COFINS": None,

                # PIS/COFINS
                "CST_PIS": item.get("CST_PIS"),
                "VL_BC_PIS": item.get("VL_BC_PIS"),
                "ALIQ_PIS": item.get("ALIQ_PIS"),
                "VL_PIS": item.get("VL_PIS"),

                "CST_COFINS": item.get("CST_COFINS"),
                "VL_BC_COFINS": item.get("VL_BC_COFINS"),
                "ALIQ_COFINS": item.get("ALIQ_COFINS"),
                "VL_COFINS": item.get("VL_COFINS"),

                "VL_PIS_RET": None,
                "VL_COFINS_RET": None,
                "CHV_NFSE": None,
            }
            rows.append(row)

    write_rows_to_template(
        template_path=template_path,
        sheet_name="SC_A100_A170",
        rows=rows,
        output_path=out_path,
    )

    return out_path