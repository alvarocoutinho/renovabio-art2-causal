"""
pipeline.psm_baseline
=====================
Processamento da base de covariáveis PSM (Censo Agro 2017 + IBGE/IDHM/PIB),
preparando o input do Propensity Score Matching declarado no pré-registro v2.2 §3.7.

Estrutura da fonte
------------------
`base_psm_integrada_raw.csv` — 5.570 munis × 165 colunas (Brasil inteiro).
- Encoding UTF-8, separador vírgula, decimal ponto.
- Bioma com mojibake (replacement chars U+FFFD por dupla codificação na origem).
- 0_cd_ibge já zfilled em 7 dígitos.
- Ano de referência uniforme = 2017 (Censo Agro).
- Colunas com prefixo numérico indicando fonte (0_=ID, 1_=PIB, 2_=Pop, 3_=MB pré,
  4_=PAM, 5-13_=Censo Agro, 14_=cobertura natural, 15_=irrigação, 16_=saneamento,
  17_=IDHM/Gini).

Decisões metodológicas
----------------------
- P1: usar `0_ano_ref` como veio (= 2017 uniforme).
- P2: irrigação detalhada (15_*) imputada com 0 (semântica: "não tem"); 16_pop_atendida_esgoto droppada (>50% missing).
- P3: derivar 5 covariáveis sintéticas (densidade, share PIB agro, etc.).
- P4: filtro CS via 0_sg_uf ∈ {SP, MG, GO, MS, MT, PR}.
- P5: renomear colunas para nomes limpos; manter rastreabilidade em
  `outputs_pre/psm_columns_provenance.csv`.

Outputs em data/interim/
------------------------
- psm_baseline_clean.csv : 2.363 munis CS × covariáveis renomeadas e tipadas.

Outputs em outputs_pre/
-----------------------
- psm_columns_provenance.csv : mapeamento original→canônico para auditoria.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from pipeline.config import (
    PARAMS, PSM_BASELINE_RAW, ensure_dir, interim, out_pre,
)
from pipeline.normalize import zfill_ibge


# ============================================================================
# CONSTANTES
# ============================================================================

# Mapeamento original → canônico. Selecionei as ~50 covariáveis mais relevantes
# para o PSM (o restante das 165 fica fora — pode ser adicionado depois).
COLUMN_RENAME = {
    # 0_ identifiers
    "0_cd_ibge": "geocode",
    "0_sg_uf": "uf",
    "0_nm_mun": "municipio",
    "0_amzon_legal": "is_amazonia_legal",
    "0_semiarido": "is_semiarido",

    # 1_ PIB e VAB
    "1_pib_total": "pib_total",
    "1_pib_percap": "pib_percap",
    "1_vadc_agro": "vab_agro",
    "1_vadc_ind": "vab_industria",
    "1_vadc_serv": "vab_servicos",
    "1_vadc_adm": "vab_admin_publica",
    "1_vadc_bruto": "vab_bruto",

    # 2_ População
    "2_pop_2017_ibge": "pop_2017",

    # 3_ MapBiomas pré
    "3_mb_sharegrp_pre_agricultura_total": "mb_share_agric_total_pre",
    "3_mb_sharegrp_pre_cana": "mb_share_cana_pre",
    "3_mb_sharegrp_pre_soja": "mb_share_soja_pre",
    "3_mb_sharegrp_pre_pastagem": "mb_share_pasto_pre",
    "3_mb_sharegrp_pre_vegetacao_nativa": "mb_share_vegnat_pre",
    "3_mb_sharegrp_pre_silvicultura": "mb_share_silvic_pre",

    # 4_ PAM
    "4_area_colhida_ha": "pam_area_colhida_total",
    "4_area_colhida_ha_cana": "pam_area_cana",
    "4_area_colhida_ha_soja": "pam_area_soja",
    "4_area_colhida_ha_milho": "pam_area_milho",
    "4_quant_prod_cana": "pam_qtd_cana",
    "4_val_prod_total": "pam_val_total",
    "4_val_prod_cana": "pam_val_cana",

    # 5_ Censo Agro: estabelecimentos
    "5_num_est_total": "censo_n_estab_total",
    "5_num_est_af": "censo_n_estab_af",  # agricultura familiar
    "5_num_est_mp": "censo_n_estab_mp",  # médio/grande produtor
    "5_num_est_lavperm_total": "censo_n_estab_lavperm",
    "5_num_est_lavtemp_total": "censo_n_estab_lavtemp",

    # 6_ Censo Agro: áreas
    "6_area_lav_total": "censo_area_lavoura",
    "6_area_pec_total": "censo_area_pecuaria",

    # 7_ Energia
    "7_est_com_energia": "censo_n_estab_com_energia",

    # 8_ Área dos estabelecimentos
    "8_area_est_total": "censo_area_estab_total",

    # 9_ Pessoal ocupado
    "9_num_pess_ocup_total": "censo_n_pess_ocup",

    # 11_ Tratores
    "11_num_est_trator_total": "censo_n_estab_com_trator",
    "11_num_trator_total": "censo_n_tratores",

    # 12_ Irrigação
    "12_num_est_irrig_total": "censo_n_estab_irrig",
    "12_area_irrig_total": "censo_area_irrigada",

    # 13_ Financiamento
    "13_num_est_fin_total": "censo_n_estab_com_finan",

    # 14_ Cobertura natural / bioma
    "14_area_total": "area_municipal_km2",
    "14_desmatado": "area_desmatada",
    "14_vegetacao_natural": "area_vegnat",
    "14_bioma": "bioma",

    # 15_ Irrigação detalhada (imputar 0 em missing)
    "15_area_irrig_ha_cana": "irrig_area_cana",
    "15_area_irrig_ha_pivos": "irrig_area_pivos",
    "15_area_irrig_ha_total": "irrig_area_total",

    # 16_ Saneamento (esgoto droppado)
    "16_populacao_atendida_agua": "pop_atendida_agua",
    "16_populacao_urbana": "pop_urbana",

    # 17_ IDHM e indicadores sociais
    "17_ivs_infraestrutura_urbana": "ivs_infra_urbana",
    "17_ivs_capital_humano": "ivs_capital_humano",
    "17_ivs_renda_e_trabalho": "ivs_renda_trabalho",
    "17_idhm_long": "idhm_longevidade",
    "17_idhm_educ": "idhm_educacao",
    "17_idhm_renda": "idhm_renda",
    "17_espvida": "esperanca_vida",
    "17_i_gini": "gini",
}

# Colunas categóricas que DEVEM permanecer string
CATEGORICAL_COLS = ("uf", "municipio", "bioma")

# Colunas de flag binárias (0/1)
FLAG_COLS = ("is_amazonia_legal", "is_semiarido")

# Colunas a IMPUTAR com 0 quando missing (semântica: ausência = zero)
IMPUTE_ZERO_COLS = (
    "irrig_area_cana", "irrig_area_pivos", "irrig_area_total",
    "pam_area_cana", "pam_area_soja", "pam_area_milho",
    "pam_qtd_cana", "pam_val_cana",
    "censo_n_estab_com_finan", "censo_n_estab_com_trator",
    "censo_n_tratores", "censo_n_estab_irrig", "censo_area_irrigada",
)

# Colunas a DROPAR completamente (>50% missing)
DROP_COLS_HIGH_MISSING = (
    "16_populacao_atentida_esgoto",  # 56% missing — typo da fonte mantido
    "15_area_irrig_ha_arroz",        # 91% missing
)

# Mapeamento de mojibake → bioma canônico
BIOMA_FIXES = {
    "Amaz\ufffd\ufffdnia": "Amazônia",
    "Mata Atl\ufffd\ufffdntica": "Mata Atlântica",
    "Cerrado": "Cerrado",
    "Caatinga": "Caatinga",
    "Pampa": "Pampa",
    "Pantanal": "Pantanal",
}


# ============================================================================
# LEITURA E LIMPEZA
# ============================================================================

def load_psm_raw() -> pd.DataFrame:
    """
    Lê base_psm_integrada_raw.csv com encoding UTF-8 + separador vírgula.
    Retorna tudo como string para tipagem controlada depois.
    """
    if not PSM_BASELINE_RAW.exists():
        raise FileNotFoundError(f"PSM raw não encontrado: {PSM_BASELINE_RAW}")
    df = pd.read_csv(PSM_BASELINE_RAW, sep=",", encoding="utf-8",
                     dtype=str, low_memory=False)
    return df


def fix_bioma_mojibake(df: pd.DataFrame) -> pd.DataFrame:
    """Corrige mojibake na coluna 14_bioma usando dicionário fechado de 6 valores."""
    df = df.copy()
    if "14_bioma" in df.columns:
        df["14_bioma"] = df["14_bioma"].replace(BIOMA_FIXES)
    return df


def drop_high_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Descarta colunas com >50% missing por decisão metodológica P2."""
    cols_to_drop = [c for c in DROP_COLS_HIGH_MISSING if c in df.columns]
    return df.drop(columns=cols_to_drop)


