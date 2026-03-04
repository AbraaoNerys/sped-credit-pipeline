from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.infra.storage.paths import PROJECT_ROOT
from src.services.company_registry import CompanyRegistry
from src.services.ingest.scanner import _ensure_staged_xmls, _extract_key_and_date_fast
from src.services.process.nfe.parser import parse_nfe_items
from src.infra.excel.writer import write_rows_to_template

import os
_PARSE_WORKERS = min(8, (os.cpu_count() or 2) * 2)


@dataclass(frozen=True)
class ProcessConfig:
    company_id: str
    year: int
    limit_docs: Optional[int] = None


def _load_file_cache(company_id: str) -> Dict[str, dict]:
    cache_path = PROJECT_ROOT / "data" / "input" / company_id / ".scan_cache.json"
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _select_year_xmls(company_id: str, year: int) -> List[Tuple[str, int, Path]]:
    """
    Retorna lista de (direction, month, xml_path) para todos os meses do ano.
    Usa cache de metadados quando disponível.
    """
    base_input = PROJECT_ROOT / "data" / "input" / company_id
    entrada_files = _ensure_staged_xmls(company_id, "entrada", base_input / "entrada")
    saida_files  = _ensure_staged_xmls(company_id, "saida",   base_input / "saida")

    file_cache = _load_file_cache(company_id)
    selected: List[Tuple[str, int, Path]] = []

    def filter_files(direction: str, files: List[Path]) -> None:
        hits = misses = 0
        for p in files:
            cached = file_cache.get(str(p))
            if cached:
                hits += 1
                if cached.get("doc_type") != "NFE" or cached.get("errors"):
                    continue
                if cached.get("year") != year:
                    continue
                month = cached.get("month")
                if month:
                    selected.append((direction, int(month), p))
            else:
                misses += 1
                _, issued_at, doc_type, err = _extract_key_and_date_fast(p)
                if err or doc_type != "NFE" or issued_at is None:
                    continue
                if issued_at.year == year:
                    selected.append((direction, issued_at.month, p))

        total = hits + misses
        found = sum(1 for d, _, _ in selected if d == direction)
        print(
            f"[{company_id}:{direction}] 📋 {found} notas de {year} "
            f"| cache={hits:,} hits / {misses:,} misses de {total:,} arquivos",
            flush=True,
        )

    filter_files("entrada", entrada_files)
    filter_files("saida",   saida_files)

    # ordena por mês para escrita ordenada na planilha
    selected.sort(key=lambda x: (x[1], x[2]))
    return selected


def _parse_one(direction: str, month: int, xml_path: Path) -> Tuple[str, int, Path, Optional[dict], Optional[str]]:
    try:
        doc = parse_nfe_items(xml_path)
        return direction, month, xml_path, doc, None
    except Exception as exc:
        return direction, month, xml_path, None, f"{type(exc).__name__}: {exc}"


