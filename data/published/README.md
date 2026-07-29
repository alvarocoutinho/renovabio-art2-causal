# RenovaBio Causal Impact Dataset — v1.0

This dataset accompanies the paper:

> Coutinho, A. L. A. (2026). *Causal impact of RenovaBio biofuel certification on
> municipal agricultural GHG emissions in Brazil's Centro-Sul: a propensity score
> matching + Callaway-Sant'Anna difference-in-differences study*. Submitted to
> Ecological Economics.

**Author:** Alvaro L. A. Coutinho (PPGI-EA, ESALQ/USP — alvaro.coutinho@usp.br)
**Release date:** 2026-05-22
**Version:** v1.0
**Licence:** CC-BY 4.0 (free use with attribution)

## Files

| File | Description | Rows | Columns |
|---|---|---:|---:|
| `renovabio_psm_cross_section_v1.0.csv/parquet` | Cross-section for PSM matching | ~2,018 | ~45 |
| `renovabio_outcomes_panel_v1.0.csv/parquet` | Long panel of outcomes | ~10,946 | ~30 |
| `CODEBOOK_PSM_v1.0.md` | Variable documentation for PSM | — | — |
| `CODEBOOK_PANEL_v1.0.md` | Variable documentation for panel | — | — |

## Quick-start

```python
import pandas as pd

# Load PSM cross-section
psm = pd.read_parquet("renovabio_psm_cross_section_v1.0.parquet")
print(psm.shape)  # (~2018, ~45)
print(psm["is_treated_ever"].sum())  # 194 treated municipalities

# Load outcomes panel
panel = pd.read_parquet("renovabio_outcomes_panel_v1.0.parquet")
print(panel.shape)  # (~10946, ~30)
panel.groupby("year")["emissions_sugarcane_direct_tco2e"].sum().plot()
```

## Universe

- **Geographic scope:** Brazil Centro-Sul region (states SP, GO, MG, MS, PR, MT)
- **Total municipalities (pre-filter):** ~2,018 in PSM cross-section
- **Sugarcane municipalities (canavieiros):** 842 (analytical universe of the paper)
- **Treated municipalities:** 194 (ever certified by ANP under RenovaBio)
- **Time coverage:**
  - SEEG emissions: 2012–2024 (13 years)
  - PAM agricultural: 2012–2024
  - MapBiomas: 2015–2024 (Collection 9 limit)

## Data sources

This dataset integrates multiple public Brazilian government datasets:

| Source | Data used | Provider |
|---|---|---|
| SEEG Coleção 9 | Municipal GHG emissions by sector and gas | Observatório do Clima / Imaflora |
| IBGE PAM 1612 | Crop areas and production | IBGE |
| IBGE Censo Agro 2017 | Land structure and farm characteristics | IBGE |
| MapBiomas Collection 9 | Annual land use shares | MapBiomas Project |
| ANP Resoluções 22-32/2018 + 758/2018 + posterior | RenovaBio certification dates | ANP |
| IBGE PIB Municipal | Economic indicators | IBGE |
| Atlas Brasil / Atlas IVS | Social indicators (HDI, GINI, IVS) | UNDP / IPEA |

## Methodology

The data integration and analytical pipeline are documented in:
- Paper Section 3 (Methods)
- Pre-registration `preregistro_renovabio_consolidado_v26.md` (request from author)
- Source code (request from author)

## Reproducibility

The dataset is provided in two formats:
- **CSV** for human inspection and language-agnostic analysis
- **Parquet** for efficient analytical workloads (preserves dtypes)

Both versions contain identical data.

## Citation

If you use this dataset, please cite:

```
@article{coutinho2026renovabio,
  title={Causal impact of RenovaBio biofuel certification on municipal
         agricultural GHG emissions in Brazil's Centro-Sul},
  author={Coutinho, Alvaro L. A.},
  journal={Ecological Economics},
  year={2026},
  note={Dataset version v1.0, released 2026-05-22}
}
```

## Contact

Questions, errata, or collaboration inquiries:
- **Email:** alvaro.coutinho@usp.br
- **Institution:** ESALQ/USP — Piracicaba, SP, Brazil
- **ORCID:** [TO BE FILLED]
- **GitHub:** [TO BE FILLED]

## Changelog

- **v1.0** (2026-05-22): initial public release.
