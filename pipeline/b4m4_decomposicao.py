"""
B4.M.4 — Decomposição mecanística: CS-DR × canais primários × 4 specs PSM
=========================================================================
Pré-registro v2.4 §7.7 (configuração E) + §6.5 (critério M paramétrico).

Espelha EXATAMENTE a chamada CS-DR canônica do notebook 11a (v4) que
produziu a Tabela 2 do v2.3.7. Diferenças vs 11a:
  1. Outcomes são os canais da decomposição (não os macro-canais)
  2. v2.4: cana_direto = res_cana + org_cana (consolidado por colinearidade
     r=0,9996 documentada em §3.10.2 / bloco J do histórico)

Estimador: differences.ATTgt (Callaway & Sant'Anna 2021, doubly-robust),
est_method='dr', control_group='never_treated', n_jobs=1.

Os 3 bugs conhecidos do 11a são respeitados:
  Bug 1 — never-treated = NaN em g_m_cs (não fillna(0))
  Bug 2 — n_jobs=1 (n_jobs=-1 quebra bootstrap)
  Bug 3 — 6 covs colidentes dropadas do painel antes do merge

Opção B (decisão 19/05): os sub-canais entram via LEFT-JOIN no
panel_canavieiro_main (842) por (geocode, ano). O painel canônico e
suas covariáveis PSM permanecem intactos.

Camadas (v2.4):
  Construção (pipeline seeg.py):   6 sub-canais separados (B4.M.1 intacto)
  Validação algébrica (B4.M.2):    Σ sub ≡ solos_manejados (intacta)
  Inferência (este módulo, v2.4):  cana_direto = res_cana + org_cana,
                                   4 outcomes primários + 2 verificação

Outcomes (§3.10.2 v2.4):
  PRIMÁRIOS (entram em H5.1/H5.2/H5.3, Tabela 4, critério M):
    asinh_cana_direto  — H5.1 (consolidado em v2.4)
    log1p_fert_n       — H5.2 (componente)
    log1p_calagem      — H5.2 (componente)
    log1p_res_outros   — H5.3 (controle não-cana)
  VERIFICAÇÃO (apêndice de cobertura, sem ATT primário):
    asinh_res_cana, asinh_org_cana (sob FULL apenas)
  res_minor reportado só em apêndice, sem ATT estimado.

Saídas:
  att_canais_main.csv        — 4 primários × 4 specs + 2 verificação (FULL)
  att_canais_eventstudy.csv  — event-study FULL × 4 primários
  att_canais_config.csv      — M_direto (cana_direto), M_proxy, Config I/II/III
"""
from __future__ import annotations
import time
import numpy as np
import pandas as pd


# v2.4: Outcomes primários (entram em H5.1/H5.2/H5.3 e critério M)
OUTCOMES_PRIMARIOS = [
    "asinh_cana_direto",   # consolidado em v2.4 (H5.1)
    "log1p_fert_n",        # H5.2
    "log1p_calagem",       # H5.2
    "log1p_res_outros",    # H5.3
]

# Outcomes de verificação (apêndice de cobertura, rodados só sob FULL)
OUTCOMES_VERIFICACAO = [
    "asinh_res_cana",
    "asinh_org_cana",
]

# Mapeia outcome → classe para o critério M
OUTCOME_META = {
    "asinh_cana_direto": ("cana_direto", "direto"),
    "log1p_fert_n":      ("fert_n",      "proxy"),
    "log1p_calagem":     ("calagem",     "proxy"),
    "log1p_res_outros":  ("res_outros",  "controle"),
}

# Sub-canais brutos no painel SEEG (camada de construção, B4.M.1)
SUBCANAIS_NIVEL_BRUTO = [
    "res_cana", "org_cana", "fert_n", "calagem", "res_outros", "res_minor"
]


def normalize_geocode(s: pd.Series) -> pd.Series:
    """Convenção do 11a: geocode como str de 7 dígitos."""
    return s.astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(7)


def build_cana_direto(panel: pd.DataFrame) -> pd.DataFrame:
    """
    Constrói `cana_direto = res_cana + org_cana` (nível tCO2e) e o
    transformado `asinh_cana_direto`. Operação na CAMADA DE INFERÊNCIA
    (v2.4), após a validação algébrica B4.M.2 que opera sobre os 6
    sub-canais separados.

    Justificativa empírica: Pearson(asinh) = 0,9996, zero células com
    apenas um dos dois não-zero — §3.10.2 v2.4.
    """
    out = panel.copy()
    if "res_cana" in out.columns and "org_cana" in out.columns:
        out["cana_direto"] = out["res_cana"].fillna(0) + out["org_cana"].fillna(0)
        out["asinh_cana_direto"] = np.arcsinh(out["cana_direto"])
        # Onde ambos eram NaN (LACUNA_SUSPEITA), manter NaN
        mask_lacuna = panel["res_cana"].isna() & panel["org_cana"].isna()
        out.loc[mask_lacuna, "cana_direto"] = np.nan
        out.loc[mask_lacuna, "asinh_cana_direto"] = np.nan
    return out