def run_year_process(cfg: ProcessConfig) -> Path:
    reg = CompanyRegistry()
    company = reg.get(cfg.company_id)
    if not company:
        raise ValueError(f"Empresa não encontrada: {cfg.company_id}")

    template_path = PROJECT_ROOT / "data" / "templates" / "sc_a100_a170_template.xlsx"
    if not template_path.exists():
        raise FileNotFoundError(
            "Template não encontrado. Coloque em: data/templates/sc_a100_a170_template.xlsx"
        )

    out_dir  = PROJECT_ROOT / "data" / "output" / cfg.company_id / str(cfg.year)
    out_path = out_dir / "SC_A100_A170.xlsx"

    # 1) Seleciona arquivos do ano
    files = _select_year_xmls(cfg.company_id, cfg.year)
    if cfg.limit_docs is not None:
        files = files[: cfg.limit_docs]

    total = len(files)
    print(
        f"📄 {total} documentos encontrados para {cfg.year} "
        f"— parse com {_PARSE_WORKERS} threads...",
        flush=True,
    )

    if total == 0:
        print(f"⚠️  Nenhum documento NFE encontrado para {cfg.year}.", flush=True)

    # 2) Parse paralelo
    rows: List[Dict[str, Any]] = []
    errors = done = 0

    with ThreadPoolExecutor(max_workers=_PARSE_WORKERS) as executor:
        futures = {
            executor.submit(_parse_one, direction, month, xml_path): (direction, month, xml_path)
            for direction, month, xml_path in files
        }

        for future in as_completed(futures):
            direction, month, xml_path, doc, err = future.result()
            done += 1

            if err:
                errors += 1
                print(f"  ⚠️  Erro ({xml_path.name}): {err}", flush=True)
                continue

            if direction == "entrada":
                cod_part      = doc.get("EMIT_CNPJ")
                cod_part_nome = doc.get("EMIT_NOME")
                ind_oper      = 0
            else:
                cod_part      = doc.get("DEST_CNPJ")
                cod_part_nome = doc.get("DEST_NOME")
                ind_oper      = 1

            for item in doc["ITENS"]:
                rows.append({
                    "LAYOUT":        "SC_A100_A170",
                    "EMPRESA":       company.cnpj.masked(),
                    "ANO":           int(cfg.year),
                    "MES":           int(month),
                    "ESTABELECIMENTO": company.cnpj.masked(),

                    "IND_OPER":      ind_oper,
                    "COD_PART":      cod_part,
                    "COD_PART_NOME": cod_part_nome,

                    "SER":           doc.get("SER") or None,
                    "SUB":           None,
                    "NUM_DOC":       doc.get("NUM_DOC"),
                    "DT_DOC":        doc.get("DT_DOC"),
                    "DT_EXE_SERV":   None,

                    "COD_ITEM":      item.get("COD_ITEM"),
                    "DESCR_ITEM":    item.get("DESCR_ITEM"),
                    "DESCR_COMPL":   item.get("DESCR_COMPL"),

                    "VL_DOC":        doc.get("VL_DOC"),
                    "VL_ITEM":       item.get("VL_ITEM"),
                    "VL_DESC":       item.get("VL_DESC"),
                    "IND_PGTO":      doc.get("IND_PGTO"),

                    "NAT_BC_CRED":   None,
                    "IND_ORIG_CRED": None,
                    "COD_CTA":       None,
                    "COD_CCUS":      None,
                    "COD_NBS":       None,
                    "VL_ISS":        None,
                    "PIS_COFINS":    None,

                    "CST_PIS":       item.get("CST_PIS"),
                    "VL_BC_PIS":     item.get("VL_BC_PIS"),
                    "ALIQ_PIS":      item.get("ALIQ_PIS"),
                    "VL_PIS":        item.get("VL_PIS"),

                    "CST_COFINS":    item.get("CST_COFINS"),
                    "VL_BC_COFINS":  item.get("VL_BC_COFINS"),
                    "ALIQ_COFINS":   item.get("ALIQ_COFINS"),
                    "VL_COFINS":     item.get("VL_COFINS"),

                    "VL_PIS_RET":    None,
                    "VL_COFINS_RET": None,
                    "CHV_NFSE":      None,
                })

            if done % 500 == 0 or done == total:
                print(f"  ⚙️  {done:,}/{total:,} documentos processados...", flush=True)

    # ordena as rows por mês e data para planilha organizada
    rows.sort(key=lambda r: (r["MES"], r["DT_DOC"] or ""))

    print(f"✅ Parse concluído: {done - errors} ok | {errors} erros | {len(rows):,} itens gerados", flush=True)

    # 3) Grava Excel
    print("💾 Gravando planilha...", flush=True)
    write_rows_to_template(
        template_path=template_path,
        sheet_name="SC_A100_A170",
        rows=rows,
        output_path=out_path,
    )

    return out_path