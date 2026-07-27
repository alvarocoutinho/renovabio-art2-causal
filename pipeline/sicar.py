"""
pipeline.sicar
==============
Processamento do painel SICAR (Sistema Nacional de Cadastro Ambiental Rural)
para construção dos outcomes H1c (intermediários do canal compliance):

- cobertura_car_ativo : cadastros com Status=Ativo / area_municipal
- adesao_pra          : área com PRA=Sim / área total cadastrada
- veg_nativa_atual    : Vegetação Nativa Atual / Imóvel Área total
+ aux: share_pra_nao_informado (controle para sensibilidade)

Estrutura da fonte
------------------
Painel SICAR mensal (mai/2014 a abr/2026, 144 meses), 344.124 linhas, 14 colunas.
Granularidade: município × período × Tipo × Adesão_PRA × Módulos × Status.

Decisões metodológicas
----------------------
- S1 (snapshot anual): dezembro de cada ano (último mês = abr/2026 com flag).
- S2 (denominador cobertura): area_total_ha do MapBiomas (já em painel).
- S3 (status Ativo): estrito "Ativo" (Pendente vai para coluna sensibilidade).
- S4 (PRA Não Informado): denominador inclui todos; share_pra_nao_informado
  fica como variável auxiliar.
- Restrição: apenas Tipo='Imóvel rural' (descarta assentamento e povos tradicionais).

Outputs em data/interim/
------------------------
- sicar_outcomes_anual.csv : município × ano × outcomes H1c
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from pipeline.config import (
    PARAMS, SICAR_PAINEL, ensure_dir, interim, out_pre,
)
from pipeline.normalize import build_muni_key, zfill_ibge


# ============================================================================
# CONSTANTES
# ============================================================================

# Janela de interesse (alinhada com o painel principal)
ANOS_PAINEL = list(range(PARAMS.YEAR_MIN_FULL, PARAMS.YEAR_MAX_FULL + 1))   # 2012-2024

# Restringe ao tipo principal (descarta assentamento e povos tradicionais)
TIPO_INCLUIDO = "Imóvel rural"

# Status considerado Ativo no critério principal (S3 estrito)
STATUS_ATIVO = "Ativo"
STATUS_ATIVO_PENDENTE = ("Ativo", "Pendente")  # sensibilidade

# Adesão ao PRA
PRA_SIM = "Sim"
PRA_NAO_INFORMADO = "Não Informado"

# Correções ortográficas: nome no SICAR → nome canônico no IBGE
SICAR_IBGE_FIXES = {
    "DONA EUSEBIA|MG":             "DONA EUZEBIA|MG",
    "SAO LUIS DO PARAITINGA|SP":   "SAO LUIZ DO PARAITINGA|SP",
    "SAO THOME DAS LETRAS|MG":     "SAO TOME DAS LETRAS|MG",
    "EMBU|SP":                     "EMBU DAS ARTES|SP",
}


# ============================================================================
# LEITURA E PARSING
# ============================================================================

def load_sicar_painel() -> pd.DataFrame:
    """
    Lê o painel SICAR completo do XLSX. Retorna DataFrame com tipos corretos.
    """
    if not SICAR_PAINEL.exists():
        raise FileNotFoundError(f"SICAR não encontrado: {SICAR_PAINEL}")

    df = pd.read_excel(SICAR_PAINEL)
    return df


def parse_municipio_sicar(s) -> tuple[Optional[str], Optional[str]]:
    """
    Parser do campo 'Municipio' SICAR — formato 'UF - NOME'.
    Returns (uf, nome).
    """
    if s is None or pd.isna(s):
        return (None, None)
    parts = str(s).split(" - ", 1)
    if len(parts) != 2:
        return (None, None)
    return (parts[0].strip(), parts[1].strip())


def parse_municipios_column(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica parse_municipio_sicar e adiciona uf_parsed/nome_parsed/muni_key."""
    df = df.copy()
    parsed = df["Municipio"].apply(parse_municipio_sicar)
    df["uf_parsed"] = parsed.apply(lambda t: t[0])
    df["nome_parsed"] = parsed.apply(lambda t: t[1])
    df["muni_key"] = build_muni_key(df["nome_parsed"], df["uf_parsed"])
    return df


# ============================================================================
# FILTROS
# ============================================================================

def filter_imovel_rural(df: pd.DataFrame) -> pd.DataFrame:
    """Restringe a Tipo='Imóvel rural' (descarta assentamento, povos tradicionais)."""
    return df[df["Tipo"] == TIPO_INCLUIDO].copy()


