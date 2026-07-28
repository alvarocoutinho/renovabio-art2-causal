# Manifesto de dados

Registro das fontes primárias, dos dados publicados e dos produtos versionados
do pacote de replicação.

| Dimensão | Escopo |
|---|---|
| Recorte espacial | Centro-Sul — SP, GO, MG, PR, MS, MT (sem ES) |
| Janela principal | 2015–2024 |
| Janela de robustez | 2012–2024 |
| Universo analítico | 842 municípios canavieiros |
| Municípios tratados | 194 (certificados pela ANP) |
| Estimador | Callaway–Sant'Anna doubly robust (CS-DR) |
| Pré-registro | v2.6 |

---

## 1. Dados publicados — `data/published/`

Datasets citáveis que acompanham o manuscrito, sob licença CC BY 4.0.

| Arquivo | Dimensões | Descrição | SHA-256 |
|---|---|---|---|
| `renovabio_psm_cross_section_v1.0.parquet` | 5.570 × 47 | Cross-section de covariáveis para pareamento | `7c3c12f161b6d335c90f5417cfb4e86e483cdf6e9f6a3f6c9f6d75d45154c216` |

> **Correção pendente.** O `README.md` que acompanha a versão distribuída desses
> dados declara dimensões incorretas (~2.018 e ~10.946 linhas). Os valores
> corretos são os da tabela acima.

---

## 2. Tabelas de resultado — `outputs/tables/`

Produtos desta pesquisa, sob licença CC BY 4.0. Sustentam os números do
manuscrito. Todas versionadas.

| Arquivo | Dimensões | Notebook | SHA-256 |
|---|---|---|---|
| `att_b4m5_dose_response.csv` | 5 × 10 | `11g` | `b5ff28abf5f44db35f3606a23f273e395d8aedd49e1c809d09be1f65ddd769f1` |
| `att_b4m5_event_por_tercil.csv` | 27 × 11 | `11g` | `7da88ec303ca969af9df78c1025464e39135040310132372982fd0cb46fe3075` |
| `att_b4m5_por_tercil.csv` | 15 × 10 | `11g` | `2fafb28a5bd1632dcb3ca1712e8a6306c5af5b25c62b3f26e3048c67c226a147` |
| `att_canais_config.csv` | 1 × 21 | `11d` | `afa14601924fcb8f707d4034f598ea8124fa798fd0f7c6a0c85b1873925c664f` |
| `att_canais_eventstudy.csv` | 54 × 7 | `11d` | `e1e8fed1f19255068fc194ceabde3bdb766ca33f23fd27eec299cd69721cc933` |
| `att_canais_main.csv` | 16 × 8 | `11d` | `1e7ea4cdb91365950cf1e55bc4351b2a035c141dc7af90e3c700dc43316a7198` |
| `att_canais_significancia_5pct.csv` | 16 × 8 | `11d` | `1df0a55cd4aa3a4927ad0fd80e67a3cee209ef0d7378bebb2318f3a3834a2d97` |
| `att_canais_verificacao.csv` | 2 × 8 | `11d` | `9d7413eb6d76dcbffdfcaa71aa0cbfac85865c6bafdcd7ede920e3f00c85ad00` |
| `att_derived_eventstudy.csv` | 26 × 4 | `11c` | `37a5868bceec1614dc6ac1878e371521c3ff4523bbdb9f2bdc52e052ebdbc1f6` |
| `att_derived_outcomes.csv` | 12 × 8 | `11c` | `ccdb0f980677dfc134918cb9bdb5b6be6c87f60c8e7eb1946e54776c645e94b1` |
| `att_substituicao_config.csv` | 1 × 29 | `11e` | `bc7e7b6f74fa0925b7b77ed797c4aa63e03da22d4826509faaf42bb57ee1e279` |
| `att_substituicao_consolidado.csv` | 40 × 12 | `11e` | `49a6e9c3fcc6c13d7ce35c9c99912135a9c4de4bd0fbad42d78a8228fda6c73f` |
| `att_substituicao_mapbiomas.csv` | 24 × 8 | `11e` | `e46cbb300f5fa23b7ed1ecd9077eb9370dbb057c992a399717de2087da9bffaa` |
| `att_substituicao_pam.csv` | 16 × 8 | `11e` | `f9eb7003d0687aedc015a56636c95f0423b8baa895ce57999e5b13156d59677c` |
| `att_t1_bacon.csv` | 5 × 4 | `11a` | `96d4d0ed3eaed33110a3cd3b1bf3f1fff1205f9207f3404aedf79d0420c6d4e4` |
| `att_t1_eventstudy_luc.csv` | 16 × 6 | `11a` | `715997fd36fef3048dfc97f540818588d5f3eac94b62473090fbaeda509af0dc` |
| `att_t1_main.csv` | 30 × 8 | `11a` | `58bbb460d91f54a070fe5d8b6d91a94d02e286c0231c54b00a3bc5a9f1478a81` |
| `att_t2t3_eventstudy_luc.csv` | 60 × 7 | `11b` | `0a257a4d285c698773b56194f8529cba324d6060cbd9e8d3719b45346f06f39e` |
| `att_t2t3_main.csv` | 120 × 12 | `11b` | `e58cdd0b73e660ef4d7160a158a613b348fc7a0fb676d8209733bac42d24e63f` |
| `b4m5_tercil_info.csv` | 1 × 11 | `11g` | `591476759734a6f6d795a946bbaaf39b5e5e11c519a0dc90d8bb1426221ed662` |
| `b4m7_balanco_co2eq.csv` | 194 × 8 | `11h` | `57304d36057dda5e47e505716190fbb70529d423230e942b69e3129986ea1097` |
| `b4m7_balanco_co2eq_ar6.csv` | 194 × 8 | `11h` | `ac757faf4f561d91dba47d79d4758aafc1b6584c7e1c1fcd7b16522259f53e0b` |
| `b4m8_intensidade_carbono.csv` | 193 × 8 | `11h` | `096ba05f2c76d8eb1fc839b2c30396f9e743c444560ea6e629a675bd6a4cd4ca` |
| `b4m8_robustez_decomposicao.csv` | 193 × 14 | `11h` | `a1d4ffb7d4852cd5a4638920046691cab9326b752d3722afabb92cc4e7ff4423` |
| `b4m8_robustez_por_coorte.csv` | 5 × 11 | `11h` | `e100e6bc64968f25437cc440e5c2f5f00c5c8fdf12e2176bc26837174003a1d5` |
| `event_study_consolidado.csv` | 180 × 9 | `11f` | `d32ff07d82e9f4b92b52e9034b8e336a6b699f07a2fd2fc47c30db7432478cfe` |
| `event_study_resumo.csv` | 18 × 19 | `11f` | `42751cf6928829d4b388575ed64778fa2797276ce472e30e84a9c325cba332eb` |
| `pretrend_test_consolidado.csv` | 18 × 7 | `11f` | `1ca5911f071e9425f651710a6a645c9d08533e7989db01fdca5f93f246d7d343` |
| `psm_balance_smd.csv` | 35 × 5 | `10` | `fab1035dc9c5ce2f134b5d9d4e7e34a2a65d9a1d51e6d7828216e8217d9bb6df` |
| `psm_diagnostics.csv` | 8 × 6 | `10` | `c3349c543d0104df0b31e0e6c564d2e270901a6896988b2e5d3367d10b58a904` |
| `psm_pscores_weights.csv` | 842 × 26 | `10` | `5762e3629ec02db5c03abfb4ec9e768fa25c428b38b2c30cde6a475a49963ed2` |
| `psm_support_masks.csv` | 842 × 34 | `10` | `addbf6fdafcc3a14f52f01232f8a76f81de6c7beab8d4723587183f3bfe3bc15` |
| `psm_support_summary.csv` | 32 × 9 | `10` | `b3f4ef24e82e172fcc02aae3c41dd6f20c2eb7fb8cb91b74a7fac3a09cc78e02` |

