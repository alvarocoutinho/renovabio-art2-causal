"""
B4 — Teste empírico da hipótese de substituição de área (pós-B4.M.4)
====================================================================
Decisão de 20/05/2026 — após descoberta de ATT_res_outros < 0 sig 5% em B4.M.4.

Hipótese a testar:
  H6.1 (PAM)        — Canavieiros certificados expandem área de cana e
                      reduzem área de outras culturas (soja, milho, algodão).
  H6.2 (MapBiomas)  — Substituição visível também no uso do solo:
                      cana ↑, pastagem/veg_nativa ↓. Detecção de desmatamento
                      associado se ATT(veg_nativa) < 0.

Estimador: CS-DR (Callaway-Sant'Anna 2021), idêntico ao 11a/11d.
3 bugs do 11a respeitados (NaN never-treated, n_jobs=1, drop 6 covs).

Outcomes (transformações conforme decisão 20/05):
  PAM (4 outcomes):
    log1p_pam_area_cana          ← cana ↑ esperado se expansão
    asinh_pam_area_soja          ← 20% zeros → asinh estável
    asinh_pam_area_milho         ← zeros possíveis
    asinh_pam_area_algodao       ← cobertura baixa em CS, asinh defensivo
  MapBiomas (6 outcomes, shares = uso do solo reorganizado):
    log1p_share_cana_mapb        ← reorganização cana
    log1p_share_pastagem_mapb    ← pastagem substituída?
    log1p_share_vegetacao_nativa_mapb ← desmatamento associado?
    asinh_share_soja_mapb        ← competição soja
    asinh_share_silvicultura_mapb ← silvicultura
    asinh_share_urbano_infra_mapb ← urbanização (controle, esperado ≈0)

Saídas:
  att_substituicao_pam.csv         — 4 outcomes × 4 specs = 16 ATTs
  att_substituicao_mapbiomas.csv   — 6 outcomes × 4 specs = 24 ATTs
  att_substituicao_config.csv      — síntese da Configuração de substituição
"""
from __future__ import annotations
import time
import numpy as np
import pandas as pd


# Outcomes PAM — sufixo _t para deixar EXPLÍCITO que é série temporal da PAM long,
# não as colunas constantes pam_area_cana/soja/milho do painel canônico (que são
# valores fixos de baseline e NÃO podem ser usados como outcome em CS-DR).
OUTCOMES_PAM = [
    "log1p_pam_area_cana_t",
    "asinh_pam_area_soja_t",
    "asinh_pam_area_milho_t",
    "asinh_pam_area_algodao_t",
]
TRANSFORM_PAM = {
    "pam_area_cana_t":    "log1p",
    "pam_area_soja_t":    "asinh",
    "pam_area_milho_t":   "asinh",
    "pam_area_algodao_t": "asinh",
}

# Outcomes MapBiomas (shares — reorganização do uso do solo)
OUTCOMES_MAPB = [
    "log1p_share_cana_mapb",
    "log1p_share_pastagem_mapb",
    "log1p_share_vegetacao_nativa_mapb",
    "asinh_share_soja_mapb",
    "asinh_share_silvicultura_mapb",
    "asinh_share_urbano_infra_mapb",
]
TRANSFORM_MAPB = {
    "share_cana_mapb":             "log1p",
    "share_pastagem_mapb":         "log1p",
    "share_vegetacao_nativa_mapb": "log1p",
    "share_soja_mapb":             "asinh",
    "share_silvicultura_mapb":     "asinh",
    "share_urbano_infra_mapb":     "asinh",
}


def normalize_geocode(s: pd.Series) -> pd.Series:
    """Convenção do 11a: geocode como str de 7 dígitos."""
    return s.astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(7)


