"""
pipeline.pam
============
Processamento da Tabela 1612 do IBGE/SIDRA (Produção Agrícola Municipal — PAM).

Estrutura da fonte (tabela1612.csv)
-----------------------------------
A tabela vem do SIDRA em formato CSV "empilhado": 6 blocos verticalmente
separados por linhas "Variável - X". Cada bloco tem ~5566 municípios × 13 anos
(2012-2024) × 1 produto (cana-de-açúcar).

Os 6 blocos:
1. Área plantada (Hectares) - PRIMÁRIO
2. Área plantada - percentual do total geral - DERIVADO (descartado)
3. Área colhida (Hectares) - PRIMÁRIO ⭐ (filtro canavieiro §3.3 v2.2)
4. Área colhida - percentual do total geral - DERIVADO (descartado)
5. Quantidade produzida (Toneladas) - PRIMÁRIO
6. Rendimento médio (Kg/Hectare) - DERIVADO de qty/area, mas mantemos

Decisões metodológicas
----------------------
- Mantém apenas variáveis primárias (descarta as 2 colunas de %).
- Tokens NA do SIDRA: "-", "..", "...", "X" → NaN.
- Geocode IBGE: 7 dígitos zfilled (consistente com crosswalk).
- Restrição ao Centro-Sul (6 UFs) na saída.

Filtro canavieiro (§3.3 v2.2)
-----------------------------
Município entra como "canavieiro baseline" se atender qualquer condição:
  (a) area_colhida_cana > 500 ha em algum ano 2015-2019
  (b) hospeda usina ANP (a integrar com 02_anp em 09_assembly)
  (c) [futuro] mb_share_cana > 5% baseline (a integrar com MapBiomas)

Outputs em data/interim/
------------------------
- pam_cana_long.csv          : município × ano × variável (long)
- pam_cana_wide.csv          : município × ano (wide, uma col por variável)
- pam_canavieiro_baseline.csv : municípios canavieiros (PAM-only baseline)
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from pipeline.config import (
    PARAMS, IBGE_PAM_1612, ensure_dir, interim, out_pre,
)
from pipeline.normalize import zfill_ibge, num_br


# ============================================================================
# CONSTANTES
# ============================================================================

# Apenas blocos primários (descarta os 2 de %)
BLOCKS_PRIMARY = {
    "Área plantada (Hectares)":             "area_plantada_ha",
    "Área colhida (Hectares)":              "area_colhida_ha",
    "Quantidade produzida (Toneladas)":     "qtd_produzida_t",
    "Rendimento médio da produção (Quilogramas por Hectare)": "rendimento_kg_ha",
}

# Tokens NA do SIDRA (já tratados via num_br, mas listados para documentação)
SIDRA_NA_TOKENS = ("-", "..", "...", "X")

# Critério de filtro canavieiro (§3.3)
FILTRO_CANA_AREA_HA = PARAMS.FILTRO_AREA_CANA_HA  # 500 ha


# ============================================================================
# LEITURA E PARSE DE BLOCOS
# ============================================================================

def _find_block_boundaries(lines: list[str]) -> list[tuple[int, int, str]]:
    """
    Identifica início/fim de cada bloco "Variável - X" no arquivo SIDRA.

    Returns
    -------
    list[(start_line, end_line, var_name)]
    """
    markers = []
    for i, line in enumerate(lines):
        if line.startswith('"Variável -'):
            # Extrai nome da variável
            name = line.strip().strip('"').replace("Variável - ", "")
            markers.append((i, name))
    # Adiciona pseudo-marcador no final
    markers.append((len(lines), None))

    boundaries = []
    for j in range(len(markers) - 1):
        start = markers[j][0]
        end = markers[j + 1][0]
        name = markers[j][1]
        boundaries.append((start, end, name))
    return boundaries


def _parse_block(
    lines: list[str], start: int, end: int, var_name: str
) -> Optional[pd.DataFrame]:
    """
    Parseia um bloco da tabela 1612 (5570 linhas típico).

    Layout do bloco:
      linha start+0: '"Variável - Área plantada (Hectares)"'
      linha start+1: '"Nível","Cód.","Município","Ano x Produto..."'
      linha start+2: '"Nível","Cód.","Município","2012","2013",...'  ← anos
      linha start+3: '"Nível","Cód.","Município","Cana...","Cana...",...' ← produto
      linha start+4 .. end-1: dados

    Returns
    -------
    DataFrame em formato wide (cód × ano) ou None se bloco vazio.
    """
    block = lines[start:end]
    if len(block) < 5:
        return None

    # Linha de anos (índice +2 dentro do bloco, índice 3 no arquivo se start=1)
    header_anos = block[2].strip().split(",")
    header_anos = [t.strip().strip('"') for t in header_anos]

    # Cols-ano são a partir da posição 3 (após "Nível", "Cód.", "Município")
    year_cols = []
    for tok in header_anos[3:]:
        if tok.isdigit() and 1900 <= int(tok) <= 2100:
            year_cols.append(int(tok))
        else:
            year_cols.append(None)  # placeholder se houver lixo

    # Dados começam na linha 4 do bloco
    data_lines = block[4:]
    rows = []
    for line in data_lines:
        line = line.rstrip("\n")
        if not line.strip():
            continue
        # CSV simples — split por vírgula respeitando aspas
        parts = []
        current = []
        in_quote = False
        for ch in line:
            if ch == '"':
                in_quote = not in_quote
            elif ch == "," and not in_quote:
                parts.append("".join(current).strip())
                current = []
            else:
                current.append(ch)
        parts.append("".join(current).strip())
        # Remove aspas externas
        parts = [p.strip().strip('"') for p in parts]

        # Estrutura: [Nível, Cód, Município, val_2012, val_2013, ..., val_2024]
        if len(parts) < 4:
            continue
        nivel = parts[0]
        cod = parts[1]
        muni = parts[2]
        valores = parts[3:]

        # Filtro: só linhas com Nível=MU (município)
        if nivel != "MU":
            continue
        if not cod or not cod.isdigit():
            continue

        row = {"geocode": cod, "municipio_pam": muni, "var_name": var_name}
        for j, ano in enumerate(year_cols):
            if ano is None:
                continue
            if j < len(valores):
                row[ano] = valores[j]
            else:
                row[ano] = None
        rows.append(row)

    if not rows:
        return None
    return pd.DataFrame(rows)


def read_pam_1612() -> dict[str, pd.DataFrame]:
    """
    Lê tabela1612.csv e retorna um dict {var_canonical: DataFrame_wide}.
    Inclui apenas blocos primários (descarta os 2 de %).
    """
    if not IBGE_PAM_1612.exists():
        raise FileNotFoundError(f"PAM 1612 não encontrado em {IBGE_PAM_1612}")

    with open(IBGE_PAM_1612, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    boundaries = _find_block_boundaries(lines)

    blocks = {}
    for start, end, var_name in boundaries:
        if var_name is None:
            continue
        # Inclui só blocos primários (descarta % derivados)
        if var_name not in BLOCKS_PRIMARY:
            continue
        var_canonical = BLOCKS_PRIMARY[var_name]
        df = _parse_block(lines, start, end, var_name)
        if df is None:
            continue
        blocks[var_canonical] = df

    return blocks


# ============================================================================
# RESHAPE E TIPAGEM
# ============================================================================

def block_to_long(df_wide: pd.DataFrame, var_canonical: str) -> pd.DataFrame:
    """
    Converte um bloco wide (geocode × ano) para long (geocode × ano × valor)
    com tipagem correta.
    """
    year_cols = [c for c in df_wide.columns
                 if isinstance(c, int) and 1900 <= c <= 2100]
    long = df_wide.melt(
        id_vars=["geocode", "municipio_pam"],
        value_vars=year_cols,
        var_name="ano",
        value_name="valor",
    )
    long["valor"] = num_br(long["valor"])
    long["geocode"] = zfill_ibge(long["geocode"], width=7)
    long["ano"] = long["ano"].astype(int)
    long["variavel"] = var_canonical
    return long


def build_pam_long(blocks: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Concatena todos os blocos primários em um único long DataFrame."""
    parts = []
    for var_canonical, df_wide in blocks.items():
        long = block_to_long(df_wide, var_canonical)
        parts.append(long)
    out = pd.concat(parts, ignore_index=True)
    return out


