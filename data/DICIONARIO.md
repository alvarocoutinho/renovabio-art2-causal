# Dicionário de dados

Conforme o Plano de Gestão de Dados aprovado (FAPESP nº 2025/01530-0).

**Codificação:** UTF-8 · **Formato:** CSV (`,`) e Parquet
**Recorte:** 842 municípios canavieiros, 6 UFs do Centro-Sul, 2015–2024
(robustez 2012–2024) · **Unidade:** município (geocode IBGE 7 dígitos)

---

## Chaves canônicas

| Chave | Tipo | Formato | Exemplo |
|---|---|---|---|
| `geocode` | string | 7 dígitos com `zfill` | `"3550308"` |
| `muni_key` | string | `MUNICIPIO_NORMALIZADO\|UF` | `"SAO PAULO\|SP"` |
| `cidade_uf_seeg` | string | `Município (UF)` | `"São Paulo (SP)"` |

Geocodes são **sempre** string — nunca `int`, que perde zeros à esquerda.
Anos sempre `int`. Emissões em escala bruta são `float`; transformações
(`log`, `log1p`, `asinh`) ficam em colunas separadas com prefixo.

## Especificações de covariáveis

| Sigla | Descrição |
|---|---|
| `LEAN` | Conjunto mínimo de covariáveis |
| `FULL` | Conjunto completo |
| `FULL2` | Conjunto completo, variante 2 |
| `RICH` | Conjunto ampliado |
| `sa_canonical` | Contraste: estimador Sun–Abraham |
| `twfe_classic` | Contraste: two-way fixed effects clássico |

---

## 1. Dados publicados — `data/published/`

### `renovabio_psm_cross_section_v1.0` (5.570 × 47)

Cross-section de covariáveis ex-ante para pareamento.

| Variável | Tipo | Descrição |
|---|---|---|
| `ibge_code` | object | `PREENCHER` |
| `municipality` | object | `PREENCHER` |
| `uf` | float64 | `PREENCHER` |
| `bioma` | object | `PREENCHER` |
| `is_canavieiro` | bool | `PREENCHER` |
| `is_treated_ever` | bool | `PREENCHER` |
| `treatment_year` | float64 | `PREENCHER` |
| `log_pib_total` | float64 | `PREENCHER` |
| `log_pib_per_capita` | float64 | `PREENCHER` |
| `log_population_2017` | float64 | `PREENCHER` |
| `log_total_area_ha` | float64 | `PREENCHER` |
| `population_density` | float64 | `PREENCHER` |
| `share_vabc_agriculture` | float64 | `PREENCHER` |
| `share_vabc_industry` | float64 | `PREENCHER` |
| `share_vabc_services` | float64 | `PREENCHER` |
| `share_vabc_public_admin` | float64 | `PREENCHER` |
| `mb_share_sugarcane_baseline` | float64 | `PREENCHER` |
| `mb_share_soybean_baseline` | float64 | `PREENCHER` |
| `mb_share_pasture_baseline` | float64 | `PREENCHER` |
| `mb_share_native_veg_baseline` | float64 | `PREENCHER` |
| `mb_share_urban_baseline` | float64 | `PREENCHER` |
| `mb_share_silviculture_baseline` | float64 | `PREENCHER` |
| `mb_share_agriculture_total_baseline` | float64 | `PREENCHER` |
| `log_sugarcane_area_ha` | float64 | `PREENCHER` |
| `log_soybean_area_ha` | float64 | `PREENCHER` |
| `log_maize_area_ha` | float64 | `PREENCHER` |
| `log_cotton_area_ha` | float64 | `PREENCHER` |
| `log_agriculture_total_area_ha` | float64 | `PREENCHER` |
| `share_sugarcane_of_agriculture` | float64 | `PREENCHER` |
| `share_family_farms` | float64 | `PREENCHER` |
| `share_medium_large_farms` | float64 | `PREENCHER` |
| `share_family_farms_area` | float64 | `PREENCHER` |
| `share_medium_large_farms_area` | float64 | `PREENCHER` |
| `tractors_per_farm` | float64 | `PREENCHER` |
| `share_irrigated_farms` | float64 | `PREENCHER` |
| `share_irrigated_area` | float64 | `PREENCHER` |
| `share_financed_farms` | float64 | `PREENCHER` |
| `share_tech_assistance` | float64 | `PREENCHER` |
| `share_natural_vegetation_area` | float64 | `PREENCHER` |
| `pct_farms_with_energy` | float64 | `PREENCHER` |
| `hdim_education` | float64 | `PREENCHER` |
| `hdim_income` | float64 | `PREENCHER` |
| `hdim_longevity` | float64 | `PREENCHER` |
| `social_vulnerability_infrastructure` | float64 | `PREENCHER` |
| `social_vulnerability_human_capital` | float64 | `PREENCHER` |
| `social_vulnerability_income_work` | float64 | `PREENCHER` |
| `gini_index` | float64 | `PREENCHER` |

