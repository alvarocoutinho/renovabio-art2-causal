"""
pipeline.seeg
=============
Carregamento e processamento dos arquivos SEEG (AR6) por UF, construção
do painel de outcomes AFOLU município × ano com 5 canais separados.

Decisões metodológicas (alinhadas ao pré-registro v2.2)
-------------------------------------------------------
- §3.10: Emissão (positivo) + Remoção (negativo) somadas com sinal.
        Bunker e Bunker NCI excluídos. NCI tratado como Emissão/Remoção
        comum (apenas categorização fina perdida).
- §3.10: Transformações por canal:
    luc                 → asinh   (pode ter remoção)
    carbono_solo        → asinh   (fluxo líquido — pode ser negativo)
    queima              → log1p
    solos_manejados     → log
    residuos_florestais → log1p

Definição dos 5 macro-canais AFOLU (decisões S1-S5)
---------------------------------------------------
luc : Setor "Mudança de Uso da Terra e Floresta", excluindo Resíduos
      florestais (canal separado). Inclui Alterações + Remoções +
      Queimadas não associadas a desmatamento.

carbono_solo : SOMA de (sinal preservado):
  - Categoria 'Carbono orgânico no solo' (Setor Agropecuária)
  - Sub-categoria 'Aumento do estoque de C no solo' (em Solos manejados)
  - Sub-categoria 'Redução do estoque de C no solo' (em Solos manejados)
  - Sub-categoria 'Mineralização de N associado a perda de C no solo'

queima : Categoria 'Queima de resíduos agrícolas' E Produto = 'Cana-de-açúcar'

solos_manejados : Categoria 'Solos manejados' EXCLUINDO:
  - Detalhamento 'Animal' (pecuária — não afetada por NEEA)
  - Componentes que vão para carbono_solo (acima)

residuos_florestais : Categoria 'Resíduos florestais' (Setor MUTF)

Decomposição do solos_manejados em sub-canais (v2.3.8 §3.10.2)
-------------------------------------------------------------
Opção 2 do refator: os 5 macro-canais permanecem INTACTOS. Em paralelo,
o macro-canal 'solos_manejados' é decomposto em 6 sub-canais que o
particionam exaustivamente (Σ sub ≡ solos_manejados, ao 4º decimal):

  res_cana   : Resíduos agrícolas ∩ Cana            → asinh  (Eqs. 62-66)
  org_cana   : Aplic. res. orgânicos ∩ Torta/Vinhaça → asinh (Eqs. 40, 42)
  fert_n     : Fertilizantes sintéticos N (agregado)  → log1p (Eqs. 52-54)
  calagem    : Corretivo agrícola ∩ Calagem          → log1p (Eqs. 89+9)
  res_outros : Resíduos agrícolas ∩ Produto ≠ Cana    → log1p (Eqs. 60-61)
  res_minor  : fechamento (solos org., queima pasto) → log1p (só apêndice)

A identidade algébrica é verificada por validate_subchannel_algebra()
e bloqueia o pipeline se falhar (B4.M.2 do pré-registro).

Auditoria F3 (cobertura município × canal × ano)
------------------------------------------------
Antes de balancear o painel com fillna(0), classifica cada célula:
- ZERO_LEGITIMO: município não-canavieiro × canal cana → 0 ok
- LACUNA_SUSPEITA: município canavieiro × canal cana ausente → investigar
- INESPERADO: município não-canavieiro com observação no canal cana
- OK: célula com observação esperada

Outputs em data/interim/
------------------------
- seeg_long.parquet                — long format (todos os canais, gases)
- seeg_outcomes_balanced.csv       — município × ano × 5 outcomes (raw)
- seeg_outcomes_audited.csv        — versão final com flags F3 + transforms

Outputs em outputs_pre/
-----------------------
- seeg_canal_definitions.csv       — tabela explícita das regras
- seeg_coverage_matrix.csv         — auditoria F3
- seeg_distribuicoes_canal_uf.csv  — sanity check
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional, Iterable

import numpy as np
import pandas as pd

from pipeline.config import (
    PARAMS, SEEG_FILES, ensure_dir, interim, out_pre,
)
from pipeline.io import file_size_mb


# ============================================================================
# CONSTANTES
# ============================================================================

# Categorias AFOLU (Mudança de Uso da Terra e Floresta + Agropecuária)
SETORES_AFOLU = ("Mudança de Uso da Terra e Floresta", "Agropecuária")

# Filtros de tipo de emissão
TIPOS_EMISSAO_INCLUSOS = ("Emissão", "Remoção", "Emissão NCI", "Remoção NCI")
TIPOS_REMOCAO = ("Remoção", "Remoção NCI")  # entram com sinal negativo
TIPOS_BUNKER = ("Bunker", "Bunker NCI")     # SEMPRE excluídos

# Janela temporal (cols-ano de interesse)
ANOS_FULL = list(range(PARAMS.YEAR_MIN_FULL, PARAMS.YEAR_MAX_FULL + 1))   # 2012-2024
ANOS_MAIN = list(range(PARAMS.YEAR_MIN_MAIN, PARAMS.YEAR_MAX_MAIN + 1))   # 2015-2024


# Sub-categorias de Solos manejados que vão para o canal carbono_solo
# (mover daqui para o seu canal de destino).
SOLOS_C_SUBCATEGORIAS = (
    "Aumento do estoque de C no solo",
    "Redução do estoque de C no solo",
    "Mineralização de N associado a perda de C no solo",
)

# Detalhamentos de Solos manejados a EXCLUIR (pecuária)
SOLOS_DETALHAMENTOS_EXCLUIR = ("Animal",)


# ============================================================================
# DECOMPOSIÇÃO DO solos_manejados EM SUB-CANAIS (pré-registro v2.3.8 §3.10.2)
# ============================================================================
# Os 5 sub-canais (+ res_minor de fechamento) particionam EXAUSTIVAMENTE e de
# forma MUTUAMENTE EXCLUSIVA as linhas que classify_channel mandou para
# 'solos_manejados'. Garantia algébrica por construção:
#   res_cana + org_cana + fert_n + calagem + res_outros + res_minor
#     ≡ solos_manejados   (para todo município × ano, ao 4º decimal)
#
# IMPORTANTE: estes sub-canais são ADICIONAIS. O macro-canal 'solos_manejados'
# continua sendo emitido intacto (Opção 2 do refator). A auditoria F3 e o
# balanceamento dos 5 macro-canais NÃO são afetados.

SUBCANAIS_SOLOS = (
    "res_cana",      # Resíduos agrícolas ∩ Cana            (Eqs. 62-66)
    "org_cana",      # Aplic. res. orgânicos ∩ Torta/Vinhaça (Eqs. 40, 42)
    "fert_n",        # Fertilizantes sintéticos N (agregado)  (Eqs. 52-54)
    "calagem",       # Corretivo agrícola ∩ Calagem          (Eqs. 89+9)
    "res_outros",    # Resíduos agrícolas ∩ Produto ≠ Cana    (Eqs. 60-61)
    "res_minor",     # fechamento: solos orgânicos, queima pasto, etc.
)

# Sub-canais cana-rotulados → entram na auditoria F3 como canais de cana
# (ausência em município canavieiro = LACUNA_SUSPEITA, como 'queima').
SUBCANAIS_CANA = ("res_cana", "org_cana")

# Sub-canais territoriais → existem em quase todo município (não-cana no F3).
SUBCANAIS_TERRITORIAIS = ("fert_n", "calagem", "res_outros", "res_minor")

# Transformações dos sub-canais (pré-registro v2.3.8 §3.10.2).
# NÃO usa 'log' puro: sub-canais cana-rotulados têm muitos zeros.
#   - cana-rotulados (res_cana, org_cana)      → asinh  (cauda esq. ~0)
#   - territoriais  (fert_n, calagem, outros)  → log1p  (não-negativo c/ zeros)
SUBCANAL_TRANSFORM = {
    "res_cana":   "asinh",
    "org_cana":   "asinh",
    "fert_n":     "log1p",
    "calagem":    "log1p",
    "res_outros": "log1p",
    "res_minor":  "log1p",   # reportado só em apêndice, sem ATT (§3.10.2)
}

# Strings canônicas das Sub-categorias emissoras dentro de 'Solos manejados'.
# ATENÇÃO: estas DEVEM bater exatamente com o SEEG. A célula de auditoria
# do notebook B4.M.1 lista as (Sub-categoria, Produto) reais ANTES de aplicar
# a classificação — se alguma string divergir, ajustar aqui.
SUBCAT_RESIDUOS_AGRICOLAS = "Resíduos agrícolas"
SUBCAT_RESIDUOS_ORGANICOS = "Aplicação de resíduos orgânicos"
SUBCAT_FERTILIZANTES_N    = "Fertilizantes sintéticos nitrogenados"
SUBCAT_CORRETIVO          = "Corretivo agrícola"
PROD_CANA                 = "Cana-de-açúcar"
PRODS_ORGANICOS_CANA      = ("Torta de filtro", "Vinhaça")
PROD_CALAGEM              = "Calagem"

# Definições rastreáveis dos 5 canais (gravadas em outputs_pre/)
CANAL_DEFINITIONS = pd.DataFrame([
    {
        "canal": "luc",
        "transformacao": "asinh",
        "regra": (
            "Setor='Mudança de Uso da Terra e Floresta' "
            "AND Categoria != 'Resíduos florestais'"
        ),
        "componentes": (
            "Alterações de uso da terra; "
            "Remoção por mudança de uso da terra; "
            "Remoção por vegetação secundária; "
            "Remoção em áreas protegidas; "
            "Queimadas não associadas a desmatamento"
        ),
        "predicao_v22": "nulo ou pequeno (H1a)",
    },
    {
        "canal": "carbono_solo",
        "transformacao": "asinh",
        "regra": (
            "Categoria='Carbono orgânico no solo' "
            "OR Sub-categoria ∈ {Aumento, Redução, Mineralização} "
            "do estoque de C no solo"
        ),
        "componentes": (
            "Carbono orgânico no solo (perdas por conversão); "
            "Aumento do estoque de C no solo (remoção por manejo conservacionista); "
            "Redução do estoque de C no solo; "
            "Mineralização de N associado a perda de C no solo"
        ),
        "predicao_v22": "positivo (H1b — remoção)",
    },
    {
        "canal": "queima",
        "transformacao": "log1p",
        "regra": (
            "Categoria='Queima de resíduos agrícolas' "
            "AND Produto='Cana-de-açúcar'"
        ),
        "componentes": "Queima de resíduos agrícolas — cana-de-açúcar",
        "predicao_v22": "negativo (H2 secundário, ver L13)",
    },
    {
        "canal": "solos_manejados",
        "transformacao": "log",
        "regra": (
            "Categoria='Solos manejados' "
            "AND Detalhamento ∉ {Animal} "
            "AND Sub-categoria ∉ {Aumento/Redução/Mineralização C solo}"
        ),
        "componentes": (
            "Detalhamentos Vegetal/Insumo/Subproduto/Solo: "
            "fertilizantes sintéticos N, ureia, vinhaça, torta de filtro, "
            "resíduos agrícolas vegetais; "
            "EXCLUI Animal (pecuária)"
        ),
        "predicao_v22": "negativo (H2 primário — NEEA penaliza fertilizantes)",
    },
    {
        "canal": "residuos_florestais",
        "transformacao": "log1p",
        "regra": "Categoria='Resíduos florestais'",
        "componentes": "Resíduos de vegetação primária/secundária",
        "predicao_v22": "auxiliar",
    },
])


# ============================================================================
# LEITURA POR UF
# ============================================================================

def read_seeg_uf(uf: str) -> pd.DataFrame:
    """
    Lê o arquivo AR6 de uma UF e retorna como DataFrame com tipos corretos.
    Não filtra nada — apenas leitura + tipagem.

    O arquivo SEEG é wide-format (cols-ano 1970–2024). Mantém wide para
    economizar memória; reshape vem depois em melt.
    """
    if uf not in SEEG_FILES:
        raise ValueError(f"UF '{uf}' não está em SEEG_FILES")
    path = SEEG_FILES[uf]
    if not path.exists():
        raise FileNotFoundError(f"SEEG {uf} não encontrado em {path}")

    # Lê tudo como string para evitar conversões prematuras; converte cols-ano
    # depois em num_br para tratar formato BR (vírgula decimal — embora SEEG
    # geralmente venha em decimal=".", garantimos)
    df = pd.read_csv(path, encoding="utf-8", low_memory=False, dtype=str)

    # Identifica cols-ano
    year_cols = [c for c in df.columns if str(c).strip().isdigit()
                 and 1900 <= int(str(c).strip()) <= 2100]

    # Restringe à janela de interesse (descarta 1970-2011, mantém 2012-2024)
    year_cols_keep = [c for c in year_cols if int(str(c).strip()) in ANOS_FULL]

    # Cols-categoria a manter
    cat_cols = [
        "Setor de emissão",
        "Categoria emissora",
        "Sub-categoria emissora",
        "Produto ou sistema",
        "Detalhamento",
        "Recorte",
        "Atividade geral",
        "Bioma",
        "Emissão/Remoção/Bunker",
        "Gás",
        "Cidade",
    ]
    cat_cols_avail = [c for c in cat_cols if c in df.columns]
    df = df[cat_cols_avail + year_cols_keep].copy()

    # Converte cols-ano para float (SEEG usa "." como decimal, sem milhar)
    for c in year_cols_keep:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Tag UF
    df["uf"] = uf

    return df


# ============================================================================
# FILTROS E SINAL
# ============================================================================

def filter_afolu(df: pd.DataFrame) -> pd.DataFrame:
    """Restringe ao setor AFOLU + Resíduos (não considerados aqui)."""
    return df[df["Setor de emissão"].isin(SETORES_AFOLU)].copy()


def filter_emission_signal(df: pd.DataFrame) -> pd.DataFrame:
    """Exclui Bunker; mantém Emissão/Remoção/NCI."""
    return df[df["Emissão/Remoção/Bunker"].isin(TIPOS_EMISSAO_INCLUSOS)].copy()


def apply_sign(df: pd.DataFrame, year_cols: list[str]) -> pd.DataFrame:
    """
    Multiplica por -1 as linhas de Remoção (incluindo Remoção NCI).
    Mantém Emissão e Emissão NCI com sinal positivo.

    Aplica em todas as cols-ano simultaneamente.
    """
    df = df.copy()
    mask_remocao = df["Emissão/Remoção/Bunker"].isin(TIPOS_REMOCAO)
    df.loc[mask_remocao, year_cols] = df.loc[mask_remocao, year_cols] * -1
    return df


def filter_co2e_gtp(df: pd.DataFrame) -> pd.DataFrame:
    """
    SEEG fornece duas métricas: GTP-AR6 e GWP-AR6 (mesmas linhas duplicadas).
    Para evitar dupla contagem, mantém apenas GWP-AR6 (padrão IPCC).
    """
    return df[df["Gás"] == "CO2e (t) GWP-AR6"].copy()


# ============================================================================
# CLASSIFICAÇÃO EM MACRO-CANAIS
# ============================================================================

def classify_channel(row) -> Optional[str]:
    """
    Atribui um macro-canal a uma linha SEEG conforme regras §3.10 v2.2.

    Retorna None se a linha não pertence a nenhum dos 5 canais de interesse
    (e.g., Resíduos sólidos urbanos, Manejo de dejetos, etc.) — essas linhas
    são descartadas no aggregate.
    """
    setor = row.get("Setor de emissão")
    cat = row.get("Categoria emissora")
    subcat = row.get("Sub-categoria emissora")
    prod = row.get("Produto ou sistema")
    detalh = row.get("Detalhamento")

    # 1. carbono_solo (compositivo): primeiro porque pega sub-categorias
    # que viriam para solos_manejados se classificadas pela categoria
    if cat == "Carbono orgânico no solo":
        return "carbono_solo"
    if subcat in SOLOS_C_SUBCATEGORIAS:
        return "carbono_solo"

    # 2. queima — só cana
    if cat == "Queima de resíduos agrícolas":
        if prod == "Cana-de-açúcar":
            return "queima"
        return None  # algodão e outros descartados

    # 3. solos_manejados (após carbono_solo, então sub-categorias já saíram)
    if cat == "Solos manejados":
        if detalh in SOLOS_DETALHAMENTOS_EXCLUIR:
            return None  # descarta pecuária
        return "solos_manejados"

    # 4. residuos_florestais
    if cat == "Resíduos florestais":
        return "residuos_florestais"

    # 5. luc — qualquer outra categoria do setor MUTF
    if setor == "Mudança de Uso da Terra e Floresta":
        return "luc"

    # Setor Agropecuária mas categoria não-classificada (e.g., Manejo de dejetos,
    # Fermentação entérica) → não vai para nenhum canal.
    return None


def classify_subchannel(row) -> Optional[str]:
    """
    Sub-classifica APENAS linhas que classify_channel mandou para
    'solos_manejados', nos 6 sub-canais de decomposição (pré-registro
    v2.3.8 §3.10.2). Para linhas de qualquer outro macro-canal, retorna
    None (não decompõe — a linha não entra no painel de sub-canais).

    Partição exaustiva e mutuamente exclusiva por construção:
    a regra 6 (res_minor) é o bucket de fechamento — qualquer linha de
    'solos_manejados' que não casa com as 5 regras anteriores cai em
    res_minor. Logo, para todo (município, ano):

        Σ sub-canais ≡ solos_manejados   (ao 4º decimal)

    Esta identidade é verificada no notebook B4.M.2 (validação algébrica).
    """
    # Só age se a linha É solos_manejados. Reusa classify_channel para
    # garantir consistência total com a definição do macro-canal (mesmos
    # filtros de carbono_solo, Detalhamento Animal, ordem de precedência).
    if classify_channel(row) != "solos_manejados":
        return None

    subcat = row.get("Sub-categoria emissora")
    prod   = row.get("Produto ou sistema")

    # 1. res_cana — Resíduos agrícolas ∩ Cana (Eqs. 62-66)
    if subcat == SUBCAT_RESIDUOS_AGRICOLAS and prod == PROD_CANA:
        return "res_cana"

    # 2. org_cana — Aplic. resíduos orgânicos ∩ {Torta, Vinhaça} (Eqs. 40, 42)
    if subcat == SUBCAT_RESIDUOS_ORGANICOS and prod in PRODS_ORGANICOS_CANA:
        return "org_cana"

    # 3. fert_n — Fertilizantes sintéticos nitrogenados, agregado (Eqs. 52-54)
    if subcat == SUBCAT_FERTILIZANTES_N:
        return "fert_n"

    # 4. calagem — Corretivo agrícola ∩ Calagem (Eqs. 89+9)
    if subcat == SUBCAT_CORRETIVO and prod == PROD_CALAGEM:
        return "calagem"

    # 5. res_outros — Resíduos agrícolas ∩ Produto ≠ Cana (Eqs. 60-61)
    if subcat == SUBCAT_RESIDUOS_AGRICOLAS and prod != PROD_CANA:
        return "res_outros"

    # 6. res_minor — fechamento exaustivo: solos orgânicos, queima de pasto,
    #    aplic. orgânicos não-cana, corretivo não-calagem, etc.
    #    Reportado só em apêndice, sem ATT estimado (§3.10.2).
    return "res_minor"


def aggregate_to_long(df: pd.DataFrame, year_cols: list[str]) -> pd.DataFrame:
    """
    Reshape wide → long (município × ano × canal), somando entre linhas
    que pertencem ao mesmo (município, ano, canal).

    Após este step:
    - cada linha é (Cidade, ano, canal, valor_signed)
    - valor pode ser positivo (emissão líquida) ou negativo (remoção líquida)

    Opção 2 do refator (v2.3.8): além dos 5 macro-canais, emite também os
    6 sub-canais de decomposição do solos_manejados, EM PARALELO. As linhas
    de sub-canal usam o mesmo esquema (Cidade, uf, canal, ano, valor), com
    `canal` ∈ SUBCANAIS_SOLOS. Macro e sub coexistem no mesmo long — o pivot
    posterior cria colunas separadas. Isto preserva 100% do pipeline dos
    macro-canais (auditoria F3, balanceamento) intacto.
    """
    df = df.copy()

    # --- Passada 1: macro-canais (idêntico ao original) ---
    df["canal"] = df.apply(classify_channel, axis=1)
    df_macro = df[df["canal"].notna()].copy()

    # --- Passada 2: sub-canais (só linhas de solos_manejados) ---
    # classify_subchannel já retorna None para tudo que não é solos_manejados,
    # então o filtro .notna() isola exatamente a decomposição.
    df_sub = df.copy()
    df_sub["canal"] = df_sub.apply(classify_subchannel, axis=1)
    df_sub = df_sub[df_sub["canal"].notna()].copy()

    # Concatena macro + sub. Ambos têm a mesma estrutura de colunas.
    df_all = pd.concat([df_macro, df_sub], ignore_index=True, sort=False)

    # Melt (idêntico ao original, agora sobre macro+sub)
    long = df_all.melt(
        id_vars=["Cidade", "uf", "canal"],
        value_vars=year_cols,
        var_name="ano",
        value_name="valor",
    )
    long["ano"] = long["ano"].astype(str).str.strip().astype(int)
    long["valor"] = long["valor"].fillna(0.0)

    # Agrega por (Cidade, ano, canal): soma com sinal já aplicado
    agg = (
        long.groupby(["Cidade", "uf", "canal", "ano"], as_index=False)["valor"]
            .sum()
    )
    return agg


# ============================================================================
# CHAVEAMENTO CIDADE → GEOCODE
# ============================================================================

def attach_geocode_to_seeg(
    seeg_long: pd.DataFrame, crosswalk: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Resolve a coluna 'Cidade' do SEEG (formato "Município (UF)") via
    crosswalk.cidade_uf_seeg. Retorna (matched, unmatched).

    Cidades sem match retornam separadas para auditoria.
    """
    cw = crosswalk[["geocode", "municipio", "uf", "cidade_uf_seeg"]].copy()
    out = seeg_long.merge(
        cw, left_on="Cidade", right_on="cidade_uf_seeg",
        how="left", suffixes=("", "_cw"),
    )
    matched = out[out["geocode"].notna()].copy()
    unmatched = out[out["geocode"].isna()].copy()
    return matched, unmatched