def join_subchannels(
    panel_canon: pd.DataFrame,
    seeg_subcanais: pd.DataFrame,
) -> pd.DataFrame:
    """
    Opção B: left-join dos sub-canais transformados E níveis brutos no
    painel canônico de 842, por (geocode, ano). Painel canônico NÃO é
    alterado — só ganha colunas novas à direita.

    Inclui níveis brutos (res_cana, org_cana) para construir cana_direto
    na camada de inferência.

    Ambos os lados têm geocode normalizado para str zfill(7) antes do join.
    """
    pc = panel_canon.copy()
    sc = seeg_subcanais.copy()

    pc["geocode"] = normalize_geocode(pc["geocode"])
    sc["geocode"] = normalize_geocode(sc["geocode"])
    pc["ano"] = pc["ano"].astype(int)
    sc["ano"] = sc["ano"].astype(int)

    # Colunas a trazer:
    # - 5 outcomes transformados (já no seeg_subcanais_panel.csv via apply_transformations)
    # - 6 níveis brutos (para reconstruir cana_direto)
    # - flags F3 dos cana-rotulados
    transformados = [
        "asinh_res_cana", "asinh_org_cana",
        "log1p_fert_n", "log1p_calagem", "log1p_res_outros",
    ]
    cols_sub = ["geocode", "ano"]
    for c in transformados + SUBCANAIS_NIVEL_BRUTO:
        if c in sc.columns:
            cols_sub.append(c)
    for fc in ("flag_res_cana", "flag_org_cana"):
        if fc in sc.columns:
            cols_sub.append(fc)
    if "solos_manejados" in sc.columns:
        cols_sub.append("solos_manejados")

    sc_keep = sc[cols_sub].drop_duplicates(subset=["geocode", "ano"])

    n_before = len(pc)
    merged = pc.merge(sc_keep, on=["geocode", "ano"], how="left",
                      suffixes=("", "_sub"))
    assert len(merged) == n_before, (
        f"join alterou n de linhas: {n_before} → {len(merged)}"
    )

    # Constrói cana_direto na camada de inferência (v2.4)
    merged = build_cana_direto(merged)

    # Diagnóstico de cobertura
    n_842 = pc["geocode"].nunique()
    n_match = merged[merged["asinh_cana_direto"].notna()]["geocode"].nunique()
    print(f"  join: {n_842} munis no painel canônico, "
          f"{n_match} com cana_direto computado")
    if n_match < n_842:
        faltam = n_842 - n_match
        print(f"  AVISO: {faltam} munis sem cana_direto — investigar")
    return merged


def compute_subchannel_shares(seeg_subcanais: pd.DataFrame,
                              anos_main: list[int]) -> dict:
    """
    Recalcula os shares definitivos dos sub-canais (§6.5 paramétrica).
    Inclui s_cana_direto = s_res_cana + s_org_cana (consolidado v2.4).
    """
    sc = seeg_subcanais.copy()
    sc = sc[sc["ano"].astype(int).isin(anos_main)]
    subs = [s for s in SUBCANAIS_NIVEL_BRUTO if s in sc.columns]
    tot = sc[subs].sum().sum()
    shares = {s: float(sc[s].sum() / tot) if tot > 0 else float("nan")
              for s in subs}
    # Adiciona o consolidado v2.4
    if "res_cana" in shares and "org_cana" in shares:
        shares["cana_direto"] = shares["res_cana"] + shares["org_cana"]
    return shares


