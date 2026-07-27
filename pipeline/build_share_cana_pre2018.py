"""
B4.M.3 — Construção do share_cana_eq52 pré-tratamento (janela 2012-2017)
========================================================================
Pré-registro v2.3.9 §9.6.

Fórmula (Eq. 52 SEEG, restrita à janela pré-RenovaBio operacional):

    share_cana_eq52_i^pre = mean_{t=2012..2017} [
        Cana_it / (Cana_it + Milho_it + Algodao_it)
    ]

calculado sobre PRODUÇÃO em toneladas (PAM/IBGE Tabela 1612).

Por que 2012-2017: antecede a operacionalização da RenovaBio
(Lei 13.576 de dez/2017, primeira certificação em 2018). Mitiga
endogeneidade do share vs seleção para tratamento (§9.6.4-i).

Por que SEM soja: a Eq. 52 do SEEG pesa fertilizantes sintéticos N
por cana+milho+algodão. Soja é leguminosa fixadora de N, recebe pouca
ureia, NÃO entra no denominador (documento metodológico SEEG, p. 44;
ver Apêndice H Parte II §6 do pré-registro).

Uso:
  - Standalone local: python3 build_share_cana_pre2018.py
  - No Colab: ajustar PATHS e rodar (ou usar o notebook 04c).

Entradas:
  pam_1612_long_2012_2024.parquet  (PAM parseada, D2)

Saídas:
  share_cana_eq52_pre2018.csv          — município × share pré-2018
  share_cana_eq52_pre2018_quality.csv  — relatório de qualidade/cobertura
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# CONFIG — paths (ajustar conforme ambiente)
# ---------------------------------------------------------------------------
try:
    from pipeline.config import interim, out_pre, PARAMS
    PAM_PARQUET = interim("pam_1612_long_2012_2024.parquet")
    OUT_SHARE = interim("share_cana_eq52_pre2018.csv")
    OUT_QUALITY = out_pre("share_cana_eq52_pre2018_quality.csv")
    UFS_CORE = set(PARAMS.UFS_CORE)
except Exception:
    # Fallback local (fora do Colab)
    BASE = Path("/mnt/user-data/outputs")
    PAM_PARQUET = BASE / "pam_1612_long_2012_2024.parquet"
    OUT_SHARE = BASE / "share_cana_eq52_pre2018.csv"
    OUT_QUALITY = BASE / "share_cana_eq52_pre2018_quality.csv"
    UFS_CORE = {"SP", "GO", "MG", "PR", "MS", "MT"}

# Janela pré-tratamento (§9.6) — ESTRITA, declarada ex-ante
PRE_YEARS = list(range(2012, 2018))   # 2012,2013,2014,2015,2016,2017

# Produtos canônicos na PAM 1612 (confirmados por inspeção D2)
PROD_CANA = "Cana-de-açúcar"
PROD_MILHO = "Milho (em grão)"
PROD_ALGODAO = "Algodão herbáceo (em caroço)"
# Soja deliberadamente EXCLUÍDA (ver docstring)


def uf_from_municipio(s: str) -> str:
    """Extrai sigla UF de 'Município (UF)'."""
    if not isinstance(s, str) or "(" not in s:
        return ""
    return s.rsplit("(", 1)[1].rstrip(")").strip()


def build_share_cana_pre2018(pam: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Constrói share_cana_eq52 pré-2018 por município.

    Retorna (df_share, df_quality).
    """
    df = pam.copy()

    # 1. Filtra janela pré-tratamento
    df = df[df["ano"].isin(PRE_YEARS)].copy()

    # 2. Mantém só as 3 culturas da Eq. 52
    prods_eq52 = [PROD_CANA, PROD_MILHO, PROD_ALGODAO]
    df = df[df["produto"].isin(prods_eq52)].copy()

    # 3. Produção em toneladas; NaN → 0 (ausência de cultivo = zero produção)
    df["qtde_produzida_t"] = pd.to_numeric(
        df["qtde_produzida_t"], errors="coerce"
    ).fillna(0.0)

    # 4. Pivot: uma linha por (município, ano), colunas = culturas
    wide = df.pivot_table(
        index=["cod_ibge", "municipio_uf", "ano"],
        columns="produto",
        values="qtde_produzida_t",
        aggfunc="sum",
        fill_value=0.0,
    ).reset_index()
    wide.columns.name = None

    for c in prods_eq52:
        if c not in wide.columns:
            wide[c] = 0.0

    # 5. Denominador Eq. 52 e share POR ANO
    wide["_denom"] = wide[PROD_CANA] + wide[PROD_MILHO] + wide[PROD_ALGODAO]
    # share do ano só é definido se denom > 0 (senão NaN, excluído da média)
    wide["_share_ano"] = np.where(
        wide["_denom"] > 0,
        wide[PROD_CANA] / wide["_denom"],
        np.nan,
    )

    # 6. Média dos shares anuais por município (mean of ratios, conforme §9.6:
    #    mean_{t} [ Cana_it / (Cana+Milho+Algodao)_it ] )
    g = wide.groupby(["cod_ibge", "municipio_uf"], as_index=False).agg(
        share_cana_eq52_pre=("_share_ano", "mean"),
        n_anos_validos=("_share_ano", lambda s: int(s.notna().sum())),
        cana_t_mean=(PROD_CANA, "mean"),
        milho_t_mean=(PROD_MILHO, "mean"),
        algodao_t_mean=(PROD_ALGODAO, "mean"),
        denom_t_mean=("_denom", "mean"),
    )

    # 7. UF e filtro Centro-Sul
    g["uf"] = g["municipio_uf"].map(uf_from_municipio)
    g_cs = g[g["uf"].isin(UFS_CORE)].copy()

    # 8. Municípios canavieiros = ao menos 1 ano com cana > 0 na janela
    g_cs = g_cs[g_cs["cana_t_mean"] > 0].copy()
    g_cs = g_cs.sort_values(["uf", "municipio_uf"]).reset_index(drop=True)

    # --- Relatório de qualidade ---
    quality = {
        "janela_pre": f"{PRE_YEARS[0]}-{PRE_YEARS[-1]}",
        "n_municipios_canavieiros_cs": len(g_cs),
        "n_municipios_pam_total": g["cod_ibge"].nunique(),
        "share_mediana": float(g_cs["share_cana_eq52_pre"].median()),
        "share_p25": float(g_cs["share_cana_eq52_pre"].quantile(0.25)),
        "share_p50": float(g_cs["share_cana_eq52_pre"].quantile(0.50)),
        "share_p75": float(g_cs["share_cana_eq52_pre"].quantile(0.75)),
        "share_p90": float(g_cs["share_cana_eq52_pre"].quantile(0.90)),
        "n_share_gt_050": int((g_cs["share_cana_eq52_pre"] > 0.50).sum()),
        "n_share_gt_075": int((g_cs["share_cana_eq52_pre"] > 0.75).sum()),
        "n_share_gt_090": int((g_cs["share_cana_eq52_pre"] > 0.90).sum()),
        "n_anos_validos_mediana": float(g_cs["n_anos_validos"].median()),
        "n_municipios_lt3_anos": int((g_cs["n_anos_validos"] < 3).sum()),
    }
    # Subsets §9.6.2 (declarados ex-ante)
    p50 = quality["share_p50"]
    p25 = quality["share_p25"]
    quality["P50_corte"] = p50
    quality["P25_corte"] = p25
    quality["n_cana_dominante_gtP50"] = int(
        (g_cs["share_cana_eq52_pre"] > p50).sum()
    )
    quality["n_cana_minoritaria_ltP25"] = int(
        (g_cs["share_cana_eq52_pre"] < p25).sum()
    )

    df_quality = pd.DataFrame([quality])

    # Marca os subsets no df principal (para uso direto em B4.M.5)
    g_cs["subset_9_6"] = np.select(
        [
            g_cs["share_cana_eq52_pre"] > p50,
            g_cs["share_cana_eq52_pre"] < p25,
        ],
        ["cana_dominante", "cana_minoritaria"],
        default="intermediario",
    )

    cols = [
        "cod_ibge", "municipio_uf", "uf",
        "share_cana_eq52_pre", "n_anos_validos",
        "cana_t_mean", "milho_t_mean", "algodao_t_mean", "denom_t_mean",
        "subset_9_6",
    ]
    return g_cs[cols], df_quality


