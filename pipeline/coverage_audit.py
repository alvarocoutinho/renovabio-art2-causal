"""
pipeline.coverage_audit
========================
Auditoria de cobertura município × canal × ano antes do balanceamento
do painel SEEG. Resolve a fricção F3 que você marcou como "mais importante
que o DiD de fato".

Status: PLACEHOLDER — implementação após seeg.py e mapbiomas.py.

Por que este módulo existe
--------------------------
O legacy fazia `df.fillna(0.0)` cego no balanceamento do painel SEEG.
Isso estava errado em ~85% dos casos de carbono_solo (ver §3.10 v2.2).

A diferença crítica:
- Município SEM CANA × canal QUEIMA_CANA → 0 é correto (nunca houve cana).
- Município COM CANA × canal QUEIMA_CANA com NaN → bug de cobertura SEEG,
  zerar cria viés.

Esta camada cruza:
- Universo core (2.363 munis × 13 anos = 30.719 cells)
- Status canavieiro (do MapBiomas pré-2020 + PAM)
- Cobertura observada no SEEG por canal

E classifica cada célula em 4 estados:

| Status canavieiro | SEEG observado | Classificação           | Tratamento  |
|-------------------|----------------|-------------------------|-------------|
| Sem cana          | NaN            | ZERO_LEGITIMO           | fillna(0)   |
| Sem cana          | Observado      | INESPERADO              | investigar  |
| Com cana          | NaN            | LACUNA_SUSPEITA         | investigar  |
| Com cana          | Observado      | OK                      | usar valor  |

Inputs
------
- crosswalk universal (universo de 30.719 cells)
- mapbiomas_panel.csv (status canavieiro pré-2020)
- pam_cana_long.csv  (área cana cross-validação)
- seeg_outcomes_balanced.csv (cobertura observada por canal)

Outputs (outputs_pre/)
-----------------------
- coverage_matrix_{canal}.csv (uma por canal AFOLU)
  Colunas: geocode, ano, status_cana_baseline, seeg_observed, classificacao

Outputs (data/processed/)
-------------------------
- seeg_outcomes_audited.csv → painel pronto, com flag de classificação
  por célula. Modelagem usa flag para decidir se aceita 0 ou NaN.

Decisões metodológicas
----------------------
- Status canavieiro pré-2020 = baseline (média 2015-2019 de share_cana e
  area_cana via MapBiomas + PAM).
- Threshold de "com cana" = mesmo do filtro canavieiro (§3.3):
    share_cana > 5% OU area_cana > 500 ha em algum ano pré-2020.

Funções (a implementar)
-----------------------
- build_coverage_matrix(crosswalk, mapbiomas, pam, seeg) -> pd.DataFrame
- classify_cell(row) -> str
- summarize_audit(matrix) -> pd.DataFrame  # contagens por classificação
- apply_audit_rules(seeg_panel, matrix) -> pd.DataFrame
"""

from __future__ import annotations
