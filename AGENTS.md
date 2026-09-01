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

### Backup obrigatório — orientação do Product Owner em 30/08/2026

- Sempre fazer backup antes de iniciar alterações em cada tarefa e antes de
  migrations, atualizações do ambiente ou operações que alterem dados existentes.
- Preservar o código atual, inclusive mudanças não commitadas; incluir banco e
  uploads quando a tarefa envolver o aplicativo ou seus dados persistentes.
- Usar pasta privada com data/hora, fora de áreas públicas e ignorada pelo Git.
  Não sobrescrever, apagar ou publicar backups anteriores.
- Verificar integridade e registrar caminho, conteúdo e hashes. Se o backup
  falhar, corrigir a falha antes de prosseguir com as alterações.
- Backup não autoriza exclusão nem restauração sobre dados atuais. Restaurações
  exigem decisão explícita e devem ser ensaiadas primeiro em ambiente isolado.

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
