# ============================================================================
# Diagnósticos G.3.1 e G.3.2 — auditoria de cobertura PAM e MapBiomas
# Para rodar nos notebooks 04_pam e 05_mapbiomas (ou em célula separada
# que tenha os DataFrames raw em memória)
# ============================================================================

# ----------------------------------------------------------------------------
# G.3.1 — Os 7 munis MB-only têm gap REAL na PAM ou foram filtrados no pipeline?
# ----------------------------------------------------------------------------
# Hipótese: a coluna area_colhida_cana == NaN nos 7 munis em 2015-2019
#           é gap nativo (PAM não publicou) OU é filtro do pipeline.

geocodes_mb_only = [
    5210562,  # Itaguari/GO
    5219738,  # Santo Antônio de Goiás/GO
    3510302,  # Capela do Alto/SP
    3519055,  # Holambra/SP
    3525854,  # Jumirim/SP
    3537503,  # Pereiras/SP
    3540853,  # Pracinha/SP
]

# RODAR no notebook 04_pam, com df_pam_raw (PAM bruto, antes de qualquer filtro):
import pandas as pd

# Ajustar nome da variável conforme seu notebook
# df_pam_raw deve ter: geocode, ano, area_colhida_cana, valor_producao, etc.
audit_pam = (df_pam_raw
             .query("geocode in @geocodes_mb_only")
             .query("2015 <= ano <= 2019")
             .groupby(['geocode', 'municipio', 'uf'])
             .agg(
                 n_anos_observados=('area_colhida_cana', lambda x: x.notna().sum()),
                 n_anos_zero=('area_colhida_cana', lambda x: (x == 0).sum()),
                 n_anos_nan=('area_colhida_cana', lambda x: x.isna().sum()),
                 area_max=('area_colhida_cana', 'max'),
                 area_mean=('area_colhida_cana', 'mean'),
             )
             .reset_index())

print("=== G.3.1 — PAM raw para os 7 MB-only ===")
print(audit_pam.to_string(index=False))

# Interpretação:
# - Se n_anos_nan == 5 para todos: gap NATIVO da PAM (não publicado)
# - Se n_anos_zero == 5: PAM publicou zero (cana < threshold de coleta)
# - Se area_max > 500: PAM tem dado mas pipeline filtrou (BUG)
# - Mix: caso a caso


# ----------------------------------------------------------------------------
# G.3.2 — Os 24 munis PAM+ANP sem MB: cobertura MB existe ou é gap real?
# ----------------------------------------------------------------------------
# Hipótese: mb_share == NaN reflete falha de match no pipeline,
#           não limitação real do MapBiomas Col 10.1.

geocodes_pam_anp_no_mb = [
    5210000, 5210109, 5211909, 5213103, 5213707, 5216403, 5221601, 5222203,  # GO (8)
    3135050, 3136306, 3147006, 3166709, 3170503,                              # MG (5)
    5002001, 5003801, 5005707, 5006275, 5007935,                              # MS (5)
    5102637, 5105234, 5105622, 5107925,                                       # MT (4)
    4115200,                                                                   # PR (1)
    3522307,                                                                   # SP (1)
]

# RODAR no notebook 05_mapbiomas, com df_mb_raw (MB bruto, antes de qualquer filtro):
# df_mb_raw deve ter: geocode, ano, share_cana, area_cana_ha, etc.
audit_mb = (df_mb_raw
            .query("geocode in @geocodes_pam_anp_no_mb")
            .query("2015 <= ano <= 2019")
            .groupby(['geocode'])
            .agg(
                n_linhas=('share_cana', 'size'),
                n_share_notna=('share_cana', lambda x: x.notna().sum()),
                share_max=('share_cana', 'max'),
                share_mean=('share_cana', 'mean'),
                area_max_ha=('area_cana_ha', 'max'),
            )
            .reset_index())

print("\n=== G.3.2 — MB raw para os 24 PAM+ANP-sem-MB ===")
print(audit_mb.to_string(index=False))

# Diagnóstico crítico:
# - Mineiros/GO (5213103) e Campo Novo Parecis/MT (5102637) DEVEM ter share alto.
#   Se MB raw tem 0 linhas para esses geocodes: bug de match no pipeline (corrigir).
#   Se MB raw tem dado mas pipeline drop: bug de filtro.
#   Se MB raw realmente publicou share=0: improvável, requer investigação MB-equipe.

# Se o resultado for n_share_notna >= 1 e share_max > 0 para a maioria,
# então o pipeline assembly perdeu o match e §G.3.2 vira "bug de pipeline a corrigir".
# Se n_linhas == 0 para todos, é gap legítimo do produto MB Col 10.1.

# ----------------------------------------------------------------------------
# OUTPUT ESPERADO PARA INTEGRAR NA v2.3.2
# ----------------------------------------------------------------------------
# Salvar os 2 DataFrames como CSV para anexar na próxima sessão:

audit_pam.to_csv('outputs_audit/g3_1_pam_diagnostic.csv', index=False)
audit_mb.to_csv('outputs_audit/g3_2_mb_diagnostic.csv', index=False)
print("\nArquivos salvos para próxima rodada de auditoria.")
