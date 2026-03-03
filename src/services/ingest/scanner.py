from __future__ import annotations

import zipfile
import shutil

import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET

from src.infra.storage.paths import PROJECT_ROOT
from .models import DocMeta, MonthBucket, ScanResult


def _iter_xml_files(folder: Path) -> List[Path]:
    if not folder.exists():
        return []
    return sorted([p for p in folder.rglob("*.xml") if p.is_file()])

def _iter_zip_files(folder: Path) -> List[Path]:
    if not folder.exists():
        return []
    return sorted([p for p in folder.rglob("*.zip") if p.is_file()])


def _safe_extract_xmls(zip_path: Path, dest_dir: Path, *, log_prefix: str = "") -> List[Path]:
    """
    Extrai SOMENTE arquivos .xml do zip para dest_dir de forma segura (anti ZipSlip).
    Loga progresso para não parecer travado.
    """
    extracted: List[Path] = []
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_real = dest_dir.resolve()

    with zipfile.ZipFile(zip_path, "r") as zf:
        infos = [i for i in zf.infolist() if (not i.is_dir()) and i.filename.lower().endswith(".xml")]
        total = len(infos)

        print(f"{log_prefix}📦 Extraindo: {zip_path.name} -> {dest_dir} | XMLs no zip: {total}", flush=True)

        for idx, info in enumerate(infos, start=1):
            name = info.filename.replace("\\", "/")
            safe_name = Path(name).name
            if not safe_name:
                continue

            target_path = dest_dir / safe_name
            target_real = target_path.resolve()

            # defesa anti ZipSlip
            if dest_real not in target_real.parents and target_real != dest_real:
                continue

            with zf.open(info, "r") as src, open(target_path, "wb") as out:
                shutil.copyfileobj(src, out, length=1024 * 1024)  # 1MB chunks

            extracted.append(target_path)

            if idx == 1 or idx % 200 == 0 or idx == total:
                print(f"{log_prefix}  - progresso: {idx}/{total}", flush=True)

    return extracted


def _ensure_staged_xmls(company_id: str, direction: str, source_dir: Path) -> List[Path]:
    """
    Para uma pasta (entrada/saida), extrai zips para staging e retorna todos os xml disponíveis:
        - xml soltos em source_dir
        - xml extraídos em data/input/<company_id>/__staging__/<direction>/<zipname>/
    """
    staging_root = PROJECT_ROOT / "data" / "input" / company_id / "__staging__" / direction
    staging_root.mkdir(parents=True, exist_ok=True)

    # xml já soltos
    xml_paths = _iter_xml_files(source_dir)

    # zips -> extrair para pastas por zip
    zips = _iter_zip_files(source_dir)
    for i, zp in enumerate(zips, start=1):
        zip_bucket = staging_root / zp.stem
        zip_bucket.mkdir(parents=True, exist_ok=True)

        already = list(zip_bucket.glob("*.xml"))
        if already:
            xml_paths.extend(already)
            print(f"[{company_id}:{direction}] ✅ Já extraído: {zp.name} | xmls={len(already)}", flush=True)
            continue

        extracted = _safe_extract_xmls(zp, zip_bucket, log_prefix=f"[{company_id}:{direction}] ({i}/{len(zips)}) ")
        xml_paths.extend(extracted)

    # remover duplicados e ordenar
    uniq = sorted({p.resolve() for p in xml_paths})
    return [Path(p) for p in uniq]


def _strip_ns(tag: str) -> str:
    # "{namespace}tag" -> "tag"
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _parse_date(text: str) -> Optional[datetime]:
    """
    Tenta interpretar datas comuns:
    - 2021-01-31T10:20:30-03:00
    - 2021-01-31T10:20:30
    - 2021-01-31
    - 20210131
    """
    if not text:
        return None
    t = text.strip()
    try:
        # ISO (com ou sem timezone)
        return datetime.fromisoformat(t.replace("Z", "+00:00"))
    except Exception:
        pass

    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(t[:10], fmt)
        except Exception:
            continue
    return None


def _detect_doc_type(root_tag: str, seen_tags: set[str]) -> str:
    rt = _strip_ns(root_tag).upper()
    if rt in {"NFE", "NFEPROC"}:
        return "NFE"
    if rt in {"CFE", "CFEPROC", "CFECANC"}:
        return "CFE"

    # fallback por tags vistas
    if "INFNFE" in seen_tags:
        return "NFE"
    if "INFCFE" in seen_tags:
        return "CFE"

    return "UNKNOWN"


