# Intensity Gains, Scale Effects: Causal Inference and Emissions Impact of Brazil's National Biofuels Policy

[![DOI](https://zenodo.org/badge/1314185166.svg)](https://doi.org/10.5281/zenodo.21675951)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Pacote de replicação do manuscrito submetido a *Ecological Economics* (Elsevier).

**Autores:** Alvaro Luz Alves Coutinho, Alexandre Nunes de Almeida, Roberto Fray da Silva, Gabriel Adrián Sarriés

**DOI (todas as versões):** [10.5281/zenodo.21675951](https://doi.org/10.5281/zenodo.21675951)
**DOI (v1.0.1):** [10.5281/zenodo.21675952](https://doi.org/10.5281/zenodo.21675952)
**Pré-registro:** v2.6

---

## Resumo

Avaliação causal dos efeitos do programa RenovaBio sobre emissões AFOLU municipais
no Centro-Sul brasileiro, com decomposição entre ganhos de intensidade produtiva e
efeitos de escala. Identificação por *propensity score matching* seguido do estimador
Callaway–Sant'Anna doubly robust (CS-DR) sobre painel municipal com tratamento
escalonado.

| Dimensão | Escopo |
|---|---|
| Recorte espacial | SP, GO, MG, PR, MS, MT (Centro-Sul, sem ES) |
| Janela principal | 2015–2024 |
| Janela de robustez | 2012–2024 |
| Universo analítico | 842 municípios canavieiros |
| Municípios tratados | 194 |

---

## Pré-registro e hipóteses

O desenho foi pré-registrado (v2.6). As hipóteses e o estado de cada uma:

| Hipótese | Desfechos | Situação |
|---|---|---|
| **H1a** (primária) | `log_luc` | Testada |
| **H1b** (secundária) | `carbono_solo` | Testada |
| **H1c** | `cobertura_car_ativo`, `adesao_pra`, `cobertura_veg_nativa` | **Não testada** — ver abaixo |
| **H2** (primária) | `log_solos_manejados` | Testada |
| **H2** (secundária) | `log_queima` | Testada |

> **Sobre a hipótese H1c.** Os três desfechos pré-registrados para H1c derivam do
> Sistema Nacional de Cadastro Ambiental Rural (SICAR). A fonte foi descartada no
> curso da pesquisa, por inadequação da unidade de análise — o desenho final opera
> em nível municipal, não de imóvel rural — e por envolver dados pessoais de
> titulares identificáveis, sujeitos à LGPD. **A decisão é anterior e independente
> dos resultados obtidos para as demais hipóteses.** A exclusão está registrada na
> Seção 2.3 do Relatório Científico Final do processo FAPESP nº 2025/01530-0.
>
> O código relativo ao SICAR permanece no repositório em estado vestigial
> (`pipeline/sicar.py`, `notebooks/06_sicar.ipynb`, constante `OUTCOMES_H1C` em
> `pipeline/config.py`), não integrando nenhuma rotina ativa. É preservado como
> registro da trajetória metodológica.

Os parâmetros do pré-registro estão congelados em `pipeline/config.py`, na classe
`Params`, com referência à seção correspondente do documento.

---

## Estrutura e fluxo de execução

```
├── pipeline/           # módulos importados pelos notebooks
├── notebooks/          # execução em cadeia, na ordem numérica
├── configs/            # pipeline.yaml
├── data/
│   ├── raw/            # NÃO versionado — ver MANIFEST.md
│   ├── interim/        # NÃO versionado — intermediários regeneráveis
│   ├── published/      # datasets citáveis que acompanham o manuscrito
│   └── DICIONARIO.md
└── outputs/
    ├── tables/         # tabelas de resultado (VERSIONADAS)
    └── figures/        # figuras do manuscrito
```

### DAG

**Camada 1 — preparação de dados** (`data/raw/` → `data/interim/`)

| Notebook | Produz |
|---|---|
| `00_setup` | Validação dos insumos brutos — não processa |
| `01_crosswalk` | Chaves canônicas `geocode` / `muni_key` / `cidade_uf_seeg` |
| `02_anp` | Coortes de tratamento a partir dos certificados |
| `03_seeg` | Desfechos de emissão balanceados |
| `04_pam` | Série da cana (PAM/IBGE) |
| `04b_seeg_subcanais` | Desagregação dos canais de emissão |
| `04c_share_cana_pre2018` | Share de cana pré-tratamento |
| `05_mapbiomas` | Painel de uso do solo (Coleção 10.1) |
| `09_panel_assembly` | Painel completo e painel canavieiro |

**Camada 2 — pareamento** (`data/interim/` → `outputs/tables/`)

| Notebook | Papel | Produz |
|---|---|---|
| `07_psm_baseline` | **Prepara** as covariáveis | `psm_baseline_clean.csv` (interim) |
| `10_psm_baseline_v2` | **Executa** o pareamento | `psm_pscores_weights`, `psm_balance_smd`, `psm_support_masks`, `psm_support_summary`, `psm_diagnostics` |

> Os dois são canônicos e complementares: `07` limpa e chaveia, `10` estima o
> escore de propensão e define o suporte comum. O sufixo `_v2` é herança de
> nomenclatura e não indica substituição.

**Camada 3 — estimação** (`outputs/tables/`)

| Notebook | Conteúdo | Tabelas |
|---|---|---|
| `11a_estimacao_t1_v4` | ATT do tratamento binário escalonado | `att_t1_main`, `att_t1_eventstudy_luc`, `att_t1_bacon` |
| `11b_estimacao_t2t3` | Doses T2 (volume) e T3 (NEEA) | `att_t2t3_main`, `att_t2t3_eventstudy_luc` |
| `11c_outcomes_derivados` | Desfechos derivados; contraste CS-DR × Sun-Abraham × TWFE | `att_derived_outcomes`, `att_derived_eventstudy` |
| `11d_decomposicao_mecanistica` | Decomposição por canal de emissão | `att_canais_*` |
| `11e_substituicao_area` | Substituição de área (PAM e MapBiomas) | `att_substituicao_*` |
| `11f_event_studies_pretrends` | Event studies e testes de pré-tendência | `event_study_*`, `pretrend_test_consolidado` |
| `11g_heterogeneidade_share` | Heterogeneidade por tercil de share e dose-resposta | `att_b4m5_*`, `b4m5_tercil_info` |
| `11h_balanco_co2eq` | Balanço de CO₂eq (SAR e AR6) e intensidade de carbono | `b4m7_*`, `b4m8_*` |
| `11i_figures_manuscript` | Figuras do manuscrito | `outputs/figures/manuscript/` |
| `11j_exportar_dados_publicacao` | Datasets citáveis | `data/published/` |

**Notebook legado:** `06_sicar` — não integra o fluxo (ver seção Pré-registro).

---

## Como reproduzir

```bash
git clone https://github.com/alvarocoutinho/renovabio-art2-causal.git
cd renovabio-art2-causal

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Os caminhos são resolvidos automaticamente a partir da raiz do repositório. Para
executar a partir de outro diretório:

```python
import os
os.environ["RENOVABIO_BASE_DIR"] = "/caminho/para/o/projeto"
```

1. Obtenha os dados brutos conforme `data/raw/MANIFEST.md` e verifique os hashes
2. Execute `00_setup` para validar os insumos
3. Execute os notebooks na ordem numérica

Cada camada lê da anterior. Se uma falhar, corrija e reexecute apenas ela — os
produtos anteriores permanecem válidos.

### Nota sobre o escopo da replicação

Este é um **pacote de evidência documentada**, não um pacote de execução
autocontida. As fontes primárias somam volume incompatível com controle de
versão e, em parte, com redistribuição.

O que é verificável sem acesso às fontes brutas:

- As **tabelas de resultado** em `outputs/tables/`, que sustentam todos os números
  do manuscrito
- Os **datasets publicados** em `data/published/`, com codebooks
- Os **notebooks executados**, cujos outputs preservados registram cada etapa
- Os **parâmetros do pré-registro**, congelados em `pipeline/config.py`

Quem quiser reexecutar do zero precisa obter as fontes conforme o manifesto.

---

## Convenções

**Chaves canônicas.** Toda camada expõe pelo menos uma de: `geocode` (IBGE 7
dígitos, string com `zfill`), `muni_key` (`MUNICIPIO_NORMALIZADO|UF`),
`cidade_uf_seeg` (formato literal SEEG).

**Tipagem.** Geocodes são sempre `string` — nunca `int`, que perde zeros à
esquerda. Anos sempre `int`. Emissões em escala bruta são `float`; transformações
(`log`, `log1p`, `asinh`) ficam em colunas separadas com prefixo correspondente.

**Especificações.** Os ATT são reportados em quatro conjuntos de covariáveis —
`LEAN`, `FULL`, `FULL2`, `RICH` — mais os contrastes de estimador
(`sa_canonical`, `twfe_classic`) em `att_derived_outcomes`.

---

## Dados e licenciamento

Dados derivados em `data/published/` e `outputs/` são produto desta pesquisa,
sob CC BY 4.0. Dados brutos de terceiros não são redistribuídos — ver
`data/raw/MANIFEST.md`.

- **Código** (`pipeline/`, `notebooks/`): MIT — ver `LICENSE`
- **Dados derivados e outputs**: CC BY 4.0 — ver `LICENSE-DATA`

## Como citar

Ver `CITATION.cff` ou o botão *Cite this repository* no GitHub.

## Transparência sobre ferramentas de apoio

Partes do código deste pipeline foram desenvolvidas com assistência de ferramenta
de IA generativa. O desenho metodológico, as decisões de identificação causal, a
validação dos resultados e a redação científica são de responsabilidade exclusiva
dos autores.

## Financiamento

This study was financed, in part, by the São Paulo Research Foundation (FAPESP),
Brazil. Process Number #2025/01530-0.