def take_december_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    """
    Para cada ano da janela, mantém o snapshot de DEZEMBRO. Para o ano mais
    recente (sem dezembro disponível), mantém o último mês com flag parcial.

    Adiciona coluna `ano` e `is_partial_year`.
    """
    df = df.copy()
    df["ano"] = df["Período"].dt.year
    df["mes"] = df["Período"].dt.month

    # Para cada (geocode, ano), pega o mês máximo. Em anos completos = 12.
    # Em ano corrente (2026 com max abril), = 4.
    max_per_year = (
        df.groupby("ano")["mes"].max().rename("mes_alvo").reset_index()
    )
    df = df.merge(max_per_year, on="ano", how="left")
    snap = df[df["mes"] == df["mes_alvo"]].copy()
    snap["is_partial_year"] = snap["mes_alvo"] != 12
    return snap


def restrict_to_window(df: pd.DataFrame, anos: list[int] = ANOS_PAINEL) -> pd.DataFrame:
    """Restringe a janela 2012-2024."""
    return df[df["ano"].isin(anos)].copy()


# ============================================================================
# CHAVEAMENTO PARA GEOCODE
# ============================================================================

def attach_geocode(
    df: pd.DataFrame, crosswalk: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Resolve geocode IBGE via crosswalk usando muni_key.
    Aplica SICAR_IBGE_FIXES para divergências ortográficas conhecidas.

    Returns
    -------
    (matched, unmatched)
    """
    df = df.copy()
    df["muni_key_corrected"] = df["muni_key"].replace(SICAR_IBGE_FIXES)

    cw_keys = crosswalk[["muni_key", "geocode", "municipio", "uf"]].copy()
    cw_keys = cw_keys.rename(columns={"municipio": "municipio_cw", "uf": "uf_cw"})

    out = df.merge(
        cw_keys, left_on="muni_key_corrected", right_on="muni_key",
        how="left", suffixes=("", "_cw_dup"),
    )
    if "muni_key_cw_dup" in out.columns:
        out = out.drop(columns=["muni_key_cw_dup"])

    matched = out[out["geocode"].notna()].copy()
    unmatched = out[out["geocode"].isna()].copy()
    return matched, unmatched


# ============================================================================
# AGREGAÇÃO PARA OUTCOMES H1c
# ============================================================================

def aggregate_outcomes(
    snap: pd.DataFrame,
) -> pd.DataFrame:
    """
    Agrega o snapshot SICAR (ano × geocode × Tipo × Adesão_PRA × Módulos × Status)
    em (ano × geocode) com 7 colunas:

    - sicar_area_total_ha     : Σ Imóvel Área (todos os status)
    - sicar_area_ativo_ha     : Σ Imóvel Área onde Status=Ativo
    - sicar_area_ativo_pendente_ha : Σ Imóvel Área onde Status ∈ {Ativo, Pendente}
    - sicar_area_pra_sim_ha   : Σ Imóvel Área onde PRA=Sim
    - sicar_area_pra_nao_informado_ha : Σ Imóvel Área onde PRA='Não Informado'
    - sicar_veg_nativa_ha     : Σ Vegetação Nativa Atual
    - sicar_n_cadastros_total : Σ Imóveis Cadastrados
    """
    df = snap.copy()
    # Garante numérico
    for col in ["Imóvel Área", "Vegetação Nativa Atual", "Imóveis Cadastrados"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Cria flags de filtro
    df["_is_ativo"] = df["Status do Imóvel"] == STATUS_ATIVO
    df["_is_ativo_pendente"] = df["Status do Imóvel"].isin(STATUS_ATIVO_PENDENTE)
    df["_is_pra_sim"] = df["Adesão ao PRA"] == PRA_SIM
    df["_is_pra_nao_inf"] = df["Adesão ao PRA"] == PRA_NAO_INFORMADO

    # Aggregates por (geocode, ano)
    g = df.groupby(["geocode", "ano"], as_index=False)
    out = g.agg(
        sicar_area_total_ha=("Imóvel Área", "sum"),
        sicar_n_cadastros_total=("Imóveis Cadastrados", "sum"),
        sicar_veg_nativa_ha=("Vegetação Nativa Atual", "sum"),
    )

    # Para os filtrados, faz um pass separado e merge
    def sum_filtered(df, mask_col, val_col, out_name):
        sub = df[df[mask_col]]
        if len(sub) == 0:
            return pd.DataFrame(columns=["geocode", "ano", out_name])
        return (
            sub.groupby(["geocode", "ano"], as_index=False)[val_col].sum()
               .rename(columns={val_col: out_name})
        )

    out = out.merge(
        sum_filtered(df, "_is_ativo", "Imóvel Área", "sicar_area_ativo_ha"),
        on=["geocode", "ano"], how="left",
    )
    out = out.merge(
        sum_filtered(df, "_is_ativo_pendente", "Imóvel Área", "sicar_area_ativo_pendente_ha"),
        on=["geocode", "ano"], how="left",
    )
    out = out.merge(
        sum_filtered(df, "_is_pra_sim", "Imóvel Área", "sicar_area_pra_sim_ha"),
        on=["geocode", "ano"], how="left",
    )
    out = out.merge(
        sum_filtered(df, "_is_pra_nao_inf", "Imóvel Área", "sicar_area_pra_nao_inf_ha"),
        on=["geocode", "ano"], how="left",
    )

    # Preencher NaN com 0
    cols_fill = [
        "sicar_area_ativo_ha", "sicar_area_ativo_pendente_ha",
        "sicar_area_pra_sim_ha", "sicar_area_pra_nao_inf_ha",
    ]
    for c in cols_fill:
        out[c] = out[c].fillna(0)

    # Anexa is_partial_year (ano corrente)
    partial = (
        snap.groupby(["geocode", "ano"], as_index=False)["is_partial_year"].any()
    )
    out = out.merge(partial, on=["geocode", "ano"], how="left")

    return out


def compute_h1c_outcomes(
    aggregated: pd.DataFrame,
    mb_panel: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calcula os 3 outcomes H1c usando area_total_ha do MapBiomas como denominador
    para cobertura (decisão S2):

    - cobertura_car_ativo  = sicar_area_ativo_ha / area_total_mb_ha
    - cobertura_car_ativo_pendente = sicar_area_ativo_pendente_ha / area_total_mb_ha
    - adesao_pra           = sicar_area_pra_sim_ha / sicar_area_total_ha
    - share_pra_nao_inf    = sicar_area_pra_nao_inf_ha / sicar_area_total_ha (auxiliar)
    - share_veg_nativa_atual = sicar_veg_nativa_ha / sicar_area_total_ha

    Parameters
    ----------
    aggregated : output de aggregate_outcomes
    mb_panel : painel MapBiomas com cols (geocode, year, area_total_ha)

    Returns
    -------
    DataFrame com chave (geocode, ano) e os outcomes H1c.
    """
    # Pega area_total_ha do MapBiomas
    mb_area = mb_panel[["geocode", "year", "area_total_ha"]].copy()
    mb_area = mb_area.rename(columns={"year": "ano", "area_total_ha": "area_total_mb_ha"})
    # Garante geocode str e ano int
    mb_area["geocode"] = mb_area["geocode"].astype(str)
    mb_area["ano"] = pd.to_numeric(mb_area["ano"], errors="coerce").astype("Int64")

    out = aggregated.copy()
    out["geocode"] = out["geocode"].astype(str)
    out["ano"] = pd.to_numeric(out["ano"], errors="coerce").astype("Int64")
    out = out.merge(mb_area, on=["geocode", "ano"], how="left")

    # Calcula outcomes
    out["cobertura_car_ativo"] = np.where(
        out["area_total_mb_ha"] > 0,
        out["sicar_area_ativo_ha"] / out["area_total_mb_ha"],
        np.nan,
    )
    out["cobertura_car_ativo_pendente"] = np.where(
        out["area_total_mb_ha"] > 0,
        out["sicar_area_ativo_pendente_ha"] / out["area_total_mb_ha"],
        np.nan,
    )
    out["adesao_pra"] = np.where(
        out["sicar_area_total_ha"] > 0,
        out["sicar_area_pra_sim_ha"] / out["sicar_area_total_ha"],
        np.nan,
    )
    out["share_pra_nao_informado"] = np.where(
        out["sicar_area_total_ha"] > 0,
        out["sicar_area_pra_nao_inf_ha"] / out["sicar_area_total_ha"],
        np.nan,
    )
    out["share_veg_nativa_atual"] = np.where(
        out["sicar_area_total_ha"] > 0,
        out["sicar_veg_nativa_ha"] / out["sicar_area_total_ha"],
        np.nan,
    )

    # Sanity: cobertura > 1 indica problema (área SICAR maior que área municipal)
    n_excess = (out["cobertura_car_ativo"] > 1).sum()
    if n_excess > 0:
        # Não erro, só sinaliza — pode ocorrer em municípios pequenos com
        # imóveis que cruzam fronteiras
        out["cobertura_car_ativo_capped_at_1"] = out["cobertura_car_ativo"].clip(
            upper=1.0
        )

    return out


# ============================================================================
# ORQUESTRAÇÃO
# ============================================================================

def run_sicar_pipeline(
    crosswalk: pd.DataFrame,
    save: bool = True,
) -> dict:
    """
    Roda o pipeline SICAR completo.

    Carrega painel MapBiomas para usar area_total_ha como denominador.
    """
    print("→ Lendo painel SICAR (~30 MB, pode levar 30s)...")
    df_raw = load_sicar_painel()
    print(f"  raw: {df_raw.shape}")

    print("\n→ Filtrando Tipo='Imóvel rural'...")
    df = filter_imovel_rural(df_raw)
    print(f"  filtered: {df.shape}")

    print("\n→ Parsing município (UF - NOME → muni_key)...")
    df = parse_municipios_column(df)

    print("\n→ Tomando snapshot anual (dezembro ou último mês)...")
    snap = take_december_snapshot(df)
    print(f"  snapshot: {snap.shape}")

    print("\n→ Restringindo à janela do painel (2012-2024)...")
    snap = restrict_to_window(snap)
    print(f"  in window: {snap.shape}")
    print(f"  anos disponíveis: {sorted(snap['ano'].unique())}")

    print("\n→ Resolvendo geocode via crosswalk (com SICAR_IBGE_FIXES)...")
    matched, unmatched = attach_geocode(snap, crosswalk)
    print(f"  matched: {len(matched)} cells | unmatched: {len(unmatched)} cells")
    if len(unmatched) > 0:
        n_unm_keys = unmatched["muni_key"].nunique()
        print(f"  unmatched muni_keys: {n_unm_keys}")
        if n_unm_keys < 10:
            print(f"    {sorted(unmatched['muni_key'].dropna().unique())}")

    print("\n→ Restringindo ao Centro-Sul...")
    matched_cs = matched[matched["uf_cw"].isin(PARAMS.UFS_CORE)].copy()
    n_munis = matched_cs["geocode"].nunique()
    print(f"  CS: {len(matched_cs)} cells, {n_munis} munis")

    print("\n→ Agregando para (geocode × ano)...")
    aggregated = aggregate_outcomes(matched_cs)
    print(f"  aggregated: {aggregated.shape}")

    print("\n→ Carregando painel MapBiomas para denominador (area_total_ha)...")
    mb_path = interim("mapbiomas_panel.csv")
    if not mb_path.exists():
        raise FileNotFoundError(
            f"MapBiomas panel não encontrado em {mb_path}. "
            f"Rode 05_mapbiomas.ipynb antes."
        )
    mb_panel = pd.read_csv(mb_path, dtype={"geocode": str})

    print("\n→ Computando outcomes H1c...")
    outcomes = compute_h1c_outcomes(aggregated, mb_panel)
    print(f"  outcomes: {outcomes.shape}")

    # Anexa nome/uf
    cw_info = crosswalk[["geocode", "municipio", "uf"]]
    outcomes = outcomes.merge(cw_info, on="geocode", how="left")

    # Reordena
    cols_lead = ["geocode", "municipio", "uf", "ano", "is_partial_year"]
    cols_outcomes = [
        "cobertura_car_ativo",
        "cobertura_car_ativo_pendente",
        "adesao_pra",
        "share_pra_nao_informado",
        "share_veg_nativa_atual",
    ]
    cols_aux = [
        "sicar_area_total_ha", "sicar_area_ativo_ha",
        "sicar_area_ativo_pendente_ha", "sicar_area_pra_sim_ha",
        "sicar_area_pra_nao_inf_ha", "sicar_veg_nativa_ha",
        "sicar_n_cadastros_total", "area_total_mb_ha",
    ]
    cols_all = cols_lead + cols_outcomes + cols_aux
    outcomes = outcomes[[c for c in cols_all if c in outcomes.columns]]
    outcomes = outcomes.sort_values(["uf", "municipio", "ano"]).reset_index(drop=True)

    # Distribuições para sanity check
    print("\n→ Distribuições dos outcomes (sanity check):")
    for c in cols_outcomes:
        if c in outcomes.columns:
            s = outcomes[c].dropna()
            if len(s) == 0:
                continue
            print(f"  {c:35s}: n={len(s):,}, "
                  f"mean={s.mean():.4f}, median={s.median():.4f}, "
                  f"p99={s.quantile(0.99):.4f}, max={s.max():.4f}")

    if save:
        print("\n→ Salvando...")
        outcomes.to_csv(interim("sicar_outcomes_anual.csv"), index=False)
        if len(unmatched) > 0:
            unm_summary = (
                unmatched.groupby(["nome_parsed", "uf_parsed"]).size()
                         .reset_index(name="n_linhas")
                         .sort_values("n_linhas", ascending=False)
            )
            unm_summary.to_csv(out_pre("sicar_unmatched.csv"), index=False)
        print("  ✓ tudo salvo")

    return {
        "outcomes": outcomes,
        "aggregated": aggregated,
        "matched": matched_cs,
        "unmatched": unmatched,
    }
