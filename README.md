<div align="center">

<h1>📊 sped-credit-pipeline</h1>

<p><strong>Pipeline automatizado para apuração de créditos PIS/COFINS a partir de XML de NF-e</strong><br>
<em>Automated pipeline for PIS/COFINS tax credit calculation from NF-e XML files</em></p>

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-Proprietary-red?style=flat-square)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/AbraaoNerys/sped-credit-pipeline/ci.yml?style=flat-square&label=CI)](https://github.com/AbraaoNerys/sped-credit-pipeline/actions)

<br>

**Desenvolvido por [Abraão Davi Nerys Frutuoso](https://www.linkedin.com/in/abraão-nerys)**

</div>

---

## 🇧🇷 Português

### O que é?

O **sped-credit-pipeline** é um pipeline em Python desenvolvido para escritórios de contabilidade. Ele lê automaticamente XMLs de **Notas Fiscais Eletrônicas (NF-e)** — sejam arquivos soltos ou dentro de `.zip` — e gera planilhas no layout **SC_A100_A170** prontas para apuração de créditos de **PIS/COFINS** no SPED.

### ✨ Funcionalidades

- 📦 **Extração automática** de XMLs dentro de arquivos `.zip` com proteção anti-ZipSlip
- 🔍 **Inventário inteligente** — escaneia e agrupa documentos por empresa e ano
- ⚡ **Processamento paralelo** — parse de múltiplos XMLs simultâneos com ThreadPoolExecutor
- 💾 **Cache de metadados** — evita reler arquivos já processados em execuções futuras
- 📋 **Exportação anual** — gera um único `SC_A100_A170.xlsx` por ano com todos os meses
- 🏢 **Multi-empresa** — suporte a múltiplas empresas com gestão via CLI
- ✅ **NF-e 3.x e 4.0** — compatível com `detPag/indPag` da versão 4.0
- 🧪 **19 testes automatizados** cobrindo parser, registry e validações
- 🔄 **CI/CD** via GitHub Actions (Python 3.11 e 3.12)

### 📁 Estrutura do Projeto

```
sped-credit-pipeline/
├── .github/
│   └── workflows/
│       └── ci.yml                        # CI/CD GitHub Actions
├── configs/
│   ├── companies.json                    # Empresas cadastradas (não versionar dados reais)
│   └── companies.example.json            # Exemplo de configuração
├── data/
│   ├── input/
│   │   └── <company_id>/
│   │       ├── entrada/                  # XMLs de NF-e entrada (.xml ou .zip)
│   │       └── saida/                    # XMLs de NF-e saída (.xml ou .zip)
│   ├── output/
│   │   └── <company_id>/
│   │       └── <YYYY>/
│   │           └── SC_A100_A170.xlsx     # Planilha gerada por ano
│   └── templates/
│       └── sc_a100_a170_template.xlsx    # Template Excel do layout
├── src/
│   ├── cli/                              # Interface de linha de comando
│   ├── core/                             # Constantes, erros, logging
│   ├── domain/                           # Entidades (Company, CNPJ/CPF)
│   ├── infra/                            # Excel writer, storage, paths
│   ├── services/
│   │   ├── ingest/                       # Scanner e inventário de XMLs
│   │   └── process/                      # Parser NF-e e geração de planilha
│   └── tests/                            # Testes automatizados
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

### ⚙️ Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/AbraaoNerys/sped-credit-pipeline.git
cd sped-credit-pipeline

# 2. Crie o ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows

# 3. Instale as dependências
pip install -e .

# 4. Coloque o template Excel em:
#    data/templates/sc_a100_a170_template.xlsx
```

### 🚀 Como usar

#### 1. Cadastrar empresa
```bash
python -m src.main company add \
  --id tonbraz \
  --razao "Tonbraz LTDA" \
  --cnpj 61146320000149 \
  --regime REAL \
  --estabelecimento 01
```

#### 2. Colocar os XMLs nas pastas
```
data/input/tonbraz/entrada/   → NF-e de compras (entrada)
data/input/tonbraz/saida/     → NF-e de vendas (saída)
```
Aceita arquivos `.xml` soltos ou `.zip` com XMLs dentro.

#### 3. Escanear e inventariar
```bash
python -m src.main ingest scan --company tonbraz --save-report
```

#### 4. Ver anos disponíveis
```bash
python -m src.main ingest plan --company tonbraz
```

#### 5. Gerar planilha anual
```bash
# Processar um ano completo
python -m src.main process run --company tonbraz --year 2024

# Processar vários anos de uma vez (Git Bash / Linux)
for year in 2021 2022 2023 2024 2025; do
  python -m src.main process run --company tonbraz --year $year
done
```

#### Resultado
```
data/output/tonbraz/2024/SC_A100_A170.xlsx
```

### 🛠️ Tecnologias

| Tecnologia | Uso |
|---|---|
| **Python 3.11+** | Linguagem principal |
| **openpyxl** | Leitura e escrita de planilhas Excel |
| **xml.etree.ElementTree** | Parser de XML (stdlib) |
| **ThreadPoolExecutor** | Processamento paralelo |
| **argparse** | Interface CLI (stdlib) |
| **pytest / unittest** | Testes automatizados |
| **GitHub Actions** | CI/CD |

### 🧪 Testes

```bash
python -m unittest discover -s src/tests -p "test_*.py" -v
```

---

## 🇺🇸 English

### What is it?

**sped-credit-pipeline** is a Python pipeline built for accounting firms. It automatically reads **Electronic Invoice (NF-e) XML files** — loose files or inside `.zip` archives — and generates spreadsheets in the **SC_A100_A170 layout** ready for **PIS/COFINS tax credit** calculation in SPED.

### ✨ Features

- 📦 **Automatic extraction** of XMLs from `.zip` files with ZipSlip protection
- 🔍 **Smart inventory** — scans and groups documents by company and year
- ⚡ **Parallel processing** — parses multiple XMLs simultaneously using ThreadPoolExecutor
- 💾 **Metadata cache** — avoids re-reading already processed files
- 📋 **Annual export** — generates a single `SC_A100_A170.xlsx` per year with all months
- 🏢 **Multi-company** — supports multiple companies managed via CLI
- ✅ **NF-e 3.x and 4.0** — compatible with version 4.0 `detPag/indPag` field
- 🧪 **19 automated tests** covering parser, registry and validations
- 🔄 **CI/CD** via GitHub Actions (Python 3.11 and 3.12)

### ⚙️ Installation

```bash
git clone https://github.com/AbraaoNerys/sped-credit-pipeline.git
cd sped-credit-pipeline
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows
pip install -e .
```

### 🚀 Quick Start

```bash
# Register a company
python -m src.main company add --id my-company --razao "My Company Ltd" \
  --cnpj 00000000000000 --regime REAL --estabelecimento 01

# Place XMLs in:
#   data/input/my-company/entrada/   (purchase invoices)
#   data/input/my-company/saida/     (sales invoices)

# Scan and inventory
python -m src.main ingest scan --company my-company --save-report

# Generate annual spreadsheet
python -m src.main process run --company my-company --year 2024
```

### 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| **Python 3.11+** | Core language |
| **openpyxl** | Excel read/write |
| **xml.etree.ElementTree** | XML parsing (stdlib) |
| **ThreadPoolExecutor** | Parallel processing |
| **argparse** | CLI interface (stdlib) |
| **pytest / unittest** | Automated testing |
| **GitHub Actions** | CI/CD |

---

<div align="center">

Desenvolvido com 💙 por **Abraão Davi Nerys Frutuoso**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Abraão%20Nerys-0077B5?style=flat-square&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/abraão-nerys)
[![GitHub](https://img.shields.io/badge/GitHub-AbraaoNerys-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/AbraaoNerys/sped-credit-pipeline)

</div>