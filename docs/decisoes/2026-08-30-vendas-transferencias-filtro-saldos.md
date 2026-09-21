# Vendas, transferência entre CAD/PROs e filtro de propriedade

Escopo solicitado pelo Product Owner em 30/08/2026, no checkout local
`.worktrees/runtime-origin-main`, branch `codex/remover-grupos-colheita`.
Complementa as Sprints existentes sem reabrir escopos independentes.

## Critérios de aceite e implementação

- Nova venda com Data, Destino, Placa, Motorista, CAD/PRO, contrato/empresa,
  nº nota produtor, nº nota empresa e peso líquido. Registro completo cria,
  reserva e entrega atomicamente; modo rascunho anterior continua disponível.
- Motorista persiste na entrega, edição, auditoria e relatório. Migration 0006
  aceita a coluna local preexistente de 120 caracteres, ampliando-a para 160
  sem excluir dados. Retorno preserva coluna/valores para reaplicação segura.
- Aba Transferência de saldo antes de Vendas, com origem identificada por
  propriedade, CAD/PRO e proprietário, tanto na origem quanto no destino.
  Propriedades com CAD/PRO compartilhado
  são opções distintas; lote e saldo seguem a propriedade selecionada.
- Transferência usa serviço existente com duas movimentações atômicas,
  proteção de saldo comprometido, idempotência e lotes compatíveis.
- Painel mostra a propriedade efetivamente filtrada, sem usar a descrição
  do CAD/PRO como nome de produção. Não mostra resultados antigos enquanto
  filtros estão pendentes e descarta respostas atrasadas.

## Arquivos principais

- Backend: `apps/vendas/{models,serializers,views,services,alteracoes_services}.py`,
  migration `0006_entregavendagraos_motorista.py`, relatório de entregas e testes
  `test_saida_completa.py`, `graos/test_transferencia_cadpro_interface.py`.
- Frontend: `pages/Vendas/`, `pages/TransferenciasSaldo/`,
  `pages/ProducaoSaldos/ProducaoSaldosPage.tsx`, `api/{vendas,transferenciasSaldo}.ts`,
  `App.tsx`, estilos e `scripts/test-components.mjs`.
- Documentação funcional: `docs/api/VENDAS.md` e `docs/api/GRAOS.md`.

## Verificação manual no ambiente local

Interface em `http://127.0.0.1:5174/`, atualizada por build/recriação apenas do
frontend Docker. Conferidos todos os campos de venda e a posição da nova aba.
Filtro LOTE 27 - CONRADO / Trigo mostrou somente a propriedade selecionada e
saldo **6.140,625 kg**. Alterar cultura ocultou resultados até aplicar filtros.

Origem apresentou `LOTE 27 - CONRADO / CAD/PRO 9534424423 / ARRENDADO`, usando
o proprietário exatamente como cadastrado. Apenas o lote dessa propriedade
ficou disponível. Selecioná-lo mostrou 6.140,625 kg; destino de outra produtora
foi bloqueado com explicação. Não foram submetidos lançamentos reais durante
a conferência. Os novos dados inseridos pelo usuário foram preservados.

## Comandos e validações

- `npm test`: 39 cenários de componentes/submissão/geometria/PWA e 13 de
  autenticação aprovados; inclui distinção de propriedades com mesmo CAD/PRO,
  identificação do proprietário e bloqueio de lotes incompatíveis.
- `npm run build` e `docker compose -p agro-ai-pro build frontend`: aprovados.
- `python manage.py check`: sem problemas; `makemigrations --check --dry-run`:
  nenhuma alteração de modelo pendente.
- `git -c core.safecrlf=false diff --check`: sem erros.
- `docker compose -p agro-ai-pro exec -T -w /app/backend backend python
  manage.py test --noinput`: 317 testes, 312 aprovados e 5 ignorados por
  condições explícitas da suíte, 157,634 segundos. Inclui concorrência real,
  insuficiência de saldo, idempotência e ciclos de migrations.
- SQLite (`config.settings.test`), módulos `apps.graos.test_transferencia_cadpro_interface`,
  `apps.vendas.test_saida_completa`, `apps.graos.test_migration_0006` e
  `apps.graos.tests.ReversaoMigrationsGraosTests`: 13 testes, 11 aprovados e
  2 ignorados porque exigem PostgreSQL, 33,785 segundos.

## Limitações e segurança

A transferência mantém a propriedade produtora original; não permite mover
produção entre propriedades distintas. Os lotes atuais do usuário não oferecem
destino compatível entre os dois CAD/PROs para a origem LOTE 27. Não foi criado
lote fictício ou modificado vínculo para contornar essa regra.

O build mantém aviso de bundle acima de 500 kB. Não há script de lint separado
no frontend; TypeScript é verificado pelo build. Não houve commit, push, merge,
publicação em produção ou nova limpeza de dados. Migrations reversas foram
validadas somente nos bancos descartáveis de teste.
