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
Distribuídos em CSV (UTF-8, separador `,`), formato aberto e adequado à
preservação de longo prazo.

| Arquivo | Dimensões | Descrição | SHA-256 |
|---|---|---|---|
| `renovabio_psm_cross_section_v1.0.csv` | 5.570 × 47 | Cross-section de covariáveis ex-ante para pareamento | `9ceb23e5e19f2ea17fff72b175d70009f1aa2b1beae6a425713dbf21da861ab2` |
| `renovabio_outcomes_panel_v1.0.csv` | 8.420 × 22 | Painel longo de desfechos de emissão | `d2f5bac066707f6c9c2357a8f52a3aea8fd465371fd5e47a72c3a801f24d4c1a` |
| `CODEBOOK_PSM_v1.0.md` | — | Codebook do cross-section | `9121300a2889a83a2843cf0da5ead131510b24ec510e7422c4509762e6b327df` |
| `CODEBOOK_PANEL_v1.0.md` | — | Codebook do painel | `dc9da4ac1ccb43b74711c8022935f05efa05678c4d88e2606db19262db133493` |
| `README.md` | — | Documentação dos datasets publicados | `ab064a74f16a021c0cba6694f4aec70569003913ea11501aabd321e267d326fe` |

Verificação:

```bash
sha256sum data/published/*
```

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

Todos os arquivos foram acessados e verificados em **2026-07-28**.

Verificação:

```powershell
Get-ChildItem -Recurse data\raw -File | Get-FileHash -Algorithm SHA256
```

### 3.1 ANP — certificação RenovaBio

A ANP publica apenas a versão corrente da tabela de certificados aprovados; as
versões anteriores não permanecem acessíveis no portal. Os três arquivos abaixo
foram obtidos a partir de instantâneos arquivados no Internet Archive. Esse
procedimento é o que torna verificável a construção das coortes de tratamento,
uma vez que a data da primeira certificação de cada usina não é reconstituível a
partir da tabela corrente.

| # | Arquivo em `data/raw/anp/` | SHA-256 |
|---|---|---|
| 1 | `certificados-aprovados.xlsx` | `332e25a1fb42a918d4159350b451d03ef13443b7a41df38cedda06e1dab6e629` |
| 2 | `certificados-aprovados-producao_2025.xlsx` | `6ea065cc780e01d4f75355c492eac140dc1807289840aa83b2c876cf0454a958` |
| 3 | `certificados-aprovados-producao_2026.xlsx` | `13a8761ccd070ac141b7f17f6dbac25622f5dfc11af54b02516ecc1d540c5335` |
| 4 | `Usinas_NEEA_consolidado.csv` | `a8f5798f2dc2aab833eb32712d4f7bbf5c90eaa3257ab3e5c19a195de017887c` |

**Instantâneos utilizados** (Internet Archive):

- https://web.archive.org/web/20210603213454/https://www.gov.br/anp/pt-br/assuntos/renovabio/certificacoes/certificados-aprovados.xlsx
- https://web.archive.org/web/20231219141824/https://www.gov.br/anp/pt-br/assuntos/renovabio/arq/certificacoes/certificados-aprovados-producao.xlsx
- https://web.archive.org/web/20260216004803/https://www.gov.br/anp/pt-br/assuntos/renovabio/arq/certificacoes/certificados-aprovados-producao.xlsx

**Datas de corte declaradas**, conforme `DATA_CORTE` em `pipeline/config.py`,
usadas para datar as coortes de tratamento:

| Arquivo | Data de corte |
|---|---|
| `certificados-aprovados.xlsx` | 2022-02-22 |
| `certificados-aprovados-producao_2025.xlsx` | 2023-10-09 |
| `certificados-aprovados-producao_2026.xlsx` | 2026-04-17 |

> As datas de corte e as datas de captura dos instantâneos são registros
> independentes. A verificação de integridade dos arquivos deve ser feita pelos
> hashes acima.

O `Usinas_NEEA_consolidado.csv` foi obtido diretamente em https://www.gov.br/anp/.

### 3.2 SEEG — emissões municipais

| Campo | Valor |
|---|---|
| Edição | **SEEG Setor Agropecuário 1970–2024, Versão 13 — janeiro de 2026** |
| Métrica de GWP | AR6 |
| Provedor | Observatório do Clima / Imaflora |
| URL | https://seeg.eco.br/ |
| Licença | CC BY-SA (confirmar termos vigentes) |

| # | UF | Arquivo em `data/raw/seeg/` | SHA-256 |
|---|---|---|---|
| 5 | GO | `ar6 - go.csv` | `27aa052ffacc097fdeba9c30bda0164a4fa699988361050300b7041c5846fb10` |
| 6 | MG | `ar6 - mg.csv` | `77c9502bcf1421e710a7f8cd5308ca8a42a6793bd8c3a733e7230ad6c916a390` |
| 7 | MS | `ar6 - ms.csv` | `48abe855dc29bf4c67d77fe2bde98efac2991fc621b1db8fc1ce1c5cc6913641` |
| 8 | MT | `ar6 - mt.csv` | `3b57e7ad0878a6297d6fc8ba5494436ada00f405e2e0d720eff4676f7218fe25` |
| 9 | PR | `ar6 - pr.csv` | `712d795d996f5f365f302000b282d39e33264107c05a1cab02158b6ff218a385` |
| 10 | SP | `ar6 - sp.csv` | `NÃO LOCALIZADO` |

