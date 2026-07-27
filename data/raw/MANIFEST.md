# Manifesto de dados brutos

Este diretório **não contém dados**. As fontes primárias não são redistribuídas
neste repositório; permanecem sujeitas às licenças e termos de uso de seus
provedores originais.

A tabela abaixo permite obter e **verificar** os mesmos arquivos utilizados na
análise. O hash SHA-256 é o que garante que você recebeu exatamente o arquivo que
gerou os resultados publicados — SEEG e PAM revisam séries retroativamente, e uma
URL viva não é garantia de reprodutibilidade.

## Como gerar e verificar os hashes

```bash
# Linux / macOS — gera para todos os arquivos de uma pasta
find data/raw -type f -exec sha256sum {} \; > hashes.txt
```

```powershell
# Windows (PowerShell)
Get-ChildItem -Recurse data\raw -File | Get-FileHash -Algorithm SHA256 |
  Select-Object Hash, Path | Export-Csv hashes.csv -NoTypeInformation
```

Divergência entre o hash obtido e o registrado significa que a fonte foi revisada
desde o acesso original — nesse caso, os resultados podem não replicar exatamente.

---

## Fontes

### 1. ANP — `data/raw/anp/`

Certificação RenovaBio e Nota de Eficiência Energético-Ambiental.

| Arquivo | URL | Data de acesso | Versão | SHA-256 | Licença |
|---|---|---|---|---|---|
| `PREENCHER.xlsx` | https://www.gov.br/anp/ | AAAA-MM-DD | — | `PREENCHER` | Dados abertos governamentais |
| `PREENCHER.xlsx` | | AAAA-MM-DD | | `PREENCHER` | |
| `PREENCHER.xlsx` | | AAAA-MM-DD | | `PREENCHER` | |
| `NEEA.csv` | | AAAA-MM-DD | | `PREENCHER` | |

### 2. SEEG — `data/raw/seeg/`

Emissões AFOLU municipais. **6 CSVs, um por UF.**

| Arquivo (UF) | URL | Data de acesso | Coleção | SHA-256 | Licença |
|---|---|---|---|---|---|
| `PREENCHER_SP.csv` | https://seeg.eco.br/ | AAAA-MM-DD | Coleção nº | `PREENCHER` | CC BY-SA (confirmar) |
| `PREENCHER_MG.csv` | | AAAA-MM-DD | | `PREENCHER` | |
| `PREENCHER_GO.csv` | | AAAA-MM-DD | | `PREENCHER` | |
| `PREENCHER_MS.csv` | | AAAA-MM-DD | | `PREENCHER` | |
| `PREENCHER_MT.csv` | | AAAA-MM-DD | | `PREENCHER` | |
| `PREENCHER_PR.csv` | | AAAA-MM-DD | | `PREENCHER` | |

> **Crítico.** Registrar o número da coleção/edição do SEEG. O sistema revisa
> séries históricas inteiras entre edições; sem essa identificação os outcomes
> não são reproduzíveis. Verificar se o SEEG mantém arquivo público das edições
> anteriores — se não mantiver, considerar o depósito do snapshot bruto no
> Zenodo, apesar do volume.

### 3. IBGE — `data/raw/ibge/`

| Arquivo | Fonte | URL | Data de acesso | Referência | SHA-256 | Licença |
|---|---|---|---|---|---|---|
| PAM tabela 1612 | SIDRA | https://sidra.ibge.gov.br/tabela/1612 | AAAA-MM-DD | Anos AAAA–AAAA | `PREENCHER` | Dados abertos |
| Universo core | | | AAAA-MM-DD | | `PREENCHER` | |
| GeoJSON malha municipal | Malhas territoriais | https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais.html | AAAA-MM-DD | Ano ref. AAAA | `PREENCHER` | Dados abertos |

### 4. MapBiomas — `data/raw/mapbiomas/`

| Arquivo | URL | Data de acesso | Coleção | SHA-256 | Licença |
|---|---|---|---|---|---|
| `panel_ready.csv` | https://brasil.mapbiomas.org/ | AAAA-MM-DD | Coleção nº | `PREENCHER` | CC BY-SA 4.0 |
| `statistics_raw.csv` | | AAAA-MM-DD | | `PREENCHER` | CC BY-SA 4.0 |

> **Atenção à licença.** CC BY-SA impõe compartilhamento pela mesma licença aos
> produtos derivados. Verificar a compatibilidade com a publicação dos dados
> derivados sob CC BY 4.0 antes do release definitivo.

### 5. Baseline socioeconômico (PSM) — `data/raw/psm_baseline/`

Covariáveis de pareamento.

| Arquivo | Fonte | URL | Data de acesso | Referência | SHA-256 | Licença |
|---|---|---|---|---|---|---|
| `PREENCHER` | `PREENCHER` | | AAAA-MM-DD | | `PREENCHER` | |

---

## Fontes descartadas no curso da pesquisa

- **SICAR** — previsto no Plano de Gestão de Dados original e presente em versões
  anteriores do pipeline (`data/raw/sicar/`, `pipeline/sicar.py`,
  `06_sicar.ipynb`). Descontinuado; não integra a análise final. Ver Seção 2.3 do
  Relatório Científico Final.

---

## Cobertura

| Dimensão | Escopo |
|---|---|
| Recorte temporal | 2015–2024 |
| Recorte espacial | Centro-Sul — UFs: `PREENCHER` |
| Unidade de análise | Município (geocode IBGE 7 dígitos) |
| Nº de municípios no painel | `PREENCHER` |

---

## Dados derivados

Produtos desta pipeline estão em `data/interim/`, `data/processed/` e `outputs/`,
sob licença CC BY 4.0. Ver `data/DICIONARIO.md`.
