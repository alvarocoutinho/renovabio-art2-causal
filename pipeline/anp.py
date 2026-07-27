"""
pipeline.anp
============
Carregamento e processamento dos certificados ANP do RenovaBio para
construção da tabela municipal de tratamento.

Reescrito do zero a partir dos 3 XLSXs primários (ignora o
Usinas_NEEA_consolidado.csv legacy do TCC).

Decisões metodológicas (alinhadas ao pré-registro v2.2)
-------------------------------------------------------
- §3.2: 6 UFs Centro-Sul (sem ES). PARAMS.UFS_CORE.
- §3.5: doses T2 (volume elegível) e T3 (NEEA) SEPARADAS, agregadas por
  média ponderada por volume produzido.
- §3.5: tratamento staggered via g_m (ano da 1ª certificação no município);
  D_it = 1[t >= g_m]; absorvente.
- §3.7.1: n_usinas_baseline = nº de CNPJs com 1ª certificação até 2019.

Filtro metodológico (D4)
-------------------------
- ROTA: apenas "Etanol combustível de primeira geração - cana-de-açúcar"
  (todas as variações ortográficas).
- BIOCOMBUSTÍVEL: apenas "Etanol anidro" para cálculo de NEEA.
- Tabela `eventos_raw` mantém TUDO sem filtro para auditoria.

Auditorias geradas em outputs_pre/
-----------------------------------
- anp_zero_neea_audit.csv     — usinas com NEEA=0 em algum snapshot
- anp_cancelados_audit.csv    — usinas em Cancelados/Anulados
- anp_cidade_uf_unmatched.csv — emissores sem match no crosswalk

Outputs em data/interim/
------------------------
- anp_eventos_raw.csv               (universo bruto, todas as rotas)
- anp_eventos_anidro_cana1g.csv     (filtrado para Anidro × cana 1G)
- anp_first_cert.csv                (1ª certificação por CNPJ × cana 1G)
- anp_neea_anidro_panel.csv         (NEEA por usina × snapshot)
- anp_muni_treat.csv                (input do PSM — município × ano)
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from pipeline.config import (
    PARAMS,
    ANP_CERT_2022, ANP_CERT_2025, ANP_CERT_2026,
    OUTPUTS_PRE, ensure_dir, interim, out_pre,
)
from pipeline.io import read_excel_with_merged_fill
from pipeline.normalize import build_muni_key


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

# Os 3 snapshots ANP. Ordem cronológica.
SNAPSHOTS = [
    ("2022", ANP_CERT_2022, "2022-02-22"),
    ("2025", ANP_CERT_2025, "2023-10-09"),  # nome do arquivo, mas data real é 2023
    ("2026", ANP_CERT_2026, "2026-04-17"),
]

SHEETS = ["Válidos", "Cancelados ou Suspensos", "Anulados"]

SHEET_TO_STATUS = {
    "Válidos": "valido",
    "Cancelados ou Suspensos": "cancelado",
    "Anulados": "anulado",
}

# Mapeamento robusto de colunas via regex
COL_PATTERNS = {
    "emissor":     [r"Emissor prim", r"Razão Social"],
    "cnpj":        [r"^CNPJ$"],
    "processo":    [r"Processo de Cert"],
    "biocomb":     [r"Biocombust"],
    "rota":        [r"^Rota$"],
    "neea":        [r"Nota de Efici"],
    "vol_eleg":    [r"Volume eleg"],
    "fator_cbio":  [r"Fator para emiss"],
    "litros_cbio": [r"Litros/CBIO"],
    "data_aprov":  [r"Aprova"],
    "validade":    [r"Validade"],
    "firma":       [r"Firma Inspe"],
    "endereco":    [r"Endereço"],
}


# ============================================================================
# HELPERS DE PARSING
# ============================================================================

def _find_col(df_cols, patterns):
    for col in df_cols:
        if col is None:
            continue
        col_str = str(col)
        for pat in patterns:
            if re.search(pat, col_str, flags=re.IGNORECASE):
                return col
    return None


def _harmonize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    for canonical, patterns in COL_PATTERNS.items():
        actual = _find_col(df.columns, patterns)
        if actual is not None:
            rename_map[actual] = canonical
    df = df.rename(columns=rename_map)
    df = df.loc[:, [
        c for c in df.columns
        if c is not None and not (isinstance(c, float) and np.isnan(c))
    ]]
    return df


def _cleanup_cidade(cidade_str) -> Optional[str]:
    """
    Limpa nome de cidade extraído pelo parse_emissor.

    O parser captura tudo entre razão social e UF como "cidade", o que
    inclui prefixos de filial/usina ("FILIAL BARRA - Barra Bonita",
    "Unidade Catanduva - Catanduva", "EM RECUPERAÇÃO JUDICIAL - Goianésia").

    O nome real do município é tipicamente o ÚLTIMO componente, mas pode
    aparecer em três formas:
    1. Após " - " (mais comum)
    2. Após " " quando o nome da cidade se repete ("Catanduva Catanduva"
       — vem de junção de quebra de linha)
    3. Sem delimitador claro (cidade = a string toda já)
    """
    if cidade_str is None or pd.isna(cidade_str):
        return None
    s = str(cidade_str).strip()

    # Tenta pegar o último componente após " - " ou " – "
    parts = re.split(r"\s+[\-–]\s+", s)
    candidate = parts[-1].strip() if parts else s

    # Casos onde a cidade está duplicada por colagem (ex: "Catanduva Catanduva",
    # "Alto Taquari Alto Taquari", "Paraguaçu Paulista Paraguaçu Paulista")
    # Detecta padrão: string contém duas ocorrências exatas da metade final.
    words = candidate.split()
    n = len(words)
    if n >= 2 and n % 2 == 0:
        half = n // 2
        first_half = " ".join(words[:half])
        second_half = " ".join(words[half:])
        if first_half == second_half:
            return first_half

    # Casos onde o último componente foi colado a "RECUPERACAO JUDICIAL -Cidade"
    # (sem espaço antes do hífen): tenta um split mais permissivo
    parts2 = re.split(r"[\-–]", candidate)
    if len(parts2) > 1:
        candidate = parts2[-1].strip()

    return candidate or None


# Dicionário de correções ortográficas conhecidas:
# nome no ANP → nome canônico no IBGE.
# Aplicado APÓS _cleanup_cidade para resolver casos de divergência ortográfica.
CORRECOES_ANP_IBGE = {
    # ANP usa "Z", IBGE usa "S"
    "LUIZ ANTONIO|SP": "LUIS ANTONIO|SP",
    # ANP usa "AS", IBGE usa "A"
    "PIRSASSUNUNGA|SP": "PIRASSUNUNGA|SP",
    # ANP usa variante, IBGE usa outra
    "SUZANOPOLIS|SP": "SUZANAPOLIS|SP",
}


def parse_emissor(s):
    """
    Parser unificado para 'Emissor primário' (2022) e
    'Razão Social - Cidade - UF' (2025/2026).

    Retorna (razao_social, cidade, uf). A cidade extraída pode conter
    prefixo de "Usina/Filial/Unidade" — usa _cleanup_cidade para extrair
    só o nome real do município.
    """
    if s is None or pd.isna(s):
        return (None, None, None)
    s = str(s).strip()
    s = re.sub(r"\s+", " ", s)

    # Padrão 1 (2022): "...Cidade/UF"
    m = re.search(
        r"^(.+?)\s*[\-–]\s*([A-Za-zÀ-ÿ\s'\-\.]+?)\s*/\s*([A-Z]{2})\s*$", s
    )
    if m:
        cidade = _cleanup_cidade(m.group(2))
        return (m.group(1).strip(" -–"), cidade, m.group(3).strip())

    # Padrão 2 (2025/2026): "...Cidade - UF" ou ", UF"
    m = re.search(
        r"^(.+?)\s*[\-–]\s*([A-Za-zÀ-ÿ\s'\-\.]+?)\s*[\-–,]\s*([A-Z]{2})\s*$", s
    )
    if m:
        cidade = _cleanup_cidade(m.group(2))
        return (m.group(1).strip(" -–,"), cidade, m.group(3).strip())

    # Padrão 3: "..., UF"
    m = re.search(r"^(.+?)\s*,\s*([A-Z]{2})\s*$", s)
    if m:
        before_uf = m.group(1).strip()
        last_dash = re.search(r"(.+?)\s+[\-–]\s+([^\-–]+)$", before_uf)
        if last_dash:
            cidade = _cleanup_cidade(last_dash.group(2))
            return (
                last_dash.group(1).strip(" -–"),
                cidade,
                m.group(2).strip(),
            )
        return (before_uf, None, m.group(2).strip())

    return (s, None, None)


def is_cana_1g(rota_str) -> bool:
    """
    True se rota é Etanol de 1ª geração de cana-de-açúcar.
    Exclui milho e variantes integradas com 2ª geração.
    """
    if rota_str is None or pd.isna(rota_str):
        return False
    import unicodedata
    s = str(rota_str).lower().strip()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("–", "-")
    s = "".join(
        ch for ch in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(ch)
    )
    has_cana = "cana" in s
    has_milho = "milho" in s
    has_2g = "segunda geracao" in s or "2g" in s
    return has_cana and not has_milho and not has_2g


def is_etanol_anidro(biocomb_str) -> bool:
    if biocomb_str is None or pd.isna(biocomb_str):
        return False
    return "anidro" in str(biocomb_str).lower().strip()


# ============================================================================
# LEITURA DOS SNAPSHOTS
# ============================================================================

def load_one_snapshot(label: str, path: Path, snap_date: str) -> pd.DataFrame:
    """Lê os 3 sheets de um snapshot, harmoniza e empilha."""
    parts = []
    for sheet in SHEETS:
        try:
            df = read_excel_with_merged_fill(path, sheet, header_row=1)
        except KeyError:
            continue
        df = _harmonize_columns(df)
        df["status"] = SHEET_TO_STATUS[sheet]
        parts.append(df)

    if not parts:
        raise RuntimeError(f"Nenhum sheet legível em {path.name}")

    out = pd.concat(parts, ignore_index=True, sort=False)
    out["snapshot"] = label
    out["snapshot_date"] = pd.to_datetime(snap_date)
    return out.dropna(how="all").reset_index(drop=True)


def load_all_snapshots() -> pd.DataFrame:
    parts = []
    for label, path, snap_date in SNAPSHOTS:
        df = load_one_snapshot(label, path, snap_date)
        parts.append(df)
    return pd.concat(parts, ignore_index=True, sort=False)


# ============================================================================
# PARSING DE CAMPOS
# ============================================================================

def parse_emissor_columns(df: pd.DataFrame) -> pd.DataFrame:
    if "emissor" not in df.columns:
        df["razao_social"] = None
        df["cidade"] = None
        df["uf"] = None
        return df
    parsed = df["emissor"].apply(parse_emissor)
    df["razao_social"] = parsed.apply(lambda t: t[0])
    df["cidade"] = parsed.apply(lambda t: t[1])
    df["uf"] = parsed.apply(lambda t: t[2])
    return df


def parse_cnpj(df: pd.DataFrame) -> pd.DataFrame:
    if "cnpj" in df.columns:
        df["cnpj_clean"] = (
            df["cnpj"].astype(str)
              .str.replace(r"\D", "", regex=True)
              .replace({"": None, "nan": None})
        )
    return df


def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converte data_aprov e validade para datetime, descartando datas
    obviamente corrompidas (pré-2018 ou pós-2030). RenovaBio foi criado
    em dez/2017 (Lei 13.576); datas anteriores são artefatos de parsing
    (cell vazio → epoch Unix).
    """
    for c in ("data_aprov", "validade"):
        if c in df.columns:
            dt = pd.to_datetime(df[c], errors="coerce")
            mask_invalid = (dt < pd.Timestamp("2018-01-01")) | (dt > pd.Timestamp("2030-12-31"))
            dt = dt.where(~mask_invalid, pd.NaT)
            df[c] = dt
    if "data_aprov" in df.columns:
        df["ano_aprov"] = df["data_aprov"].dt.year
    return df


