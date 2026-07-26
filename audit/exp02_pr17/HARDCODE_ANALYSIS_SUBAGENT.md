# Análise de Hardcoding — Subagente Auditor (deleg_edef787e)

Este documento consolida a análise realizada por subagente auditor independente sobre os 5 scripts `populate_phaseN.py` (commit 0cb4ea06) confrontados com `queries.json` e `gold_answers.json`.

## Achado Central

Os scripts **declaram explicitamente em suas docstrings** que contaminam o conteúdo:

- `populate_phase_1.py`, linhas 5-6: *"Enriched contents: each memory's content field includes key vocabulary from the queries that should retrieve it, to maximize Jaccard lexical overlap with the search engine."*
- `populate_phase_2.py`, linha 3: *"Enriched contents for lexical overlap with queries."*
- `populate_phase_3.py`, linha 3: *"Enriched contents for lexical overlap."*
- `populate_phase_4.py`, linha 3: *"Enriched contents for lexical overlap."*
- `populate_phase_5.py`, linha 3: *"Idempotent. Enriched contents for lexical overlap."*

Esta é uma **confissão explícita** de que o conteúdo das memórias foi escrito para casar com queries específicas, comprometendo a independência entre dataset de memórias e dataset de avaliação.

## Per-phase Breakdown

### populate_phase_1.py
Memórias criadas: `fact-boreal-obj`, `dec-boreal-iot`, `evi-who-guidelines`, `chk-boreal-p1`, `doc-boreal-charter`.

Trechos suspeitos:
- **dec-boreal-iot** (atende q02, q16):
  - q02 = "Como o projeto **monitorava as temperaturas antes da mudança**?"
  - content: *"O projeto **monitorava as temperaturas desta forma antes da** mudanca para o sistema dual..."*
- **dec-boreal-iot**: *"Esta **decisao** de usar apenas **loggers IoT foi posteriormente abandonada**..."* — espelha q03/q17 ("a decisao inicial de usar apenas loggers IoT foi abandonada").
- **chk-boreal-p1**: *"Comparado com o checkpoint final, mostra **toda a evolucao** do projeto..."* — eco de q12 (delta checkpoints).
- **chk-boreal-p1** `active_decisions=["dec-boreal-iot"]` — hardcode de ID esperado em q02.
- **doc-boreal-charter** `constituent_ids=["fact-boreal-obj","dec-boreal-iot"]` — hardcode de ID esperado.

### populate_phase_2.py
Memórias criadas: `epi-transport-excursion`, `evi-logger-gap`, `hyp-battery-failure`, `lrn-battery-cold-degradation` (rascunho), `chk-boreal-p2`.

Trechos suspeitos:
- **epi-transport-excursion** (atende q03, q17):
  - content: *"Este episodio foi a **causa principal do abandono** da abordagem inicial com apenas loggers IoT."* — espelha q03 ("Por que a decisao... foi abandonada?") e q17 ("O que fez a equipe desistir...").
- **epi-transport-excursion**: *"O **palpite inicial** foi que as baterias falharam..."* — espelha q19 ("Qual foi o **palpite inicial** sobre o **apagao de dados**...").
- **hyp-battery-failure** content: *"A **hipotese inicial** do Projeto Boreal sobre o **apagao de dados** na rota..."* — espelha q05/q19.
- **hyp-battery-failure**: *"A **hipotese explicou as falhas nos dados** durante o transporte."* — espelha q05 ("Qual **hipotese explicou as falhas nos dados durante o transporte**?").
- Hardcodes de IDs: `supported_claims=["hyp-battery-failure"]` em evi-logger-gap; `origin_episode_ids=[epid]`, `evidence_ids=[evid]`; `active_decisions=["dec-boreal-iot"]` em chk-boreal-p2.

### populate_phase_3.py (commit 0cb4ea06)
Memórias criadas: `evi-lab-battery-test`, `hyp-battery-confirmed`, `lrn-battery-cold-degradation`, `fact-battery-threshold`, `doc-investigation-report`.

Trechos suspeitos:
- **evi-lab-battery-test** (atende q04/q18):
  - q04 = "Que **evidencia** demonstrou que as **baterias falham no frio extremo**?"
  - content: *"Teste de laboratorio... camara fria... demonstrou que as baterias falham no frio extremo..."*
- **hyp-battery-confirmed**:
  - q05 = "Qual **hipotese explicou as falhas nos dados** durante o transporte?"
  - content: *"esta **hipotese explicou as falhas nos dados durante o transporte**..."* (aparece NA versão commitada; o stash contém versão ainda mais literal).
- **lrn-battery-cold-degradation** (atende q06, q17):
  - q06 = "O que **aprendemos** sobre o uso de **baterias quimicas em temperaturas negativas**?"
  - content: *"O **aprendizado** principal do Projeto Boreal sobre **baterias quimicas em temperaturas negativas**..."*
  - q17 = "O que **fez a equipe desistir** dos sensores eletronicos que usavam pilhas?"
  - content: *"foi a razao principal que **fez a equipe desistir** dos sensores eletronicos que usavam pilhas."*
