"""
B4.M.5 — Heterogeneidade por intensidade de cana (Configuração D §6.5)
======================================================================
Pré-registro v2.5 §6.5 + revisão metodológica para v2.6.

REVISÃO DE DESENHO (21/05/2026):
A H6 original (v2.3.7/v2.3.8) comparava cana-dominante (>P50 universo CS) vs
cana-minoritária (<P25 universo CS). Aplicada aos 842 canavieiros, restam
apenas 1 município "cana-minoritário" entre os 194 tratados (definição
universo CS leva 505 munis sem cana para esse grupo). Teste binário
inviável.

ALTERAÇÃO: usar TERCIS INTRA-CANAVIEIROS do share_cana_eq52_pre (P33, P66
calculados dos 842 munis). Distribui n equilibrado por tercil e permite
ver gradiente de efeito (dose-response) — argumentação causal mais forte
que comparação binária. Mudança ex-post pelos dados (estrutura do universo
revelada após filtro), não pelo ATT — registrada como J6/K-extra v2.6.

ANÁLISE:
- 5 outcomes: log_solos_manejados (H6 original) + 4 primários B4.M.4
  (asinh_cana_direto, log1p_fert_n, log1p_calagem, log1p_res_outros)
- 1 spec: FULL2 (decisão v2.4; robustez por spec já validada em 11d/11f)
- 3 tercis: cada um rodado independentemente com CS-DR (Bug 1 NaN never-treated)

CRITÉRIO §6.5 Configuração D refinado para tercis:
  Confirmada se ATT(T3 alto) > ATT(T1 baixo) com gradiente monotônico
  para o outcome principal (cana_direto). Espera-se dose-response causal:
  canavieiros mais "puros" recebem mais incentivo proporcional via CBIO.
"""
from __future__ import annotations
import time
import numpy as np
import pandas as pd


# Outcomes B4.M.5 (decisão 21/05): H6 original + decomposição B4.M.4 v2.4
OUTCOMES_B4M5 = [
    "log_solos_manejados",     # H6 original (v2.3.7)
    "asinh_cana_direto",       # Configuração I §6.5 v2.4 — outcome chave
    "log1p_fert_n",            # H5.2
    "log1p_calagem",           # H5.2
    "log1p_res_outros",        # H5.3
]


def normalize_geocode(s: pd.Series) -> pd.Series:
    return s.astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(7)


def build_tercil_subsets(
    panel: pd.DataFrame,
    share_csv_path: str,
) -> tuple[pd.DataFrame, dict]:
    """
    Adiciona coluna `tercil_share_cana` ao painel com 3 valores: T1, T2, T3
    (baixo, médio, alto). Tercis calculados intra-canavieiros (842 munis),
    não no universo CS.

    Parameters
    ----------
    panel : painel canônico canavieiro (842 munis × 10 anos = 8.420 linhas)
    share_csv_path : caminho para share_cana_eq52_pre2018.csv

    Returns
    -------
    panel_with_tercil : painel com coluna `tercil_share_cana` adicionada
    tercil_info : dict com P33, P66, n por tercil, n tratados por tercil
    """
    sc = pd.read_csv(share_csv_path)

    # Normalizar geocode (no CSV o nome é 'cod_ibge', no painel é 'geocode')
    sc["geocode"] = normalize_geocode(sc["cod_ibge"])
    sc = sc[["geocode", "share_cana_eq52_pre"]].drop_duplicates("geocode")

    pc = panel.copy()
    pc["geocode"] = normalize_geocode(pc["geocode"])

    # Restringir share_csv aos 842 canavieiros antes de calcular os tercis
    canavieiros = pc["geocode"].unique()
    sc_can = sc[sc["geocode"].isin(canavieiros)].copy()

    # Calcular P33, P66 intra-canavieiros
    p33 = float(sc_can["share_cana_eq52_pre"].quantile(0.33))
    p66 = float(sc_can["share_cana_eq52_pre"].quantile(0.66))

    # Classificar
    def classify(x):
        if pd.isna(x):
            return np.nan
        if x < p33:
            return "T1_baixo"
        elif x < p66:
            return "T2_medio"
        else:
            return "T3_alto"

    sc_can["tercil_share_cana"] = sc_can["share_cana_eq52_pre"].apply(classify)

    # Merge no painel (left-join, preserva n_linhas)
    n_before = len(pc)
    merged = pc.merge(
        sc_can[["geocode", "share_cana_eq52_pre", "tercil_share_cana"]],
        on="geocode", how="left",
    )
    assert len(merged) == n_before, f"join alterou n: {n_before} -> {len(merged)}"

    # Diagnóstico
    n_total = pc["geocode"].nunique()
    n_match = merged.dropna(subset=["tercil_share_cana"])["geocode"].nunique()
    n_no_match = n_total - n_match

    # Contar tratados por tercil
    if "is_treated_ever" in merged.columns:
        is_treat_col = "is_treated_ever"
    elif "treated" in merged.columns:
        is_treat_col = "treated"
    else:
        is_treat_col = None

    info = {
        "p33": p33, "p66": p66,
        "n_canavieiros": n_total,
        "n_com_share": n_match,
        "n_sem_share": n_no_match,
    }

    print(f"  P33 (intra-canavieiros) = {p33:.4f}")
    print(f"  P66 (intra-canavieiros) = {p66:.4f}")
    print(f"\n  Distribuição dos 842 canavieiros por tercil:")
    one_per_muni = (merged.drop_duplicates("geocode")
                    .groupby("tercil_share_cana").size())
    for t in ["T1_baixo", "T2_medio", "T3_alto"]:
        n_t = int(one_per_muni.get(t, 0))
        info[f"n_{t}"] = n_t
        print(f"    {t}: {n_t} munis")
    if n_no_match > 0:
        print(f"    sem tercil (NaN): {n_no_match} munis")

    if is_treat_col:
        print(f"\n  Tratados ({is_treat_col}=True) por tercil:")
        treated_per_t = (merged[merged[is_treat_col] == True]
                         .drop_duplicates("geocode")
                         .groupby("tercil_share_cana").size())
        for t in ["T1_baixo", "T2_medio", "T3_alto"]:
            n_t = int(treated_per_t.get(t, 0))
            info[f"n_{t}_tratados"] = n_t
            print(f"    {t}: {n_t} tratados")

    return merged, info