def join_pam_areas_temporal(panel: pd.DataFrame,
                            pam_long: pd.DataFrame) -> pd.DataFrame:
    """
    Traz as 4 culturas (cana, soja, milho, algodão) da PAM long como SÉRIE
    TEMPORAL município × ano. Sufixo _t deixa explícito que é série temporal.

    ATENÇÃO (descoberta 20/05/2026): as colunas `pam_area_cana`, `pam_area_soja`,
    `pam_area_milho` do `panel_canavieiro_main` são valores CONSTANTES por
    município (baseline pré-tratamento). Variância intra-município = 0 nos
    842 munis. Usar essas colunas como outcome em CS-DR produz ATT=0 SE=NaN
    porque todas as diferenças temporais são zero. Esta função traz as
    séries temporais reais via PAM long.

    Salva também a contagem de munis com variação temporal por cultura
    (diagnóstico de cobertura).
    """
    PRODS = {
        "Cana-de-açúcar":               "pam_area_cana_t",
        "Soja (em grão)":               "pam_area_soja_t",
        "Milho (em grão)":              "pam_area_milho_t",
        "Algodão herbáceo (em caroço)": "pam_area_algodao_t",
    }
    pc = panel.copy()
    pc["geocode"] = normalize_geocode(pc["geocode"])
    pc["ano"] = pc["ano"].astype(int)

    pl = pam_long[pam_long["produto"].isin(PRODS.keys())].copy()
    pl["geocode"] = normalize_geocode(pl["cod_ibge"])
    pl["ano"] = pl["ano"].astype(int)
    pl["area_plantada_ha"] = pd.to_numeric(
        pl["area_plantada_ha"], errors="coerce"
    ).fillna(0.0)

    # Pivot: 1 linha por (geocode, ano), 4 colunas culturas
    piv = pl.pivot_table(
        index=["geocode", "ano"], columns="produto",
        values="area_plantada_ha", aggfunc="sum", fill_value=0.0,
    ).reset_index()
    piv.columns.name = None
    piv = piv.rename(columns=PRODS)
    for c in PRODS.values():
        if c not in piv.columns:
            piv[c] = 0.0

    piv_keep = piv[["geocode", "ano"] + list(PRODS.values())]
    piv_keep = piv_keep.drop_duplicates(subset=["geocode", "ano"])

    # Drop columns colidentes (as constantes do painel canônico) ANTES do merge,
    # para evitar suffixes _x/_y e garantir que usaremos as séries temporais.
    drop_const = [c for c in ["pam_area_cana", "pam_area_soja", "pam_area_milho"]
                  if c in pc.columns]
    if drop_const:
        pc = pc.drop(columns=drop_const)
        print(f"  dropadas (eram constantes intra-municipio): {drop_const}")

    n_before = len(pc)
    merged = pc.merge(piv_keep, on=["geocode", "ano"], how="left")
    assert len(merged) == n_before, (
        f"join PAM alterou n linhas: {n_before} -> {len(merged)}"
    )

    # Munis sem registro na PAM = zero plantio (não NaN — PAM cobre 5.562 munis,
    # canavieiros estão todos lá)
    for col in PRODS.values():
        merged[col] = merged[col].fillna(0.0)

    # Diagnóstico de variação temporal (sanidade)
    print(f"  PAM joinada como série temporal:")
    for col in PRODS.values():
        munis_var = (merged.groupby("geocode")[col].std() > 0).sum()
        zeros = int((merged[col] == 0).sum())
        print(f"    {col:22s}: {munis_var}/842 munis variam temporalmente, "
              f"{zeros} celulas == 0")
    return merged


# Alias legado (mantém compat com notebook 11e v1, descontinuar em v2)
def join_algodao_from_pam(panel, pam_long):
    """DEPRECATED v2 (20/05/2026): use join_pam_areas_temporal."""
    print("  AVISO: join_algodao_from_pam descontinuada — use "
          "join_pam_areas_temporal (traz as 4 culturas como série temporal).")
    return join_pam_areas_temporal(panel, pam_long)


