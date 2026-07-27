# Intensity Gains, Scale Effects: Causal Inference and Emissions Impact of Brazil's National Biofuels Policy

Pacote de replicação do manuscrito submetido a *Ecological Economics* (Elsevier).

**Autores:** Alvaro Luz Alves Coutinho, Alexandre Nunes de Almeida, Roberto Fray da Silva, Gabriel Adrián Sarriés

**DOI:** `10.5281/zenodo.XXXXXXX` <!-- substituir pelo concept DOI após o primeiro release -->

**Versão:** `PREENCHER` <!-- 0.1.0-skeleton era a versão anterior; atualizar -->

---

## Resumo

Avaliação causal dos efeitos do programa RenovaBio sobre emissões AFOLU municipais
no Centro-Sul brasileiro (2015–2024), com decomposição entre ganhos de intensidade
produtiva e efeitos de escala. O desenho de identificação segue o pré-registro
consolidado (v`PREENCHER`) e emprega o estimador Callaway–Sant'Anna doubly robust
(CS-DR), em substituição ao SDID previsto originalmente.

---

## Estrutura

```
├── data/
│   ├── raw/          # bases brutas — NÃO versionadas (ver MANIFEST.md)
│   ├── interim/      # bases limpas e chaveadas, sem decisão metodológica
│   ├── processed/    # painéis finais para modelagem
│   └── DICIONARIO.md
├── pipeline/         # módulos Python importados pelos notebooks
├── notebooks/        # orquestrador + validações por camada
├── configs/          # pipeline.yaml
├── outputs/          # tabelas e figuras do manuscrito
└── requirements.txt
```

### Hierarquia de dados em 3 níveis

- **`data/raw/`** — fontes brutas, exatamente como vieram. Nunca editar, substituir
  ou deletar. **Não redistribuídas neste repositório** — ver `data/raw/MANIFEST.md`.
- **`data/interim/`** — dados limpos e chaveados pela função normalizadora, sem
  decisão metodológica de modelagem (sem `fillna` agressivo, sem filtros de amostra).
- **`data/processed/`** — painéis finais, prontos para PSM / CS-DR.

---

## Como reproduzir

1. Instale as dependências:

   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Obtenha os dados brutos conforme `data/raw/MANIFEST.md` e verifique os hashes.

3. Execute os notebooks na ordem numérica. Cada camada lê da anterior; se uma
   falhar, corrija e reexecute apenas ela — os outputs anteriores permanecem válidos.

| Notebook | Saída em `interim/` |
|---|---|
| `00_setup.ipynb` | (apenas validação do raw) |
| `01_crosswalk.ipynb` | `crosswalk_centrosul.csv` |
| `02_anp.ipynb` | `anp_muni_treat.csv` |
| `03_seeg.ipynb` | `seeg_outcomes_balanced.csv` |
| `04_pam.ipynb` | `pam_cana_long.csv` |
| `05_mapbiomas.ipynb` | `mapbiomas_panel.csv` |
| `07_psm_baseline.ipynb` | `psm_baseline_full.csv` |
| `08_coverage_audit.ipynb` | `seeg_outcomes_audited.csv` |
| `09_assembly.ipynb` | painel completo + canavieiro |

> **Nota.** A camada SICAR constante de versões anteriores do pipeline foi
> descontinuada e não integra a análise final.

O `00_setup.ipynb` não processa nada: monta o ambiente, adiciona `pipeline/` ao
`sys.path`, inventaria `data/raw/`, valida encoding/separador/shape de cada arquivo
e reporta cobertura por UF e período.

---

## Convenções

### Chaves canônicas

Toda camada expõe pelo menos uma destas três chaves:

- `geocode` — IBGE 7 dígitos, **string** com `zfill` (ex.: `"3550308"`)
- `muni_key` — `MUNICIPIO_NORMALIZADO|UF` (ex.: `"SAO PAULO|SP"`)
- `cidade_uf_seeg` — formato literal SEEG `Município (UF)`

### Tipagem

- Geocodes são **sempre** string. Nunca `int` — perde zeros à esquerda.
- Anos são sempre `int`.
- Outcomes AFOLU em escala bruta (gCO₂eq) são `float`; transformações
  (`log` / `log1p` / `asinh`) ficam em colunas separadas com prefixo correspondente.

### Reprodutibilidade

Semente única declarada em `configs/pipeline.yaml`, governando todos os
procedimentos estocásticos (bootstrap do CS-DR, matching do PSM).

### Pré-registro

Toda decisão metodológica tem âncora explícita em uma seção do
`preregistro_renovabio_consolidado_v PREENCHER.md`. Os módulos referenciam por
docstring. Para auditar uma decisão, leia primeiro a seção correspondente do
pré-registro.

---

## Dados

Dados derivados em `data/interim/`, `data/processed/` e `outputs/` são produto desta
pesquisa, sob licença CC BY 4.0.

Dados brutos de terceiros (ANP, IBGE/PAM, SEEG, MapBiomas, e demais fontes do
baseline socioeconômico) **não são redistribuídos**. Fontes, URLs, datas de acesso,
versões e hashes SHA-256 constam em `data/raw/MANIFEST.md`.

## Licenciamento

- **Código** (`pipeline/`, `notebooks/`): MIT — ver `LICENSE`
- **Dados derivados e outputs**: CC BY 4.0 — ver `LICENSE-DATA`

## Como citar

Ver `CITATION.cff` ou o botão *Cite this repository* no GitHub.

## Transparência sobre ferramentas de apoio

Partes do código deste pipeline foram desenvolvidas com assistência de ferramenta de
IA generativa (Claude, Anthropic). Todo o desenho metodológico, as decisões de
identificação causal, a validação dos resultados e a redação científica são de
responsabilidade exclusiva dos autores. Esta nota deve ser mantida consistente com
a declaração de uso de IA apresentada ao periódico.

## Financiamento

This study was financed, in part, by the São Paulo Research Foundation (FAPESP),
Brazil. Process Number #2025/01530-0.