### `renovabio_outcomes_panel_v1.0` (8.420 × 22)

Painel longo de desfechos de emissão.

> **AUSENTE DO REPOSITÓRIO.** Este dataset foi exportado pelo notebook 11j
> mas não está em `data/published/`. Precisa ser commitado antes do release.

> Ambos acompanhados de codebook próprio (`CODEBOOK_PSM_v1.0.md`,
> `CODEBOOK_PANEL_v1.0.md`).

---

## 2. Tabelas de resultado — `outputs/tables/`

Estrutura de colunas de cada tabela publicada. Os campos comuns aos ATT
(`outcome`, `spec`, `att`, `se`, `pval`, `ci_low`, `ci_high`, `n`) seguem a
convenção do estimador Callaway–Sant'Anna.


### Camada 2 — pareamento (notebook 10)

| Arquivo | Dim. | Colunas |
|---|---|---|
| `psm_pscores_weights.csv` | 842×26 | `geocode`, `treated`, `pscore_LEAN_std`, `wipw_LEAN_std`, `watt_LEAN_std`, `pscore_LEAN_lasso`, `wipw_LEAN_lasso`, `watt_LEAN_lasso`, `pscore_FULL_std`, `wipw_FULL_std`, `watt_FULL_std`, `pscore_FULL_lasso`, `wipw_FULL_lasso`, `watt_FULL_lasso`, `pscore_FULL2_std`, `wipw_FULL2_std`, `watt_FULL2_std`, `pscore_FULL2_lasso`, `wipw_FULL2_lasso`, `watt_FULL2_lasso`, `pscore_RICH_std`, `wipw_RICH_std`, `watt_RICH_std`, `pscore_RICH_lasso`, `wipw_RICH_lasso`, `watt_RICH_lasso` |
| `psm_balance_smd.csv` | 35×5 | `covariavel`, `SMD_pre`, `SMD_post`, `|SMD_pre|`, `|SMD_post|` |
| `psm_support_masks.csv` | 842×34 | `geocode`, `treated`, `in_LEAN_std_crump_2.5`, `in_LEAN_std_trim_5_95`, `in_LEAN_std_minmax`, `in_LEAN_std_kennedy_1`, `in_LEAN_lasso_crump_2.5`, `in_LEAN_lasso_trim_5_95`, `in_LEAN_lasso_minmax`, `in_LEAN_lasso_kennedy_1`, `in_FULL_std_crump_2.5`, `in_FULL_std_trim_5_95`, `in_FULL_std_minmax`, `in_FULL_std_kennedy_1`, `in_FULL_lasso_crump_2.5`, `in_FULL_lasso_trim_5_95`, `in_FULL_lasso_minmax`, `in_FULL_lasso_kennedy_1`, `in_FULL2_std_crump_2.5`, `in_FULL2_std_trim_5_95`, `in_FULL2_std_minmax`, `in_FULL2_std_kennedy_1`, `in_FULL2_lasso_crump_2.5`, `in_FULL2_lasso_trim_5_95`, `in_FULL2_lasso_minmax`, `in_FULL2_lasso_kennedy_1`, `in_RICH_std_crump_2.5`, `in_RICH_std_trim_5_95`, `in_RICH_std_minmax`, `in_RICH_std_kennedy_1`, `in_RICH_lasso_crump_2.5`, `in_RICH_lasso_trim_5_95`, `in_RICH_lasso_minmax`, `in_RICH_lasso_kennedy_1` |
| `psm_support_summary.csv` | 32×9 | `model`, `method`, `lo`, `hi`, `n_in`, `n_treat_in`, `n_ctrl_in`, `pct_treat_in`, `pct_ctrl_in` |
| `psm_diagnostics.csv` | 8×6 | `model`, `auc`, `pseudo_r2`, `n_covs_total`, `n_active`, `active_covs` |

