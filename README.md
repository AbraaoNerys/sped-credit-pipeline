# sped-credit-pipeline

Pipeline em Python para inventariar e processar XMLs fiscais (NF-e / CF-e) e gerar planilhas no layout **SC_A100_A170** para análise de crédito de **PIS/COFINS**.

> Status atual: ingest (scan/plan) funcionando + exportação inicial para SC_A100_A170 (modo itemizado/por item) com template Excel.

---

## Objetivo

- Receber XMLs de **entrada** e **saída** (geralmente em .zip)
- Fazer staging (descompactar) com segurança
- Inventariar e agrupar por **ano/mês**
- Processar por **lotes mensais**
- Exportar para uma planilha Excel padronizada no layout **SC_A100_A170**

---

## Estrutura de pastas



---

## Pré-requisitos

- Python 3.11+ (recomendado)
- Dependências: `openpyxl`

---

## Configuração do template

Coloque o template do layout aqui:

`data/templates/sc_a100_a170_template.xlsx`

A aba esperada (por padrão) é: `SC_A100_A170`.

---

## Como usar (CLI)

### 1) Cadastrar empresa

```bash
python -m src.main company add \
  --id tonbraz \
  --razao "Tonbraz LTDA" \
  --cnpj  123455678910\
  --regime REAL \
  --estabelecimento 01

Inventariar XMLs (scan)

-python -m src.main ingest scan --company tonbraz

Ver plano de lotes (plan)

-python -m src.main ingest plan --company tonbraz

Gerar planilha por mês (process)

Teste pequeno (debug):

-python -m src.main process run --company tonbraz --month 2021-01 --limit-docs 10

Processamento completo do mês:

-python -m src.main process run --company tonbraz --month 2021-01

Saída:

data/output/<company_id>/<YYYY-MM>/SC_A100_A170.xlsx