def run_csdr_outcomes(
    panel_cs: pd.DataFrame,
    outcomes: list[str],
    specs: dict,
    n_boot: int,
    random_state: int = 42,
    cohort_col: str = "g_m_cs",
) -> pd.DataFrame:
    """
    Roda CS-DR (differences.ATTgt) sobre os outcomes × specs.
    Chamada IDÊNTICA à do 11a célula 14 (mesmos argumentos).
    """
    from differences import ATTgt

    results = []
    t0 = time.time()
    for outcome in outcomes:
        if outcome not in panel_cs.columns:
            print(f"\n>>> {outcome}  — AUSENTE no painel, pulado")
            continue
        print(f"\n>>> {outcome}")
        for spec_name, covs in specs.items():
            t_spec = time.time()
            formula = f"{outcome} ~ " + " + ".join(covs)
            try:
                data = (panel_cs
                        .dropna(subset=[outcome])
                        .set_index(["geocode", "ano"])
                        .sort_index())
                n_munis = data.index.get_level_values("geocode").nunique()

                attgt = ATTgt(data=data, cohort_column=cohort_col)
                attgt.fit(
                    formula=formula,
                    est_method="dr",
                    control_group="never_treated",
                    boot_iterations=n_boot,
                    random_state=random_state,
                    progress_bar=False,
                    n_jobs=1,  # Bug 2
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
                results.append({
                    "outcome": outcome, "spec": spec_name,
                    "estimator": "CS-DR", "ATT": att, "SE": se,
                    "CI_lo": ci_lo, "CI_hi": ci_hi, "n_munis": n_munis,
                })
                print(f"  {spec_name:6s} ATT = {att:+.4f} "
                      f"(SE={se:.4f})  [{time.time()-t_spec:.1f}s]")
            except Exception as e:
                print(f"  {spec_name:6s} FALHOU: "
                      f"{type(e).__name__}: {str(e)[:80]}")
                results.append({
                    "outcome": outcome, "spec": spec_name,
                    "estimator": "CS-DR", "ATT": np.nan, "SE": np.nan,
                    "CI_lo": np.nan, "CI_hi": np.nan, "n_munis": 0,
                })
    df = pd.DataFrame(results)
    ok = df["ATT"].notna().sum()
    print(f"\n✓ CS-DR: {ok}/{len(df)} sucessos em {time.time()-t0:.1f}s")
    return df


def decide_configuration(
    att_df: pd.DataFrame,
    shares: dict,
    spec_principal: str = "FULL",
    fator: float = 1.5,
) -> dict:
    """
    Critério M_direto/M_proxy paramétrico (§6.5 v2.4).
    Denominadores = shares medidos em B4.M.1. cana_direto consolidado.

    M_direto = |ATT_cana_direto| / s_cana_direto                (v2.4)
    M_proxy  = |ATT_fert_n|/s_fert_n + |ATT_calagem|/s_calagem  (inalterado)

    Configuração I  se M_direto > 1.5·M_proxy E ATT_cana_direto sig. 5%
    Configuração II se M_proxy  > 1.5·M_direto E ≥1 comp. H5.2 sig. 5%
    Configuração III caso contrário
    """
    d = att_df.query("spec == @spec_principal and estimator == 'CS-DR'").copy()
    d = d.set_index("outcome")

    def get(o):
        if o in d.index and pd.notna(d.loc[o, "ATT"]):
            att = float(d.loc[o, "ATT"])
            se = float(d.loc[o, "SE"]) if pd.notna(d.loc[o, "SE"]) else np.nan
            sig = (np.isfinite(se) and se > 0
                   and abs(att / se) > 1.959963985)
            return att, se, sig
        return np.nan, np.nan, False

    a_cd, se_cd, sig_cd = get("asinh_cana_direto")
    a_fn, se_fn, sig_fn = get("log1p_fert_n")
    a_ca, se_ca, sig_ca = get("log1p_calagem")
    a_ro, se_ro, sig_ro = get("log1p_res_outros")

    s_cd = shares.get("cana_direto", np.nan)
    s_fn = shares.get("fert_n", np.nan)
    s_ca = shares.get("calagem", np.nan)

    M_direto = abs(a_cd) / s_cd
    M_proxy = abs(a_fn) / s_fn + abs(a_ca) / s_ca

    h51_sig = sig_cd                  # H5.1 = um termo (consolidado v2.4)
    h52_sig = sig_fn or sig_ca        # H5.2 = OR (≥1 componente)
    h53_null = not sig_ro             # H5.3 = res_outros não-significante

    if M_direto > fator * M_proxy and h51_sig:
        config = "I"
        narrativa = ("Cana-direta sustentada — efeito no canal "
                     "cana_direto consolidado; ver §6.5 Configuração I")
    elif M_proxy > fator * M_direto and h52_sig:
        config = "II"
        narrativa = ("Alocação proxy dominante — efeito em fert_n/calagem; "
                     "ver §6.5 Configuração II")
    else:
        config = "III"
        narrativa = ("Efeito disperso — sem canal dominante; "
                     "ver §6.5 Configuração III")

    return {
        "spec_principal": spec_principal,
        "fator": fator,
        "M_direto": M_direto,
        "M_proxy": M_proxy,
        "razao_direto_proxy": (M_direto / M_proxy
                               if M_proxy > 0 else np.inf),
        "ATT_cana_direto": a_cd, "sig_cana_direto": sig_cd,
        "ATT_fert_n": a_fn, "sig_fert_n": sig_fn,
        "ATT_calagem": a_ca, "sig_calagem": sig_ca,
        "ATT_res_outros": a_ro, "sig_res_outros": sig_ro,
        "H5.1_signif": h51_sig,
        "H5.2_signif": h52_sig,
        "H5.3_nulo": h53_null,
        "s_cana_direto": s_cd,
        "s_fert_n": s_fn, "s_calagem": s_ca,
        "configuracao": config,
        "narrativa": narrativa,
    }