### 11a — ATT do tratamento binário escalonado

| Arquivo | Dim. | Colunas |
|---|---|---|
| `att_t1_main.csv` | 30×8 | `outcome`, `spec`, `estimator`, `ATT`, `SE`, `CI_lo`, `CI_hi`, `n_munis` |
| `att_t1_eventstudy_luc.csv` | 16×6 | `Unnamed: 0`, `EventAggregation`, `EventAggregation.1`, `EventAggregation.2`, `EventAggregation.3`, `EventAggregation.4` |
| `att_t1_bacon.csv` | 5×4 | `outcome`, `w_treated_vs_never`, `w_early_vs_late`, `w_late_vs_early_forbidden` |

### 11b — Doses T2 (volume) e T3 (NEEA)

| Arquivo | Dim. | Colunas |
|---|---|---|
| `att_t2t3_main.csv` | 120×12 | `treatment`, `snapshot`, `outcome`, `spec`, `ATT_mean`, `SE_mean`, `CI_lo`, `CI_hi`, `dose_slope`, `n_strata`, `n_munis`, `time_s` |
| `att_t2t3_eventstudy_luc.csv` | 60×7 | `Unnamed: 0`, `Unnamed: 1`, `EventAggregation`, `EventAggregation.1`, `EventAggregation.2`, `EventAggregation.3`, `EventAggregation.4` |

### 11c — Desfechos derivados e contraste de estimadores

| Arquivo | Dim. | Colunas |
|---|---|---|
| `att_derived_outcomes.csv` | 12×8 | `outcome`, `spec`, `estimator`, `ATT`, `SE`, `CI_lo`, `CI_hi`, `n_munis` |
| `att_derived_eventstudy.csv` | 26×4 | `outcome`, `event_time`, `ATT`, `SE` |

### 11d — Decomposição mecanística por canal

| Arquivo | Dim. | Colunas |
|---|---|---|
| `att_canais_main.csv` | 16×8 | `outcome`, `spec`, `estimator`, `ATT`, `SE`, `CI_lo`, `CI_hi`, `n_munis` |
| `att_canais_eventstudy.csv` | 54×7 | `relative_period`, `EventAggregation`, `EventAggregation.1`, `EventAggregation.2`, `EventAggregation.3`, `EventAggregation.4`, `outcome` |
| `att_canais_significancia_5pct.csv` | 16×8 | `outcome`, `spec`, `ATT`, `SE`, `z`, `CI_lo`, `CI_hi`, `sig_5pct` |
| `att_canais_config.csv` | 1×21 | `spec_principal`, `fator`, `M_direto`, `M_proxy`, `razao_direto_proxy`, `ATT_cana_direto`, `sig_cana_direto`, `ATT_fert_n`, `sig_fert_n`, `ATT_calagem`, `sig_calagem`, `ATT_res_outros`, `sig_res_outros`, `H5.1_signif`, `H5.2_signif`, `H5.3_nulo`, `s_cana_direto`, `s_fert_n`, `s_calagem`, `configuracao`, `narrativa` |
| `att_canais_verificacao.csv` | 2×8 | `outcome`, `spec`, `estimator`, `ATT`, `SE`, `CI_lo`, `CI_hi`, `n_munis` |

### 11e — Substituição de área

