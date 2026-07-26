# Experimento Real 01 — MEC Lab

## Memória longitudinal do Projeto Atlas

### Objetivo

Testar se o MEC Lab consegue acompanhar uma história de projeto ao longo do tempo
e recuperar corretamente: fato vigente, obsoleto, decisão, evidência, mudança,
conflito, próximo trabalho e ausência de evidência.

### Estrutura

```
experiments/exp-01/
├── README.md               # este arquivo
├── populate_phase_1.py     # Fase 1: decisão inicial (batch)
├── populate_phase_2.py     # Fase 2: problema observado (duplicação)
├── populate_phase_3.py     # Fase 3: mudança de decisão (fila persistente)
├── populate_phase_4.py     # Fase 4: estado atual (implementação parcial)
├── queries.json            # 20 consultas (12 obrigatórias + 8 parafraseadas)
├── gold_answers.json       # Gabarito criado ANTES da avaliação
├── run_experiment.py       # Orquestrador completo
├── REPORT.md               # Relatório final
└── RAW_RESULTS/            # Snapshots, métricas brutas, evidências
    ├── snapshot_phase_1.json
    ├── snapshot_phase_2.json
    ├── snapshot_phase_3.json
    ├── snapshot_phase_4.json
    ├── snapshot_final.json
    ├── phase_queries_phase_1.json
    ├── phase_queries_phase_2.json
    ├── phase_queries_phase_3.json
    ├── per_query_details.json
    ├── aggregate_metrics.json
    └── verdict.txt
```

### Execução

```bash
cd /d/memoria_teste
python experiments/exp-01/run_experiment.py
```

### Memórias por tipo

| Tipo       | Quantidade | IDs |
|------------|-----------|-----|
| Fact       | 4         | fact-atlas-obj, fact-atlas-impl, fact-atlas-risk, fact-atlas-next |
| Decision   | 2         | dec-atlas-batch (SUPERSEDED), dec-atlas-queue (ACTIVE) |
| Hypothesis | 2         | hyp-atlas-cap, hyp-atlas-replay |
| Evidence   | 3         | evi-atlas-bench, evi-atlas-log, evi-atlas-queue-bench |
| Learning   | 1         | lrn-atlas-idem |
| Episode    | 1         | epi-atlas-dup |
| Checkpoint | 4         | chk-atlas-01, chk-atlas-02, chk-atlas-03, chk-atlas-04 |
| Document   | 1         | doc-atlas-arch |

### Relações utilizadas

SUPPORTED_BY, CAUSED_BY, DERIVED_FROM, SUPERSEDES, CONTRADICTED_BY,
REFERENCES, SUMMARIZES, PART_OF

### Critérios de aprovação

1. Todos os 116 testes existentes continuam passando
2. Todos os 8 tipos de memória usados substantivamente
3. Decisão vigente supera a obsoleta nas consultas atuais
4. Decisão obsoleta continuar recuperável em consultas históricas
5. SUPERSEDES e obsolescência produzem conflito detectável
6. Próxima ação correta recuperada
7. Consulta sem evidência não produz resposta afirmativa inventada
8. Fake source rate = 0
9. Resultados reproduzíveis a partir dos artefatos versionados

### Regras do experimento

- Motor, pesos e thresholds NÃO foram alterados
- Datasets antigos e holdouts de auditoria NÃO foram acessados
- Nenhum hardcode por query-ID foi usado
- Gabarito foi criado ANTES da avaliação final