def run_csdr_by_tercil(
    panel_cs: pd.DataFrame,
    outcomes: list[str],
    covs: list[str],
    tercil_col: str = "tercil_share_cana",
    tercis: list[str] = ("T1_baixo", "T2_medio", "T3_alto"),
    n_boot: int = 999,
    random_state: int = 42,
    cohort_col: str = "g_m_cs",
) -> pd.DataFrame:
    """
    Roda CS-DR para cada (outcome × tercil) usando como amostra:
      tratados pertencentes ao tercil + TODOS nunca-tratados (642 munis).

    Justificativa: usar nunca-tratados de todos os tercis como controle
    aumenta poder e permite identificação heterogênea correta (estimador
    CS-DR usa never-treated como contrafactual via PSM).

    Bug 1 do 11a respeitado (NaN = never-treated em g_m_cs).
    """
    from differences import ATTgt

    results = []
    t0 = time.time()

    # Identificar never-treated (g_m_cs = NaN)
    never_mask = panel_cs[cohort_col].isna()
    never_geocodes = panel_cs[never_mask]["geocode"].unique()

    for outcome in outcomes:
        if outcome not in panel_cs.columns:
            print(f">>> {outcome}: AUSENTE, pulado")
            continue
        print(f"\n>>> {outcome}")
        for tercil in tercis:
            t_sub = time.time()
            try:
                # Subset: tratados deste tercil + todos nunca-tratados
                tratados_no_tercil = (
                    panel_cs[
                        (~panel_cs[cohort_col].isna())  # tratados
                        & (panel_cs[tercil_col] == tercil)
                    ]["geocode"].unique()
                )
                amostra = list(tratados_no_tercil) + list(never_geocodes)
                data = (
                    panel_cs[panel_cs["geocode"].isin(amostra)]
                    .dropna(subset=[outcome])
                    .set_index(["geocode", "ano"])
                    .sort_index()
                )
                n_munis_total = data.index.get_level_values("geocode").nunique()
                n_tratados_tercil = len(tratados_no_tercil)

                attgt = ATTgt(data=data, cohort_column=cohort_col)
                attgt.fit(
                    formula=f"{outcome} ~ " + " + ".join(covs),
                    est_method="dr",
                    control_group="never_treated",
                    boot_iterations=n_boot,
                    random_state=random_state,
                    progress_bar=False,
                    n_jobs=1,
                )
                agg = attgt.aggregate("simple")
                agg_flat = (agg.copy() if isinstance(agg, pd.DataFrame)
                            else pd.DataFrame([agg]))
                att = float(agg_flat.iloc[0, 0])
                se = float(agg_flat.iloc[0, 1])
                ci_lo = (float(agg_flat.iloc[0, 2])
                         if agg_flat.shape[1] > 2 else att - 1.96 * se)
                ci_hi = (float(agg_flat.iloc[0, 3])
                         if agg_flat.shape[1] > 3 else att + 1.96 * se)
                z = abs(att / se) if (np.isfinite(se) and se > 0) else np.nan
                sig = (np.isfinite(z) and z > 1.959963985)

                results.append({
                    "outcome": outcome,
                    "tercil": tercil,
                    "ATT": att, "SE": se,
                    "z": z if np.isfinite(z) else np.nan,
                    "sig_5pct": sig,
                    "CI_lo": ci_lo, "CI_hi": ci_hi,
                    "n_munis_total": n_munis_total,
                    "n_tratados_tercil": n_tratados_tercil,
                })
                flag = "*" if sig else " "
                print(f"  {tercil:10s} ATT = {att:+.4f}  SE={se:.4f}  "
                      f"|z|={z:.2f}{flag}  (n_trat={n_tratados_tercil})  "
                      f"[{time.time()-t_sub:.1f}s]")
            except Exception as e:
                print(f"  {tercil:10s} FALHOU: "
                      f"{type(e).__name__}: {str(e)[:80]}")
                results.append({
                    "outcome": outcome, "tercil": tercil,
                    "ATT": np.nan, "SE": np.nan, "z": np.nan,
                    "sig_5pct": False, "CI_lo": np.nan, "CI_hi": np.nan,
                    "n_munis_total": 0, "n_tratados_tercil": 0,
                })
    df = pd.DataFrame(results)
    ok = df["ATT"].notna().sum()
    print(f"\nOK CS-DR por tercil: {ok}/{len(df)} sucessos em "
          f"{time.time()-t0:.1f}s")
    return df


