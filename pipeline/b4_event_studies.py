"""
B4 — Event-study e análise de pre-trends para todos os outcomes
==============================================================
Versão corrigida — 21/05/2026.

Correções principais:
1. `ATTgt.aggregate("event")` do pacote `differences` pode retornar um
   DataFrame com índice `relative_period` e colunas em MultiIndex.
   A versão anterior não fazia `reset_index()` quando o índice se chamava
   `relative_period`, deslocando as colunas: ATT podia virar event_time.
2. `_flatten_event_result` agora achata MultiIndex por nome, com fallback
   posicional apenas quando necessário.
3. `test_pretrends` agora aceita `pre_periods=(-4, -2)` como janela inclusiva
   ou lista explícita de períodos, ex.: `[-4, -3, -2]`.
4. `run_event_study` aceita `event_window=(-4, 6)` para filtrar o horizonte
   reportado após a agregação.
"""

from __future__ import annotations

import time
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


OUTCOMES_GRUPOS = {
    "G1_macro_v237": [
        "asinh_luc",
        "asinh_carbono_solo",
        "log1p_queima",
        "log_solos_manejados",
    ],
    "G2_decomposicao_B4M4": [
        "asinh_cana_direto",
        "log1p_fert_n",
        "log1p_calagem",
        "log1p_res_outros",
    ],
    "G3_substituicao_PAM": [
        "log1p_pam_area_cana_t",
        "asinh_pam_area_soja_t",
        "asinh_pam_area_milho_t",
        "asinh_pam_area_algodao_t",
    ],
    "G4_substituicao_MAPB": [
        "log1p_share_cana_mapb",
        "log1p_share_pastagem_mapb",
        "log1p_share_vegetacao_nativa_mapb",
        "asinh_share_soja_mapb",
        "asinh_share_silvicultura_mapb",
        "asinh_share_urbano_infra_mapb",
    ],
}


def _clean_col_name(col) -> str:
    """Converte nomes simples ou MultiIndex tuple em string estável."""
    if isinstance(col, tuple):
        parts = [str(x).strip() for x in col if str(x).strip() not in ("", "None", "nan")]
        return "_".join(parts) if parts else ""
    return str(col).strip()


def _norm_name(name: str) -> str:
    return (
        str(name)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace(".", "_")
        .replace("-", "_")
        .replace("__", "_")
    )


def _first_existing(columns: Sequence[str], predicates: Iterable) -> str | None:
    for col in columns:
        n = _norm_name(col)
        if any(pred(n) for pred in predicates):
            return col
    return None


def _ensure_event_time(event_df: pd.DataFrame) -> pd.DataFrame:
    """
    Garante coluna canônica `event_time`.
    Aceita também `relative_period`, `period` ou variações.
    """
    df = event_df.copy()
    if "event_time" in df.columns:
        return df

    candidates = [
        c for c in df.columns
        if _norm_name(c) in {
            "relative_period",
            "event_time",
            "event",
            "period",
            "time",
            "att_g_t_event_time",
            "attgt_event_time",
        }
        or "relative_period" in _norm_name(c)
        or "event_time" in _norm_name(c)
    ]

    if candidates:
        df = df.rename(columns={candidates[0]: "event_time"})
        return df

    raise KeyError(
        "Não encontrei coluna de tempo do evento. "
        f"Colunas disponíveis: {list(df.columns)}"
    )


