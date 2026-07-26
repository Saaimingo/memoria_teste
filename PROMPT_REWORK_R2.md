# PROMPT — REWORK R2 DO MEC LAB

## Papel

Você é o Agente Implementador de Rework R2. Você não é o agente auditor.

## Autoridade documental

Leia integralmente:

1. issue de rework R2;
2. PR #6;
3. relatório `audit/REPORT_PR6.md` na branch `audit/rework-r1-pr6`;
4. `evidence/rework-r1/REPORT.md`;
5. `PROMPT_REWORK.md`.

## Base e branch

- base obrigatória: `rework/mec-lab-baseline-r1`
- branch obrigatória: `rework/mec-lab-baseline-r2`
- PR draft deve apontar para `rework/mec-lab-baseline-r1`

## Objetivo

Corrigir o bug de temporal hints, elevar robustez lexical/semântica sem hardcodes e preparar nova reauditoria independente.

## Itens obrigatórios

1. eliminar overlap entre stopwords e gatilhos temporais sem reintroduzir ruído lexical;
2. adicionar testes comportamentais que provem que hints históricos, atuais e de ação disparam;
3. preservar os 107 testes existentes;
4. revisar TF-IDF e enriquecimento vocabular por regras gerais, não por consultas conhecidas;
5. não ler nem usar o conteúdo do novo holdout criado pelo auditor;
6. manter detecção de conflitos funcionando para CONTRADICTED_BY, SUPERSEDES, OBSOLETE e versões;
7. produzir comparação R1 versus R2 com métricas e evidências;
8. não alterar datasets e gold answers originais;
9. não criar aliases específicos para queries cegas conhecidas;
10. documentar claramente qualquer limitação ainda existente.

## Critérios mínimos para estado final

- todos os testes existentes passando;
- novos testes de temporal hints passando;
- zero overlap indevido entre stopwords e hints;
- nenhuma regressão na detecção de conflitos;
- evidências reproduzíveis;
- estado máximo: `READY_FOR_INDEPENDENT_REAUDIT`.

## Proibições

- não fazer merge, tag ou release;
- não alterar main diretamente;
- não alterar branches de auditoria;
- não alterar o Harness Cognitivo principal;
- não acessar o novo holdout reservado além do que já foi publicamente resumido no relatório.
