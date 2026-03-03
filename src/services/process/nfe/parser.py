from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def _find_first(elem: ET.Element, name: str) -> Optional[ET.Element]:
    name_u = name.upper()
    for e in elem.iter():
        if _strip_ns(e.tag).upper() == name_u:
            return e
    return None


def _find_all(elem: ET.Element, name: str) -> List[ET.Element]:
    name_u = name.upper()
    return [e for e in elem.iter() if _strip_ns(e.tag).upper() == name_u]


def _text(elem: Optional[ET.Element]) -> Optional[str]:
    if elem is None or elem.text is None:
        return None
    t = elem.text.strip()
    return t if t else None


def _parse_iso_date(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = s.strip()
    if "T" in s:
        return s.split("T", 1)[0]
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    if len(s) >= 8 and s[:8].isdigit():
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    return None


def _to_float(s: Optional[str]) -> Optional[float]:
    if s is None:
        return None
    try:
        return float(s.replace(",", "."))
    except Exception:
        return None


def _parse_pis(det: ET.Element) -> Tuple[Optional[str], Optional[float], Optional[float], Optional[float]]:
    imp = _find_first(det, "imposto")
    if imp is None:
        return None, None, None, None

    pis = _find_first(imp, "PIS")
    if pis is None:
        return None, None, None, None

    # Itera todos os grupos filhos; o primeiro que tiver CST válido vence
    # (PISAliq, PISOutr, PISNT, PISQtde, etc.)
    for grp in list(pis):
        cst = _text(_find_first(grp, "CST"))
        if cst is None:
            continue  # grupo sem CST não é um grupo válido de PIS

        vbc = _to_float(_text(_find_first(grp, "vBC")))
        pp = _to_float(_text(_find_first(grp, "pPIS")))
        vpis = _to_float(_text(_find_first(grp, "vPIS")))

        # PISQtde: base é quantidade e alíquota é por unidade
        if vbc is None:
            qbc = _to_float(_text(_find_first(grp, "qBCProd")))
            valiq = _to_float(_text(_find_first(grp, "vAliqProd")))
            if qbc is not None:
                vbc = qbc
            if pp is None and valiq is not None:
                pp = valiq

        return cst, vbc, pp, vpis

    return None, None, None, None


def _parse_cofins(det: ET.Element) -> Tuple[Optional[str], Optional[float], Optional[float], Optional[float]]:
    imp = _find_first(det, "imposto")
    if imp is None:
        return None, None, None, None

    cof = _find_first(imp, "COFINS")
    if cof is None:
        return None, None, None, None

    # Itera todos os grupos filhos; o primeiro que tiver CST válido vence
    # (COFINSAliq, COFINSOutr, COFINSNT, COFINSQtde, etc.)
    for grp in list(cof):
        cst = _text(_find_first(grp, "CST"))
        if cst is None:
            continue  # grupo sem CST não é um grupo válido de COFINS

        vbc = _to_float(_text(_find_first(grp, "vBC")))
        pp = _to_float(_text(_find_first(grp, "pCOFINS")))
        vcof = _to_float(_text(_find_first(grp, "vCOFINS")))

        # COFINSQtde: base é quantidade e alíquota é por unidade
        if vbc is None:
            qbc = _to_float(_text(_find_first(grp, "qBCProd")))
            valiq = _to_float(_text(_find_first(grp, "vAliqProd")))
            if qbc is not None:
                vbc = qbc
            if pp is None and valiq is not None:
                pp = valiq

        return cst, vbc, pp, vcof

    return None, None, None, None


def parse_nfe_items(xml_path: Path) -> Dict[str, Any]:
    root = ET.parse(xml_path).getroot()

    infnfe: Optional[ET.Element] = None
    for e in root.iter():
        if _strip_ns(e.tag).upper() == "INFNFE":
            infnfe = e
            break
    if infnfe is None:
        raise ValueError("infNFe não encontrado")

    chave = infnfe.attrib.get("Id") or infnfe.attrib.get("ID")
    if chave and chave.upper().startswith("NFE"):
        chave = chave[3:]

    ide = _find_first(infnfe, "ide")
    emit = _find_first(infnfe, "emit")
    dest = _find_first(infnfe, "dest")

    serie = _text(_find_first(ide, "serie"))
    nnf = _text(_find_first(ide, "nNF"))

    dhemi = _text(_find_first(ide, "dhEmi")) or _text(_find_first(ide, "dEmi"))
    dt_doc = _parse_iso_date(dhemi)

    indpag = _text(_find_first(ide, "indPag"))

    # NF-e 4.0: indPag migrou para detPag/indPag
    if indpag is None:
        det_pag = _find_first(infnfe, "detPag")
        if det_pag is not None:
            indpag = _text(_find_first(det_pag, "indPag"))

    total = _find_first(infnfe, "total")
    icmstot = _find_first(total, "ICMSTot") if total is not None else None
    vnf = _to_float(_text(_find_first(icmstot, "vNF")))
    vdesc_doc = _to_float(_text(_find_first(icmstot, "vDesc")))

    emit_cnpj = _text(_find_first(emit, "CNPJ")) or _text(_find_first(emit, "CPF"))
    emit_nome = _text(_find_first(emit, "xNome"))
    dest_cnpj = _text(_find_first(dest, "CNPJ")) or _text(_find_first(dest, "CPF"))
    dest_nome = _text(_find_first(dest, "xNome"))

    itens: List[Dict[str, Any]] = []
    for det in _find_all(infnfe, "det"):
        prod = _find_first(det, "prod")
        cprod = _text(_find_first(prod, "cProd"))
        xprod = _text(_find_first(prod, "xProd"))
        vprod = _to_float(_text(_find_first(prod, "vProd")))
        vdesc_item = _to_float(_text(_find_first(prod, "vDesc")))
        infadprod = _text(_find_first(det, "infAdProd"))

        cst_pis, vbc_pis, aliq_pis, v_pis = _parse_pis(det)
        cst_cof, vbc_cof, aliq_cof, v_cof = _parse_cofins(det)

        itens.append(
            {
                "COD_ITEM": cprod,
                "DESCR_ITEM": xprod,
                "DESCR_COMPL": infadprod,
                "VL_ITEM": vprod,
                "VL_DESC": vdesc_item,
                "CST_PIS": cst_pis,
                "VL_BC_PIS": vbc_pis,
                "ALIQ_PIS": aliq_pis,
                "VL_PIS": v_pis,
                "CST_COFINS": cst_cof,
                "VL_BC_COFINS": vbc_cof,
                "ALIQ_COFINS": aliq_cof,
                "VL_COFINS": v_cof,
            }
        )

    return {
        "CHAVE": chave,
        "SER": serie,
        "NUM_DOC": nnf,
        "DT_DOC": dt_doc,
        "IND_PGTO": indpag,
        "VL_DOC": vnf,
        "VL_DESC_DOC": vdesc_doc,
        "EMIT_CNPJ": emit_cnpj,
        "EMIT_NOME": emit_nome,
        "DEST_CNPJ": dest_cnpj,
        "DEST_NOME": dest_nome,
        "ITENS": itens,
    }