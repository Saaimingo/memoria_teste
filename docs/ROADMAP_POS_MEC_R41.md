# Roadmap Pós-MEC R4.1 — Retomada do Harness Cognitivo

**Data:** 2026-07-27  
**Estado:** aprovado como ordem de execução

## 1. Objetivo

Encerrar o ciclo isolado do MEC e retomar o Harness Cognitivo sem reconstruir capacidades operacionais que já existem no Hermes Agent.

O MEC passa a ser o subsistema de memória do projeto. O Hermes Agent passa a ser candidato a fundação operacional do Harness por meio de fork controlado.

## 2. Marco 0 — Publicação e consolidação do MEC

Antes de qualquer integração:

1. publicar a cadeia local de commits do MEC R4.1;
2. abrir Pull Request contra a `main`;
3. executar CI remota;
4. revisar o diff acumulado;
5. confirmar que os 310 testes permanecem verdes;
6. validar que bancos e artefatos locais não foram commitados indevidamente;
7. fazer merge somente depois da revisão;
8. criar tag de marco;
9. registrar o contrato público da versão.

Saída esperada:

`MEC_R41_RELEASE_CANDIDATE_APPROVED`

## 3. Marco 1 — Fork controlado do Hermes Agent

Criar repositório próprio a partir de `NousResearch/hermes-agent`.

Requisitos:

- preservar licença MIT e copyright;
- configurar `origin` e `upstream`;
- registrar o commit-base;
- instalar ambiente de desenvolvimento;
- executar testes oficiais relevantes;
- iniciar CLI e Desktop a partir do source checkout;
- registrar estrutura dos principais subsistemas;
- não adicionar MEC nesta primeira etapa.

Saída esperada:

`HERMES_FORK_BASELINE_APPROVED`

## 4. Marco 2 — Localização nativa `pt-BR`

Implementar localização seletiva do Desktop.

Traduzir:

- experiência humana;
- navegação;
- configurações;
- notificações;
- estados operacionais;
- ajuda;
- mensagens explicativas;
- narração e respostas padrão do LLM.

Preservar:

- código;
- símbolos;
- comandos;
- flags;
- caminhos;
- arquivos;
- branches;
- commits;
- nomes de modelos e providers;
- APIs, endpoints e formatos técnicos.

Critérios:

- `Português (Brasil)` aparece no seletor;
- fallback para inglês funciona;
- nenhuma chave do locale-base fica silenciosamente ausente;
- layouts críticos não quebram;
- termos técnicos permanecem intactos;
- a tradução é mantida em arquivos de locale, não espalhada pelo núcleo.

Saída esperada:

`HERMES_DESKTOP_PTBR_APPROVED`

## 5. Marco 3 — Mapa funcional do Hermes Desktop

Durante o uso da interface traduzida, documentar:

- sessões;
- agentes;
- Command Center;
- capabilities;
- artifacts;
- providers;
- tools;
- plugins;
- memory;
- context compression;
- workspace;
- cron;
- gateway;
- messaging;
- voice;
- security;
- approvals;
- profiles;
- notifications;
- observabilidade.

Para cada área registrar:

1. o que faz;
2. onde está implementada;
3. qual problema resolve;
4. limitações encontradas;
5. o que será reutilizado;
6. o que será melhorado no Harness Cognitivo.

Saída esperada:

`HERMES_FUNCTIONAL_MAP_APPROVED`

## 6. Marco 4 — Memory Provider MEC mínimo

Criar um plugin de memória para o fork.

Primeiro objetivo:

> provar que o Hermes pode consultar o MEC R4.1 e receber uma cápsula de memória verificável antes de chamar o LLM.

Escopo mínimo:

- configuração por perfil;
- banco MEC separado por perfil ou projeto;
- `prefetch()`;
- ferramenta explícita de busca;
- tratamento dos quatro estados;
- fontes e scores preservados;
- `MEMORY_NOT_FOUND` não convertido em lembrança;
- no máximo três esclarecimentos;
- encerramento limpo;
- processamento não bloqueante quando necessário.

Não implementar ainda consolidação automática completa.

Saída esperada:

`MEC_MEMORY_PROVIDER_VERTICAL_SLICE_APPROVED`

## 7. Marco 5 — Circuito real com provider

Usar um provider já suportado pelo Hermes, inicialmente o OpenAI/Codex já configurado pelo usuário.

Fluxo:

1. usuário envia pergunta;
2. Hermes encaminha consulta ao provider MEC;
3. MEC retorna estado e fontes;
4. Harness monta cápsula;
5. provider LLM responde em `pt-BR`;
6. resposta distingue memória, inferência e conhecimento geral;
7. sessão registra fontes utilizadas.

Casos obrigatórios:

- memória confirmada;
- ambiguidade;
- esclarecimento;
- ausência;
- identificador inexistente;
- decisão vigente e histórica;
- nova sessão recuperando memória anterior.

Saída esperada:

`HARNESS_MEMORY_LLM_CIRCUIT_APPROVED`

## 8. Marco 6 — Memória pessoal progressiva

Implementar o ciclo que torna o Harness progressivamente personalizado:

1. observar candidata a memória pessoal;
2. classificar tipo e sensibilidade;
3. verificar duplicidade ou conflito;
4. confirmar quando necessário;
5. gravar com proveniência;
6. substituir preferência anterior sem apagá-la;
7. gerar perfil compacto vigente;
8. carregar o perfil em novas sessões;
9. manter detalhes no MEC sob demanda.

Camadas:

- perfil quente;
- memória de sessão;
- memória operacional;
- memória profunda.

Saída esperada:

`PERSONAL_MEMORY_LOOP_APPROVED`

## 9. Marco 7 — Retomada das fases do Harness

Depois do circuito de memória aprovado, retomar a sequência formal do Harness Cognitivo.

Prioridade prevista:

- integração com fases existentes;
- `GateDecision`;
- `Release`;
- `Incident`;
- governança;
- coordenação de agentes;
- segurança;
- auditoria;
- custos;
- automações;
- painéis cognitivos.

Esses módulos devem consumir o MEC e a infraestrutura Hermes, evitando implementações paralelas.

## 10. Regras de controle

- não reabrir o núcleo do MEC sem necessidade observada;
- não modificar o núcleo Hermes quando plugin ou hook resolver;
- não misturar tradução com mudança cognitiva profunda;
- não calibrar retrieval durante teste de integração;
- não inserir segredos em repositório;
- não tratar teste local como release remoto;
- toda etapa deve possuir commit, testes, limitações e veredito;
- decisões de arquitetura devem ser registradas em ADR.

## 11. Próxima ação permitida

A próxima ação autorizada é:

> publicar e consolidar o MEC R4.1 no GitHub.

Depois disso:

> criar o fork baseline do Hermes Agent e iniciar a localização nativa `pt-BR`.