def assess_dose_response(att_df: pd.DataFrame) -> pd.DataFrame:
    """
    Diagnóstico de dose-response por outcome.

    Para cada outcome, verifica se há gradiente monotônico T1 < T2 < T3
    (esperado para outcomes positivos como cana_direto sob hipótese causal).

    Vereditos:
    - DOSE_RESPONSE_POSITIVO: T3 > T2 > T1 e T3 sig 5%
    - DOSE_RESPONSE_NEGATIVO: T3 < T2 < T1 e T3 sig 5% (gradiente decrescente)
    - SEM_DOSE_RESPONSE_SIG: T3 sig mas sem gradiente claro
    - SEM_EFEITO: nenhum tercil sig
    - PARCIAL: gradiente sem T3 sig 5%
    """
    rows = []
    for outcome in att_df["outcome"].unique():
        sub = att_df[att_df["outcome"] == outcome].set_index("tercil")
        att_t1 = sub.loc["T1_baixo", "ATT"] if "T1_baixo" in sub.index else np.nan
        att_t2 = sub.loc["T2_medio", "ATT"] if "T2_medio" in sub.index else np.nan
        att_t3 = sub.loc["T3_alto", "ATT"] if "T3_alto" in sub.index else np.nan
        sig_t1 = (sub.loc["T1_baixo", "sig_5pct"]
                  if "T1_baixo" in sub.index else False)
        sig_t2 = (sub.loc["T2_medio", "sig_5pct"]
                  if "T2_medio" in sub.index else False)
        sig_t3 = (sub.loc["T3_alto", "sig_5pct"]
                  if "T3_alto" in sub.index else False)

        # Diferença T3 - T1 (dose-response cru)
        delta_t3_t1 = att_t3 - att_t1 if (np.isfinite(att_t1)
                                          and np.isfinite(att_t3)) else np.nan

        # Monotonicidade positiva
        mono_pos = (np.isfinite(att_t1) and np.isfinite(att_t2)
                    and np.isfinite(att_t3) and att_t1 < att_t2 < att_t3)
        mono_neg = (np.isfinite(att_t1) and np.isfinite(att_t2)
                    and np.isfinite(att_t3) and att_t1 > att_t2 > att_t3)
        algum_sig = sig_t1 or sig_t2 or sig_t3

        if mono_pos and sig_t3:
            veredito = "DOSE_RESPONSE_POSITIVO"
        elif mono_neg and sig_t3:
            veredito = "DOSE_RESPONSE_NEGATIVO"
        elif sig_t3 and not (mono_pos or mono_neg):
            veredito = "SEM_DOSE_RESPONSE_SIG"
        elif algum_sig and (mono_pos or mono_neg):
            veredito = "PARCIAL"
        elif not algum_sig:
            veredito = "SEM_EFEITO"
        else:
            veredito = "MISTO"

        rows.append({
            "outcome": outcome,
            "ATT_T1": att_t1, "sig_T1": sig_t1,
            "ATT_T2": att_t2, "sig_T2": sig_t2,
            "ATT_T3": att_t3, "sig_T3": sig_t3,
            "delta_T3_T1": delta_t3_t1,
            "monotonia": "+" if mono_pos else ("-" if mono_neg else "0"),
            "veredito": veredito,
        })
    return pd.DataFrame(rows)
