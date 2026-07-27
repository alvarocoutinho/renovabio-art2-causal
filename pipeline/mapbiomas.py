"""
pipeline.mapbiomas
==================
Processamento do painel MapBiomas Coleção 10 (uso e cobertura do solo).

Estrutura da fonte
------------------
`mapbiomas_municipal_year_panel_ready.csv` — painel município × ano já em
formato painel:
- 31.213 linhas (~2.401 munis × 13 anos 2012-2024)
- Encoding: latin-1, sep=";", decimal=","
- 51 colunas: identificadores + áreas absolutas (ha) + shares (%) + lags + flags
- Áreas com "1.234,56" (formato BR)
- Shares com "12,3456%" (formato BR + %)

Decisões metodológicas
----------------------
- Critério canavieiro complementar (§3.3 v2.2): mb_share_cana > 5%
  em algum ano 2015-2019.
- Restrição ao Centro-Sul (6 UFs).
- Universo canavieiro FINAL = união de 3 critérios:
    (a) PAM area_colhida > 500ha (já em pipeline.pam.build_canavieiro_baseline)
    (b) MapBiomas mb_share_cana > 5% (este módulo)
    (c) ANP hospeda usina certificada (pipeline.anp.muni_treat)

Outputs em data/interim/
------------------------
- mapbiomas_panel.csv             : painel limpo (município × ano × cols)
- mapbiomas_canavieiro_baseline.csv : municípios com share_cana > 5% baseline
- universo_canavieiro_final.csv   : união dos 3 critérios (PAM ∪ MB ∪ ANP)
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from pipeline.config import (
    PARAMS, MAPBIOMAS_PANEL, ensure_dir, interim, out_pre,
)
from pipeline.normalize import build_muni_key, num_br, zfill_ibge


# ============================================================================
# CONSTANTES
# ============================================================================

# Threshold para critério canavieiro MapBiomas (§3.3 v2.2)
FILTRO_SHARE_CANA = PARAMS.FILTRO_SHARE_CANA  # 0.05 = 5%

# Janela baseline (2015-2019)
BASELINE_YEARS = PARAMS.BASELINE_YEARS

# Correções ortográficas conhecidas: nome no MapBiomas → nome canônico no IBGE
MAPBIOMAS_IBGE_FIXES = {
    "PINGO-D'AGUA|MG":             "PINGO D'AGUA|MG",
    "SANTO ANTONIO DE LEVERGER|MT": "SANTO ANTONIO DO LEVERGER|MT",
}

# Colunas de área (absolutas em ha, formato BR)
COLS_AREAS = [
    "area_total_ha", "area_sugarcane_ha", "area_soybean_ha", "area_cotton_ha",
    "area_temp_crop_ha", "area_perennial_crop_ha", "area_agriculture_ha",
    "area_pasture_ha", "area_forest_ha", "area_nonforest_natural_ha",
    "area_natural_ha", "area_anthropic_ha", "area_mosaic_uses_ha",
    "area_forest_plantation_ha", "area_water_ha", "area_urban_ha",
    "area_mining_ha", "area_sugarcane_ha_lag1", "area_sugarcane_ha_change",
]

# Colunas de share (proporção, formato BR + "%")
COLS_SHARES = [
    "share_sugarcane", "share_soybean", "share_cotton", "share_temp_crop",
    "share_perennial_crop", "share_agriculture", "share_pasture",
    "share_forest", "share_nonforest_natural", "share_natural",
    "share_anthropic", "share_mosaic_uses", "share_forest_plantation",
    "share_water", "share_urban", "share_mining",
    "share_sugarcane_lag1", "share_sugarcane_change",
    "share_natural_lag1", "share_natural_change",
    "share_pasture_lag1", "share_pasture_change",
    "share_agriculture_lag1", "share_agriculture_change",
]


# ============================================================================
# LEITURA E LIMPEZA
# ============================================================================

def load_mapbiomas_panel() -> pd.DataFrame:
    """
    Lê o painel MapBiomas com encoding/separador corretos.

    NÃO faz tipagem ainda — retorna tudo como string para que clean_mb_panel
    possa decidir como tratar cada coluna.
    """
    if not MAPBIOMAS_PANEL.exists():
        raise FileNotFoundError(f"MapBiomas panel não encontrado: {MAPBIOMAS_PANEL}")

    df = pd.read_csv(
        MAPBIOMAS_PANEL,
        encoding="latin-1",
        sep=";",
        low_memory=False,
        dtype=str,  # tudo string; convertemos depois
    )
    return df


def clean_mb_panel(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpa o painel MapBiomas:
    1. Converte ano para int.
    2. Áreas (formato BR "1.234,56") → float via num_br.
    3. Shares (formato BR + "%" ex: "12,34%") → float via num_br
       (que já strip "%" e converte vírgula).
    4. Flags binárias para int.
    """
    out = df.copy()

    # Ano
    if "year" in out.columns:
        out["year"] = pd.to_numeric(out["year"], errors="coerce").astype("Int64")

    # Áreas (formato BR — vírgula decimal, ponto separador de milhar)
    for col in COLS_AREAS:
        if col in out.columns:
            out[col] = num_br(out[col])

    # Shares (formato BR com %)
    for col in COLS_SHARES:
        if col in out.columns:
            out[col] = num_br(out[col])
            # num_br já strip "%"; mas se valor era 12.3456% (string),
            # virá como 12.3456 (não 0.1234). Normalizamos para [0, 1].
            # Detecta se valores são >1 (provavelmente em %) e divide
            if out[col].abs().max() > 2:  # se max > 2, está em %
                out[col] = out[col] / 100.0

    # Flags
    for col in ("sugarcane_present", "post_2018", "post_2020"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")

    return out


def attach_geocode(
    df: pd.DataFrame, crosswalk: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Resolve geocode IBGE via crosswalk usando muni_key.

    Aplica MAPBIOMAS_IBGE_FIXES para correções ortográficas conhecidas.

    Returns
    -------
    (matched, unmatched) — dois DataFrames separados.
    """
    df = df.copy()

    # Constrói muni_key
    df["muni_key"] = build_muni_key(df["municipality"], df["state_acronym"])
    # Aplica correções
    df["muni_key_corrected"] = df["muni_key"].replace(MAPBIOMAS_IBGE_FIXES)

    cw_keys = crosswalk[["muni_key", "geocode", "municipio", "uf"]].copy()
    cw_keys = cw_keys.rename(columns={
        "municipio": "municipio_cw",
        "uf": "uf_cw",
    })

    out = df.merge(
        cw_keys, left_on="muni_key_corrected", right_on="muni_key",
        how="left", suffixes=("", "_cw_dup"),
    )
    if "muni_key_cw_dup" in out.columns:
        out = out.drop(columns=["muni_key_cw_dup"])

    matched = out[out["geocode"].notna()].copy()
    unmatched = out[out["geocode"].isna()].copy()
    return matched, unmatched


def restrict_to_core(df: pd.DataFrame) -> pd.DataFrame:
    """Restringe a 6 UFs Centro-Sul (já está, mas garante)."""
    return df[df["uf_cw"].isin(PARAMS.UFS_CORE)].copy()


# ============================================================================
# CRITÉRIO CANAVIEIRO MAPBIOMAS
# ============================================================================

def build_canavieiro_baseline_mb(
    df_clean: pd.DataFrame,
    threshold_share: float = FILTRO_SHARE_CANA,
    baseline_years: tuple[int, int] = BASELINE_YEARS,
) -> pd.DataFrame:
    """
    Identifica municípios canavieiros via MapBiomas: share_cana > threshold
    em algum ano da janela baseline.

    Parameters
    ----------
    df_clean : painel já limpo e com geocode anexado.
    threshold_share : limiar de share (default 0.05 = 5%).
    baseline_years : (y0, y1) inclusivos.

    Returns
    -------
    DataFrame com:
        geocode, municipio_cw, uf_cw,
        mb_share_cana_max_baseline, mb_share_cana_mean_baseline,
        mb_area_cana_max_baseline,
        is_canavieiro_mb (sempre True nas linhas retornadas),
        criterio_mapbiomas
    """
    y0, y1 = baseline_years
    pre = df_clean[
        (df_clean["year"] >= y0) & (df_clean["year"] <= y1)
    ].copy()

    agg = (
        pre.groupby(["geocode", "municipio_cw", "uf_cw"])
           .agg(
               mb_share_cana_max_baseline=("share_sugarcane", "max"),
               mb_share_cana_mean_baseline=("share_sugarcane", "mean"),
               mb_area_cana_max_baseline=("area_sugarcane_ha", "max"),
               n_anos_acima_threshold_mb=(
                   "share_sugarcane",
                   lambda s: (s.dropna() > threshold_share).sum(),
               ),
           )
           .reset_index()
    )

    canavieiros = agg[agg["mb_share_cana_max_baseline"] > threshold_share].copy()
    canavieiros["is_canavieiro_mb"] = True
    canavieiros["criterio_mapbiomas"] = (
        f"share_cana > {threshold_share*100:.0f}% em algum ano "
        f"{y0}-{y1}"
    )

    return canavieiros.sort_values(
        "mb_share_cana_max_baseline", ascending=False
    ).reset_index(drop=True)


# ============================================================================
# UNIVERSO CANAVIEIRO FINAL (UNIÃO DOS 3 CRITÉRIOS)
# ============================================================================

def build_universo_canavieiro_final(
    canavieiros_mb: pd.DataFrame,
    canavieiros_pam: Optional[pd.DataFrame] = None,
    muni_treat_anp: Optional[pd.DataFrame] = None,
    crosswalk: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Constrói o universo canavieiro final pela UNIÃO de 3 critérios (§3.3 v2.2):
        (a) PAM area_colhida > 500ha em algum ano baseline (→ canavieiros_pam)
        (b) MapBiomas mb_share_cana > 5% em algum ano baseline (→ canavieiros_mb)
        (c) ANP hospeda usina certificada (→ muni_treat_anp)

    Parameters
    ----------
    canavieiros_mb : output de build_canavieiro_baseline_mb (obrigatório)
    canavieiros_pam : output de pipeline.pam.build_canavieiro_baseline (opcional)
    muni_treat_anp : output de pipeline.anp.run_anp_pipeline['muni_treat'] (opcional)
    crosswalk : pd.DataFrame com geocode/municipio/uf (recomendado, para
        garantir municipio/uf preenchidos quando linha vem só de PAM ou ANP).

    Returns
    -------
    DataFrame com:
        geocode, municipio, uf,
        is_canavieiro_pam, is_canavieiro_mb, is_canavieiro_anp,
        n_criterios_atendidos, is_canavieiro_uniao,
        + colunas-detalhe de cada critério (max baseline, etc.)
    """
    # Iniciar pelo MapBiomas (sempre presente)
    df = canavieiros_mb[[
        "geocode", "municipio_cw", "uf_cw",
        "mb_share_cana_max_baseline", "mb_share_cana_mean_baseline",
        "mb_area_cana_max_baseline",
    ]].copy()
    df = df.rename(columns={"municipio_cw": "municipio", "uf_cw": "uf"})
    df["is_canavieiro_mb"] = True

    # Merge PAM
    if canavieiros_pam is not None:
        pam_subset = canavieiros_pam[[
            "geocode", "area_colhida_max_baseline",
            "area_colhida_mean_baseline", "n_anos_acima_threshold",
        ]].copy()
        pam_subset["is_canavieiro_pam"] = True
        pam_subset = pam_subset.rename(
            columns={"n_anos_acima_threshold": "n_anos_acima_threshold_pam"}
        )
        df = df.merge(pam_subset, on="geocode", how="outer")

    # Merge ANP
    if muni_treat_anp is not None:
        anp_subset = muni_treat_anp[["geocode", "g_m", "n_usinas"]].copy()
        anp_subset["is_canavieiro_anp"] = True
        df = df.merge(anp_subset, on="geocode", how="outer")

    # Preenche municipio/uf via crosswalk (resolve NaN dos outer joins quando
    # registro vem só de PAM ou só de ANP, não está em MB)
    if crosswalk is not None:
        cw_geo = crosswalk[["geocode", "municipio", "uf"]].copy()
        cw_geo = cw_geo.rename(columns={"municipio": "municipio_cw", "uf": "uf_cw"})
        df = df.merge(cw_geo, on="geocode", how="left")
        # Coalesce: usa nome/UF do crosswalk se MB não trouxe
        df["municipio"] = df["municipio"].fillna(df["municipio_cw"])
        df["uf"] = df["uf"].fillna(df["uf_cw"])
        df = df.drop(columns=["municipio_cw", "uf_cw"])

    # Preenche flags binárias
    if "is_canavieiro_mb" in df.columns:
        df["is_canavieiro_mb"] = df["is_canavieiro_mb"].fillna(False).astype(bool)
    if "is_canavieiro_pam" in df.columns:
        df["is_canavieiro_pam"] = df["is_canavieiro_pam"].fillna(False).astype(bool)
    else:
        df["is_canavieiro_pam"] = False
    if "is_canavieiro_anp" in df.columns:
        df["is_canavieiro_anp"] = df["is_canavieiro_anp"].fillna(False).astype(bool)
    else:
        df["is_canavieiro_anp"] = False

    # Conta critérios atendidos por município
    df["n_criterios_atendidos"] = (
        df["is_canavieiro_mb"].astype(int)
        + df["is_canavieiro_pam"].astype(int)
        + df["is_canavieiro_anp"].astype(int)
    )
    df["is_canavieiro_uniao"] = df["n_criterios_atendidos"] >= 1

    # Reordena colunas
    cols_lead = [
        "geocode", "municipio", "uf",
        "is_canavieiro_mb", "is_canavieiro_pam", "is_canavieiro_anp",
        "n_criterios_atendidos", "is_canavieiro_uniao",
    ]
    cols_other = [c for c in df.columns if c not in cols_lead]
    df = df[cols_lead + cols_other]

    return df.sort_values(
        ["n_criterios_atendidos", "uf", "municipio"],
        ascending=[False, True, True]
    ).reset_index(drop=True)


# ============================================================================
# ORQUESTRAÇÃO
# ============================================================================

def run_mapbiomas_pipeline(
    crosswalk: pd.DataFrame,
    canavieiros_pam: Optional[pd.DataFrame] = None,
    muni_treat_anp: Optional[pd.DataFrame] = None,
    save: bool = True,
) -> dict:
    """
    Roda o pipeline MapBiomas completo + integra com PAM e ANP para
    construir o universo canavieiro final.
    """
    print("→ Lendo painel MapBiomas...")
    df_raw = load_mapbiomas_panel()
    print(f"  raw: {df_raw.shape}")

    print("\n→ Limpando tipagem (áreas BR, shares com %)...")
    df_clean = clean_mb_panel(df_raw)
    print(f"  cleaned: {df_clean.shape}")

    print("\n→ Resolvendo geocode via crosswalk...")
    matched, unmatched = attach_geocode(df_clean, crosswalk)
    n_munis_unmatched = unmatched["muni_key"].nunique() if len(unmatched) > 0 else 0
    print(f"  matched: {len(matched)} cells | "
          f"unmatched: {len(unmatched)} cells ({n_munis_unmatched} munis)")

    print("\n→ Restringindo ao Centro-Sul...")
    df_cs = restrict_to_core(matched)
    print(f"  CS: {df_cs.shape} ({df_cs['geocode'].nunique()} munis × "
          f"{df_cs['year'].nunique()} anos)")

    print(f"\n→ Construindo critério canavieiro MapBiomas (share > "
          f"{FILTRO_SHARE_CANA*100:.0f}% baseline)...")
    canavieiros_mb = build_canavieiro_baseline_mb(df_cs)
    print(f"  Canavieiros MapBiomas: {len(canavieiros_mb)} munis")
    print(f"  Por UF:")
    print(canavieiros_mb.groupby("uf_cw").size().to_string())

    print("\n→ Construindo universo canavieiro final (união dos 3 critérios)...")
    universo = build_universo_canavieiro_final(
        canavieiros_mb=canavieiros_mb,
        canavieiros_pam=canavieiros_pam,
        muni_treat_anp=muni_treat_anp,
        crosswalk=crosswalk,
    )
    print(f"  Total na união: {len(universo)} munis")
    print(f"  Por nº de critérios atendidos:")
    print(universo["n_criterios_atendidos"].value_counts().sort_index().to_string())
    print(f"\n  Por UF:")
    print(universo.groupby("uf").size().to_string())

    if save:
        print("\n→ Salvando...")
        df_cs.to_csv(interim("mapbiomas_panel.csv"), index=False)
        canavieiros_mb.to_csv(
            interim("mapbiomas_canavieiro_baseline.csv"), index=False
        )
        universo.to_csv(interim("universo_canavieiro_final.csv"), index=False)
        if len(unmatched) > 0:
            unmatched_summary = (
                unmatched.groupby(["municipality", "state_acronym"]).size()
                         .reset_index(name="n_linhas")
                         .sort_values("n_linhas", ascending=False)
            )
            unmatched_summary.to_csv(
                out_pre("mapbiomas_unmatched.csv"), index=False
            )
        print("  ✓ tudo salvo")

    return {
        "panel": df_cs,
        "canavieiros_mb": canavieiros_mb,
        "universo": universo,
        "unmatched": unmatched,
    }