- **lrn-battery-cold-degradation**: *"A **licao** sobre **pilhas** em ambientes **gelados**..."* — espelha q20 ("Que **licao** tiramos sobre **pilhas** em ambientes **gelados**?").
- `doc-investigation-report` `constituent_ids=["epi-transport-excursion","evi-lab-battery-test","hyp-battery-confirmed"]`
- Mutação direta no final da função: `old_hyp.superseded_by=hid_conf`, `new_hyp.supersedes="hyp-battery-failure"` — configura cadeia de superseded que favorece q05.

### populate_phase_4.py
Memórias criadas: `dec-boreal-dual`, `evi-who-pqs-vvm`, `chk-boreal-p4`, `doc-dual-spec`.

Trechos suspeitos:
- **dec-boreal-dual** (atende q01, q11, q15):
  - q01 = "Qual abordagem esta **vigente** para o **monitoramento de temperatura** na cadeia fria?"
  - content: *"A **decisao vigente** do Projeto Boreal para **monitoramento de temperatura**..."*
  - q15 = "Que sistema de **vigilancia de temperatura** esta sendo usado agora?"
  - content: *"abordagem de **vigilancia de temperatura** resolve o conflito..."*
- **evi-who-pqs-vvm** (atende q13):
  - q13 = "O projeto tem **evidencia** de que os novos **indicadores quimicos funcionam**?"
  - content: *"certificacao WHO PQS... garante que os VVM sao confiaveis..."*
  - `supported_claims=["dec-boreal-dual"]` — hardcode.
- **doc-dual-spec** (atende q09, q23):
  - q09 = "Qual **documento descreve a arquitetura** do novo sistema de monitoramento?"
  - content: *"Especificacao Tecnica... descreve a arquitetura..."*
  - q23 = "documentacao do **plano de monitoramento atualizado**"
  - content: *"documentacao do **plano de monitoramento atualizado**..."*
  - `constituent_ids=["dec-boreal-dual","evi-who-pqs-vvm","fact-battery-threshold"]`
- **chk-boreal-p4** `active_decisions=["dec-boreal-dual"]`, `pending_items=["Aquisicao de 5000 VVM","Treinamento para leitura de VVM"]` — hardcodes.

### populate_phase_5.py
Memórias criadas: `chk-boreal-p5`, `lrn-staff-training-gap`, `fact-training-risk`, `fact-deployment-status`, `chk-boreal-p5-risco` (atualizado).

Trechos suspeitos:
- **lrn-staff-training-gap** (atende q14):
  - q14 = "Qual e o **bloqueio que impede a implantacao completa**?"
  - content: *"o **aprendizado sobre a lacuna de treinamento e o principal bloqueio que impede a implantacao completa**..."*
- **fact-training-risk** (atende q08, q22):
  - q08 = "Que **risco ainda pode atrasar** a implantacao?"
  - content: *"O principal **risco que ainda pode atrasar a implantacao** do Projeto Boreal..."*
  - q22 = "Existe algum **perigo** que ainda pode **melar a instalacao**?"
  - content/justification usa vocabulario equivalente: "risco principal", "atraso na aprovacao".
  - assertion: *"Risco principal: atraso no treinamento pode impactar 12.000 doses."*
- **chk-boreal-p5** (atende q07, q12, q14, q21):
  - q07 = "Qual e a **proxima acao prioritaria** do projeto?"
  - content: *"A **proxima acao prioritaria** e concluir o material de treinamento..."*
  - q12 = "O que **mudou entre o primeiro checkpoint e o estado atual**?"
  - content: *"mostra tudo que **mudou entre o primeiro checkpoint e o estado atual**..."*
  - q21 = "No que a equipe deveria **focar agora** para **avancar**?"
  - content: *"A equipe deve **focar agora** na aprovacao do treinamento para **avancar**."*
  - `deep_dive_refs=["doc-dual-spec","lrn-staff-training-gap","fact-training-risk"]` — aponta para IDs esperados em q08/q22/q14, criando relevancia secundaria.
  - `blockers=["Material de treinamento pendente de aprovacao","Treinamento presencial de 12 operadores nao agendado"]` — atende q14.
  - `next_allowed_action="Concluir e aprovar material de treinamento e agendar..."` — atende q07.

### Relação SUPERSEDES (rel-20)
- Criada explicitamente para satisfazer q11 ("Quais decisoes estao em conflito ou foram substituidas?") e subsidiar q01.
- `queries.json` q01 declara `"expected_conflicts": ["SUPERSEDES"]`.
- `queries.json` q11 declara `"expected_conflicts": ["SUPERSEDES","STATE_CONFLICT"]`.
- `gold_answers.json` q11 justificativa: *"A decisao dual SUPERSEDES a decisao original de IoT, que esta marcada como SUPERSEDED."*
- Implementacao tripla: (i) relacao SUPERSEDES em si; (ii) `dec-boreal-iot.decision_status = SUPERSEDED` (STATE_CONFLICT); (iii) re-aplicacao em phase_5 (`superseded_by`).

---

## Notas

1. O subagente confirmou os achados do auditor principal por inspeção textual independente.
2. Nenhum arquivo foi alterado durante a analisa.
3. A comparacao com a versao do stash (modificacao nao commitada em populate_phase_3.py) mostra que a iteracao de enriquecimento continuou apos o commit — a versao stashada adiciona literalmente "esta hipotese explicou as falhas nos dados durante o transporte" e "fez a equipe desistir dos sensores eletronicos que usavam pilhas", que sao frases exatas de q05 e q17.

_Análise preservada como evidência complementar da auditoria._