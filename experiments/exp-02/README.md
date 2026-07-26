# Experimento Real 02 — MEC Lab

## Projeto Boreal — Cadeia Fria para Distribuição de Vacinas

### Objetivo

Testar se as melhorias do R3 generalizam para um domínio e vocabulário diferentes do Projeto Atlas. O Projeto Boreal representa uma operação fictícia de cadeia fria para distribuição de vacinas, com evolução temporal em cinco fases.

### Fases

1. **Decisão Inicial** — Adoção de loggers IoT com amostragem periódica
2. **Problema Observado** — Excursão de temperatura durante transporte, lacuna de dados
3. **Investigação** — Confirmação laboratorial de falha de bateria no frio extremo
4. **Mudança de Decisão** — Substituição por sistema dual (IoT + indicadores químicos VVM)
5. **Estado Atual** — Implantação parcial, risco de treinamento, bloqueio documental

### Métricas-alvo

- Hit@1 >= 0.50
- Hit@3 >= 0.75
- Fake source rate = 0
- Decisão vigente supera substituída em consultas atuais
- Decisão anterior aparece no top-3 em consultas históricas
- Ausência retorna vazio ou "absent"

### Artefatos

- `populate_phase_1.py` a `populate_phase_5.py` — scripts de população progressiva
- `queries.json` — 27 consultas (17 diretas + 10 paráfrases adversariais)
- `gold_answers.json` — gabarito criado antes da avaliação
- `run_experiment.py` — execução completa com snapshots e avaliação
- `RAW_RESULTS/` — resultados brutos e snapshots por fase
- `REPORT.md` — relatório final
