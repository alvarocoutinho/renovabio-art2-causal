"""
pipeline.normalize
==================
Helpers de normalização de strings, códigos IBGE e números no formato BR.

Convenção: funções deste módulo NÃO têm efeito colateral. Recebem entrada,
retornam saída limpa. Não leem disco, não salvam nada.

Por que esse módulo existe:
- Bases brasileiras misturam acentos, encoding latin-1/utf-8, "1.234,56" como
  número, geocode como float (5550308.0) ou string ("5550308") ou int.
- Sem normalização consistente, fazer merge entre fontes é uma fonte
  inesgotável de bugs silenciosos (município "São Paulo" vs "Sao Paulo" não
  bate, geocode 6 dígitos vs 7 dígitos não bate, etc).
- Toda lógica de chaveamento do pipeline depende dessas três funções.
"""

from __future__ import annotations
import re
import unicodedata
from typing import Iterable, Optional

import numpy as np
import pandas as pd


# ============================================================================
# STRINGS
# ============================================================================

def norm_str(x, upper: bool = True, ascii_only: bool = True) -> Optional[str]:
    """
    Normaliza string: remove acentos, apóstrofos e hifens, colapsa espaços,
    opcionalmente upper.

    A remoção de apóstrofos e hifens resolve discrepâncias entre fontes que
    representam D'Oeste / D'Água / nomes com hífen de formas diferentes
    (ex: SICAR escreve "DOESTE" sem apóstrofo enquanto IBGE/MapBiomas escreve
    "D'OESTE", e nomes hifenizados como "ARCO-ÍRIS" vs "ARCO IRIS").

    >>> norm_str("São Paulo")
    'SAO PAULO'
    >>> norm_str("Pirassununga / SP", upper=False)
    'Pirassununga / SP'
    >>> norm_str("D'OESTE")
    'DOESTE'
    >>> norm_str("ARCO-ÍRIS")
    'ARCO IRIS'
    >>> norm_str(None)
    None
    """
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    s = str(x).strip()
    if not s:
        return None
    s = re.sub(r"\s+", " ", s)
    s = s.replace("–", "-").replace("—", "-")
    # Remove apóstrofos (curly e straight) e converte hifens em espaço
    s = s.replace("'", "").replace("\u2019", "")
    s = s.replace("-", " ")
    # Recolapsa espaços após substituições
    s = re.sub(r"\s+", " ", s).strip()
    if ascii_only:
        s = unicodedata.normalize("NFKD", s)
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.upper() if upper else s


def strip_uf_suffix(x) -> Optional[str]:
    """
    Remove sufixo " - UF" ou " (UF)" de fim de string.

    >>> strip_uf_suffix("Ribeirão Preto - SP")
    'Ribeirão Preto'
    >>> strip_uf_suffix("Pirassununga (SP)")
    'Pirassununga'
    """
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    s = str(x).strip()
    s = re.sub(r"\s*-\s*[A-Z]{2}\s*$", "", s)
    s = re.sub(r"\s*\([A-Z]{2}\)\s*$", "", s)
    return s.strip()


# ============================================================================
# CÓDIGOS IBGE
# ============================================================================

def zfill_ibge(s, width: int = 7) -> pd.Series:
    """
    Normaliza geocode IBGE para string de N dígitos (default 7).

    Trata casos comuns:
    - float vazado: "5550308.0" → "5550308"
    - código 6 dígitos antigo: "550308" → "0550308" (zfill)
    - lixo não-numérico: removido por regex

    >>> zfill_ibge(pd.Series([3550308, "3550308.0", "3550308"]))
    0    3550308
    1    3550308
    2    3550308
    dtype: object
    """
    if not isinstance(s, pd.Series):
        s = pd.Series(s)
    ss = s.astype(str).str.strip()
    ss = ss.str.replace(r"\.0$", "", regex=True)
    ss = ss.str.replace(r"\D", "", regex=True)
    return ss.str.zfill(width)


def parse_uf_from_str(s) -> Optional[str]:
    """
    Extrai UF (2 letras maiúsculas) do fim de uma string.

    >>> parse_uf_from_str("Ribeirão Preto/SP")
    'SP'
    >>> parse_uf_from_str("Pirassununga (SP)")
    'SP'
    >>> parse_uf_from_str("Cidade sem UF")
    None
    """
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return None
    s = str(s).strip()
    m = re.search(r"[/\(\-]\s*([A-Z]{2})\s*\)?\s*$", s)
    return m.group(1) if m else None


# ============================================================================
# NÚMEROS NO FORMATO BR (vírgula decimal, ponto separador de milhar)
# ============================================================================

def num_br(s) -> pd.Series:
    """
    Converte série tipo BR ("1.234,56" / "0,33%" / "-") em float.

    Regras:
    - Remove "%" do final.
    - "." é separador de milhar e some.
    - "," vira ".".
    - Tokens de NA brasileiros (-, --, ..., NA, X) viram NaN.

    >>> num_br(pd.Series(["1.234,56", "0,33%", "-", "100"]))
    0    1234.56
    1       0.33
    2        NaN
    3     100.00
    dtype: float64
    """
    if not isinstance(s, pd.Series):
        s = pd.Series(s)
    ss = s.astype(str).str.strip()
    NA_TOKENS = {"", "nan", "None", "NULL", "NA", "N/A", "-", "--", "...", "..", "X"}
    ss = ss.where(~ss.isin(NA_TOKENS), other=np.nan)
    ss = (ss
          .str.replace(r"\s+", "", regex=True)
          .str.replace("%", "", regex=False)
          .str.replace(".", "", regex=False)   # separador de milhar
          .str.replace(",", ".", regex=False)) # decimal
    return pd.to_numeric(ss, errors="coerce")


# ============================================================================
# CHAVES COMPOSTAS
# ============================================================================

def build_muni_key(municipio: pd.Series, uf: pd.Series) -> pd.Series:
    """
    Constrói muni_key = MUNICIPIO_NORMALIZADO|UF.

    Esta é a chave canônica para fazer merge entre fontes que não têm geocode
    confiável (ANP, NEEA, SEEG-cidade-textual).

    >>> build_muni_key(pd.Series(["São Paulo", "Pirassununga"]), pd.Series(["SP", "SP"]))
    0       SAO PAULO|SP
    1    PIRASSUNUNGA|SP
    dtype: object
    """
    muni_norm = municipio.apply(norm_str)
    return muni_norm.astype(str) + "|" + uf.astype(str).str.upper()


# ============================================================================
# ENCODINGS / SEPARADORES (auto-detecção simples)
# ============================================================================

def detect_encoding(path) -> str:
    """
    Tenta UTF-8 primeiro, fallback para Latin-1.
    Retorna a primeira que funcionar (Latin-1 quase sempre funciona).
    """
    for enc in ("utf-8", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                f.read(8192)
            return enc
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return "latin-1"


def detect_sep(path, encoding: str = "utf-8") -> str:
    """
    Detecta separador (',' ou ';') olhando primeiras 2KB.
    Retorna o que aparece mais, com tie-break para ','.
    """
    with open(path, "r", encoding=encoding, errors="replace") as f:
        head = f.read(2048)
    n_comma = head.count(",")
    n_semi  = head.count(";")
    return ";" if n_semi > n_comma else ","
