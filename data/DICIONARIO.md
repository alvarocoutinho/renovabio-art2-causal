# Dicionário de dados

Documentação das variáveis conforme o Plano de Gestão de Dados aprovado
(FAPESP nº 2025/01530-0): nome, unidade, descrição, intervalo temporal e tipo.

**Codificação:** UTF-8
**Formato:** CSV (separador `,`), GeoJSON
**Sistema de coordenadas:** `PREENCHER` (ex.: EPSG:4674 — SIRGAS 2000)
**Recorte temporal:** 2015–2024
**Unidade de análise:** município (geocode IBGE 7 dígitos)

---

## Chaves canônicas

| Chave | Tipo | Formato | Exemplo | Observação |
|---|---|---|---|---|
| `geocode` | string | 7 dígitos com `zfill` | `"3550308"` | **Nunca** `int` — perde zeros à esquerda |
| `muni_key` | string | `MUNICIPIO_NORMALIZADO\|UF` | `"SAO PAULO\|SP"` | Normalização em `pipeline/normalize.py` |
| `cidade_uf_seeg` | string | `Município (UF)` | `"São Paulo (SP)"` | Formato literal do SEEG |

## Convenções de tipagem

| Regra | Detalhe |
|---|---|
| Geocodes | Sempre `string` |
| Anos | Sempre `int` |
| Outcomes AFOLU | `float`, escala bruta em gCO₂eq |
| Transformações | Colunas separadas com prefixo (`log_`, `log1p_`, `asinh_`) |

---

## Camada `interim/`

### `crosswalk_centrosul.csv`
Tabela de correspondência entre as três chaves canônicas.

| Variável | Tipo | Unidade | Descrição |
|---|---|---|---|
| `PREENCHER` | | | |

### `anp_muni_treat.csv`
Indicador de tratamento municipal derivado da certificação ANP.

| Variável | Tipo | Unidade | Descrição |
|---|---|---|---|
| `geocode` | string | — | Chave municipal |
| `PREENCHER` (coorte de tratamento) | int | ano | Ano da primeira certificação — define a coorte `g` do CS-DR |
| `PREENCHER` | | | |

### `seeg_outcomes_balanced.csv`
Outcomes AFOLU balanceados por município-ano.

| Variável | Tipo | Unidade | Descrição |
|---|---|---|---|
| `PREENCHER` | float | gCO₂eq | |

### `pam_cana_long.csv`
Produção, área colhida e rendimento da cana (PAM/IBGE), formato longo.

| Variável | Tipo | Unidade | Descrição |
|---|---|---|---|
| `PREENCHER` | | | |

### `mapbiomas_panel.csv`
Cobertura e uso do solo por município-ano.

| Variável | Tipo | Unidade | Descrição |
|---|---|---|---|
| `PREENCHER` | | ha | |

### `psm_baseline_full.csv`
Covariáveis socioeconômicas de linha de base para pareamento.

| Variável | Tipo | Unidade | Descrição |
|---|---|---|---|
| `PREENCHER` | | | |

### `seeg_outcomes_audited.csv`
Outcomes após auditoria de cobertura.

| Variável | Tipo | Unidade | Descrição |
|---|---|---|---|
| `PREENCHER` | | | |

---

## Camada `processed/`

### `painel_completo.csv`
Painel municipal completo, pronto para modelagem.

| Variável | Tipo | Unidade | Descrição |
|---|---|---|---|
| `PREENCHER` | | | |

### `painel_canavieiro.csv`
Subamostra do universo canavieiro.

| Variável | Tipo | Unidade | Descrição |
|---|---|---|---|
| `PREENCHER` | | | |

---

## Mecanismos e decomposição

| Componente | Definição | Unidade |
|---|---|---|
| Efeito de intensidade | `PREENCHER` | |
| Efeito de escala | `PREENCHER` | |
| Canal de maior contribuição positiva | `PREENCHER` | |

---

## Parâmetros de identificação

| Parâmetro | Valor | Âncora no pré-registro |
|---|---|---|
| Estimador | Callaway–Sant'Anna doubly robust (CS-DR) | Seção `PREENCHER` |
| Grupo de comparação | `PREENCHER` (never-treated / not-yet-treated) | Seção `PREENCHER` |
| Período de tratamento | `PREENCHER` | Seção `PREENCHER` |
| Agregação dos ATT(g,t) | `PREENCHER` (simple / dynamic / group / calendar) | Seção `PREENCHER` |
| Inferência | `PREENCHER` (bootstrap multiplicador / clusterizado) | Seção `PREENCHER` |
| Nº de repetições bootstrap | `PREENCHER` | Seção `PREENCHER` |
| Semente aleatória | `PREENCHER` | `configs/pipeline.yaml` |
| Covariáveis do PSM | `PREENCHER` | Seção `PREENCHER` |

> **Nota metodológica.** O SDID previsto no projeto original foi substituído pelo
> CS-DR. A justificativa da alteração consta do Relatório Científico Final e do
> pré-registro consolidado.

---

## Outputs

| Arquivo | Conteúdo | Seção do manuscrito |
|---|---|---|
| `PREENCHER` | | |