def _flatten_event_result(ev) -> pd.DataFrame:
    """
    Normaliza o retorno de `ATTgt.aggregate("event")` para colunas planas:

        event_time | ATT | SE | CI_lo | CI_hi | zero_not_in_cband

    A estrutura observada no diagnóstico foi:
    - index.name = 'relative_period'
    - columns = MultiIndex com:
      ('EventAggregation', '', 'ATT'),
      ('EventAggregation', 'analytic', 'std_error'),
      ('EventAggregation', 'pointwise conf. band', 'lower'),
      ('EventAggregation', 'pointwise conf. band', 'upper'),
      ('EventAggregation', 'pointwise conf. band', 'zero_not_in_cband')

    Esta função também tenta lidar com versões alternativas do pacote.
    """
    original_type = type(ev).__name__
    original_index = getattr(ev, "index", None)
    original_cols = None
    try:
        original_cols = list(ev.columns) if hasattr(ev, "columns") else None
    except Exception:
        original_cols = None

    try:
        # Series: normalmente índice = event_time e valor = ATT.
        if isinstance(ev, pd.Series):
            name = ev.name if ev.name is not None else "ATT"
            ev = ev.rename(name).reset_index()
            if ev.columns.size >= 2:
                ev = ev.rename(columns={ev.columns[0]: "event_time", ev.columns[1]: "ATT"})

        if not isinstance(ev, pd.DataFrame):
            raise TypeError(f"Objeto retornado não é DataFrame/Series: {type(ev).__name__}")

        ev = ev.copy()

        # O ponto crucial: quando index é relative_period, ele deve virar coluna.
        if not isinstance(ev.index, pd.RangeIndex) or ev.index.name is not None:
            ev = ev.reset_index()

        # Achatar colunas MultiIndex, inclusive a coluna criada por reset_index:
        # ('relative_period', '', '') -> 'relative_period'
        if isinstance(ev.columns, pd.MultiIndex):
            ev.columns = [_clean_col_name(c) for c in ev.columns]
        else:
            ev.columns = [_clean_col_name(c) for c in ev.columns]

        cols = list(ev.columns)

        # Identificação por nome.
        event_col = _first_existing(cols, [
            lambda n: n in {"relative_period", "event_time", "event", "period", "time"},
            lambda n: "relative_period" in n,
            lambda n: "event_time" in n,
        ])
        att_col = _first_existing(cols, [
            lambda n: n == "att",
            lambda n: n.endswith("_att"),
            lambda n: "eventaggregation_att" in n,
        ])
        se_col = _first_existing(cols, [
            lambda n: n in {"se", "std_error", "stderr", "std_err"},
            lambda n: "std_error" in n,
            lambda n: n.endswith("_se"),
        ])
        lo_col = _first_existing(cols, [
            lambda n: n in {"ci_lo", "lower", "lwr", "conf_low", "ci_lower"},
            lambda n: n.endswith("_lower"),
            lambda n: "conf_band_lower" in n,
        ])
        hi_col = _first_existing(cols, [
            lambda n: n in {"ci_hi", "upper", "upr", "conf_high", "ci_upper"},
            lambda n: n.endswith("_upper"),
            lambda n: "conf_band_upper" in n,
        ])
        sig_col = _first_existing(cols, [
            lambda n: "zero_not_in_cband" in n,
            lambda n: "zero_not" in n,
            lambda n: "signif" in n,
        ])

        # Fallback posicional, agora seguro porque o índice já foi resetado.
        # Esperado: event_time, ATT, SE, lower, upper, [flag]
        if event_col is None and len(cols) >= 1:
            event_col = cols[0]
        if att_col is None and len(cols) >= 2:
            att_col = cols[1]
        if se_col is None and len(cols) >= 3:
            se_col = cols[2]
        if lo_col is None and len(cols) >= 4:
            lo_col = cols[3]
        if hi_col is None and len(cols) >= 5:
            hi_col = cols[4]
        if sig_col is None and len(cols) >= 6:
            sig_col = cols[5]

        required = {
            "event_time": event_col,
            "ATT": att_col,
            "SE": se_col,
            "CI_lo": lo_col,
            "CI_hi": hi_col,
        }
        missing = [k for k, v in required.items() if v is None]
        if missing:
            raise KeyError(
                f"Não consegui identificar colunas obrigatórias: {missing}. "
                f"Colunas após flatten: {cols}"
            )

        out = pd.DataFrame({
            "event_time": pd.to_numeric(ev[event_col], errors="coerce"),
            "ATT": pd.to_numeric(ev[att_col], errors="coerce"),
            "SE": pd.to_numeric(ev[se_col], errors="coerce"),
            "CI_lo": pd.to_numeric(ev[lo_col], errors="coerce"),
            "CI_hi": pd.to_numeric(ev[hi_col], errors="coerce"),
        })

        if sig_col is not None and sig_col in ev.columns:
            out["zero_not_in_cband"] = ev[sig_col].astype(str).str.strip()
        else:
            out["zero_not_in_cband"] = np.where(
                (out["CI_lo"] > 0) | (out["CI_hi"] < 0),
                "*",
                "",
            )

        out = out.dropna(subset=["event_time"]).copy()
        if np.all(np.isclose(out["event_time"], np.round(out["event_time"]))):
            out["event_time"] = out["event_time"].astype(int)

        return out.sort_values("event_time").reset_index(drop=True)

    except Exception as e:
        print(f"    !!! _flatten_event_result falhou: {type(e).__name__}: {e}")
        print(f"    Formato original: type={original_type}")
        if original_index is not None:
            print(f"    Index original: name={getattr(original_index, 'name', None)!r}; "
                  f"type={type(original_index).__name__}")
        print(f"    Colunas originais: {original_cols}")
        raise