def main():
    print("=" * 60)
    print("B4.M.3 — share_cana_eq52 pré-2018 (janela 2012-2017)")
    print("Pré-registro v2.3.9 §9.6")
    print("=" * 60)

    if not Path(PAM_PARQUET).exists():
        print(f"✗ PAM não encontrada em {PAM_PARQUET}")
        print("  Suba pam_1612_long_2012_2024.parquet para data/interim/")
        sys.exit(1)

    pam = pd.read_parquet(PAM_PARQUET)
    print(f"PAM carregada: {pam.shape}")
    print(f"Anos disponíveis: {sorted(pam['ano'].unique())}")
    print(f"Janela pré usada: {PRE_YEARS}")

    df_share, df_quality = build_share_cana_pre2018(pam)

    print(f"\n→ share_cana_eq52_pre construído: {df_share.shape}")
    print("\nDistribuição (canavieiros Centro-Sul, janela 2012-2017):")
    q = df_quality.iloc[0]
    print(f"  n municípios canavieiros : {q['n_municipios_canavieiros_cs']}")
    print(f"  mediana                  : {q['share_mediana']:.4f}")
    print(f"  P25 / P50 / P75 / P90    : {q['share_p25']:.3f} / "
          f"{q['share_p50']:.3f} / {q['share_p75']:.3f} / {q['share_p90']:.3f}")
    print(f"  share > 0,50             : {q['n_share_gt_050']}")
    print(f"  share > 0,75             : {q['n_share_gt_075']}")
    print(f"  share > 0,90             : {q['n_share_gt_090']}")
    print(f"\nSubsets §9.6.2 (cortes ex-ante):")
    print(f"  cana_dominante (>P50={q['P50_corte']:.3f}) : "
          f"{q['n_cana_dominante_gtP50']}")
    print(f"  cana_minoritaria (<P25={q['P25_corte']:.3f}): "
          f"{q['n_cana_minoritaria_ltP25']}")
    print(f"\nQualidade:")
    print(f"  n_anos_validos mediana   : {q['n_anos_validos_mediana']:.0f} "
          f"(de 6 possíveis)")
    print(f"  munis com <3 anos válidos: {q['n_municipios_lt3_anos']} "
          f"(power baixo, §9.6.4-ii)")

    df_share.to_csv(OUT_SHARE, index=False)
    df_quality.to_csv(OUT_QUALITY, index=False)
    print(f"\n✓ salvo: {OUT_SHARE}")
    print(f"✓ salvo: {OUT_QUALITY}")

    # Comparação com a versão all-years (sanity)
    print("\n--- Sanity: comparação com share all-years (se disponível) ---")
    try:
        ay_path = Path(str(OUT_SHARE).replace(
            "share_cana_eq52_pre2018.csv", "share_cana_eq52_municipio.csv"
        ))
        if not ay_path.exists():
            ay_path = Path("/mnt/user-data/outputs/share_cana_eq52_municipio.csv")
        ay = pd.read_csv(ay_path)
        merged = df_share.assign(
            cod_ibge=df_share["cod_ibge"].astype(str)
        ).merge(
            ay.assign(cod_ibge=ay["cod_ibge"].astype(str))[
                ["cod_ibge", "share_cana_eq52_mean"]
            ],
            on="cod_ibge", how="inner",
        )
        if len(merged):
            corr = merged["share_cana_eq52_pre"].corr(
                merged["share_cana_eq52_mean"]
            )
            diff = (merged["share_cana_eq52_pre"]
                    - merged["share_cana_eq52_mean"]).abs()
            print(f"  municípios em comum     : {len(merged)}")
            print(f"  correlação pre vs all   : {corr:.4f}")
            print(f"  |diff| média            : {diff.mean():.4f}")
            print(f"  |diff| máx               : {diff.max():.4f}")
            print("  (correlação alta esperada; diff reflete que a janela")
            print("   pré exclui 2018-2024, onde share pode ter mudado)")
    except Exception as e:
        print(f"  (comparação pulada: {e})")

    print("\n" + "=" * 60)
    print("B4.M.3 concluído.")
    print("=" * 60)


if __name__ == "__main__":
    main()