def rename_to_canonical(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Renomeia colunas para nomes canônicos.
    Retorna (df_renomeado, tabela_provenance).

    Colunas não mapeadas em COLUMN_RENAME são DESCARTADAS (mas listadas
    na tabela de provenance para auditoria).
    """
    keep_cols = [c for c in df.columns if c in COLUMN_RENAME]
    drop_cols = [c for c in df.columns if c not in COLUMN_RENAME]

    df = df[keep_cols].rename(columns=COLUMN_RENAME)

    provenance = pd.DataFrame([
        {"original": orig, "canonico": canon, "status": "renomeada"}
        for orig, canon in COLUMN_RENAME.items()
        if orig in keep_cols
    ] + [
        {"original": orig, "canonico": "", "status": "descartada"}
        for orig in drop_cols
    ])

    return df, provenance


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converte colunas numéricas para float, mantendo categóricas como string,
    e flags como Int64.
    """
    df = df.copy()

    # Geocode — string com zfill 7
    if "geocode" in df.columns:
        df["geocode"] = zfill_ibge(df["geocode"], width=7)

    # Categóricas → mantém string mas trim
    for c in CATEGORICAL_COLS:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
            df.loc[df[c].isin(["nan", "None", ""]), c] = pd.NA

    # Flags → Int64
    for c in FLAG_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype("Int64")

    # Numéricas → float (formato US, decimal=".", sem milhar)
    cat_or_flag = set(CATEGORICAL_COLS) | set(FLAG_COLS) | {"geocode"}
    for c in df.columns:
        if c in cat_or_flag:
            continue
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


def impute_zero_where_appropriate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Imputa 0 em colunas onde missing tem semântica clara de ausência
    (irrigação, área de cana, financiamento, tratores).
    """
    df = df.copy()
    for c in IMPUTE_ZERO_COLS:
        if c in df.columns:
            df[c] = df[c].fillna(0)
    return df


# ============================================================================
# DERIVAÇÃO DE COVARIÁVEIS
# ============================================================================

def add_derived_covariates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona covariáveis derivadas (P3) úteis para PSM:

    - densidade_pop : pop_2017 / area_municipal_km2
    - share_vab_agro : vab_agro / vab_bruto
    - tratores_per_estab : censo_n_tratores / censo_n_estab_total
    - share_area_irrig : censo_area_irrigada / censo_area_estab_total
    - share_estab_af : censo_n_estab_af / censo_n_estab_total (agricultura familiar)
    - log_pop : log1p(pop_2017)
    - log_pib_percap : log(pib_percap) — proxy de prosperidade
    """
    df = df.copy()

    def safe_ratio(num, den):
        return np.where((den.notna()) & (den > 0), num / den, np.nan)

    if "pop_2017" in df.columns and "area_municipal_km2" in df.columns:
        df["densidade_pop"] = safe_ratio(df["pop_2017"], df["area_municipal_km2"])

    if "vab_agro" in df.columns and "vab_bruto" in df.columns:
        df["share_vab_agro"] = safe_ratio(df["vab_agro"], df["vab_bruto"])

    if "censo_n_tratores" in df.columns and "censo_n_estab_total" in df.columns:
        df["tratores_per_estab"] = safe_ratio(
            df["censo_n_tratores"], df["censo_n_estab_total"]
        )

    if "censo_area_irrigada" in df.columns and "censo_area_estab_total" in df.columns:
        df["share_area_irrig"] = safe_ratio(
            df["censo_area_irrigada"], df["censo_area_estab_total"]
        )

    if "censo_n_estab_af" in df.columns and "censo_n_estab_total" in df.columns:
        df["share_estab_af"] = safe_ratio(
            df["censo_n_estab_af"], df["censo_n_estab_total"]
        )

    if "pop_2017" in df.columns:
        df["log_pop"] = np.log1p(df["pop_2017"].astype(float))

    if "pib_percap" in df.columns:
        with np.errstate(invalid="ignore", divide="ignore"):
            df["log_pib_percap"] = np.where(
                df["pib_percap"] > 0,
                np.log(df["pib_percap"].astype(float)),
                np.nan,
            )

    return df


def add_bioma_dummies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cria dummies para os 6 biomas (one-hot, sem drop_first).
    Útil para PSM com bioma como controle categórico.
    """
    if "bioma" not in df.columns:
        return df
    dummies = pd.get_dummies(df["bioma"], prefix="bioma", dtype="Int64")
    return pd.concat([df, dummies], axis=1)


# ============================================================================
# FILTRO CS
# ============================================================================

def restrict_to_cs(df: pd.DataFrame) -> pd.DataFrame:
    """Restringe ao Centro-Sul (6 UFs)."""
    return df[df["uf"].isin(PARAMS.UFS_CORE)].copy()


# ============================================================================
# ORQUESTRAÇÃO
# ============================================================================

def run_psm_baseline_pipeline(save: bool = True) -> dict:
    """
    Pipeline completo:
    1. Lê base_psm_integrada_raw.csv
    2. Conserta mojibake (bioma)
    3. Drop colunas com >50% missing
    4. Renomeia colunas para canônicas
    5. Tipagem (geocode str, números float, flags Int64)
    6. Imputação de zeros onde apropriado
    7. Derivação de 7 covariáveis
    8. Dummies de bioma
    9. Filtro CS (6 UFs)

    Returns
    -------
    dict com chaves 'data' (DataFrame final) e 'provenance' (mapeamento).
    """
    print("→ Lendo base PSM raw...")
    df_raw = load_psm_raw()
    print(f"  raw: {df_raw.shape}")

    print("\n→ Corrigindo mojibake do bioma...")
    df = fix_bioma_mojibake(df_raw)

    print("\n→ Descartando colunas com >50% missing...")
    df = drop_high_missing(df)
    print(f"  após drop: {df.shape}")

    print("\n→ Renomeando colunas (165 → ~50 canônicas)...")
    df, provenance = rename_to_canonical(df)
    n_kept = (provenance["status"] == "renomeada").sum()
    n_dropped = (provenance["status"] == "descartada").sum()
    print(f"  renomeadas: {n_kept} | descartadas: {n_dropped}")

    print("\n→ Tipagem (geocode str, números float)...")
    df = coerce_types(df)

    print("\n→ Imputação de 0 em colunas com semântica de ausência...")
    df = impute_zero_where_appropriate(df)

    print("\n→ Derivando 7 covariáveis sintéticas...")
    df = add_derived_covariates(df)

    print("\n→ Adicionando dummies de bioma...")
    df = add_bioma_dummies(df)
    bioma_cols = [c for c in df.columns if c.startswith("bioma_")]
    print(f"  dummies criadas: {bioma_cols}")

    print("\n→ Filtrando ao Centro-Sul (6 UFs)...")
    df_cs = restrict_to_cs(df)
    print(f"  CS: {len(df_cs)} munis (esperado 2.363)")
    print(f"  Por UF:")
    print(df_cs.groupby("uf").size().to_string())

    if save:
        print("\n→ Salvando...")
        df_cs.to_csv(interim("psm_baseline_clean.csv"), index=False)
        provenance.to_csv(out_pre("psm_columns_provenance.csv"), index=False)
        print("  ✓ tudo salvo")

    return {
        "data": df_cs,
        "provenance": provenance,
    }