def parse_numeric(df: pd.DataFrame) -> pd.DataFrame:
    for c in ("neea", "vol_eleg", "fator_cbio", "litros_cbio"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def add_filter_flags(df: pd.DataFrame) -> pd.DataFrame:
    df["is_cana_1g"] = df["rota"].apply(is_cana_1g) if "rota" in df.columns else False
    df["is_anidro"] = df["biocomb"].apply(is_etanol_anidro) if "biocomb" in df.columns else False
    return df


# ============================================================================
# PIPELINE PRINCIPAL
# ============================================================================

def build_eventos_raw() -> pd.DataFrame:
    """Universo bruto: 3 snapshots × 3 sheets, com parsing aplicado."""
    df = load_all_snapshots()
    df = parse_emissor_columns(df)
    df = parse_cnpj(df)
    df = parse_dates(df)
    df = parse_numeric(df)
    df = add_filter_flags(df)
    df["muni_key"] = build_muni_key(
        df["cidade"].fillna(""), df["uf"].fillna("")
    )
    return df


# ============================================================================
# AUDITORIAS
# ============================================================================

def audit_zero_neea(eventos: pd.DataFrame) -> pd.DataFrame:
    """Classifica padrão de NEEA=0/ausente entre snapshots."""
    df = eventos[
        eventos["is_cana_1g"] & eventos["is_anidro"] & eventos["cnpj_clean"].notna()
    ].copy()

    pivot = (
        df.groupby(["cnpj_clean", "snapshot"])["neea"]
          .mean()
          .unstack("snapshot")
          .reset_index()
    )

    def classify(row):
        years = ["2022", "2025", "2026"]
        vals = [row[y] if y in row.index else None for y in years]
        present = [v is not None and pd.notna(v) and v > 0 for v in vals]
        if all(present):
            return "todas_presentes"
        if not any(present):
            return "todas_ausentes"
        first_idx = present.index(True)
        last_idx = len(present) - 1 - present[::-1].index(True)
        if first_idx > 0 and last_idx == len(present) - 1:
            return "adocao_tardia"
        if first_idx == 0 and last_idx < len(present) - 1:
            return "descredenciamento_ou_venda"
        return "misto"

    pivot["padrao"] = pivot.apply(classify, axis=1)

    info = (
        df.sort_values("snapshot_date", ascending=False)
          .drop_duplicates(subset="cnpj_clean", keep="first")
          [["cnpj_clean", "razao_social", "cidade", "uf"]]
    )
    out = pivot.merge(info, on="cnpj_clean", how="left")
    audit = out[out["padrao"] != "todas_presentes"].sort_values(
        ["padrao", "uf", "cidade"]
    )
    return audit


def audit_cancelados(eventos: pd.DataFrame) -> pd.DataFrame:
    """Lista CNPJs com algum status cancelado/anulado em cana 1G."""
    df = eventos[
        eventos["is_cana_1g"] & eventos["cnpj_clean"].notna()
    ].copy()

    by_cnpj = (
        df.groupby("cnpj_clean")
          .agg(
              statuses=("status", lambda s: sorted(set(s))),
              snapshots=("snapshot", lambda s: sorted(set(s))),
              razao=("razao_social", lambda s: s.dropna().iloc[0] if s.notna().any() else None),
              cidade=("cidade", lambda s: s.dropna().iloc[0] if s.notna().any() else None),
              uf=("uf", lambda s: s.dropna().iloc[0] if s.notna().any() else None),
          )
          .reset_index()
    )

    audit = by_cnpj[by_cnpj["statuses"].apply(
        lambda s: any(st in ("cancelado", "anulado") for st in s)
    )].copy()
    audit["tem_valido_tb"] = audit["statuses"].apply(lambda s: "valido" in s)
    audit["apenas_cancelado_anulado"] = ~audit["tem_valido_tb"]
    return audit


# ============================================================================
# CONSTRUÇÃO DA TABELA MUNICIPAL
# ============================================================================

def build_first_cert(eventos: pd.DataFrame) -> pd.DataFrame:
    """1ª certificação por CNPJ × cana 1G válida (qualquer biocombustível)."""
    df = eventos[
        eventos["is_cana_1g"]
        & (eventos["status"] == "valido")
        & eventos["cnpj_clean"].notna()
        & eventos["data_aprov"].notna()
    ].copy()

    if len(df) == 0:
        return pd.DataFrame(columns=[
            "cnpj_clean", "razao_social", "cidade", "uf", "muni_key",
            "g_data", "g_year",
        ])

    df = df.sort_values(["cnpj_clean", "data_aprov"])
    first = df.drop_duplicates(subset="cnpj_clean", keep="first").copy()
    first = first.rename(columns={"data_aprov": "g_data"})
    first["g_year"] = first["g_data"].dt.year

    keep = ["cnpj_clean", "razao_social", "cidade", "uf", "muni_key",
            "g_data", "g_year"]
    return first[keep].reset_index(drop=True)


def build_neea_panel(eventos: pd.DataFrame) -> pd.DataFrame:
    """Painel CNPJ × snapshot com NEEA Anidro × cana 1G e vol_eleg."""
    df = eventos[
        eventos["is_cana_1g"]
        & eventos["is_anidro"]
        & (eventos["status"] == "valido")
        & eventos["cnpj_clean"].notna()
    ].copy()

    panel = (
        df.groupby(["cnpj_clean", "snapshot"])
          .agg(
              neea=("neea", "mean"),
              vol_eleg=("vol_eleg", "mean"),
          )
          .reset_index()
    )
    return panel


def _fuzzy_match_unmatched(
    df_unmatched: pd.DataFrame, crosswalk: pd.DataFrame,
    cutoff: float = 0.85,
) -> pd.DataFrame:
    """
    Para CNPJs sem match exato, tenta dois passos:
    1. Trim progressivo: pega últimas 1, 2, 3 palavras da cidade e re-tenta
       match exato contra o crosswalk filtrado pela UF.
    2. Fuzzy match (difflib): se trim não resolver, busca cidade mais
       próxima no crosswalk filtrado pela UF, com cutoff de similaridade.
    """
    from difflib import get_close_matches

    out = df_unmatched.copy()
    out["geocode_fuzzy"] = None
    out["municipio_fuzzy"] = None
    out["fuzzy_method"] = None
    out["fuzzy_score"] = None

    cw_by_uf = {uf: g for uf, g in crosswalk.groupby("uf")}

    for idx, row in out.iterrows():
        cidade = row.get("cidade")
        uf = row.get("uf")
        if cidade is None or pd.isna(cidade) or uf is None or pd.isna(uf):
            continue
        if uf not in cw_by_uf:
            continue
        candidates = cw_by_uf[uf]

        # 1. Trim progressivo: tenta últimas N palavras
        words = str(cidade).split()
        for n_words in range(1, min(len(words) + 1, 5)):
            trimmed = " ".join(words[-n_words:])
            from pipeline.normalize import norm_str
            trimmed_key = (norm_str(trimmed) or "") + "|" + uf
            match = candidates[candidates["muni_key"] == trimmed_key]
            if len(match) == 1:
                out.at[idx, "geocode_fuzzy"] = match.iloc[0]["geocode"]
                out.at[idx, "municipio_fuzzy"] = match.iloc[0]["municipio"]
                out.at[idx, "fuzzy_method"] = f"trim_{n_words}w"
                out.at[idx, "fuzzy_score"] = 1.0
                break

        if out.at[idx, "geocode_fuzzy"] is not None:
            continue

        # 2. Fuzzy match contra todos os nomes da UF
        from pipeline.normalize import norm_str
        cidade_norm = norm_str(cidade)
        if cidade_norm is None:
            continue
        cw_names = [norm_str(c) for c in candidates["municipio"].dropna().tolist()]
        cw_names = [c for c in cw_names if c is not None]
        if not cw_names:
            continue
        matches = get_close_matches(cidade_norm, cw_names, n=1, cutoff=cutoff)
        if matches:
            best = matches[0]
            cand_idx = cw_names.index(best)
            cand = candidates.iloc[cand_idx]
            out.at[idx, "geocode_fuzzy"] = cand["geocode"]
            out.at[idx, "municipio_fuzzy"] = cand["municipio"]
            out.at[idx, "fuzzy_method"] = "fuzzy"
            from difflib import SequenceMatcher
            out.at[idx, "fuzzy_score"] = round(
                SequenceMatcher(None, cidade_norm, best).ratio(), 3
            )

    return out


def attach_geocode_via_crosswalk(
    df: pd.DataFrame, crosswalk: pd.DataFrame, key_col: str = "muni_key",
    use_fuzzy: bool = True, fuzzy_cutoff: float = 0.85,
) -> pd.DataFrame:
    """
    Resolve cidade/UF para geocode IBGE via crosswalk.

    Pipeline:
    1. Match exato em muni_key (com correções de CORRECOES_ANP_IBGE).
    2. Para sem-match: trim progressivo (tenta últimas N palavras).
    3. Para sem-match: fuzzy match (difflib) com cutoff configurável.

    Adiciona colunas:
    - geocode, municipio_cw, uf_cw : do match (exato ou fuzzy)
    - match_exact : True se match foi exato (após correções)
    - match_method : 'exact' | 'trim_Nw' | 'fuzzy' | None
    - fuzzy_score : score de similaridade [0,1] se fuzzy
    """
    df = df.copy()
    df["muni_key_corrected"] = df[key_col].replace(CORRECOES_ANP_IBGE)

    cw_keys = crosswalk[["muni_key", "geocode", "municipio", "uf"]].copy()
    cw_keys = cw_keys.rename(columns={"municipio": "municipio_cw", "uf": "uf_cw"})

    out = df.merge(
        cw_keys, left_on="muni_key_corrected", right_on="muni_key",
        how="left", suffixes=("", "_cw_dup")
    )
    if "muni_key_cw_dup" in out.columns:
        out = out.drop(columns=["muni_key_cw_dup"])
    out["match_exact"] = out["geocode"].notna()
    out["match_method"] = out["match_exact"].apply(lambda x: "exact" if x else None)
    out["fuzzy_score"] = None

    # 2-3. Fuzzy fallback
    if use_fuzzy:
        unmatched_idx = out.index[~out["match_exact"]]
        if len(unmatched_idx) > 0:
            cw_for_fuzzy = crosswalk[["geocode", "municipio", "uf", "muni_key"]]
            fuzzy_out = _fuzzy_match_unmatched(
                out.loc[unmatched_idx], cw_for_fuzzy, cutoff=fuzzy_cutoff
            )
            # Preenche os matches fuzzy nas linhas correspondentes
            fuzzy_hits = fuzzy_out[fuzzy_out["geocode_fuzzy"].notna()]
            for idx in fuzzy_hits.index:
                out.at[idx, "geocode"] = fuzzy_hits.at[idx, "geocode_fuzzy"]
                out.at[idx, "municipio_cw"] = fuzzy_hits.at[idx, "municipio_fuzzy"]
                out.at[idx, "uf_cw"] = fuzzy_hits.at[idx, "uf"]
                out.at[idx, "match_method"] = fuzzy_hits.at[idx, "fuzzy_method"]
                out.at[idx, "fuzzy_score"] = fuzzy_hits.at[idx, "fuzzy_score"]

    out["match_any"] = out["geocode"].notna()
    return out


def _weighted_mean(group, val_col, weight_col):
    v = group[val_col]
    w = group[weight_col]
    mask = v.notna() & w.notna() & (w > 0)
    if not mask.any():
        return np.nan
    return (v[mask] * w[mask]).sum() / w[mask].sum()


def build_muni_treatment(
    first_cert: pd.DataFrame,
    neea_panel: pd.DataFrame,
    crosswalk: pd.DataFrame,
) -> pd.DataFrame:
    """
    Tabela municipal final.

    Colunas:
    - geocode, municipio, uf
    - g_m         : ano da 1ª certificação (mín entre suas usinas)
    - g_data_m    : data correspondente
    - n_usinas    : nº de CNPJs já certificados (qualquer momento)
    - n_usinas_baseline : nº de CNPJs com 1ª cert ATÉ 2019 (§3.7.1)
    - dose_T2_2022, dose_T2_2025, dose_T2_2026 : vol_eleg médio
    - dose_T3_2022, dose_T3_2025, dose_T3_2026 : NEEA média ponderada por vol_eleg
    """
    fc = attach_geocode_via_crosswalk(first_cert, crosswalk).copy()
    fc_ok = fc[fc["geocode"].notna()].copy()

    # Restringe ao Centro-Sul (defesa adicional)
    fc_ok = fc_ok[fc_ok["uf_cw"].isin(PARAMS.UFS_CORE)].copy()

    # Agregados de 1ª certificação por município
    g_per_muni = (
        fc_ok.groupby("geocode")
              .agg(
                  g_m=("g_year", "min"),
                  g_data_m=("g_data", "min"),
                  n_usinas=("cnpj_clean", "nunique"),
              )
              .reset_index()
    )

    # n_usinas_baseline (até 2019)
    n_baseline = (
        fc_ok[fc_ok["g_year"] <= 2019]
              .groupby("geocode")
              .agg(n_usinas_baseline=("cnpj_clean", "nunique"))
              .reset_index()
    )
    g_per_muni = g_per_muni.merge(n_baseline, on="geocode", how="left")
    g_per_muni["n_usinas_baseline"] = (
        g_per_muni["n_usinas_baseline"].fillna(0).astype(int)
    )

    # Doses T2 e T3 — JOIN do neea_panel com fc_ok (geocode)
    fc_geo = fc_ok[["cnpj_clean", "geocode"]].drop_duplicates()
    panel_geo = neea_panel.merge(fc_geo, on="cnpj_clean", how="inner")

    rows = []
    for (geo, snap), g in panel_geo.groupby(["geocode", "snapshot"]):
        rows.append({
            "geocode": geo,
            "snapshot": snap,
            "T2": g["vol_eleg"].mean(),  # média simples (sem peso disponível)
            "T3": _weighted_mean(g, "neea", "vol_eleg"),
        })
    doses = pd.DataFrame(rows)

    if len(doses) > 0:
        doses_wide = doses.pivot(
            index="geocode", columns="snapshot", values=["T2", "T3"]
        )
        doses_wide.columns = [f"dose_{a}_{b}" for a, b in doses_wide.columns]
        doses_wide = doses_wide.reset_index()
    else:
        doses_wide = pd.DataFrame({"geocode": []})

    muni = g_per_muni.merge(doses_wide, on="geocode", how="left")

    cw_info = crosswalk[["geocode", "municipio", "uf"]]
    muni = muni.merge(cw_info, on="geocode", how="left")

    cols_lead = ["geocode", "municipio", "uf", "g_m", "g_data_m",
                 "n_usinas", "n_usinas_baseline"]
    cols_dose = sorted([c for c in muni.columns if c.startswith("dose_")])
    cols_other = [c for c in muni.columns if c not in cols_lead + cols_dose]
    muni = muni[cols_lead + cols_dose + cols_other]

    return muni.sort_values(["uf", "municipio"]).reset_index(drop=True)


# ============================================================================
# ORQUESTRAÇÃO
# ============================================================================

def run_anp_pipeline(crosswalk: pd.DataFrame, save: bool = True) -> dict:
    """
    Roda o pipeline ANP completo. Retorna dict com todos os artefatos
    e (se save=True) salva-os em interim/ e outputs_pre/.
    """
    print("→ Lendo 3 snapshots ANP com unmerge+fill...")
    eventos = build_eventos_raw()
    print(f"  eventos_raw: {len(eventos):,} linhas")

    eventos_anidro = eventos[
        eventos["is_cana_1g"] & eventos["is_anidro"] & (eventos["status"] == "valido")
    ].copy()
    print(f"  eventos_anidro_cana1g: {len(eventos_anidro):,} linhas, "
          f"{eventos_anidro['cnpj_clean'].nunique()} CNPJs únicos")

    first_cert = build_first_cert(eventos)
    print(f"  first_cert: {len(first_cert):,} CNPJs cana 1G")

    neea_panel = build_neea_panel(eventos)
    print(f"  neea_panel: {len(neea_panel):,} linhas (CNPJ × snapshot)")

    audit_zero = audit_zero_neea(eventos)
    print(f"  audit_zero_neea: {len(audit_zero):,} CNPJs com algum NEEA ausente/zero")

    audit_canc = audit_cancelados(eventos)
    print(f"  audit_cancelados: {len(audit_canc):,} CNPJs com cancelado/anulado")

    muni = build_muni_treatment(first_cert, neea_panel, crosswalk)
    print(f"  muni_treat: {len(muni):,} municípios tratados (Centro-Sul)")

    fc_attached = attach_geocode_via_crosswalk(first_cert, crosswalk)
    audit_unmatched = fc_attached[~fc_attached["match_any"]].copy()
    print(f"  audit_unmatched: {len(audit_unmatched):,} CNPJs sem geocode")

    if save:
        print("\n→ Salvando interim/ e outputs_pre/...")
        eventos.to_csv(interim("anp_eventos_raw.csv"), index=False)
        eventos_anidro.to_csv(interim("anp_eventos_anidro_cana1g.csv"), index=False)
        first_cert.to_csv(interim("anp_first_cert.csv"), index=False)
        neea_panel.to_csv(interim("anp_neea_anidro_panel.csv"), index=False)
        muni.to_csv(interim("anp_muni_treat.csv"), index=False)
        audit_zero.to_csv(out_pre("anp_zero_neea_audit.csv"), index=False)
        audit_canc.to_csv(out_pre("anp_cancelados_audit.csv"), index=False)
        audit_unmatched.to_csv(out_pre("anp_cidade_uf_unmatched.csv"), index=False)
        print("  ✓ todos os arquivos salvos")

    return {
        "eventos_raw": eventos,
        "eventos_anidro": eventos_anidro,
        "first_cert": first_cert,
        "neea_panel": neea_panel,
        "muni_treat": muni,
        "audit_zero_neea": audit_zero,
        "audit_cancelados": audit_canc,
        "audit_unmatched": audit_unmatched,
    }