### `outputs/tables/diagnostico_solos/`

Diagnóstico do canal de solos manejados — único canal com efeito conjunto
significativo após correção FDR.

| Arquivo | Dimensões | SHA-256 |
|---|---|---|
| `arvore_solos_manejados_nivel_A.csv` | 9 × 6 | `fd9b32d8522c5de1a5a4cb7805055a8e4ae7e9c41f0a55c3f2d3c4a33a71ecd1` |
| `arvore_solos_manejados_nivel_B.csv` | 33 × 6 | `2c9d5ea7b9cf01721276af7092fbc5456b3bcb20da640dd011136579cab13bd3` |
| `arvore_solos_manejados_nivel_C.csv` | 33 × 7 | `7580a195c06b91c651ff0dcb12e5d75c8f032e1d070a354578848a42ec17fcf1` |
| `correlacao_intra_municipio.csv` | 1973 × 4 | `66a65efffb12130ea138f43fbbe229caf419987679a6d095228eb339712beffb` |
| `share_cana_atribuivel_municipio.csv` | 2369 × 7 | `f1cedbf6ebbcc71a82ec84af9dd505a80888f966d50eb193dfec9834e551503f` |
| `solos_cana_atribuivel_municipio_ano.csv` | 30797 × 8 | `e4c929b16bb1b30edca9d6f194f5391866e09906bdc0c13bf76108b5ebfe9344` |

> **Proveniência incompleta.** Nenhum notebook ou módulo deste repositório gera
> os seis arquivos acima. Foram produzidos por rotina externa ao pacote. O código
> correspondente deve ser incorporado, ou a origem declarada explicitamente,
> antes do release definitivo.

Verificação:

```bash
find outputs/tables data/published -type f -exec sha256sum {} \;
```

---

## 3. Fontes primárias — não redistribuídas

Dados abertos de instituições públicas, sujeitos às licenças de seus provedores.
Não versionados: o volume bruto excede o praticável em controle de versão, e os
produtos das Seções 1 e 2 já permitem verificar os resultados.

