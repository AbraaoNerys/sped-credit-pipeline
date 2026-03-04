from __future__ import annotations

import argparse
from typing import Optional

from src.domain.company import Company, TaxRegime
from src.domain.value_objects import CNPJ
from src.services.company_registry import CompanyRegistry


def _print_company(c: Company) -> None:
    print(f"- id: {c.company_id}")
    print(f"  razao_social: {c.razao_social}")
    print(f"  cnpj: {c.cnpj.masked()}")
    print(f"  regime: {c.regime.value}")
    print(f"  estabelecimento: {c.estabelecimento}")
    print(f"  ativo: {c.ativo}")
    if c.observacoes:
        print(f"  observacoes: {c.observacoes}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sped-credit-pipeline",
        description="Pipeline para gerar layout SC_A100_A170 a partir de XML (NF-e/CF-e).",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ---- company ----
    company = sub.add_parser("company", help="Gerenciar cadastro de empresas")
    company_sub = company.add_subparsers(dest="company_cmd", required=True)

    add = company_sub.add_parser("add", help="Cadastrar/atualizar empresa")
    add.add_argument("--id",             required=True, help="Identificador único (slug)")
    add.add_argument("--razao",          required=True, help="Razão social")
    add.add_argument("--cnpj",           required=True, help="CNPJ (com ou sem máscara)")
    add.add_argument("--regime",         required=True, choices=[r.value for r in TaxRegime])
    add.add_argument("--estabelecimento",required=True, help="Código do estabelecimento (ex: 01)")
    add.add_argument("--ativo",   action="store_true", help="Marca empresa como ativa (default)")
    add.add_argument("--inativo", action="store_true", help="Marca empresa como inativa")
    add.add_argument("--obs", default=None, help="Observações (opcional)")

    company_sub.add_parser("list",  help="Listar empresas")

    show = company_sub.add_parser("show", help="Mostrar detalhes de uma empresa")
    show.add_argument("--id", required=True)

    delete = company_sub.add_parser("delete", help="Remover empresa")
    delete.add_argument("--id", required=True)

    # ---- ingest ----
    ingest = sub.add_parser("ingest", help="Ingestão/varredura de XML")
    ingest_sub = ingest.add_subparsers(dest="ingest_cmd", required=True)

    scan = ingest_sub.add_parser("scan", help="Escanear XMLs e agrupar por ano/mês")
    scan.add_argument("--company",      required=True)
    scan.add_argument("--save-report",  action="store_true")

    plan = ingest_sub.add_parser("plan", help="Gerar plano de processamento por ano")
    plan.add_argument("--company", required=True)

    # ---- process ----
    process = sub.add_parser("process", help="Processar XMLs e gerar planilha anual")
    process_sub = process.add_subparsers(dest="process_cmd", required=True)

    run = process_sub.add_parser("run", help="Processar um ano completo e gerar SC_A100_A170.xlsx")
    run.add_argument("--company",    required=True, help="Company ID")
    run.add_argument("--year",       required=True, help="Ano no formato YYYY (ex: 2021)")
    run.add_argument("--limit-docs", type=int, default=None, help="Limitar documentos (debug)")

    return parser


def run_cli(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    registry = CompanyRegistry()

    # ── COMPANY ──────────────────────────────────────────────────────────────
    if args.command == "company":
        if args.company_cmd == "add":
            ativo = True
            if args.inativo:
                ativo = False

            company = Company(
                company_id=args.id.strip(),
                razao_social=args.razao.strip(),
                cnpj=CNPJ.from_raw(args.cnpj),
                regime=TaxRegime(args.regime),
                estabelecimento=str(args.estabelecimento).strip(),
                ativo=ativo,
                observacoes=args.obs.strip() if isinstance(args.obs, str) and args.obs.strip() else None,
            )
            registry.upsert(company)
            print("✅ Empresa cadastrada/atualizada com sucesso:")
            _print_company(company)
            return 0

        if args.company_cmd == "list":
            companies = registry.list()
            if not companies:
                print("Nenhuma empresa cadastrada ainda.")
                return 0
            print(f"Empresas cadastradas: {len(companies)}")
            for c in companies:
                status = "ATIVA" if c.ativo else "INATIVA"
                print(f"- {c.company_id} | {c.cnpj.masked()} | {c.regime.value} | {status} | {c.razao_social}")
            return 0

        if args.company_cmd == "show":
            c = registry.get(args.id)
            if not c:
                print(f"❌ Empresa não encontrada: {args.id}")
                return 1
            _print_company(c)
            return 0

        if args.company_cmd == "delete":
            ok = registry.delete(args.id)
            if not ok:
                print(f"❌ Empresa não encontrada: {args.id}")
                return 1
            print(f"✅ Empresa removida: {args.id}")
            return 0

    # ── INGEST ───────────────────────────────────────────────────────────────
    if args.command == "ingest":
        from src.services.ingest.scanner import scan_company_inputs, save_scan_report

        company_id = args.company.strip()
        result = scan_company_inputs(company_id)

        if args.ingest_cmd == "scan":
            print("📦 Ingest Scan (inventário de XML)")
            print(f"Empresa: {result.company_id}")
            print(f"Total XML: {result.total_files} | entrada: {result.total_entrada} | saída: {result.total_saida}")
            print(f"Tipos: NFE={result.total_nfe} | CFE={result.total_cfe} | UNKNOWN={result.total_unknown}")
            print(f"Com data: {result.total_with_date} | Sem data: {result.total_without_date}")

            if result.buckets:
                print("\nPor ano (ano-mês): entrada | saída | NFE | CFE | UNKNOWN")
                for b in result.buckets:
                    ym = f"{b.year:04d}-{b.month:02d}"
                    print(f"- {ym}: {b.entrada} | {b.saida} | {b.nfe} | {b.cfe} | {b.unknown}")
            else:
                print("\nNenhum XML com data reconhecida.")

            if result.samples_errors:
                print("\nAmostra de erros (até 10):")
                for e in result.samples_errors:
                    print(f"- {e.path} :: {e.errors}")

            if getattr(args, "save_report", False):
                path = save_scan_report(result)
                print(f"\n✅ Relatório salvo em: {path}")
            return 0

        if args.ingest_cmd == "plan":
            print("📅 Plano de processamento por ano")
            print(f"Empresa: {result.company_id}")

            if not result.buckets:
                print("Nenhum lote encontrado.")
                return 0

            # agrupa por ano
            from collections import defaultdict
            by_year: dict = defaultdict(lambda: {"entrada": 0, "saida": 0, "nfe": 0, "meses": set()})
            for b in result.buckets:
                by_year[b.year]["entrada"] += b.entrada
                by_year[b.year]["saida"]   += b.saida
                by_year[b.year]["nfe"]     += b.nfe
                by_year[b.year]["meses"].add(b.month)

            print("\nAnos disponíveis para processar:")
            for year in sorted(by_year.keys()):
                d = by_year[year]
                meses = len(d["meses"])
                total = d["entrada"] + d["saida"]
                print(
                    f"  {year}: {total:,} docs | entrada={d['entrada']:,} | "
                    f"saída={d['saida']:,} | NFE={d['nfe']:,} | {meses} meses"
                )

            print("\nComando para processar:")
            for year in sorted(by_year.keys()):
                print(f"  python -m src.main process run --company {result.company_id} --year {year}")
            return 0

    # ── PROCESS ──────────────────────────────────────────────────────────────
    if args.command == "process":
        if args.process_cmd == "run":
            from src.services.process.runner import ProcessConfig, run_year_process
            import re as _re

            if not _re.fullmatch(r"\d{4}", args.year):
                print(f"❌ Formato de ano inválido: '{args.year}'. Use YYYY (ex: 2021).")
                return 2

            year = int(args.year)
            if not (2000 <= year <= 2099):
                print(f"❌ Ano fora do intervalo válido: {year}.")
                return 2

            cfg = ProcessConfig(
                company_id=args.company.strip(),
                year=year,
                limit_docs=args.limit_docs,
            )

            out_path = run_year_process(cfg)
            print(f"✅ Planilha gerada: {out_path}")
            return 0

    print("Comando não reconhecido.")
    return 2