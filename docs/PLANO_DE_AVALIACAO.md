# Plano de Avaliação — MEC Lab

## 1. Objetivo

Avaliar se a arquitetura proposta para o MEC produz recuperação mais precisa, explicável e eficiente que abordagens simples.

## 2. Dataset controlado

Criar ao menos três projetos sintéticos ou sanitizados.

### Projeto A — Simulador de futebol

Elementos esperados:

- calendário de temporadas;
- acesso e rebaixamento;
- aposentadoria;
- geração de novos jogadores;
- projeto interrompido;
- checkpoint conhecido.

### Projeto B — Alertas financeiros

Elementos esperados:

- alertas duplicados;
- eventos;
- reinicialização;
- idempotência;
- correção aplicada;
- evidências de teste.

### Projeto C — Estoque e filas

Elementos esperados:

- produtos ou operações duplicadas;
- fila de eventos;
- falha após reinicialização;
- solução estrutural semelhante ao Projeto B;
- vocabulário diferente.

## 3. Casos de recuperação direta

Exemplos:

- "Aquele jogo antigo que tinha problema de calendário e aposentadoria."
- "O projeto de mercado em que os alertas apareciam duas vezes depois de reiniciar."
- "Qual decisão definiu que a conversa não era fonte normativa?"

Para cada consulta, registrar:

- candidato correto;
- posição esperada;
- pistas obrigatórias;
- pistas distratoras;
- registros que devem ser recuperados;
- registros que não devem aparecer.

## 4. Casos de memória parcial

Criar consultas em que:

- falta o nome do projeto;
- existe mais de um candidato;
- a informação foi substituída;
- há evidências conflitantes;
- o documento existe, mas a implementação não;
- o checkpoint está desatualizado.

O sistema deve declarar incerteza em vez de inventar continuidade.

## 5. Casos de analogia estrutural

Exemplo:

- perguntar por duplicação de alertas após reinicialização;
- verificar se o sistema recupera o episódio de duplicação de itens em fila, mesmo com vocabulário distinto;
- exigir explicação da estrutura causal compartilhada.

Essa etapa é experimental e pode ser separada da linha de base.

## 6. Estratégias comparadas

### Baseline A — Busca lexical

Palavras, filtros e índice textual.

### Baseline B — Busca semântica

Similaridade vetorial sem uso explícito do grafo causal.

### Candidato C — Busca híbrida MEC

Combinação de:

- texto;
- semântica;
- entidades;
- tipo de memória;
- relações;
- temporalidade;
- estado;
- escopo de projeto.

## 7. Métricas

### 7.1 Precisão

Proporção dos itens recuperados que são realmente relevantes.

### 7.2 Cobertura

Proporção dos itens relevantes existentes que foram recuperados.

### 7.3 Ranking

Posição do candidato correto.

Métricas sugeridas:

- Hit@1;
- Hit@3;
- MRR;
- nDCG, se houver graus de relevância.

### 7.4 Explicabilidade

Avaliar se a explicação:

- cita IDs reais;
- aponta pistas realmente usadas;
- não inventa relação inexistente;
- separa memória de inferência.

### 7.5 Preservação causal

A cápsula deve manter:

- problema;
- ação;
- resultado;
- condição;
- consequência;
- estado atual.

### 7.6 Alucinação

Contar afirmações sem suporte no dataset.

### 7.7 Eficiência

Medir:

- caracteres ou tokens recuperados;
- tempo de consulta;
- tamanho da cápsula;
- quantidade de fontes abertas;
- custo de embeddings ou LLM, quando usados.

### 7.8 Qualidade de retomada

Um agente sem acesso ao histórico bruto recebe apenas a cápsula e deve:

- identificar o projeto;
- explicar onde parou;
- listar decisões vigentes;
- declarar lacunas;
- propor próximo passo coerente.

Comparar com o gabarito.

## 8. Teste cego

Separar funções:

- agente implementador;
- agente gerador do dataset;
- agente avaliador.

O avaliador não deve alterar:

- dataset;
- gabaritos;
- métricas;
- critérios de aprovação.

O agente avaliado não deve produzir a própria evidência final sem verificação externa.

## 9. Ablation tests

Executar a busca híbrida removendo um componente por vez:

- sem embeddings;
- sem grafo;
- sem temporalidade;
- sem tipagem;
- sem checkpoint;
- sem estado de validade.

Objetivo: descobrir quais partes realmente trazem ganho.

## 10. Critérios iniciais de aprovação

Os valores exatos podem ser ajustados antes do teste cego, nunca depois de observar o resultado final.

Linha inicial sugerida:

- Hit@1 >= 0,80 em recuperação direta;
- Hit@3 >= 0,95;
- zero fonte inventada;
- 100% das inferências marcadas como inferência;
- detecção de conflito em todos os casos projetados para conflito;
- cápsula com redução mínima de 60% frente ao histórico bruto;
- retomada correta em ao menos 80% dos cenários cegos;
- execução reproduzível com mesma versão, configuração e seed.

## 11. Evidências obrigatórias

- versão do código;
- hash do dataset;
- configuração usada;
- seed;
- logs de avaliação;
- resultados por consulta;
- métricas agregadas;
- casos de falha;
- relatório final;
- limitações observadas.

## 12. Resultado permitido

O relatório final pode concluir:

- hipótese sustentada;
- parcialmente sustentada;
- rejeitada;
- inconclusiva.

Não existe obrigação de confirmar o MEC.
