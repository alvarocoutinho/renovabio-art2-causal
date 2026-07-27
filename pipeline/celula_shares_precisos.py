# ============================================================================
# Célula avulsa — extração PRECISA dos shares (4 decimais) para v2.3.9
# Rodar no Colab APÓS o notebook 04b (reusa `panel` em memória).
# Cole numa célula nova ao final do 04b_seeg_subcanais.ipynb.
# ============================================================================

SUBCANAIS_SOLOS = ("res_cana", "org_cana", "fert_n",
                   "calagem", "res_outros", "res_minor")

anos_main = list(range(PARAMS.YEAR_MIN_MAIN, PARAMS.YEAR_MAX_MAIN + 1))  # 2015-2024
pm = panel[panel['ano'].isin(anos_main)]

# Soma total do solos_pipeline (= soma de todos os sub-canais)
tot = pm[list(SUBCANAIS_SOLOS)].sum().sum()

print("Shares definitivos dos sub-canais (CS 2015-2024) — 4 decimais")
print("=" * 60)
print(f"{'sub-canal':<14}{'soma tCO2e':>18}{'share':>12}")
print("-" * 60)
shares = {}
for c in SUBCANAIS_SOLOS:
    s = pm[c].sum()
    share = s / tot if tot > 0 else 0.0
    shares[c] = share
    print(f"{c:<14}{s:>18,.1f}{share:>11.4f}")
print("-" * 60)
print(f"{'TOTAL':<14}{tot:>18,.1f}{sum(shares.values()):>11.4f}")
print()

# Bloco pronto para colar na v2.3.9 (formato denominadores §6.5)
print("=== Para os denominadores do critério M (§6.5) ===")
print(f"  res_cana   = {shares['res_cana']:.4f}  (era 0,053)")
print(f"  org_cana   = {shares['org_cana']:.4f}  (era 0,041)")
print(f"  fert_n     = {shares['fert_n']:.4f}  (era 0,273)")
print(f"  calagem    = {shares['calagem']:.4f}  (era 0,242)")
print()
print("=== Para a coluna '% do pipeline' da tabela §3.10.2 ===")
for c in SUBCANAIS_SOLOS:
    print(f"  {c:<12} {100*shares[c]:.1f}%")

# Salva para anexar ao pré-registro como evidência rastreável
import pandas as pd
df_shares = pd.DataFrame([
    {"sub_canal": c,
     "soma_tCO2e": pm[c].sum(),
     "share": shares[c],
     "share_pct": round(100 * shares[c], 2)}
    for c in SUBCANAIS_SOLOS
])
df_shares.to_csv(out_pre("seeg_subcanais_shares_definitivos_v239.csv"),
                 index=False)
print("\n→ salvo em outputs_pre/seeg_subcanais_shares_definitivos_v239.csv")
