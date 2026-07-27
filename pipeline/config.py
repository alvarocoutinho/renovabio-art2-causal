"""
pipeline.config
================
Configuração central do pipeline RenovaBio × AFOLU (paper EcolEcon).

Este módulo NÃO contém lógica de processamento. É apenas definição
estática de paths, parâmetros do pré-registro, e nomes-padrão de arquivos.

Convenção:
- BASE_DIR é o diretório-raiz do projeto no Google Drive.
- Tudo o mais é derivado por composição.
- Quando rodando fora do Colab (testes locais), basta sobrescrever BASE_DIR.

Referências ao pré-registro:
- §3.2: 6 UFs Centro-Sul (sem ES)
- §3.4: janela 2015-2024 principal, 2012-2024 robustez
- §3.5: tratamento staggered T1 + doses T2 (vol) + T3 (NEEA)
- §3.7.1: covariáveis baseline pré-2020
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple


# ============================================================================
# DIRETÓRIO-RAIZ DO PROJETO
# ============================================================================
# Em Colab: o Drive é montado em /content/drive/MyDrive/
# Pasta do projeto: "Renovabio - EcoEco"
BASE_DIR = Path("/content/drive/MyDrive/Renovabio - EcoEco")


# ============================================================================
# HIERARQUIA DE DADOS (3 níveis)
# ============================================================================
# raw      → bases brutas, intocáveis, exatamente como vieram da fonte
# interim  → bases limpas, chaveadas, sem decisão metodológica de modelagem
# processed → painéis prontos para PSM/CS/SDID
DATA_RAW       = BASE_DIR / "data" / "raw"
DATA_INTERIM   = BASE_DIR / "data" / "interim"
DATA_PROCESSED = BASE_DIR / "data" / "processed"

# Subpastas de raw (uma por fonte)
RAW_ANP          = DATA_RAW / "anp"
RAW_SEEG         = DATA_RAW / "seeg"
RAW_IBGE         = DATA_RAW / "ibge"
RAW_MAPBIOMAS    = DATA_RAW / "mapbiomas"
RAW_SICAR        = DATA_RAW / "sicar"
RAW_PSM_BASELINE = DATA_RAW / "psm_baseline"

# Outputs auxiliares (relatórios de auditoria, logs, NÃO entram na modelagem)
OUTPUTS_PRE = BASE_DIR / "outputs_pre"


# ============================================================================
# ARQUIVOS DE INPUT (em data/raw/)
# ============================================================================
# ANP — 3 snapshots de certificados + NEEA consolidado
ANP_CERT_2022 = RAW_ANP / "certificados-aprovados.xlsx"
ANP_CERT_2025 = RAW_ANP / "certificados-aprovados-producao_2025.xlsx"
ANP_CERT_2026 = RAW_ANP / "certificados-aprovados-producao_2026.xlsx"
ANP_NEEA      = RAW_ANP / "Usinas_NEEA_consolidado.csv"

# Cada snapshot tem uma data de corte oficial — usada para datar coortes
ANP_SNAP_DATES = {
    ANP_CERT_2022.name: "2022-02-22",
    ANP_CERT_2025.name: "2023-10-09",
    ANP_CERT_2026.name: "2026-04-17",
}

# IBGE
IBGE_PAM_1612      = RAW_IBGE / "tabela1612.csv"
IBGE_UNIVERSO_CORE = RAW_IBGE / "01_universo_core_6ufs.csv"
IBGE_GEOJSON_CS    = RAW_IBGE / "centro_sul.geojson"

# SEEG (6 arquivos por UF)
SEEG_FILES = {
    "GO": RAW_SEEG / "ar6 - go.csv",
    "MG": RAW_SEEG / "ar6 - mg.csv",
    "MS": RAW_SEEG / "ar6 - ms.csv",
    "MT": RAW_SEEG / "ar6 - mt.csv",
    "PR": RAW_SEEG / "ar6 - pr.csv",
    "SP": RAW_SEEG / "ar6 - sp.csv",
}

# MapBiomas — usamos o painel pronto como input principal e o raw como backup
MAPBIOMAS_PANEL = RAW_MAPBIOMAS / "mapbiomas_municipal_year_panel_ready.csv"
MAPBIOMAS_RAW   = RAW_MAPBIOMAS / "MAPBIOMAS_BRAZIL-COVERAGE_STATISTICS-COL.10.1-MUNICIPALITIES_STATES_BIOMES.csv"

# SICAR — painel mensal
SICAR_PAINEL = RAW_SICAR / "sicar_painel.xlsx"

# PSM baseline — covariáveis socioeconômicas
PSM_BASELINE_RAW = RAW_PSM_BASELINE / "base_psm_integrada_raw.csv"


# ============================================================================
# PARÂMETROS METODOLÓGICOS DO PRÉ-REGISTRO V2.2
# ============================================================================

@dataclass(frozen=True)
class Params:
    """Parâmetros metodológicos imutáveis declarados no pré-registro."""

    # --- Universo geográfico (§3.2) ---
    # Centro-Sul SEM Espírito Santo
    UFS_CORE: Tuple[str, ...] = ("SP", "GO", "MG", "PR", "MS", "MT")

    # --- Janela temporal (§3.4) ---
    YEAR_MIN_MAIN: int = 2015      # painel principal: 2015–2024 (5+5)
    YEAR_MAX_MAIN: int = 2024
    YEAR_MIN_FULL: int = 2012      # painel estendido para robustez 2012–2024
    YEAR_MAX_FULL: int = 2024

    # --- Tratamento (§3.5) ---
    # Coorte = ano da primeira certificação no município (g_m)
    # Tratamento absorvente: D_it = 1[t >= g_m]
    PROGRAM_START_YEAR: int = 2020          # primeira onda operacional
    PRE_PROGRAM_CUTOFF: int = 2018          # certificados < 2018 são artefatos
    BASELINE_YEARS: Tuple[int, int] = (2015, 2019)   # covariáveis baseline

    # --- Filtro canavieiro (§3.3) ---
    # Município entra se: share_cana > 5% OU area_cana > 500ha em 2015-2019,
    # OU município hospeda usina ANP
    FILTRO_SHARE_CANA: float = 0.05
    FILTRO_AREA_CANA_HA: float = 500.0

    # --- CRS (referência espacial) ---
    CRS_GEO: str = "EPSG:4326"        # geográfico
    CRS_PROJ: str = "EPSG:5880"       # SIRGAS 2000 Brazil Polyconic

    # --- Hipóteses e outcomes (§2 H1, H2 v2.2) ---
    # H1a primário: log_luc          (predição: nulo ou pequeno)
    # H1b secundário: carbono_solo   (predição: positivo)
    # H1c primário: cobertura_car_ativo + adesao_pra (SICAR)
    # H1c secundário: cobertura_veg_nativa (SICAR)
    # H2 primário: log_solos_manejados (predição: negativo conforme NEEA ↑)
    # H2 secundário: log_queima        (predição: negativo, mas com L13)
    OUTCOMES_AFOLU = (
        "log_luc",                  # H1a
        "carbono_solo",             # H1b — usar asinh
        "log_queima",               # H2 secundário (L13)
        "log_solos_manejados",      # H2 primário
        "log_residuos_florestais",  # auxiliar
    )
    OUTCOMES_H1C = (
        "cobertura_car_ativo",      # H1c-1
        "adesao_pra",               # H1c-2
        "cobertura_veg_nativa",     # H1c-3
    )

    # --- Transformações (§3.10) ---
    # log     → variável estritamente positiva sem zeros
    # log1p   → variável não-negativa com zeros possíveis
    # asinh   → variável que pode ter remoções (negativos), incluindo carbono_solo
    OUTCOME_TRANSFORM = {
        "luc":                  "asinh",   # SEEG inclui remoções
        "carbono_solo":         "asinh",   # fluxo líquido com remoções
        "queima":               "log1p",
        "solos_manejados":      "log",
        "residuos_florestais":  "log1p",
    }


# Instância única
PARAMS = Params()


# ============================================================================
# HELPERS DE PATH
# ============================================================================

def ensure_dir(p: Path) -> Path:
    """Cria diretório se não existir, retorna o path."""
    p.mkdir(parents=True, exist_ok=True)
    return p


def out_pre(filename: str) -> Path:
    """Caminho para um arquivo de auditoria em outputs_pre/, criando dir se necessário."""
    ensure_dir(OUTPUTS_PRE)
    return OUTPUTS_PRE / filename


def interim(filename: str) -> Path:
    """Caminho para um arquivo intermediário em data/interim/."""
    ensure_dir(DATA_INTERIM)
    return DATA_INTERIM / filename


def processed(filename: str) -> Path:
    """Caminho para um arquivo final em data/processed/."""
    ensure_dir(DATA_PROCESSED)
    return DATA_PROCESSED / filename


# ============================================================================
# INVENTÁRIO DE INPUTS RAW (para validação no notebook 00)
# ============================================================================

RAW_INPUTS = {
    "anp.cert_2022":   ANP_CERT_2022,
    "anp.cert_2025":   ANP_CERT_2025,
    "anp.cert_2026":   ANP_CERT_2026,
    "anp.neea":        ANP_NEEA,
    "ibge.pam":        IBGE_PAM_1612,
    "ibge.universo":   IBGE_UNIVERSO_CORE,
    "ibge.geojson":    IBGE_GEOJSON_CS,
    "seeg.go":         SEEG_FILES["GO"],
    "seeg.mg":         SEEG_FILES["MG"],
    "seeg.ms":         SEEG_FILES["MS"],
    "seeg.mt":         SEEG_FILES["MT"],
    "seeg.pr":         SEEG_FILES["PR"],
    "seeg.sp":         SEEG_FILES["SP"],
    "mapbiomas.panel": MAPBIOMAS_PANEL,
    "mapbiomas.raw":   MAPBIOMAS_RAW,
    "sicar.painel":    SICAR_PAINEL,
    "psm.baseline":    PSM_BASELINE_RAW,
}