def join_mapbiomas_shares(panel: pd.DataFrame,
                          mapb_panel: pd.DataFrame) -> pd.DataFrame:
    """
    Left-join dos 6 shares MapBiomas no painel canônico por (geocode, ano).
    """
    pc = panel.copy()
    pc["geocode"] = normalize_geocode(pc["geocode"])
    pc["ano"] = pc["ano"].astype(int)

    mb = mapb_panel.copy()
    mb["geocode"] = normalize_geocode(mb["geocode"])
    mb["ano"] = mb["ano"].astype(int)

    cols_to_join = ["geocode", "ano"] + list(TRANSFORM_MAPB.keys())
    cols_present = [c for c in cols_to_join if c in mb.columns]
    missing = set(TRANSFORM_MAPB.keys()) - set(mb.columns)
    if missing:
        print(f"  ATENCAO: colunas MapBiomas ausentes: {missing}")
    mb_keep = mb[cols_present].drop_duplicates(subset=["geocode", "ano"])

    n_before = len(pc)
    merged = pc.merge(mb_keep, on=["geocode", "ano"], how="left")
    assert len(merged) == n_before, (
        f"join mapbiomas alterou n linhas: {n_before} -> {len(merged)}"
    )

    n_842 = pc["geocode"].nunique()
    n_match = merged[merged["share_cana_mapb"].notna()]["geocode"].nunique()
    print(f"  mapbiomas: {n_842} munis no painel canonico, "
          f"{n_match} com shares casados")
    return merged


