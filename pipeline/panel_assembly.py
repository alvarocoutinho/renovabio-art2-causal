"""
pipeline.panel_assembly
=======================
Integração final do pipeline ETL: junta os 7 outputs de interim/ em
2 painéis balanceados prontos para modelagem CS/SDID/TWFE.

Inputs (todos em data/interim/)
-------------------------------
- crosswalk_centrosul.csv         : universo (2.363 munis × 5 chaves)
- seeg_outcomes_audited.csv       : outcomes AFOLU (5 + transformações + flags F3)
- sicar_outcomes_anual.csv        : outcomes H1c (3 + auxiliares)
- anp_muni_treat.csv              : tratamento (g_m, doses T2/T3)
- pam_cana_wide.csv               : controles dinâmicos (4 cols)
- mapbiomas_panel.csv             : uso do solo (51 cols → 15 estratégicas)
- psm_baseline_clean.csv          : covariáveis pré-tratamento (71 cols)
- universo_canavieiro_final.csv   : flag canavieiro (4 critérios)

Outputs em data/interim/
------------------------
- panel_full_2012_2024.csv  : 2.363 munis × 13 anos × ~120 cols (universo CS)
- panel_main_2015_2024.csv  : 2.363 munis × 10 anos × ~120 cols
- panel_canavieiro_main.csv : 842 canavieiros × 10 anos × ~120 cols (subset principal)

Decisões metodológicas
----------------------
A1 (janela): produzir 3 painéis (full, main, canavieiro_main) — pré-registro v2.2 §3.4.
A2 (MapBiomas): manter 15 cols estratégicas das 51 originais (descartar redundâncias).
A3 (g_m): NaN para não-tratados, alinhando com convenção CS/Synth.

Derivações no painel
--------------------
- treatment_dummy_t       : 1 se ano >= g_m, senão 0 (staggered, absorvente)
- period_relative_g       : t - g_m (event-time, para dynamic effects)
- post_2018, post_2020    : dummies de janela (controles de robustez)
- T2_dummy_t, T3_dummy_t  : interação treatment_dummy × dose (continuous treatment)
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from pipeline.config import (
    PARAMS, ensure_dir, interim, out_pre,
)
from pipeline.normalize import zfill_ibge


# ============================================================================
# CONSTANTES
# ============================================================================

# Janela main (10 anos) e full (13 anos)
ANOS_MAIN = list(range(PARAMS.YEAR_MIN_MAIN, PARAMS.YEAR_MAX_MAIN + 1))   # 2015-2024
ANOS_FULL = list(range(PARAMS.YEAR_MIN_FULL, PARAMS.YEAR_MAX_FULL + 1))   # 2012-2024

# 15 colunas MapBiomas estratégicas (decisão A2)
MAPBIOMAS_COLS_KEEP = [
    # Áreas absolutas (6)
    "area_total_ha", "area_sugarcane_ha", "area_pasture_ha",
    "area_forest_ha", "area_natural_ha", "area_anthropic_ha",
    # Shares (5)
    "share_sugarcane", "share_pasture", "share_natural",
    "share_agriculture", "share_anthropic",
    # Dinâmicos (4)
    "area_sugarcane_ha_change", "share_sugarcane_change",
    "share_natural_change", "share_pasture_change",
]

# Cols de interesse do SEEG painel (após audited.csv)
SEEG_OUTCOME_COLS = [
    # Raw outcomes (5)
    "luc", "carbono_solo", "queima", "solos_manejados", "residuos_florestais",
    # Transformações (5)
    "asinh_luc", "asinh_carbono_solo", "log1p_queima",
    "log_solos_manejados", "log1p_residuos_florestais",
]

# Cols de interesse do SICAR
SICAR_OUTCOME_COLS = [
    "cobertura_car_ativo", "cobertura_car_ativo_pendente",
    "adesao_pra", "share_pra_nao_informado", "share_veg_nativa_atual",
    "is_partial_year",
]

# Cols de interesse do PAM dinâmico
PAM_DYNAMIC_COLS = [
    "area_plantada_ha", "area_colhida_ha", "qtd_produzida_t", "rendimento_kg_ha",
]


# ============================================================================
# CARREGAMENTO
# ============================================================================

def load_inputs() -> dict:
    """Carrega os 7 inputs de data/interim/."""
    inputs = {}

    crosswalk = pd.read_csv(interim("crosswalk_centrosul.csv"), dtype={"geocode": str})
    inputs["crosswalk"] = crosswalk
    print(f"  crosswalk: {crosswalk.shape}")

    inputs["seeg"] = pd.read_csv(
        interim("seeg_outcomes_audited.csv"), dtype={"geocode": str}
    )
    print(f"  seeg: {inputs['seeg'].shape}")

    inputs["sicar"] = pd.read_csv(
        interim("sicar_outcomes_anual.csv"), dtype={"geocode": str}
    )
    print(f"  sicar: {inputs['sicar'].shape}")

    inputs["anp"] = pd.read_csv(
        interim("anp_muni_treat.csv"), dtype={"geocode": str}
    )
    print(f"  anp: {inputs['anp'].shape}")

    inputs["pam"] = pd.read_csv(
        interim("pam_cana_wide.csv"), dtype={"geocode": str}
    )
    print(f"  pam: {inputs['pam'].shape}")

    inputs["mapbiomas"] = pd.read_csv(
        interim("mapbiomas_panel.csv"), low_memory=False
    )
    print(f"  mapbiomas: {inputs['mapbiomas'].shape}")

    inputs["psm"] = pd.read_csv(
        interim("psm_baseline_clean.csv"), dtype={"geocode": str}
    )
    print(f"  psm: {inputs['psm'].shape}")

    inputs["universo"] = pd.read_csv(
        interim("universo_canavieiro_final.csv"), dtype={"geocode": str}
    )
    print(f"  universo: {inputs['universo'].shape}")

    return inputs


# ============================================================================
# CONSTRUÇÃO DA GRADE BASE
# ============================================================================

def build_grid(crosswalk: pd.DataFrame, anos: list[int]) -> pd.DataFrame:
    """
    Cross-product crosswalk × anos para criar grade balanceada.

    Returns: DataFrame (2.363 × len(anos)) com cols [geocode, municipio, uf, ano].
    """
    munis = crosswalk[["geocode", "municipio", "uf"]].copy()
    grid = (
        munis.assign(_k=1)
             .merge(pd.DataFrame({"ano": anos, "_k": 1}), on="_k")
             .drop(columns="_k")
    )
    return grid.sort_values(["uf", "municipio", "ano"]).reset_index(drop=True)


# ============================================================================
# JOINS POR FONTE
# ============================================================================

def attach_seeg(panel: pd.DataFrame, seeg: pd.DataFrame) -> pd.DataFrame:
    """Anexa outcomes SEEG (raw + transformações + flags F3)."""
    cols_keep = ["geocode", "ano"] + [
        c for c in seeg.columns
        if c in SEEG_OUTCOME_COLS or c.startswith("flag_")
    ]
    sub = seeg[cols_keep].copy()
    return panel.merge(sub, on=["geocode", "ano"], how="left")


def attach_sicar(panel: pd.DataFrame, sicar: pd.DataFrame) -> pd.DataFrame:
    """Anexa outcomes SICAR (H1c)."""
    cols_keep = ["geocode", "ano"] + [
        c for c in SICAR_OUTCOME_COLS if c in sicar.columns
    ]
    sub = sicar[cols_keep].copy()
    return panel.merge(sub, on=["geocode", "ano"], how="left")


def attach_anp(panel: pd.DataFrame, anp: pd.DataFrame) -> pd.DataFrame:
    """
    Anexa variáveis de tratamento ANP (cross-section).
    g_m, n_usinas, n_usinas_baseline, dose_T2_*, dose_T3_*.
    """
    # Drop municipio/uf do ANP (já no painel via crosswalk)
    cols_drop = [c for c in ("municipio", "uf") if c in anp.columns]
    sub = anp.drop(columns=cols_drop)
    return panel.merge(sub, on="geocode", how="left")


def attach_pam(panel: pd.DataFrame, pam: pd.DataFrame) -> pd.DataFrame:
    """Anexa variáveis dinâmicas PAM (4 cols)."""
    cols_keep = ["geocode", "ano"] + [
        c for c in PAM_DYNAMIC_COLS if c in pam.columns
    ]
    sub = pam[cols_keep].copy()
    # Renomeia para sufixo _pam (evita conflito com _baseline do PSM)
    rename = {c: f"{c}_pam" for c in PAM_DYNAMIC_COLS if c in sub.columns}
    sub = sub.rename(columns=rename)
    return panel.merge(sub, on=["geocode", "ano"], how="left")


def attach_mapbiomas(panel: pd.DataFrame, mb: pd.DataFrame) -> pd.DataFrame:
    """Anexa 15 colunas estratégicas do MapBiomas (uso do solo dinâmico)."""
    # MapBiomas tem geocode + year (não 'ano') — alinhar
    mb = mb.copy()
    mb["geocode"] = zfill_ibge(mb["geocode"], width=7)
    mb["year"] = pd.to_numeric(mb["year"], errors="coerce").astype("Int64")

    cols_keep = ["geocode", "year"] + [c for c in MAPBIOMAS_COLS_KEEP if c in mb.columns]
    sub = mb[cols_keep].rename(columns={"year": "ano"}).copy()
    sub["ano"] = pd.to_numeric(sub["ano"], errors="coerce").astype(int)

    # Renomeia com prefixo mb_ para evitar colisão
    rename = {c: f"mb_{c}" for c in MAPBIOMAS_COLS_KEEP if c in sub.columns}
    sub = sub.rename(columns=rename)

    return panel.merge(sub, on=["geocode", "ano"], how="left")


def attach_psm_baseline(panel: pd.DataFrame, psm: pd.DataFrame) -> pd.DataFrame:
    """
    Anexa 71 covariáveis baseline (cross-section, replicadas por ano).
    PSM baseline = 2017 (Censo Agro), valor estático invariante por ano.
    """
    # Drop municipio/uf do PSM (já no painel)
    cols_drop = [c for c in ("municipio", "uf") if c in psm.columns]
    sub = psm.drop(columns=cols_drop)
    return panel.merge(sub, on="geocode", how="left")


def attach_universo_canavieiro(panel: pd.DataFrame, uni: pd.DataFrame) -> pd.DataFrame:
    """
    Anexa flags do universo canavieiro (4 critérios + n_criterios_atendidos).
    Não-canavieiros recebem False/0.
    """
    cols_keep = ["geocode", "is_canavieiro_mb", "is_canavieiro_pam",
                 "is_canavieiro_anp", "n_criterios_atendidos",
                 "is_canavieiro_uniao"]
    cols_keep = [c for c in cols_keep if c in uni.columns]
    sub = uni[cols_keep].copy()

    panel = panel.merge(sub, on="geocode", how="left")

    # Para munis não no universo (controles puros), preenche com False/0
    for c in ("is_canavieiro_mb", "is_canavieiro_pam", "is_canavieiro_anp",
              "is_canavieiro_uniao"):
        if c in panel.columns:
            panel[c] = panel[c].fillna(False).astype(bool)
    if "n_criterios_atendidos" in panel.columns:
        panel["n_criterios_atendidos"] = (
            panel["n_criterios_atendidos"].fillna(0).astype(int)
        )

    return panel


# ============================================================================
# DERIVAÇÕES NO PAINEL
# ============================================================================

def add_treatment_derivations(panel: pd.DataFrame) -> pd.DataFrame:
    """
    Cria variáveis de tratamento staggered:
    - treatment_dummy_t  : 1 se ano >= g_m E g_m notna, senão 0 (absorvente)
    - period_relative_g  : ano - g_m (event-time, NaN para não-tratados)
    - is_treated_ever    : True se g_m notna (cross-section)
    - is_treated_main    : True se g_m está dentro de 2019-2024 (janela main)
    """
    panel = panel.copy()

    if "g_m" not in panel.columns:
        panel["g_m"] = np.nan

    # Cross-section
    panel["is_treated_ever"] = panel["g_m"].notna()
    panel["is_treated_main"] = (
        panel["g_m"].notna()
        & (panel["g_m"] >= 2019)
        & (panel["g_m"] <= 2024)
    )

    # Time-varying (absorvente)
    panel["treatment_dummy_t"] = (
        panel["g_m"].notna() & (panel["ano"] >= panel["g_m"])
    ).astype(int)

    # Event-time
    panel["period_relative_g"] = np.where(
        panel["g_m"].notna(),
        panel["ano"] - panel["g_m"],
        np.nan,
    )

    return panel


def add_window_dummies(panel: pd.DataFrame) -> pd.DataFrame:
    """
    Cria dummies de janela (controles de robustez):
    - post_2018 : 1 se ano >= 2018 (transição RenovaCalc)
    - post_2020 : 1 se ano >= 2020 (1ª certificação ANP majoritária)
    """
    panel = panel.copy()
    panel["post_2018"] = (panel["ano"] >= 2018).astype(int)
    panel["post_2020"] = (panel["ano"] >= 2020).astype(int)
    return panel


def add_dose_interactions(panel: pd.DataFrame) -> pd.DataFrame:
    """
    Interações treatment × dose (continuous treatment).
    Para cada snapshot ANP (2022, 2025, 2026), cria:
    - T2_dummy_t_*  = treatment_dummy_t × dose_T2_*
    - T3_dummy_t_*  = treatment_dummy_t × dose_T3_*
    """
    panel = panel.copy()
    if "treatment_dummy_t" not in panel.columns:
        return panel

    for snap in ("2022", "2025", "2026"):
        for tipo in ("T2", "T3"):
            dose_col = f"dose_{tipo}_{snap}"
            if dose_col not in panel.columns:
                continue
            interaction_col = f"{tipo}_dummy_t_{snap}"
            panel[interaction_col] = panel["treatment_dummy_t"] * panel[dose_col].fillna(0)

    return panel


# ============================================================================
# ASSEMBLY ORQUESTRADO
# ============================================================================

def assemble_panel(
    inputs: dict,
    anos: list[int],
    label: str = "panel",
) -> pd.DataFrame:
    """
    Constrói um painel balanceado para a janela `anos` especificada.
    """
    print(f"\n  Janela: {anos[0]}-{anos[-1]} ({len(anos)} anos)")

    grid = build_grid(inputs["crosswalk"], anos)
    print(f"    grid base: {grid.shape}")

    panel = grid
    panel = attach_seeg(panel, inputs["seeg"])
    panel = attach_sicar(panel, inputs["sicar"])
    panel = attach_anp(panel, inputs["anp"])
    panel = attach_pam(panel, inputs["pam"])
    panel = attach_mapbiomas(panel, inputs["mapbiomas"])
    panel = attach_psm_baseline(panel, inputs["psm"])
    panel = attach_universo_canavieiro(panel, inputs["universo"])

    # Derivações
    panel = add_treatment_derivations(panel)
    panel = add_window_dummies(panel)
    panel = add_dose_interactions(panel)

    print(f"    panel completo: {panel.shape}")
    return panel


# ============================================================================
# ORQUESTRAÇÃO
# ============================================================================

def run_panel_assembly(save: bool = True) -> dict:
    """
    Roda o assembly final, gera 3 painéis:
    - panel_full_2012_2024 (universo, 13 anos)
    - panel_main_2015_2024 (universo, 10 anos)
    - panel_canavieiro_main (filtro canavieiro, 10 anos)
    """
    print("→ Carregando 7 inputs de data/interim/...")
    inputs = load_inputs()

    print("\n→ Construindo painéis...")

    panel_full = assemble_panel(inputs, ANOS_FULL, "panel_full_2012_2024")
    panel_main = assemble_panel(inputs, ANOS_MAIN, "panel_main_2015_2024")

    # Painel canavieiro = subset de panel_main (filtra apenas canavieiros uniao)
    panel_canavieiro = panel_main[panel_main["is_canavieiro_uniao"]].copy()
    print(f"\n  panel_canavieiro_main (subset main): {panel_canavieiro.shape}")
    n_munis_can = panel_canavieiro["geocode"].nunique()
    print(f"    {n_munis_can} munis × {len(ANOS_MAIN)} anos = {n_munis_can * len(ANOS_MAIN)} cells esperadas")

    if save:
        print("\n→ Salvando 3 painéis...")
        panel_full.to_csv(interim("panel_full_2012_2024.csv"), index=False)
        panel_main.to_csv(interim("panel_main_2015_2024.csv"), index=False)
        panel_canavieiro.to_csv(interim("panel_canavieiro_main.csv"), index=False)
        print("  ✓ tudo salvo")

    return {
        "panel_full": panel_full,
        "panel_main": panel_main,
        "panel_canavieiro": panel_canavieiro,
    }


# ============================================================================
# SUMÁRIO PARA AUDITORIA
# ============================================================================

def panel_summary(panel: pd.DataFrame, label: str = "panel") -> dict:
    """Retorna métricas-chave do painel para auditoria visual."""
    summary = {
        "label": label,
        "shape": panel.shape,
        "n_munis": panel["geocode"].nunique(),
        "n_anos": panel["ano"].nunique(),
        "anos_range": (panel["ano"].min(), panel["ano"].max()),
        "n_tratados_ever": panel.groupby("geocode")["is_treated_ever"].first().sum(),
        "n_canavieiros": panel.groupby("geocode")["is_canavieiro_uniao"].first().sum(),
        "n_cols": len(panel.columns),
    }

    # Cobertura por outcome principal
    for outcome in ("luc", "carbono_solo", "solos_manejados", "queima",
                    "cobertura_car_ativo", "adesao_pra"):
        if outcome in panel.columns:
            summary[f"cov_{outcome}"] = panel[outcome].notna().sum()

    return summary
