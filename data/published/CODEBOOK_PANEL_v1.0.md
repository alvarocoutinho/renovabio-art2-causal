# Codebook — RenovaBio Outcomes Panel (v1.0)

**File:** `renovabio_outcomes_panel_v1.0.{csv,parquet}`
**Unit of observation:** Municipality × year
**Universe:** 842 sugarcane municipalities (canavieiros) × 13 years (2012-2024) = up to 10,946 rows
**Release:** 2026-05-22

## Columns

### Identifiers
| Column | Type | Description |
|---|---|---|
| `ibge_code` | string(7) | IBGE municipal code (7-digit), zero-padded |
| `year` | int | Year of observation |
| `municipality` | string | Municipality name |
| `uf` | string(2) | State |
| `bioma` | string | Biome |
| `is_treated_ever` | boolean | Ever certified by ANP under RenovaBio |
| `treatment_year` | float | Year of first ANP certification |
| `is_post_treatment` | boolean | Is this observation in the post-treatment period for the municipality |

### SEEG emissions — totals (tCO2eq/year, GWP-AR5)
| Column | Type | Description | Source |
|---|---|---|---|
| `emissions_burning_tco2e` | float | Burning of agricultural residues | SEEG Coleção 9 |
| `emissions_soils_managed_tco2e` | float | Managed soils (sum of N inputs, residues) | SEEG Coleção 9 |
| `emissions_luc_tco2e` | float | Land use change | SEEG Coleção 9 |
| `emissions_carbon_soil_tco2e` | float | Soil carbon flux | SEEG Coleção 9 |

### SEEG emissions — sugarcane decomposition (tCO2eq/year, GWP-AR5)
| Column | Type | Description | SEEG Equation |
|---|---|---|---|
| `emissions_sugarcane_residues_tco2e` | float | Residues left after sugarcane harvest (N2O from decomposition) | Eq. 62-66 |
| `emissions_sugarcane_organic_tco2e` | float | Organic inputs from sugarcane (filter cake, vinasse) | Eq. 40, 42 |
| `emissions_sugarcane_direct_tco2e` | float | Sum of residues + organic (consolidated, used as main outcome) | derived |
| `emissions_n_fertilizer_tco2e` | float | Synthetic N fertilizers | Eq. 52-54 |
| `emissions_liming_tco2e` | float | Liming (calcium oxide application) | Eq. 89, 9 |
| `emissions_other_residues_tco2e` | float | Residues other than sugarcane | Eq. 60-61 |

### PAM agricultural production (areas in hectares, production in tonnes)
| Column | Type | Description | Source |
|---|---|---|---|
| `area_sugarcane_ha` | float | Sugarcane cropped area | IBGE PAM 1612 |
| `area_soybean_ha` | float | Soybean cropped area | IBGE PAM 1612 |
| `area_maize_ha` | float | Maize cropped area | IBGE PAM 1612 |
| `area_cotton_ha` | float | Cotton cropped area | IBGE PAM 1612 |
| `production_sugarcane_t` | float | Sugarcane production | IBGE PAM 1612 |
| `production_soybean_t` | float | Soybean production | IBGE PAM 1612 |
| `production_maize_t` | float | Maize production | IBGE PAM 1612 |
| `production_cotton_t` | float | Cotton production | IBGE PAM 1612 |

### MapBiomas land use shares (annual, fraction of total municipal area)
| Column | Type | Description | Source |
|---|---|---|---|
| `mb_share_sugarcane` | float | Sugarcane share | MapBiomas Collection 9 |
| `mb_share_pasture` | float | Pasture share | MapBiomas Collection 9 |
| `mb_share_native_veg` | float | Native vegetation share | MapBiomas Collection 9 |
| `mb_share_soybean` | float | Soybean share | MapBiomas Collection 9 |
| `mb_share_silviculture` | float | Silviculture share | MapBiomas Collection 9 |
| `mb_share_urban` | float | Urban/infrastructure share | MapBiomas Collection 9 |
| `mb_share_agriculture_total` | float | Total agriculture share | MapBiomas Collection 9 |

## Notes

- Emissions are reported in tCO2eq/year using GWP-AR5 conversion factors (SEEG default): CH4=28, N2O=265.
- For GWP-AR6 conversion, multiply N2O-dominated channels by 273/265 = 1.030.
- SEEG sub-channels were extracted via decomposition of original SEEG categories — see paper Section 3 and Brasil (2020e) for methodology.
- MapBiomas shares cover years 2015-2024 (Collection 9 limitation).
- PAM data covers 2012-2024.
- Missing values are not imputed in the exported file.

## Reference equations (SEEG / IPCC Tier 2)

- **Eq. 52**: N fertilizer-N2O = N_applied × EF1 × 44/28 × GWP_N2O
- **Eq. 62-66**: Residue-N2O from sugarcane harvest (depends on %manual harvest with burning)
- **Eq. 40, 42**: Organic N from filter cake and vinasse
- **Eq. 60-61**: Residue-N2O from other crops
- **Eq. 89, 9**: Liming CO2 emissions

Full equations available in Brasil (2020e) - 4° Inventário Nacional de Emissões e Remoções
Antrópicas de Gases de Efeito Estufa: Relatório de Referência — Setor Agropecuária.
