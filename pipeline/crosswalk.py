"""
pipeline.crosswalk
==================
Constrói o crosswalk universal das 6 UFs do Centro-Sul a partir do
universo core já validado (01_universo_core_6ufs.csv).

Inputs
------
- IBGE_UNIVERSO_CORE (data/raw/ibge/01_universo_core_6ufs.csv)

Outputs
-------
- data/interim/crosswalk_centrosul.csv
  Colunas: geocode, municipio, uf, municipio_uf, cidade_uf_seeg, muni_key

Decisões
--------
- 6 UFs: SP, GO, MG, PR, MS, MT (sem ES) — §3.2 v2.2
- Total: 2.363 municípios = soma exata IBGE
- 3 chaves expostas: geocode (chave primária), muni_key, cidade_uf_seeg
"""

from __future__ import annotations
import pandas as pd

from pipeline.config import (
    PARAMS, IBGE_UNIVERSO_CORE, interim,
)
from pipeline.normalize import zfill_ibge, build_muni_key


# Total esperado por UF (referência IBGE oficial 2022)
IBGE_REF_COUNTS = {
    "MG": 853, "SP": 645, "PR": 399, "GO": 246, "MT": 141, "MS": 79
}


def load_universo_core() -> pd.DataFrame:
    """Lê o universo core já validado, com tipagem correta de geocode."""
    df = pd.read_csv(IBGE_UNIVERSO_CORE, dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]
    return df


def build_crosswalk() -> pd.DataFrame:
    """
    Constrói o crosswalk canônico das 6 UFs Centro-Sul.

    Colunas de saída:
    - geocode         : str, 7 dígitos zfill — chave primária
    - municipio       : str, nome com acentos preservados
    - uf              : str, 2 letras
    - cidade_uf_seeg  : str, formato literal SEEG "Município (UF)"
    - muni_key        : str, normalizado MUNICIPIO|UF (sem acentos, upper)

    Returns
    -------
    pd.DataFrame com 2.363 linhas.
    """
    df = load_universo_core()

    # Garantir geocode em 7 dígitos
    df["geocode"] = zfill_ibge(df["geocode"], width=7)

    # Restringir a 6 UFs (defesa: pode ter colunas extras ou linhas a mais)
    df = df[df["uf"].isin(PARAMS.UFS_CORE)].reset_index(drop=True)

    # Construir chaves derivadas canônicas
    df["cidade_uf_seeg"] = df["municipio"].astype(str) + " (" + df["uf"] + ")"
    df["muni_key"] = build_muni_key(df["municipio"], df["uf"])

    # Reordenar (nota: dropamos municipio_uf legacy do universo_core para evitar
    # confusão — ele vinha com formato "Município/UF" do IBGE, mas usamos
    # cidade_uf_seeg como chave canônica externa)
    cols_out = ["geocode", "municipio", "uf", "cidade_uf_seeg", "muni_key"]
    df = df[cols_out].drop_duplicates(subset="geocode").reset_index(drop=True)

    return df


def validate_crosswalk(df: pd.DataFrame) -> dict:
    """
    Valida o crosswalk em 4 dimensões:
    1. Total de linhas bate com IBGE (2.363).
    2. Contagem por UF bate com IBGE.
    3. geocode é único.
    4. muni_key é único.

    Returns
    -------
    dict com chaves: ok (bool), n_total, by_uf, errors (list).
    """
    errors = []

    # 1. Total
    n_expected = sum(IBGE_REF_COUNTS.values())
    if len(df) != n_expected:
        errors.append(
            f"total: obs={len(df)}, esperado={n_expected}, "
            f"diff={len(df) - n_expected:+d}"
        )

    # 2. Por UF
    by_uf = df["uf"].value_counts().to_dict()
    for uf, n_ref in IBGE_REF_COUNTS.items():
        n_obs = by_uf.get(uf, 0)
        if n_obs != n_ref:
            errors.append(
                f"{uf}: obs={n_obs}, IBGE={n_ref}, diff={n_obs - n_ref:+d}"
            )

    # 3. geocode único
    n_dup_geo = df["geocode"].duplicated().sum()
    if n_dup_geo > 0:
        errors.append(f"{n_dup_geo} geocodes duplicados")

    # 4. muni_key único
    n_dup_key = df["muni_key"].duplicated().sum()
    if n_dup_key > 0:
        errors.append(f"{n_dup_key} muni_keys duplicadas")

    return {
        "ok": len(errors) == 0,
        "n_total": len(df),
        "by_uf": by_uf,
        "errors": errors,
    }


def save_crosswalk(df: pd.DataFrame, name: str = "crosswalk_centrosul.csv") -> None:
    """Salva o crosswalk em data/interim/."""
    out_path = interim(name)
    df.to_csv(out_path, index=False)
    print(f"✓ Salvo: {out_path}")