def apply_transformations(panel: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica log1p ou asinh para cada outcome conforme TRANSFORM_PAM e
    TRANSFORM_MAPB. Espelha a lógica do apply_transformations em seeg.py
    e do build_cana_direto em b4m4_decomposicao.py.
    """
    out = panel.copy()
    all_transforms = {**TRANSFORM_PAM, **TRANSFORM_MAPB}

    for col, transform in all_transforms.items():
        if col not in out.columns:
            print(f"  AVISO: {col} ausente, transformacao pulada")
            continue
        x = pd.to_numeric(out[col], errors="coerce")
        if transform == "log1p":
            # log1p exige x >= 0; clipa em 0 para shares numericamente negativos
            out[f"log1p_{col}"] = np.log1p(x.clip(lower=0))
        elif transform == "asinh":
            out[f"asinh_{col}"] = np.arcsinh(x)
        else:
            raise ValueError(f"transform desconhecida: {transform}")
    return out


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
    Chamada IDÊNTICA à do 11a célula 14 e ao b4m4_decomposicao v2.4.
    """
    from differences import ATTgt

    results = []
    t0 = time.time()
    for outcome in outcomes:
        if outcome not in panel_cs.columns:
            print(f"\n>>> {outcome}  -- AUSENTE, pulado")
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
    print(f"\nOK CS-DR: {ok}/{len(df)} sucessos em {time.time()-t0:.1f}s")
    return df


def assess_substitution(
    att_pam: pd.DataFrame,
    att_mapb: pd.DataFrame,
    spec_principal: str = "FULL2",
) -> dict:
    """
    Diagnóstico de substituição de área usando os ATTs do spec principal.
    
    Critérios:
      Substituição agrícola PAM: ATT(cana) > 0 sig E ATT(soja|milho|algodao) < 0 sig
      Substituição MapBiomas:    ATT(share_cana) > 0 sig E ATT(pastagem|veg_nat) < 0 sig
      Desmatamento associado:    ATT(share_vegetacao_nativa) < 0 sig (sub-critério)
    """
    Z_CRIT = 1.959963985

    def get_sig(df, outcome):
        sub = df[(df["outcome"] == outcome) & (df["spec"] == spec_principal)]
        if sub.empty or pd.isna(sub.iloc[0]["ATT"]):
            return np.nan, np.nan, False, False
        att = float(sub.iloc[0]["ATT"])
        se = float(sub.iloc[0]["SE"]) if pd.notna(sub.iloc[0]["SE"]) else np.nan
        sig = (np.isfinite(se) and se > 0 and abs(att / se) > Z_CRIT)
        return att, se, sig, sig and att < 0

    # PAM
    pam = {}
    for o in OUTCOMES_PAM:
        att, se, sig, neg_sig = get_sig(att_pam, o)
        pam[o] = {"ATT": att, "SE": se, "sig_5pct": sig, "neg_sig": neg_sig}

    # MapBiomas
    mapb = {}
    for o in OUTCOMES_MAPB:
        att, se, sig, neg_sig = get_sig(att_mapb, o)
        mapb[o] = {"ATT": att, "SE": se, "sig_5pct": sig, "neg_sig": neg_sig}

    # Diagnósticos
    cana_pam_pos_sig = pam["log1p_pam_area_cana_t"]["ATT"] > 0 and \
                       pam["log1p_pam_area_cana_t"]["sig_5pct"]
    outras_pam_neg_sig = any(pam[o]["neg_sig"] for o in [
        "asinh_pam_area_soja_t", "asinh_pam_area_milho_t", "asinh_pam_area_algodao_t"
    ])

    cana_mapb_pos_sig = mapb["log1p_share_cana_mapb"]["ATT"] > 0 and \
                        mapb["log1p_share_cana_mapb"]["sig_5pct"]
    pastagem_neg_sig = mapb["log1p_share_pastagem_mapb"]["neg_sig"]
    vegnat_neg_sig = mapb["log1p_share_vegetacao_nativa_mapb"]["neg_sig"]

    # Configuração
    if cana_pam_pos_sig and outras_pam_neg_sig and cana_mapb_pos_sig and \
       (pastagem_neg_sig or vegnat_neg_sig):
        config = "SUB-COMPLETA"
        narrativa = ("Substituição confirmada PAM + MapBiomas: cana expande, "
                     "outras culturas/usos diminuem. Mecanismo da H5.3 res_outros<0.")
    elif cana_pam_pos_sig and outras_pam_neg_sig:
        config = "SUB-PARCIAL-PAM"
        narrativa = ("Substituição agrícola visível em PAM mas não em MapBiomas. "
                     "Interpretação cautelosa.")
    elif cana_mapb_pos_sig and (pastagem_neg_sig or vegnat_neg_sig):
        config = "SUB-PARCIAL-MAPB"
        narrativa = ("Substituição visível em MapBiomas mas não em PAM. "
                     "Reorganização de uso do solo sem mudança em área plantada declarada.")
    elif cana_pam_pos_sig or cana_mapb_pos_sig:
        config = "EXPANSAO-SEM-SUB"
        narrativa = ("Cana expande mas não há contração detectável de outras "
                     "culturas/usos. Expansão sobre fronteira agrícola nova?")
    else:
        config = "SEM-EXPANSAO"
        narrativa = ("Sem evidência de expansão de cana nem de substituição. "
                     "Mecanismo da H5.3 res_outros<0 NÃO suportado.")

    return {
        "spec_principal": spec_principal,
        "configuracao_substituicao": config,
        "narrativa": narrativa,
        "pam_cana_pos_sig": cana_pam_pos_sig,
        "pam_outras_neg_sig": outras_pam_neg_sig,
        "mapb_cana_pos_sig": cana_mapb_pos_sig,
        "mapb_pastagem_neg_sig": pastagem_neg_sig,
        "mapb_vegnat_neg_sig": vegnat_neg_sig,
        "desmatamento_associado": vegnat_neg_sig,
        **{f"PAM_{k}_ATT": v["ATT"] for k, v in pam.items()},
        **{f"PAM_{k}_sig": v["sig_5pct"] for k, v in pam.items()},
        **{f"MAPB_{k}_ATT": v["ATT"] for k, v in mapb.items()},
        **{f"MAPB_{k}_sig": v["sig_5pct"] for k, v in mapb.items()},
    }