| Arquivo | Dim. | Colunas |
|---|---|---|
| `att_substituicao_consolidado.csv` | 40×12 | `outcome`, `spec`, `estimator`, `ATT`, `SE`, `CI_lo`, `CI_hi`, `n_munis`, `grupo`, `z`, `sig_5pct`, `sinal` |
| `att_substituicao_pam.csv` | 16×8 | `outcome`, `spec`, `estimator`, `ATT`, `SE`, `CI_lo`, `CI_hi`, `n_munis` |
| `att_substituicao_mapbiomas.csv` | 24×8 | `outcome`, `spec`, `estimator`, `ATT`, `SE`, `CI_lo`, `CI_hi`, `n_munis` |
| `att_substituicao_config.csv` | 1×29 | `spec_principal`, `configuracao_substituicao`, `narrativa`, `pam_cana_pos_sig`, `pam_outras_neg_sig`, `mapb_cana_pos_sig`, `mapb_pastagem_neg_sig`, `mapb_vegnat_neg_sig`, `desmatamento_associado`, `PAM_log1p_pam_area_cana_t_ATT`, `PAM_asinh_pam_area_soja_t_ATT`, `PAM_asinh_pam_area_milho_t_ATT`, `PAM_asinh_pam_area_algodao_t_ATT`, `PAM_log1p_pam_area_cana_t_sig`, `PAM_asinh_pam_area_soja_t_sig`, `PAM_asinh_pam_area_milho_t_sig`, `PAM_asinh_pam_area_algodao_t_sig`, `MAPB_log1p_share_cana_mapb_ATT`, `MAPB_log1p_share_pastagem_mapb_ATT`, `MAPB_log1p_share_vegetacao_nativa_mapb_ATT`, `MAPB_asinh_share_soja_mapb_ATT`, `MAPB_asinh_share_silvicultura_mapb_ATT`, `MAPB_asinh_share_urbano_infra_mapb_ATT`, `MAPB_log1p_share_cana_mapb_sig`, `MAPB_log1p_share_pastagem_mapb_sig`, `MAPB_log1p_share_vegetacao_nativa_mapb_sig`, `MAPB_asinh_share_soja_mapb_sig`, `MAPB_asinh_share_silvicultura_mapb_sig`, `MAPB_asinh_share_urbano_infra_mapb_sig` |

### 11f — Event studies e pré-tendências

| Arquivo | Dim. | Colunas |
|---|---|---|
| `event_study_consolidado.csv` | 180×9 | `event_time`, `ATT`, `SE`, `CI_lo`, `CI_hi`, `zero_not_in_cband`, `outcome`, `spec`, `n_munis` |
| `event_study_resumo.csv` | 18×19 | `outcome`, `att_t-2`, `se_t-2`, `sig_t-2`, `att_t+0`, `se_t+0`, `sig_t+0`, `att_t+1`, `se_t+1`, `sig_t+1`, `att_t+3`, `se_t+3`, `sig_t+3`, `att_t+5`, `se_t+5`, `sig_t+5`, `pretrend_flag`, `pretrend_wald_p`, `veredito` |
| `pretrend_test_consolidado.csv` | 18×7 | `outcome`, `pre_periods`, `n_pre_periods`, `n_pre_sig_individual`, `wald_stat_approx`, `p_value_approx`, `pretrend_flag` |

### 11g — Heterogeneidade por tercil de share

| Arquivo | Dim. | Colunas |
|---|---|---|
| `att_b4m5_por_tercil.csv` | 15×10 | `outcome`, `tercil`, `ATT`, `SE`, `z`, `sig_5pct`, `CI_lo`, `CI_hi`, `n_munis_total`, `n_tratados_tercil` |
| `att_b4m5_event_por_tercil.csv` | 27×11 | `event_time`, `ATT`, `SE`, `CI_lo`, `CI_hi`, `zero_not_in_cband`, `outcome`, `tercil`, `spec`, `n_munis_total`, `n_tratados_tercil` |
| `att_b4m5_dose_response.csv` | 5×10 | `outcome`, `ATT_T1`, `sig_T1`, `ATT_T2`, `sig_T2`, `ATT_T3`, `sig_T3`, `delta_T3_T1`, `monotonia`, `veredito` |
| `b4m5_tercil_info.csv` | 1×11 | `p33`, `p66`, `n_canavieiros`, `n_com_share`, `n_sem_share`, `n_T1_baixo`, `n_T2_medio`, `n_T3_alto`, `n_T1_baixo_tratados`, `n_T2_medio_tratados`, `n_T3_alto_tratados` |

### 11h — Balanço de CO2eq e intensidade de carbono