> **`ar6 - sp.csv` não foi localizado** na verificação de 2026-07-28. São Paulo
> concentra a maior parte do universo canavieiro analisado; o arquivo deve ser
> recuperado e seu hash registrado antes do release definitivo.

### 3.3 IBGE

| # | Conteúdo | Arquivo em `data/raw/ibge/` | Referência | SHA-256 |
|---|---|---|---|---|
| 11 | PAM — tabela 1612 | `tabela1612.csv` | 2012–2026 | `4c419a69e5e1ddc317b4fb0b7599756f7750efc3921701e3643f7be9d93c7111` |
| 12 | PAM — recorte cana, soja, algodão e milho | `tabela1612 - cana, soja, algodão e milho.csv` | 2012–2026 | `4ca8f47a8b94fb6d1cd2d2d77537ffacc047df92a0b70b681cf0bdd9d3a634c8` |
| 13 | Universo core, 6 UFs | `01_universo_core_6ufs.csv` | — | `a08e3b1c033690149bb2b72f5b916d74f0595fbf57897553d6532efba768a4a8` |
| 14 | Malha municipal Centro-Sul | `centro_sul.geojson` | **Ano de referência 2022** | `PREENCHER` |

PAM: https://sidra.ibge.gov.br/tabela/1612 ·
Malhas: https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais.html

> A malha municipal não foi localizada em `data/raw/ibge/` na verificação de
> 2026-07-28. É reconstruível a partir das malhas territoriais do IBGE
> (ano de referência 2022), restringidas aos municípios do crosswalk.

### 3.4 MapBiomas

URL: https://brasil.mapbiomas.org/ · **Coleção 10.1** · Licença: CC BY-SA 4.0

| # | Conteúdo | Arquivo em `data/raw/mapbiomas/` | SHA-256 |
|---|---|---|---|
| 15 | Painel municipal-ano pronto | `mapbiomas_municipal_year_panel_ready.csv` | `63c7334e247c7b9fbec6e13b69f71a42c869ef12d45da4ea06a706f76b05afc9` |
| 16 | Estatísticas de cobertura (backup) | `MAPBIOMAS_BRAZIL-COVERAGE_STATISTICS-COL.10.1-MUNICIPALITIES_STATES_BIOMES.csv` | `913352cf256305485659e6e73f36b07311c1d521e40cdb348472a468cb62f0f3` |

### 3.5 Baseline socioeconômico ex-ante

| # | Arquivo em `data/raw/psm_baseline/` | SHA-256 |
|---|---|---|
| 17 | `base_psm_integrada_raw.csv` | `cd1bbcb153b09b3af58e9e9d45d38ab6ce3530a656219aa47c3f674a181e1973` |

Base integrada de covariáveis ex-ante, em 17 blocos temáticos. Ano de referência
predominante: **2017**. Composição por provedor:

| Bloco | Conteúdo | Provedor | URL |
|---|---|---|---|
| 0 | Identificadores territoriais | IBGE | https://www.ibge.gov.br/ |
| 1 | PIB municipal e valor adicionado por setor | IBGE | https://www.ibge.gov.br/ |
| 2 | População estimada (2017) | IBGE | https://www.ibge.gov.br/ |
| 3 | Participação das classes de uso do solo | MapBiomas | https://brasil.mapbiomas.org/ |
| 4 | Área colhida, quantidade e valor da produção (2017) | IBGE / SIDRA | https://sidra.ibge.gov.br/ |
| 5–13 | Estrutura fundiária, ocupação, assistência técnica, maquinário, irrigação e financiamento | IBGE — Censo Agropecuário 2017 | https://sidra.ibge.gov.br/ |
| 14 | Bioma, desmatamento e vegetação natural | **INPE** | http://www.inpe.br/ |
| 15 | Área irrigada por cultura | ANA | https://www.gov.br/ana/ |
| 16 | Saneamento básico e população urbana | ANA | https://www.gov.br/ana/ |
| 17 | IVS, IDHM, esperança de vida e Gini | IPEA / PNUD — Atlas Brasil | http://www.atlasbrasil.org.br/ |

Dicionário completo, variável a variável: `data/DICIONARIO.md`.

> Este arquivo é compartilhado com o pacote de replicação do Artigo 1
> (`renovabio-art1-spatial`), onde consta com hash idêntico.

---

### Notas transversais

> **Share-alike.** MapBiomas (CC BY-SA 4.0) e SEEG podem impor compartilhamento
> pela mesma licença aos produtos derivados. Verificar antes do release
> definitivo.

> **Revisão retroativa.** SEEG, PAM e MapBiomas revisam séries históricas entre
> edições. O registro da edição e do hash é o que permite distinguir uma falha de
> replicação de uma atualização da fonte. No caso da ANP, o problema é mais
> severo: as versões anteriores da tabela de certificados deixam de estar
> disponíveis no portal, e sua recuperação depende de arquivamento externo
> (Seção 3.1).

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
