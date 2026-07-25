# AGRO-AI-PRO — Instruções permanentes para agentes

Este arquivo é a porta de entrada obrigatória para qualquer agente de IA que trabalhe neste repositório.

## Leitura obrigatória

Antes de alterar qualquer arquivo, leia integralmente:

1. `docs/PROMPT-MESTRE-AGRO-AI-PRO.md`
2. `docs/REQUISITOS.md`
3. `docs/SPRINTS.md`

Em caso de conflito, aplique esta prioridade:

1. instrução explícita da tarefa atual;
2. `docs/PROMPT-MESTRE-AGRO-AI-PRO.md`;
3. `docs/REQUISITOS.md`;
4. `docs/SPRINTS.md`.

Se o conflito envolver regra de negócio, perda de dados, credenciais, custo externo ou alteração irreversível, pare e solicite decisão do Product Owner.

## Modo autônomo

Para cada tarefa:

1. confirme a branch e o estado do repositório;
2. analise o código e a documentação existentes;
3. identifique a primeira Sprint pendente quando a tarefa não indicar uma Sprint específica;
4. transforme o objetivo em critérios de aceite verificáveis;
5. implemente a solução completa, preservando a arquitetura;
6. crie ou atualize migrations quando necessário;
7. use os scripts e comandos reais do projeto, sem inventar caminhos ou serviços;
8. execute verificações, testes, lint e build disponíveis;
9. corrija automaticamente erros técnicos relacionados à tarefa;
10. repita os testes até estabilizar;
11. atualize a documentação e o status da Sprint somente após cumprir os critérios de aceite;
12. apresente relatório final com arquivos, comandos, testes, riscos e pendências.

Não interrompa por problemas técnicos comuns. Investigue e tente uma correção segura antes de pedir ajuda.

## Autorizado

O agente pode:

- criar, editar e mover arquivos dentro do repositório;
- criar models, serializers, views, services, componentes e testes;
- criar migrations;
- atualizar dependências justificadas e seus arquivos de lock;
- ajustar Docker e scripts relacionados à tarefa;
- executar comandos de validação e testes;
- corrigir erros diretamente relacionados ao escopo.

## Proibido sem autorização explícita

- `git merge`;
- publicação em produção;
- exclusão de banco, volumes, backups ou dados;
- `git reset --hard`;
- `git clean -fd`;
- alteração ou exposição de credenciais e secrets;
- remoção de funcionalidades existentes sem análise de impacto.

Commit e push somente quando a tarefa autorizar expressamente. O merge sempre depende da aprovação do Product Owner.

## Regra de conclusão

Não declare uma tarefa concluída apenas porque o código foi escrito. A conclusão exige:

- critérios de aceite atendidos;
- verificações relevantes aprovadas;
- migrations consistentes;
- testes aprovados ou limitações claramente registradas;
- documentação atualizada;
- revisão final do diff;
- ausência de credenciais, arquivos temporários ou alterações acidentais.