| Arquivo | Dim. | Colunas |
|---|---|---|
| `b4m7_balanco_co2eq.csv` | 194×8 | `geocode`, `delta_queima`, `delta_cana_dir`, `delta_fert_n`, `delta_calagem`, `delta_res_outros`, `balanco_liquido_total`, `balanco_so_robustos` |
| `b4m7_balanco_co2eq_ar6.csv` | 194×8 | `geocode`, `delta_queima_ar6`, `delta_cana_dir_ar6`, `delta_fert_n_ar6`, `delta_calagem_ar6`, `delta_res_outros_ar6`, `balanco_so_robustos_ar6`, `balanco_liquido_total_ar6` |
| `b4m8_intensidade_carbono.csv` | 193×8 | `geocode`, `intensity_pre_kgco2_ton`, `intensity_pos_kgco2_ton`, `delta_intensity_kgco2_ton`, `delta_relativo_pct`, `termo_escala_tco2e`, `termo_intensidade_tco2e`, `termo_interacao_tco2e` |
| `b4m8_robustez_decomposicao.csv` | 193×14 | `geocode`, `intensity_pre_kgco2_ton`, `intensity_pos_kgco2_ton`, `delta_intensity_kgco2_ton`, `delta_relativo_pct`, `termo_escala_tco2e`, `termo_intensidade_tco2e`, `termo_interacao_tco2e`, `size_pre`, `size_decil`, `intensity_pre`, `intensity_pos`, `geocode_key`, `cohort` |
| `b4m8_robustez_por_coorte.csv` | 5×11 | `cohort`, `n`, `int_pre_med`, `int_pos_med`, `delta_med`, `delta_rel_med`, `delta_rel_mean`, `n_caiu`, `n_subiu`, `termo_escala_med`, `termo_int_med` |

### `diagnostico_solos/` — canal de solos manejados

Único canal com efeito conjunto significativo após correção FDR. Diagnóstico
da atribuição das emissões de solos manejados à cultura da cana.

| Arquivo | Dim. | Colunas |
|---|---|---|
| `arvore_solos_manejados_nivel_A.csv` | 9×6 | `Sub-categoria emissora`, `soma_2015_2024`, `n_linhas`, `n_munis_emissao_pos`, `share_pct`, `pipeline_status` |
| `arvore_solos_manejados_nivel_B.csv` | 33×6 | `Sub-categoria emissora`, `Produto ou sistema`, `soma_2015_2024`, `n_linhas`, `share_pct`, `pipeline_status` |
| `arvore_solos_manejados_nivel_C.csv` | 33×7 | `Sub-categoria emissora`, `Produto ou sistema`, `Detalhamento`, `pipeline_status`, `soma_2015_2024`, `n_linhas`, `share_pct` |
| `correlacao_intra_municipio.csv` | 1973×4 | `Cidade`, `uf`, `corr_pearson`, `corr_spearman` |
| `share_cana_atribuivel_municipio.csv` | 2369×7 | `Cidade`, `uf`, `share_cana_mean`, `share_cana_median`, `solos_pipeline_total`, `solos_cana_atribuivel_total`, `n_anos` |
| `solos_cana_atribuivel_municipio_ano.csv` | 30797×8 | `Cidade`, `uf`, `ano`, `solos_pipeline`, `solos_cana_residuo`, `solos_cana_subproduto`, `solos_cana_atribuivel`, `share_cana` |

> **Proveniência.** Estes seis arquivos foram produzidos por rotina externa ao
> repositório. Ver nota em `data/raw/MANIFEST.md`, Seção 2.

---

## 3. Parâmetros de identificação

Congelados em `pipeline/config.py`, classe `Params`, com referência à seção
correspondente do pré-registro v2.6.

| Parâmetro | Valor |
|---|---|
| Estimador | Callaway–Sant'Anna doubly robust (CS-DR) |
| Grupo de comparação | `PREENCHER` (never-treated / not-yet-treated) |
| Agregação dos ATT(g,t) | `PREENCHER` |
| Inferência | `PREENCHER` |
| Correção de múltiplas comparações | FDR |
| Semente aleatória | `PREENCHER` |

## 4. Hipóteses

| Hipótese | Desfecho | Situação |
|---|---|---|
| H1a (primária) | `log_luc` | Testada |
| H1b (secundária) | `carbono_solo` | Testada |
| H1c | `cobertura_car_ativo`, `adesao_pra`, `cobertura_veg_nativa` | **Não testada** — SICAR descartado |
| H2 (primária) | `log_solos_manejados` | Testada |
| H2 (secundária) | `log_queima` | Testada |

Ver a seção *Pré-registro e hipóteses* do README.

