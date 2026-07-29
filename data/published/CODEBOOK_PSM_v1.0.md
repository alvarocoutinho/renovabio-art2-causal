# Codebook — RenovaBio PSM Cross-section (v1.0)

**File:** `renovabio_psm_cross_section_v1.0.{csv,parquet}`
**Unit of observation:** Municipality
**Universe:** 2,018 municipalities in Brazilian Centro-Sul (states: SP, GO, MG, MS, PR, MT) after B1 filters
**Release:** 2026-05-22

## Columns

### Identifiers and treatment status
| Column | Type | Description |
|---|---|---|
| `ibge_code` | string(7) | IBGE municipal code (7-digit), zero-padded |
| `municipality` | string | Municipality name |
| `uf` | string(2) | State (SP, GO, MG, MS, PR, MT) |
| `bioma` | string | Biome (Cerrado, Mata Atlantica, etc.) |
| `is_canavieiro` | boolean | Flag for sugarcane-producing municipality (n=842 universe of paper) |
| `is_treated_ever` | boolean | Ever certified by ANP under RenovaBio (n=194 among canavieiros) |
| `treatment_year` | float | Year of first ANP certification (NaN for never-treated) |

### Demographics and economy (baseline 2015-2019)
| Column | Type | Description | Source |
|---|---|---|---|
| `log_pib_total` | float | log(1 + total GDP, R$ thousand) | IBGE PIB Municipal |
| `log_pib_per_capita` | float | log(1 + GDP per capita, R$) | IBGE PIB Municipal |
| `log_population_2017` | float | log(1 + population 2017) | IBGE Estimativa Populacional |
| `log_total_area_ha` | float | log(1 + total area, hectares) | IBGE |
| `population_density` | float | inhab/ha | derived |
| `share_vabc_agriculture` | float | Agriculture share of municipal value added | IBGE PIB Setorial |
| `share_vabc_industry` | float | Industry share | IBGE PIB Setorial |
| `share_vabc_services` | float | Services share | IBGE PIB Setorial |
| `share_vabc_public_admin` | float | Public administration share | IBGE PIB Setorial |

### MapBiomas baseline (mean 2015-2017)
| Column | Type | Description | Source |
|---|---|---|---|
| `mb_share_sugarcane_baseline` | float | Sugarcane share of municipal area | MapBiomas Collection 9 |
| `mb_share_soybean_baseline` | float | Soybean share | MapBiomas Collection 9 |
| `mb_share_pasture_baseline` | float | Pasture share | MapBiomas Collection 9 |
| `mb_share_native_veg_baseline` | float | Native vegetation share | MapBiomas Collection 9 |
| `mb_share_urban_baseline` | float | Urban/infrastructure share | MapBiomas Collection 9 |
| `mb_share_silviculture_baseline` | float | Silviculture share | MapBiomas Collection 9 |
| `mb_share_agriculture_total_baseline` | float | Total agriculture share | MapBiomas Collection 9 |

### PAM baseline (mean 2015-2017)
| Column | Type | Description | Source |
|---|---|---|---|
| `log_sugarcane_area_ha` | float | log(1 + sugarcane area, ha) | IBGE PAM Tabela 1612 |
| `log_soybean_area_ha` | float | log(1 + soybean area, ha) | IBGE PAM 1612 |
| `log_maize_area_ha` | float | log(1 + maize area, ha) | IBGE PAM 1612 |
| `log_cotton_area_ha` | float | log(1 + cotton area, ha) | IBGE PAM 1612 |
| `log_agriculture_total_area_ha` | float | log(1 + total cropped area) | IBGE PAM 1612 |
| `share_sugarcane_of_agriculture` | float | Sugarcane / total cropped area | derived |

### Censo Agropecuário 2017 — Land structure
| Column | Type | Description | Source |
|---|---|---|---|
| `share_family_farms` | float | Family farms (count) / total farms | IBGE Censo Agro 2017 |
| `share_medium_large_farms` | float | Medium-large farms / total farms | IBGE Censo Agro 2017 |
| `share_family_farms_area` | float | Family farms (area) / total area | IBGE Censo Agro 2017 |
| `share_medium_large_farms_area` | float | Medium-large farms (area) / total area | IBGE Censo Agro 2017 |
| `tractors_per_farm` | float | Mechanization proxy | IBGE Censo Agro 2017 |
| `share_irrigated_farms` | float | Share of farms with irrigation | IBGE Censo Agro 2017 |
| `share_irrigated_area` | float | Share of cropped area irrigated | IBGE Censo Agro 2017 |
| `share_financed_farms` | float | Share of farms with rural credit | IBGE Censo Agro 2017 |
| `share_tech_assistance` | float | Share of farms receiving extension | IBGE Censo Agro 2017 |
| `share_natural_vegetation_area` | float | Natural vegetation share of total area | IBGE Censo Agro 2017 |
| `pct_farms_with_energy` | float | Percent of farms with electricity | IBGE Censo Agro 2017 |

### Social indicators (Atlas Brasil 2017/IDHM, Atlas IVS)
| Column | Type | Description | Source |
|---|---|---|---|
| `hdim_education` | float | HDI education component | Atlas Brasil 2017 |
| `hdim_income` | float | HDI income component | Atlas Brasil 2017 |
| `hdim_longevity` | float | HDI longevity component | Atlas Brasil 2017 |
| `social_vulnerability_infrastructure` | float | Urban infrastructure vulnerability (IVS) | Atlas IVS IPEA |
| `social_vulnerability_human_capital` | float | Human capital vulnerability (IVS) | Atlas IVS IPEA |
| `social_vulnerability_income_work` | float | Income-work vulnerability (IVS) | Atlas IVS IPEA |
| `gini_index` | float | Gini index | Atlas Brasil 2017 |

### Estimated propensity scores (optional, if available)
| Column | Type | Description |
|---|---|---|
| `propensity_score_full2` | float | Estimated propensity score, FULL2 specification (33 covariates) |

## Notes

- All log transformations use `log(1+x)` to handle zeros.
- Share variables are clipped to [0, 1] when 80% of values fall in [-0.05, 1.05].
- Missing values imputed with state-level median in main analysis (not in this exported file).
- For full PSM specification and analysis pipeline, see paper Section 3 and supplementary code.