def _filter_event_window(ev: pd.DataFrame, event_window: tuple[int, int] | None) -> pd.DataFrame:
    """Filtra event_time dentro de uma janela inclusiva, se fornecida."""
    ev = _ensure_event_time(ev)
    if event_window is None:
        return ev
    lo, hi = event_window
    return ev[(ev["event_time"] >= lo) & (ev["event_time"] <= hi)].copy()


def run_event_study(
    panel_cs: pd.DataFrame,
    outcomes: list[str],
    covs: list[str],
    n_boot: int = 999,
    random_state: int = 42,
    cohort_col: str = "g_m_cs",
    spec_name: str = "FULL2",
    event_window: tuple[int, int] | None = (-4, 6),
) -> pd.DataFrame:
    """
    Roda CS-DR + aggregate("event") para cada outcome.

    Parameters
    ----------
    event_window:
        Janela inclusiva de períodos relativos a manter no resultado final.
        Use `(-4, 6)` para o horizonte do B4 ou `None` para manter tudo.
    """
    from differences import ATTgt

    rows = []
    t0 = time.time()

    for outcome in outcomes:
        if outcome not in panel_cs.columns:
            print(f">>> {outcome}: AUSENTE no painel, pulado")
            continue

        t_o = time.time()
        try:
            data = (
                panel_cs
                .dropna(subset=[outcome])
                .set_index(["geocode", "ano"])
                .sort_index()
            )

            n_munis = data.index.get_level_values("geocode").nunique()

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

            ev_raw = attgt.aggregate("event")
            ev = _flatten_event_result(ev_raw)
            ev = _filter_event_window(ev, event_window)
            ev["outcome"] = outcome
            ev["spec"] = spec_name
            ev["n_munis"] = n_munis
            rows.append(ev)

            if ev.empty:
                msg_periods = "0 períodos após filtro"
            else:
                msg_periods = f"{ev.shape[0]} períodos t=[{ev['event_time'].min()}, {ev['event_time'].max()}]"

            print(
                f"  OK {outcome:38s} [{time.time() - t_o:.1f}s]  "
                f"{msg_periods}"
            )

        except Exception as e:
            print(f"  XX {outcome:38s} {type(e).__name__}: {str(e)[:140]}")

    if not rows:
        return pd.DataFrame()

    df = pd.concat(rows, ignore_index=True, sort=False)
    print(f"\nOK event-study: {time.time() - t0:.1f}s total, {df.shape[0]} linhas")
    return df


def _pretrend_mask(event_time: pd.Series, pre_periods) -> pd.Series:
    """
    Seleciona períodos de pré-tendência.
    - tuple/list de tamanho 2, ex. (-4, -2): janela inclusiva.
    - lista maior, ex. [-4, -3, -2]: períodos explícitos.
    """
    if pre_periods is None:
        return event_time < 0

    periods = list(pre_periods)
    if len(periods) == 2:
        lo, hi = min(periods), max(periods)
        return (event_time >= lo) & (event_time <= hi)

    return event_time.isin(periods)


def _is_sig_from_ci_or_z(row) -> bool:
    """Significância individual: prioriza IC; fallback para |z| > 1.96."""
    lo = row.get("CI_lo", np.nan)
    hi = row.get("CI_hi", np.nan)
    if pd.notna(lo) and pd.notna(hi):
        return bool((lo > 0) or (hi < 0))

    att = row.get("ATT", np.nan)
    se = row.get("SE", np.nan)
    return bool(pd.notna(att) and pd.notna(se) and se > 0 and abs(att / se) > 1.959963985)