| # | Órgão | Conteúdo | Arquivo esperado em `data/raw/` | URL | Data de acesso | Versão | SHA-256 | Licença |
|---|---|---|---|---|---|---|---|---|
| 1 | ANP | Certificados aprovados (corte 2022-02-22) | `anp/certificados-aprovados.xlsx` | https://www.gov.br/anp/ | `PREENCHER` | — | `PREENCHER` | Dados abertos |
| 2 | ANP | Certificados aprovados (corte 2023-10-09) | `anp/certificados-aprovados-producao_2025.xlsx` | idem | `PREENCHER` | — | `PREENCHER` | Dados abertos |
| 3 | ANP | Certificados aprovados (corte 2026-04-17) | `anp/certificados-aprovados-producao_2026.xlsx` | idem | `PREENCHER` | — | `PREENCHER` | Dados abertos |
| 4 | ANP | NEEA consolidado por usina | `anp/Usinas_NEEA_consolidado.csv` | idem | `PREENCHER` | — | `PREENCHER` | Dados abertos |
| 5 | SEEG | Emissões municipais — GO | `seeg/ar6 - go.csv` | https://seeg.eco.br/ | `PREENCHER` | AR6, Coleção `PREENCHER` | `PREENCHER` | CC BY-SA (confirmar) |
| 6 | SEEG | Emissões municipais — MG | `seeg/ar6 - mg.csv` | idem | `PREENCHER` | idem | `PREENCHER` | idem |
| 7 | SEEG | Emissões municipais — MS | `seeg/ar6 - ms.csv` | idem | `PREENCHER` | idem | `PREENCHER` | idem |
| 8 | SEEG | Emissões municipais — MT | `seeg/ar6 - mt.csv` | idem | `PREENCHER` | idem | `PREENCHER` | idem |
| 9 | SEEG | Emissões municipais — PR | `seeg/ar6 - pr.csv` | idem | `PREENCHER` | idem | `PREENCHER` | idem |
| 10 | SEEG | Emissões municipais — SP | `seeg/ar6 - sp.csv` | idem | `PREENCHER` | idem | `PREENCHER` | idem |
| 11 | IBGE | PAM tabela 1612 | `ibge/tabela1612.csv` | https://sidra.ibge.gov.br/tabela/1612 | `PREENCHER` | — | `PREENCHER` | Dados abertos |
| 12 | IBGE | Universo core 6 UFs | `ibge/01_universo_core_6ufs.csv` | https://www.ibge.gov.br/ | `PREENCHER` | — | `PREENCHER` | Dados abertos |
| 13 | IBGE | Malha municipal Centro-Sul | `ibge/centro_sul.geojson` | https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais.html | `PREENCHER` | Ano `PREENCHER` | `PREENCHER` | Dados abertos |
| 14 | MapBiomas | Painel municipal-ano pronto | `mapbiomas/mapbiomas_municipal_year_panel_ready.csv` | https://brasil.mapbiomas.org/ | `PREENCHER` | **Coleção 10.1** | `PREENCHER` | CC BY-SA 4.0 |
| 15 | MapBiomas | Estatísticas de cobertura (backup) | `mapbiomas/MAPBIOMAS_BRAZIL-COVERAGE_STATISTICS-COL.10.1-….csv` | idem | `PREENCHER` | **Coleção 10.1** | `PREENCHER` | CC BY-SA 4.0 |
| 16 | IBGE / Atlas Brasil / IPEA | Covariáveis socioeconômicas de baseline | `psm_baseline/base_psm_integrada_raw.csv` | `PREENCHER` | `PREENCHER` | `PREENCHER` | `PREENCHER` | Dados abertos |

> **Share-alike.** MapBiomas e SEEG podem impor compartilhamento pela mesma
> licença aos produtos derivados. Verificar antes do release definitivo.

> **Revisão retroativa.** SEEG, PAM e MapBiomas revisam séries históricas entre
> edições. O registro da coleção e do hash é o que permite distinguir uma falha
> de replicação de uma atualização da fonte.

---

## 4. Fontes descartadas no curso da pesquisa

| Fonte | Situação |
|---|---|
| SICAR | Prevista no Plano de Gestão de Dados original e no pré-registro (desfechos da hipótese H1c). Descartada por inadequação da unidade de análise e por envolver dados pessoais de titulares de imóveis rurais (LGPD). A decisão é anterior e independente dos resultados obtidos para H1a, H1b e H2. Ver a seção *Pré-registro e hipóteses* do README. |

---

## 5. Dados intermediários — não versionados

`data/interim/` guarda produtos regeneráveis (camadas ANP, SEEG, PAM, MapBiomas,
painéis montados, `psm_baseline_clean.csv`). Não versionados por serem
reconstruíveis a partir das fontes primárias.

**Tabelas de resultado não moram em `data/interim/`** — estão em
`outputs/tables/`, conforme a Seção 2.