def restrict_to_core(
    df: pd.DataFrame, crosswalk: pd.DataFrame
) -> pd.DataFrame:
    """Restringe ao universo Centro-Sul via inner join no geocode."""
    cw_geos = crosswalk[["geocode", "municipio", "uf"]]
    return df.merge(cw_geos, on="geocode", how="inner")


def pivot_to_wide(df_long: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot variavel-long → wide.
    Output: geocode × ano × {area_plantada_ha, area_colhida_ha, ...}
    """
    wide = df_long.pivot_table(
        index=["geocode", "municipio", "uf", "ano"],
        columns="variavel",
        values="valor",
        aggfunc="first",
    ).reset_index()
    wide.columns.name = None
    return wide


# ============================================================================
# FILTRO CANAVIEIRO BASELINE
# ============================================================================

def build_canavieiro_baseline(
    df_long: pd.DataFrame,
    var_filter: str = "area_colhida_ha",
    threshold_ha: float = FILTRO_CANA_AREA_HA,
    baseline_years: tuple[int, int] = PARAMS.BASELINE_YEARS,
) -> pd.DataFrame:
    """
    Constrói o universo canavieiro baseline conforme §3.3 v2.2.

    Critério: município entra se atendeu, em ALGUM ano da janela baseline,
    `var_filter > threshold_ha`. Default: area_colhida_ha > 500 em 2015-2019.

    Returns
    -------
    DataFrame com colunas:
        geocode, municipio, uf,
        area_colhida_max_baseline (maior valor 2015-2019),
        area_plantada_max_baseline,
        n_anos_acima_threshold (n de anos em 2015-2019 com area > threshold),
        is_canavieiro_baseline (sempre True nas linhas retornadas)
    """
    y0, y1 = baseline_years
    pre = df_long[
        (df_long["variavel"] == var_filter)
        & (df_long["ano"] >= y0)
        & (df_long["ano"] <= y1)
    ].copy()

    # Aggregate per geocode
    agg = (
        pre.groupby(["geocode", "municipio", "uf"])
           .agg(
               area_colhida_max_baseline=("valor", "max"),
               area_colhida_mean_baseline=("valor", "mean"),
               n_anos_acima_threshold=(
                   "valor",
                   lambda s: (s.dropna() > threshold_ha).sum(),
               ),
           )
           .reset_index()
    )

    # Aplica critério (a): area_colhida_max > threshold em algum ano
    canavieiros = agg[agg["area_colhida_max_baseline"] > threshold_ha].copy()
    canavieiros["is_canavieiro_baseline"] = True
    canavieiros["criterio_pam"] = (
        f"area_colhida_ha > {threshold_ha:.0f}ha em algum ano "
        f"{y0}-{y1}"
    )

    return canavieiros.sort_values(
        "area_colhida_max_baseline", ascending=False
    ).reset_index(drop=True)


# ============================================================================
# ORQUESTRAÇÃO
# ============================================================================

def run_pam_pipeline(
    crosswalk: pd.DataFrame,
    save: bool = True,
) -> dict:
    """
    Roda o pipeline PAM completo.

    Returns
    -------
    dict com chaves:
        pam_long, pam_wide, canavieiro_baseline
    """
    print("→ Lendo tabela 1612 (formato SIDRA empilhado)...")
    blocks = read_pam_1612()
    print(f"  {len(blocks)} blocos primários: {list(blocks.keys())}")
    for k, df in blocks.items():
        print(f"    {k}: {df.shape}")

    print("\n→ Reshape long...")
    pam_long_br = build_pam_long(blocks)
    print(f"  pam_long (Brasil): {pam_long_br.shape}")

    print("\n→ Restrição ao Centro-Sul...")
    pam_long = restrict_to_core(pam_long_br, crosswalk)
    print(f"  pam_long (CS): {pam_long.shape}")
    n_munis = pam_long["geocode"].nunique()
    print(f"  Municípios CS: {n_munis} (esperado 2.363)")

    print("\n→ Pivot wide...")
    pam_wide = pivot_to_wide(pam_long)
    print(f"  pam_wide: {pam_wide.shape}")

    print("\n→ Construindo universo canavieiro baseline...")
    canavieiros = build_canavieiro_baseline(pam_long)
    print(f"  Canavieiros baseline (area_colhida > {FILTRO_CANA_AREA_HA:.0f}ha em "
          f"algum ano {PARAMS.BASELINE_YEARS[0]}-{PARAMS.BASELINE_YEARS[1]}): "
          f"{len(canavieiros)} munis")
    print(f"  Por UF:")
    print(canavieiros.groupby("uf").size().to_string())

    if save:
        print("\n→ Salvando...")
        pam_long.to_csv(interim("pam_cana_long.csv"), index=False)
        pam_wide.to_csv(interim("pam_cana_wide.csv"), index=False)
        canavieiros.to_csv(interim("pam_canavieiro_baseline.csv"), index=False)
        print("  ✓ tudo salvo")

    return {
        "pam_long": pam_long,
        "pam_wide": pam_wide,
        "canavieiro_baseline": canavieiros,
    }


# ============================================================================
# REFINAMENTO DA F3 DO SEEG
# ============================================================================

def rerun_seeg_coverage_with_pam(
    canavieiros_geocodes: list[str],
    save: bool = True,
) -> pd.DataFrame:
    """
    Re-roda a auditoria F3 do SEEG usando o universo canavieiro do PAM
    como `cana_baseline_munis`. Não reprocessa o painel SEEG — apenas
    refaz a matriz de cobertura com o novo critério.

    Parameters
    ----------
    canavieiros_geocodes : list[str]
        Geocodes dos municípios canavieiros via PAM (output de
        build_canavieiro_baseline).
    """
    from pipeline.seeg import build_coverage_matrix

    panel = pd.read_csv(
        interim("seeg_outcomes_audited.csv"), dtype={"geocode": str}
    )

    # Leitura do crosswalk
    cw = pd.read_csv(
        interim("crosswalk_centrosul.csv"), dtype={"geocode": str}
    )

    # Constrói matriz de cobertura com universo PAM
    panel_for_coverage = panel[[
        "geocode", "municipio", "uf", "ano",
        "luc", "carbono_solo", "queima",
        "solos_manejados", "residuos_florestais",
    ]]

    coverage = build_coverage_matrix(
        panel_for_coverage, cw,
        canais_cana=("queima",),
        cana_baseline_munis=canavieiros_geocodes,
    )

    if save:
        coverage.to_csv(out_pre("seeg_coverage_matrix.csv"), index=False)

    return coverage