def _extract_key_and_date_fast(xml_path: Path) -> Tuple[Optional[str], Optional[datetime], str, Optional[str]]:
    """
    Leitura rápida (sem mapear tudo):
    - tenta achar Id em infNFe/infCFe
    - tenta achar dhEmi/dEmi
    - detecta tipo (NFE/CFE/UNKNOWN)
    Retorna: (key, issued_at, doc_type, error)
    """
    seen_tags: set[str] = set()
    key: Optional[str] = None
    issued_at: Optional[datetime] = None
    doc_type: str = "UNKNOWN"
    root_tag: Optional[str] = None

    try:
        # iterparse único — captura root_tag na primeira tag encontrada
        for event, elem in ET.iterparse(xml_path, events=("start",)):
            tag = _strip_ns(elem.tag).upper()

            # primeira tag processada = root
            if root_tag is None:
                root_tag = tag

            seen_tags.add(tag)

            # pegar chave/id via atributo Id
            if tag in {"INFNFE", "INFCFE"}:
                _id = elem.attrib.get("Id") or elem.attrib.get("ID")
                if _id:
                    _id = _id.strip()
                    if _id.upper().startswith("NFE"):
                        _id = _id[3:]
                    if _id.upper().startswith("CFE"):
                        _id = _id[3:]
                    key = _id

            # pegar data de emissão
            if tag in {"DHEMI", "DEMI"} and issued_at is None:
                issued_at = _parse_date(elem.text or "")

        # doc_type inferido sem segundo parse — usa root_tag capturado acima
        doc_type = _detect_doc_type(root_tag or "", seen_tags)

        return key, issued_at, doc_type, None

    except Exception as e:
        return None, None, "UNKNOWN", f"{type(e).__name__}: {e}"


def scan_company_inputs(company_id: str) -> ScanResult:
    """
    Varre:
        data/input/<company_id>/entrada
        data/input/<company_id>/saida
    Agrupa por ano/mês usando a data extraída do XML.
    """
    base_input = PROJECT_ROOT / "data" / "input" / company_id
    entrada_dir = base_input / "entrada"
    saida_dir = base_input / "saida"

    entrada_files = _ensure_staged_xmls(company_id, "entrada", entrada_dir)
    saida_files = _ensure_staged_xmls(company_id, "saida", saida_dir)
    
    metas: List[DocMeta] = []

    def handle(files: List[Path], direction: str) -> None:
        for p in files:
            key, issued_at, doc_type, err = _extract_key_and_date_fast(p)
            year = issued_at.year if issued_at else None
            month = issued_at.month if issued_at else None
            metas.append(
                DocMeta(
                    path=str(p),
                    direction=direction,
                    doc_type=doc_type,
                    issued_at=issued_at,
                    year=year,
                    month=month,
                    key=key,
                    errors=err,
                )
            )

    handle(entrada_files, "entrada")
    handle(saida_files, "saida")

    total_files = len(metas)
    total_entrada = len(entrada_files)
    total_saida = len(saida_files)

    total_nfe = sum(1 for m in metas if m.doc_type == "NFE")
    total_cfe = sum(1 for m in metas if m.doc_type == "CFE")
    total_unknown = sum(1 for m in metas if m.doc_type == "UNKNOWN")

    total_with_date = sum(1 for m in metas if m.issued_at is not None)
    total_without_date = total_files - total_with_date

    # bucket por (ano, mes)
    agg: Dict[Tuple[int, int], Dict[str, int]] = {}
    for m in metas:
        if m.year is None or m.month is None:
            continue
        k = (m.year, m.month)
        if k not in agg:
            agg[k] = {"entrada": 0, "saida": 0, "nfe": 0, "cfe": 0, "unknown": 0}
        agg[k][m.direction] += 1
        if m.doc_type == "NFE":
            agg[k]["nfe"] += 1
        elif m.doc_type == "CFE":
            agg[k]["cfe"] += 1
        else:
            agg[k]["unknown"] += 1

    buckets = [
        MonthBucket(
            year=y,
            month=mo,
            entrada=v["entrada"],
            saida=v["saida"],
            nfe=v["nfe"],
            cfe=v["cfe"],
            unknown=v["unknown"],
        )
        for (y, mo), v in sorted(agg.items())
    ]

    # guardar uma amostra de erros (até 10)
    samples_errors = [m for m in metas if m.errors][:10]

    return ScanResult(
        company_id=company_id,
        total_files=total_files,
        total_entrada=total_entrada,
        total_saida=total_saida,
        total_nfe=total_nfe,
        total_cfe=total_cfe,
        total_unknown=total_unknown,
        total_with_date=total_with_date,
        total_without_date=total_without_date,
        buckets=buckets,
        samples_errors=samples_errors,
    )


def save_scan_report(result: ScanResult) -> Path:
    out_dir = PROJECT_ROOT / "data" / "output" / result.company_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "ingest_scan_report.json"
    path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path