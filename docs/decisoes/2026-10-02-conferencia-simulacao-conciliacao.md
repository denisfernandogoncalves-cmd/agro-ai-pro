# Sete melhorias autorizadas em 02/10/2026

## Critérios de aceite

- Conferência somente leitura: totais do histórico completo por posição, divergência e histórico paginado.
- Simulação: saldo antes/depois nas vendas e na prévia de envio de insumos, sem lançamento.
- Estorno: motivo obrigatório, original preservado, validação comercial/cargas e idempotência.
- Conciliação: comparação com extrato informado, identificando empresa, posição e diferença, sem ajuste automático.
- Rascunhos: privados por usuário, recuperação explícita e limpeza depois de sucesso.
- Relatórios salvos: filtros, colunas e impressão associados ao favorito privado.
- Backup periódico: hashes, integridade e restauração em PostgreSQL isolado, sem tocar no banco operacional.

Backup inicial validado: `backups/sincronizacao-20261002-133905` (código, uploads e PostgreSQL custom dump).
Status: implementação, testes e revisão visual concluídos; validação final em 03/10/2026.

## Arquivos e validação

- Backend: core/conferencia.py, core/rascunhos.py, models/serializers/views/urls e migration core0002; vendas/particular_services.py e testes de confirmação da prévia.
- Frontend: ConferenciaSaldo, RascunhoAutomatico, FiltrosFavoritos, Produção e saldos, Vendas e Relatórios; cenários de rascunhos e componentes.
- Backup: scripts/backup_verificado.py, verificar_backup.py e test_verificar_backup.py.
- `python manage.py test --settings=config.settings.test --noinput`: 525 casos, 486 aprovados e 39 skips. Log de falha simulada de importação é esperado pelo teste. Uma execução anterior foi interrompida ao reiniciar backend e refeita integralmente.
- `python manage.py test apps.core.test_conferencia apps.core.test_evolucao apps.vendas.test_particular --noinput`: PostgreSQL, 34 aprovados antes dos dois cenários finais de mudança de saldo.
- `npm.cmd test`: componentes, 14 cenários de autenticação e 6 de rascunhos aprovados.
- `npm.cmd run build`: TypeScript e Vite aprovados. Primeiro comando foi emitido na raiz sem package.json e corrigido; execução elevada teve restrição no tsbuildinfo e foi executada normalmente no workspace com sucesso.
- `python scripts/test_verificar_backup.py`: três cenários de integridade aprovados.
- `python manage.py migrate --noinput`: core0002 aplicada; `makemigrations --check --dry-run`: sem alterações.
- `git diff --check`: sem erros de whitespace; avisos CRLF preexistentes.
- Não existe script de lint separado no frontend.

## Backups e limites

Antes da migration: `.worktrees/runtime-origin-main/backups/agro-ai-pro-2026-10-02-135053-036199`, código/DB/uploads e prova real de restauração isolada aprovada.

Escopo dos rascunhos: novas vendas e crédito de produção. Escopo das colunas salvas: tabela de produção por propriedade. Conciliação manual e visual; não importa nem persiste extratos. Estornos de cargas e vendas devem seguir os respectivos lançamentos; transferências não são estornadas individualmente nesta tela. Veja a documentação de API para limites de fechamento, disponibilidade e encerramento abrupto do navegador.

Nenhum usuário ou permissão real foi modificado para testes. Nenhum saldo existente foi corrigido automaticamente. Foram preservadas todas as alterações locais. Posteriormente o Product Owner autorizou commit e push para atualização do GitHub; merge e publicação em produção continuam fora do escopo.

## Fechamento em 03/10/2026

Suíte final completa: 540 casos, 500 aprovados e 40 pulados no SQLite; 34 casos adicionais aprovados no PostgreSQL (transferências, conferência e venda particular). Os logs de falha simulada são esperados. Testes frontend, TypeScript e build aprovados; instalação limpa e imagem Docker com axios 1.20.0 e nanoid 3.3.19, audit sem vulnerabilidades. node_modules antigo no host permanece com restrição EPERM, sem mudança de ACL.

Revisão visual confirmou conferência de saldo, comparação manual, escolha de cultura, correções de transferência e avisos de exclusão de carga, sem lançamentos reais. Layout verificado em 360, 768 e 1366 pixels. Os limites de rascunhos, relatório e conciliação acima permanecem explícitos.

Backup final da retomada com restauração isolada aprovada: backups/agro-ai-pro-2026-10-03-073329-457606. Backup semanal ativo aos domingos às 06h, America/Sao_Paulo, com verificação de hashes e restauração isolada de dump.