# ============================================================================
# PIVOT WIDE (município × ano × 5 canais)
# ============================================================================

def pivot_to_outcomes_wide(seeg_long: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot canal-long → wide com 5 colunas de outcome.
    """
    wide = (
        seeg_long.pivot_table(
            index=["geocode", "municipio", "uf", "ano"],
            columns="canal",
            values="valor",
            aggfunc="sum",
        )
        .reset_index()
    )
    wide.columns.name = None
    return wide


# ============================================================================
# AUDITORIA F3 (cobertura município × canal × ano)
# ============================================================================

def build_coverage_matrix(
    seeg_wide: pd.DataFrame,
    crosswalk: pd.DataFrame,
    canais_cana: tuple[str, ...] = ("queima",),
    cana_baseline_munis: Optional[Iterable[str]] = None,
    anos: Optional[list[int]] = None,
) -> pd.DataFrame:
    """
    Gera matriz de cobertura município × canal × ano com classificação F3.

    Parameters
    ----------
    seeg_wide : DataFrame com painel SEEG (geocode × ano × canais)
    crosswalk : DataFrame universal (todos os 2.363 municípios CS)
    canais_cana : tuple
        Canais específicos de cana onde "ausência" pode significar
        legitimamente "município não-canavieiro" (default: apenas 'queima').
    cana_baseline_munis : iterable de geocodes
        Municípios identificados como canavieiros pelo filtro baseline
        (PAM area_cana > 500ha OU MapBiomas share_cana > 5% OU hospeda usina).
        Se None, sinaliza com flag "indeterminado".
    anos : list[int] | None
        Janela temporal (default: ANOS_MAIN, 2015-2024).

    Returns
    -------
    DataFrame com colunas:
        geocode, ano, canal, valor (NaN se ausente),
        is_canavieiro_baseline, classificacao
    """
    if anos is None:
        anos = ANOS_MAIN
    canais_todos = ("luc", "carbono_solo", "queima", "solos_manejados",
                    "residuos_florestais")

    # Universo completo: todos os munis × todos os anos × todos os canais
    grid = (
        crosswalk[["geocode", "municipio", "uf"]]
            .assign(_key=1)
            .merge(pd.DataFrame({"ano": anos, "_key": 1}), on="_key")
            .drop(columns="_key")
    )
    grid = grid.assign(_key=1).merge(
        pd.DataFrame({"canal": canais_todos, "_key": 1}), on="_key"
    ).drop(columns="_key")

    # Long format para join
    seeg_long = seeg_wide.melt(
        id_vars=["geocode", "municipio", "uf", "ano"],
        value_vars=[c for c in canais_todos if c in seeg_wide.columns],
        var_name="canal", value_name="valor",
    )

    matrix = grid.merge(
        seeg_long[["geocode", "ano", "canal", "valor"]],
        on=["geocode", "ano", "canal"], how="left",
    )

    # Flag canavieiro
    if cana_baseline_munis is not None:
        cana_set = set(str(g) for g in cana_baseline_munis)
        matrix["is_canavieiro_baseline"] = matrix["geocode"].astype(str).isin(cana_set)
    else:
        matrix["is_canavieiro_baseline"] = pd.NA

    # Classificação por célula
    # Distingue 3 estados de `valor`:
    #   NaN   → célula realmente ausente do SEEG
    #   0.0   → registro estrutural sem emissão real (típico SEEG-AR6)
    #   > 0   → observação efetiva
    def classify(row):
        is_cana = row["is_canavieiro_baseline"]
        is_cana_channel = row["canal"] in canais_cana
        valor = row["valor"]
        is_nan = pd.isna(valor)
        is_zero = (not is_nan) and (abs(valor) < 1e-9)
        is_observed = (not is_nan) and (not is_zero)

        # Quando is_cana é desconhecido (sem cana_baseline_munis informado)
        if is_cana is pd.NA:
            if is_nan:
                return "NAN_INDETERMINADO"
            elif is_zero:
                return "ZERO_INDETERMINADO"
            else:
                return "OK_INDETERMINADO"

        # Município canavieiro
        if is_cana:
            if is_nan:
                return "LACUNA_SUSPEITA"  # canavieiro sem registro = bug de cobertura
            elif is_zero:
                return "OK_ZERO_CANAVIEIRO"  # canavieiro mas zero — possível
            else:
                return "OK"

        # Município não-canavieiro
        else:
            if is_nan:
                return "ZERO_LEGITIMO"  # não-canavieiro sem registro = ok
            elif is_zero:
                if is_cana_channel:
                    return "ZERO_LEGITIMO"  # não-canavieiro × canal cana × zero = ok
                else:
                    return "ZERO_NAO_CANAVIEIRO"  # canal não-cana × zero = ok
            else:
                if is_cana_channel:
                    return "RUIDO_ESTRUTURAL"  # não-canavieiro × canal cana × valor > 0 = ruído SEEG
                else:
                    return "OK"  # não-canavieiro com observação em canal não-cana é OK

    matrix["classificacao"] = matrix.apply(classify, axis=1)
    return matrix


# ============================================================================
# BALANCEAMENTO INFORMADO PELA AUDITORIA
# ============================================================================

def balance_panel_audited(
    seeg_wide: pd.DataFrame,
    crosswalk: pd.DataFrame,
    coverage_matrix: pd.DataFrame,
    canais: tuple[str, ...] = ("luc", "carbono_solo", "queima",
                                "solos_manejados", "residuos_florestais"),
    anos: Optional[list[int]] = None,
) -> pd.DataFrame:
    """
    Balanceia o painel à grade completa (município × ano × canal) e aplica
    fillna informado pela coverage_matrix:

    - ZERO_LEGITIMO ou ZERO_NAO_CANAVIEIRO → fillna(0)
    - LACUNA_SUSPEITA → mantém NaN (modelagem decide o que fazer)
    - AUSENTE_INDETERMINADO → fillna(0) com flag (mais conservador)

    Output expõe os outcomes em wide + flags por canal.
    """
    if anos is None:
        anos = ANOS_MAIN
    canais = tuple(c for c in canais if c in seeg_wide.columns)

    # Grade completa
    grid = (
        crosswalk[["geocode", "municipio", "uf"]]
            .assign(_k=1)
            .merge(pd.DataFrame({"ano": anos, "_k": 1}), on="_k")
            .drop(columns="_k")
    )

    # Restringe a anos da janela
    seeg_w = seeg_wide[seeg_wide["ano"].isin(anos)].copy()

    # Reduz para colunas de interesse
    keep = ["geocode", "ano"] + list(canais)
    seeg_w = seeg_w[[c for c in keep if c in seeg_w.columns]]

    # Merge grid
    panel = grid.merge(seeg_w, on=["geocode", "ano"], how="left")

    # Aplica fillna informado pela coverage_matrix
    cov = coverage_matrix[["geocode", "ano", "canal", "classificacao"]]
    cov_pivot = cov.pivot_table(
        index=["geocode", "ano"], columns="canal",
        values="classificacao", aggfunc="first"
    ).reset_index()
    cov_pivot.columns = ["geocode", "ano"] + [
        f"flag_{c}" for c in cov_pivot.columns[2:]
    ]
    panel = panel.merge(cov_pivot, on=["geocode", "ano"], how="left")

    # Aplica fillna por canal de acordo com o flag
    for canal in canais:
        flag_col = f"flag_{canal}"
        if flag_col not in panel.columns:
            continue
        # ZERO_LEGITIMO + ZERO_NAO_CANAVIEIRO + indeterminados → 0
        # LACUNA_SUSPEITA → mantém NaN (modelagem decide)
        # OK / OK_ZERO_CANAVIEIRO / RUIDO_ESTRUTURAL → mantém valor observado
        zero_flags = ("ZERO_LEGITIMO", "ZERO_NAO_CANAVIEIRO",
                      "NAN_INDETERMINADO", "ZERO_INDETERMINADO")
        mask_zero = panel[flag_col].isin(zero_flags) & panel[canal].isna()
        panel.loc[mask_zero, canal] = 0.0

    return panel


# ============================================================================
# TRANSFORMAÇÕES (§3.10)
# ============================================================================

def apply_transformations(panel: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica transformações por canal conforme §3.10:
      luc                  → asinh
      carbono_solo         → asinh
      queima               → log1p
      solos_manejados      → log
      residuos_florestais  → log1p

    Cria colunas com prefixo da transformação: log_luc não existe; usa
    asinh_luc; log_solos_manejados, etc. Para casos onde log() é aplicado
    sobre valor ≤ 0, retorna NaN (comportamento desejado — modelagem
    posterior trata).
    """
    out = panel.copy()
    transforms = dict(PARAMS.OUTCOME_TRANSFORM)
    # Adiciona transformações dos sub-canais (v2.3.8 §3.10.2). Não muta o
    # config (frozen); apenas estende localmente o mapa canal→transformação.
    transforms.update(SUBCANAL_TRANSFORM)

    for canal, transform in transforms.items():
        if canal not in out.columns:
            continue
        if transform == "log":
            with np.errstate(invalid="ignore", divide="ignore"):
                out[f"log_{canal}"] = np.where(
                    out[canal] > 0, np.log(out[canal]), np.nan
                )
        elif transform == "log1p":
            with np.errstate(invalid="ignore"):
                out[f"log1p_{canal}"] = np.where(
                    out[canal] >= 0, np.log1p(out[canal]), np.nan
                )
        elif transform == "asinh":
            out[f"asinh_{canal}"] = np.arcsinh(out[canal])
    return out


# ============================================================================
# BALANCEAMENTO E VALIDAÇÃO DOS SUB-CANAIS (v2.3.8)
# ============================================================================

def balance_subchannels(
    panel_macro: pd.DataFrame,
    seeg_wide: pd.DataFrame,
    crosswalk: pd.DataFrame,
    coverage_matrix: pd.DataFrame,
    anos: Optional[list[int]] = None,
) -> pd.DataFrame:
    """
    Acrescenta as colunas dos 6 sub-canais ao painel já balanceado dos
    macro-canais, aplicando a regra de preenchimento correta por tipo:

    - Sub-canais cana-rotulados (res_cana, org_cana): reusa a coverage_matrix
      do macro-canal 'queima' (mesma lógica F3 — ausência em município
      canavieiro = LACUNA_SUSPEITA, mantém NaN; não-canavieiro = ZERO).
      Justificativa: res_cana/org_cana são canais de cana exatamente como
      queima; um município sem cana legitimamente não tem resíduo de cana.

    - Sub-canais territoriais (fert_n, calagem, res_outros, res_minor):
      existem em praticamente todo município com qualquer agricultura.
      Ausência = zero estrutural. fillna(0) direto, sem flag F3.

    O painel macro NÃO é alterado — apenas recebe colunas novas à direita.
    A identidade algébrica (Σ sub == solos_manejados) é verificada
    separadamente por validate_subchannel_algebra().

    Parameters
    ----------
    panel_macro : saída de balance_panel_audited (5 macro-canais balanceados)
    seeg_wide   : pivot wide com TODAS as colunas (macro + sub)
    crosswalk   : universo canônico
    coverage_matrix : matriz F3 dos macro-canais (tem flag de 'queima')
    anos        : janela (default ANOS_MAIN)
    """
    if anos is None:
        anos = ANOS_MAIN

    out = panel_macro.copy()
    sub_presentes = [c for c in SUBCANAIS_SOLOS if c in seeg_wide.columns]

    # Traz os valores dos sub-canais do seeg_wide para o painel balanceado,
    # alinhando por (geocode, ano).
    sub_cols = ["geocode", "ano"] + sub_presentes
    sub_wide = seeg_wide[[c for c in sub_cols if c in seeg_wide.columns]].copy()
    sub_wide = sub_wide[sub_wide["ano"].isin(anos)]
    sub_wide = sub_wide.drop_duplicates(subset=["geocode", "ano"])
    out = out.merge(sub_wide, on=["geocode", "ano"], how="left")

    # --- Cana-rotulados: aplica F3 da 'queima' ---
    # A coverage_matrix tem (geocode, ano, canal, classificacao). Pega só
    # o canal 'queima' como referência de cobertura de cana.
    cov_queima = coverage_matrix[
        coverage_matrix["canal"] == "queima"
    ][["geocode", "ano", "classificacao"]].copy()
    cov_queima = cov_queima.drop_duplicates(subset=["geocode", "ano"])
    cov_queima = cov_queima.rename(columns={"classificacao": "_flag_cana"})
    out = out.merge(cov_queima, on=["geocode", "ano"], how="left")

    zero_flags = ("ZERO_LEGITIMO", "ZERO_NAO_CANAVIEIRO",
                  "NAN_INDETERMINADO", "ZERO_INDETERMINADO")
    for canal in SUBCANAIS_CANA:
        if canal not in out.columns:
            continue
        # município não-canavieiro (flag zero) e valor ausente → 0
        mask_zero = out["_flag_cana"].isin(zero_flags) & out[canal].isna()
        out.loc[mask_zero, canal] = 0.0
        # LACUNA_SUSPEITA em canavieiro → mantém NaN (modelagem decide),
        #   espelhando o tratamento de 'queima'.
        out[f"flag_{canal}"] = out["_flag_cana"]

    out = out.drop(columns=["_flag_cana"])

    # --- Territoriais: zero estrutural direto ---
    for canal in SUBCANAIS_TERRITORIAIS:
        if canal not in out.columns:
            continue
        out[canal] = out[canal].fillna(0.0)

    return out


def validate_subchannel_algebra(
    panel: pd.DataFrame,
    tol: float = 1e-4,
) -> dict:
    """
    Verifica a identidade algébrica do pré-registro v2.3.8 §7.7:

        Σ (res_cana, org_cana, fert_n, calagem, res_outros, res_minor)
          ≡ solos_manejados   (para todo município × ano)

    Tolerância default 1e-4 tCO2e (4º decimal), conforme §7.7.

    A verificação só considera células onde solos_manejados NÃO é NaN
    (células LACUNA_SUSPEITA mantêm NaN por design e são excluídas da
    identidade — mas registramos quantas são).

    Returns
    -------
    dict com:
      ok                 : bool — True se max_abs_diff <= tol
      n_cells            : células verificadas
      n_excluded_nan     : células puladas por solos_manejados NaN
      max_abs_diff       : maior |Σsub − solos_manejados|
      worst              : DataFrame top-10 piores discrepâncias (ou vazio)
    """
    need = list(SUBCANAIS_SOLOS) + ["solos_manejados"]
    missing = [c for c in need if c not in panel.columns]
    if missing:
        return {
            "ok": False,
            "error": f"colunas ausentes: {missing}",
            "n_cells": 0,
            "n_excluded_nan": 0,
            "max_abs_diff": float("nan"),
            "worst": pd.DataFrame(),
        }

    df = panel.copy()
    # Soma dos sub-canais tratando NaN como 0 APENAS para os cana-rotulados
    # que podem ter NaN legítimo (LACUNA_SUSPEITA). Para a identidade valer,
    # comparamos onde solos_manejados é observado.
    sub_sum = df[list(SUBCANAIS_SOLOS)].sum(axis=1, skipna=True)
    sm = df["solos_manejados"]

    mask_valid = sm.notna()
    n_excluded = int((~mask_valid).sum())

    diff = (sub_sum[mask_valid] - sm[mask_valid]).abs()
    max_diff = float(diff.max()) if len(diff) else 0.0
    ok = bool(max_diff <= tol)

    worst = pd.DataFrame()
    if not ok:
        tmp = df.loc[mask_valid, ["geocode", "ano",
                                  "solos_manejados"] + list(SUBCANAIS_SOLOS)].copy()
        tmp["_sub_sum"] = sub_sum[mask_valid].values
        tmp["_abs_diff"] = diff.values
        worst = tmp.sort_values("_abs_diff", ascending=False).head(10)

    return {
        "ok": ok,
        "n_cells": int(mask_valid.sum()),
        "n_excluded_nan": n_excluded,
        "max_abs_diff": max_diff,
        "worst": worst,
    }


# ============================================================================
# ORQUESTRAÇÃO
# ============================================================================

def process_uf(uf: str) -> pd.DataFrame:
    """
    Pipeline completo de UMA UF: lê → filtra AFOLU+sinal+gás → classifica
    canal → agrega para long.

    Retorna long com (Cidade, uf, canal, ano, valor).
    """
    df = read_seeg_uf(uf)
    df = filter_afolu(df)
    df = filter_emission_signal(df)
    df = filter_co2e_gtp(df)

    year_cols = [c for c in df.columns if str(c).strip().isdigit()
                 and int(str(c).strip()) in ANOS_FULL]
    df = apply_sign(df, year_cols)

    long = aggregate_to_long(df, year_cols)
    return long


def run_seeg_pipeline(
    crosswalk: pd.DataFrame,
    cana_baseline_munis: Optional[Iterable[str]] = None,
    save: bool = True,
) -> dict:
    """
    Roda o pipeline SEEG completo nas 6 UFs Centro-Sul.

    Parameters
    ----------
    crosswalk : DataFrame canônico (universo 2.363 munis).
    cana_baseline_munis : geocodes dos municípios canavieiros (para F3).
        Se None, F3 sinaliza ausências como AUSENTE_INDETERMINADO (conservador).
    save : se True, salva em interim/ e outputs_pre/.
    """
    print("→ Processando 6 UFs Centro-Sul (pode levar 1-3min em Colab)...")
    parts = []
    for uf in PARAMS.UFS_CORE:
        print(f"  · {uf} ({file_size_mb(SEEG_FILES[uf]):.1f} MB)... ", end="")
        long_uf = process_uf(uf)
        print(f"{len(long_uf):,} linhas long")
        parts.append(long_uf)
    seeg_long = pd.concat(parts, ignore_index=True, sort=False)
    print(f"  Concatenado: {len(seeg_long):,} linhas")

    # Resolve geocode
    print("\n→ Chaveando contra crosswalk...")
    matched, unmatched = attach_geocode_to_seeg(seeg_long, crosswalk)
    print(f"  matched: {len(matched):,} | unmatched: {len(unmatched):,}")
    if len(unmatched) > 0:
        n_unm_unique = unmatched["Cidade"].nunique()
        print(f"  cidades únicas sem match: {n_unm_unique}")

    # Pivot wide
    seeg_wide = pivot_to_outcomes_wide(matched)
    print(f"\n→ Painel wide: {seeg_wide.shape}")
    canais_presentes = [c for c in ["luc", "carbono_solo", "queima",
                                     "solos_manejados", "residuos_florestais"]
                        if c in seeg_wide.columns]
    print(f"  canais detectados: {canais_presentes}")

    # Auditoria F3
    print("\n→ Auditoria F3 (cobertura município × canal × ano)...")
    coverage = build_coverage_matrix(
        seeg_wide, crosswalk,
        canais_cana=("queima",),
        cana_baseline_munis=cana_baseline_munis,
    )
    print(f"  cells totais: {len(coverage):,}")
    print(f"  classificações:")
    print(coverage["classificacao"].value_counts().to_string())

    # Balanceamento auditado
    print("\n→ Balanceando painel (informado pelo audit)...")
    panel = balance_panel_audited(seeg_wide, crosswalk, coverage)
    print(f"  panel balanceado (macro): {panel.shape}")

    # Balanceamento dos sub-canais (v2.3.8 — Opção 2)
    print("\n→ Balanceando sub-canais do solos_manejados...")
    sub_presentes = [c for c in SUBCANAIS_SOLOS if c in seeg_wide.columns]
    print(f"  sub-canais detectados: {sub_presentes}")
    panel = balance_subchannels(panel, seeg_wide, crosswalk, coverage)
    print(f"  panel balanceado (macro+sub): {panel.shape}")

    # Validação algébrica (B4.M.2 — pré-registro §7.7)
    print("\n→ Validação algébrica Σ sub-canais ≡ solos_manejados...")
    algebra = validate_subchannel_algebra(panel, tol=1e-4)
    if algebra["ok"]:
        print(f"  ✓ PASSOU — max |Σsub − solos_manejados| = "
              f"{algebra['max_abs_diff']:.2e} tCO2e "
              f"(≤ 1e-4) em {algebra['n_cells']:,} células")
        print(f"    ({algebra['n_excluded_nan']:,} células LACUNA_SUSPEITA "
              f"excluídas por design)")
    else:
        print(f"  ✗ FALHOU — max |Σsub − solos_manejados| = "
              f"{algebra['max_abs_diff']:.4f} tCO2e (> 1e-4)")
        print(f"    Top discrepâncias:")
        print(algebra["worst"].to_string())
        raise AssertionError(
            "Validação algébrica B4.M.2 falhou: a soma dos sub-canais não "
            "reproduz solos_manejados ao 4º decimal. Pipeline abortado para "
            "não gerar painel inconsistente. Verifique as strings de "
            "Sub-categoria/Produto contra o SEEG real (célula de auditoria "
            "do notebook B4.M.1)."
        )

    # Transformações
    panel_t = apply_transformations(panel)
    n_transformed = sum(1 for c in panel_t.columns
                        if c.startswith(("log_", "log1p_", "asinh_")))
    print(f"  colunas transformadas: {n_transformed}")

    # Distribuições por canal/UF (sanity check)
    print("\n→ Calculando distribuições para sanity check...")
    distrib_rows = []
    for canal in canais_presentes:
        if canal not in panel.columns:
            continue
        for uf in PARAMS.UFS_CORE:
            sub = panel[panel["uf"] == uf][canal].dropna()
            if len(sub) == 0:
                continue
            distrib_rows.append({
                "uf": uf, "canal": canal,
                "n": len(sub),
                "n_zero": (sub == 0).sum(),
                "n_neg": (sub < 0).sum(),
                "n_pos": (sub > 0).sum(),
                "mean": sub.mean(),
                "median": sub.median(),
                "min": sub.min(),
                "max": sub.max(),
            })
    distrib = pd.DataFrame(distrib_rows)

    # Save
    if save:
        print("\n→ Salvando...")
        seeg_long.to_parquet(interim("seeg_long.parquet"), index=False)
        seeg_wide.to_csv(interim("seeg_outcomes_balanced.csv"), index=False)
        panel_t.to_csv(interim("seeg_outcomes_audited.csv"), index=False)
        coverage.to_csv(out_pre("seeg_coverage_matrix.csv"), index=False)
        distrib.to_csv(out_pre("seeg_distribuicoes_canal_uf.csv"), index=False)
        CANAL_DEFINITIONS.to_csv(out_pre("seeg_canal_definitions.csv"), index=False)
        # v2.3.8: painel dedicado dos sub-canais (B4.M.1) + relatório de
        # validação algébrica (B4.M.2). Facilita consumo pelo notebook de
        # decomposição (B4.M.4) sem reprocessar o pipeline inteiro.
        sub_cols_present = [c for c in SUBCANAIS_SOLOS if c in panel_t.columns]
        sub_trans_cols = [c for c in panel_t.columns
                          if any(c == f"{p}{s}" for p in
                                 ("asinh_", "log1p_", "log_")
                                 for s in SUBCANAIS_SOLOS)]
        panel_subcanais = panel_t[
            ["geocode", "municipio", "uf", "ano",
             "solos_manejados"]
            + sub_cols_present + sub_trans_cols
            + [f"flag_{c}" for c in SUBCANAIS_CANA
               if f"flag_{c}" in panel_t.columns]
        ].copy()
        panel_subcanais.to_csv(
            interim("seeg_subcanais_panel.csv"), index=False
        )
        pd.DataFrame([{
            "max_abs_diff": algebra["max_abs_diff"],
            "n_cells": algebra["n_cells"],
            "n_excluded_lacuna": algebra["n_excluded_nan"],
            "tolerancia": 1e-4,
            "passou": algebra["ok"],
        }]).to_csv(
            out_pre("seeg_subcanais_validacao_algebrica.csv"), index=False
        )
        if len(unmatched) > 0:
            unm_summary = (
                unmatched.groupby("Cidade").size().reset_index(name="n_linhas")
                .sort_values("n_linhas", ascending=False)
            )
            unm_summary.to_csv(out_pre("seeg_cidade_unmatched.csv"), index=False)
        print("  ✓ tudo salvo (incl. seeg_subcanais_panel.csv)")

    return {
        "seeg_long": seeg_long,
        "seeg_wide": seeg_wide,
        "panel": panel_t,
        "coverage": coverage,
        "distrib": distrib,
        "unmatched": unmatched,
        "canal_definitions": CANAL_DEFINITIONS,
        "subchannel_algebra": algebra,
    }
