# RenovaBio Causal Impact Dataset — v1.0

This dataset accompanies the paper:

> Coutinho, A. L. A., Almeida, A. N., Silva, R. F., & Sarriés, G. A. (2026).
> *Intensity Gains, Scale Effects: Causal Inference and Emissions Impact of
> Brazil's National Biofuels Policy*. Submitted to Ecological Economics.

**Corresponding author:** Alvaro L. A. Coutinho (PPGI-EA, ESALQ/USP — alvaro.coutinho@usp.br)
**Version:** v1.0
**Licence:** CC BY 4.0 (free use with attribution)

---

## Files

| File | Description | Rows | Columns |
|---|---|---:|---:|
| `renovabio_psm_cross_section_v1.0.csv` | Cross-section for PSM matching | 5,570 | 47 |
| `renovabio_outcomes_panel_v1.0.csv` | Long panel of outcomes | 8,420 | 22 |
| `CODEBOOK_PSM_v1.0.md` | Variable documentation for the cross-section | — | — |
| `CODEBOOK_PANEL_v1.0.md` | Variable documentation for the panel | — | — |

Distributed as CSV (UTF-8, comma-separated) — an open, language-agnostic format
suited to long-term preservation.

SHA-256 checksums for every file are recorded in `data/raw/MANIFEST.md` of the
replication repository.

## Quick-start

```python
import pandas as pd

# Cross-section used for propensity score matching
psm = pd.read_csv("renovabio_psm_cross_section_v1.0.csv", dtype={"geocode": str})
print(psm.shape)                       # (5570, 47)
print(psm["is_treated_ever"].sum())    # 194 treated municipalities

# Long panel of outcomes
panel = pd.read_csv("renovabio_outcomes_panel_v1.0.csv", dtype={"geocode": str})
print(panel.shape)                     # (8420, 22)
```

> **Note.** Municipality codes (`geocode`) must be read as strings. Reading them
> as integers strips leading zeros and silently corrupts the merge keys.

## Universe

- **Geographic scope:** Brazil's Centro-Sul region (SP, GO, MG, MS, PR, MT)
- **Cross-section coverage:** 5,570 municipalities
- **Sugarcane municipalities (*canavieiros*):** 842 — the analytical universe of the paper
- **Treated municipalities:** 194 (ever certified by ANP under RenovaBio)
- **Panel:** 842 municipalities × 10 years = 8,420 rows
- **Main analytical window:** 2015–2024
- **Robustness window:** 2012–2024

## Data sources

| Source | Data used | Provider |
|---|---|---|
| SEEG (AR6) | Municipal GHG emissions by sector and gas | Observatório do Clima / Imaflora |
| IBGE PAM, table 1612 | Crop area and production | IBGE |
| IBGE Censo Agropecuário 2017 | Land structure and farm characteristics | IBGE |
| MapBiomas Collection 10.1 | Annual land use shares | MapBiomas Project |
| ANP | RenovaBio certification records | ANP |
| IBGE PIB Municipal | Economic indicators | IBGE |
| Atlas Brasil / Atlas IVS | Social indicators (HDI, GINI, IVS) | UNDP / IPEA |

Full source documentation — URLs, access dates, collection versions and
checksums — is in `data/raw/MANIFEST.md` of the replication repository.

> **Retroactive revision.** SEEG, PAM and MapBiomas revise historical series
> between editions. Results depend on the specific edition used; see the
> manifest for the exact versions.

## Methodology

- Paper, Section 3 (Methods)
- Pre-registration v2.6
- Replication package: https://github.com/alvarocoutinho/renovabio-art2-causal

Identification proceeds by propensity score matching followed by the
Callaway–Sant'Anna doubly robust estimator (CS-DR) on a staggered-treatment
municipal panel. Result tables supporting every figure in the paper are in
`outputs/tables/` of the replication repository.

## Citation

```bibtex
@article{coutinho2026renovabio,
  title   = {Intensity Gains, Scale Effects: Causal Inference and Emissions
             Impact of Brazil's National Biofuels Policy},
  author  = {Coutinho, Alvaro L. A. and Almeida, Alexandre Nunes de and
             Silva, Roberto Fray da and Sarri{\'e}s, Gabriel Adri{\'a}n},
  journal = {Ecological Economics},
  year    = {2026},
  note    = {Dataset version v1.0}
}
```

## Contact

- **Email:** alvaro.coutinho@usp.br
- **Institution:** ESALQ/USP — Piracicaba, SP, Brazil
- **ORCID:** https://orcid.org/0009-0002-5118-0972
- **Repository:** https://github.com/alvarocoutinho/renovabio-art2-causal

## Funding

This study was financed, in part, by the São Paulo Research Foundation (FAPESP),
Brazil. Process Number #2025/01530-0.

## Changelog

- **v1.0** — initial public release.