def test_pretrends(
    event_df: pd.DataFrame,
    pre_periods: tuple[int, int] | list[int] = (-4, -2),
) -> pd.DataFrame:
    """
    Teste aproximado de pre-trends por outcome.

    Para cada outcome:
    - conta quantos períodos pré são individualmente significativos;
    - calcula Wald aproximado = soma((ATT/SE)^2);
    - calcula p-valor chi-quadrado aproximado com df = número de períodos.

    Observação: este NÃO é o teste conjunto exato com matriz de covariância
    completa. É uma triagem diagnóstica útil para flagar outcomes suspeitos.
    """
    from scipy.stats import chi2

    event_df = _ensure_event_time(event_df)

    results = []
    for outcome in event_df["outcome"].dropna().unique():
        sub = event_df[event_df["outcome"] == outcome].copy()
        sub_pre = sub[_pretrend_mask(sub["event_time"], pre_periods)].copy()
        sub_pre = sub_pre.dropna(subset=["ATT", "SE"])
        sub_pre = sub_pre[sub_pre["SE"] > 0].copy()

        if sub_pre.empty:
            results.append({
                "outcome": outcome,
                "pre_periods": str(pre_periods),
                "n_pre_periods": 0,
                "n_pre_sig_individual": 0,
                "wald_stat_approx": np.nan,
                "p_value_approx": np.nan,
                "pretrend_flag": "NO_DATA",
            })
            continue

        z_vals = sub_pre["ATT"] / sub_pre["SE"]
        n_pre = int(len(sub_pre))
        n_sig_ind = int(sub_pre.apply(_is_sig_from_ci_or_z, axis=1).sum())
        wald = float((z_vals ** 2).sum())
        pval = float(1 - chi2.cdf(wald, df=n_pre))

        if n_sig_ind == 0 and pval > 0.10:
            flag = "PRE_TRENDS_PLANOS"
        elif n_sig_ind == 0 and pval > 0.05:
            flag = "PRE_TRENDS_MARGINAIS"
        elif n_sig_ind >= 1 or pval <= 0.05:
            flag = "PRE_TRENDS_VIOLADOS"
        else:
            flag = "INDETERMINADO"

        results.append({
            "outcome": outcome,
            "pre_periods": str(pre_periods),
            "n_pre_periods": n_pre,
            "n_pre_sig_individual": n_sig_ind,
            "wald_stat_approx": wald,
            "p_value_approx": pval,
            "pretrend_flag": flag,
        })

    return pd.DataFrame(results)


def assess_event_studies(
    event_df: pd.DataFrame,
    pretrend_df: pd.DataFrame,
    horizons: Sequence[int] = (-2, 0, 1, 3, 5),
) -> pd.DataFrame:
    """
    Síntese compacta por outcome: ATT em horizontes selecionados + flag de
    pre-trend + classificação editorial.
    """
    event_df = _ensure_event_time(event_df)

    rows = []
    for outcome in event_df["outcome"].dropna().unique():
        sub = event_df[event_df["outcome"] == outcome].copy()
        pre = (
            pretrend_df[pretrend_df["outcome"] == outcome].iloc[0]
            if (pretrend_df["outcome"] == outcome).any()
            else None
        )

        def get_att(t: int):
            x = sub[sub["event_time"] == t]
            if x.empty or pd.isna(x.iloc[0]["ATT"]):
                return np.nan, np.nan, False
            row = x.iloc[0]
            att = float(row["ATT"])
            se = float(row["SE"]) if pd.notna(row["SE"]) else np.nan
            sig = _is_sig_from_ci_or_z(row)
            return att, se, sig

        row = {"outcome": outcome}

        for t in horizons:
            att, se, sig = get_att(int(t))
            row[f"att_t{int(t):+d}"] = att
            row[f"se_t{int(t):+d}"] = se
            row[f"sig_t{int(t):+d}"] = sig

        row["pretrend_flag"] = pre["pretrend_flag"] if pre is not None else "NA"
        row["pretrend_wald_p"] = pre["p_value_approx"] if pre is not None else np.nan

        post_sig = any(
            row.get(f"sig_t{int(t):+d}", False)
            for t in horizons
            if int(t) >= 0
        )

        if row["pretrend_flag"] == "PRE_TRENDS_PLANOS" and post_sig:
            row["veredito"] = "ATT_ROBUSTO"
        elif row["pretrend_flag"] == "PRE_TRENDS_PLANOS" and not post_sig:
            row["veredito"] = "NULO_LIMPO"
        elif row["pretrend_flag"] == "PRE_TRENDS_VIOLADOS":
            row["veredito"] = "ATT_SUSPEITO_VIES"
        elif row["pretrend_flag"] == "PRE_TRENDS_MARGINAIS":
            row["veredito"] = "ATT_CAUTELOSO"
        else:
            row["veredito"] = "INSPECAO_MANUAL"

        rows.append(row)

    return pd.DataFrame(rows)
