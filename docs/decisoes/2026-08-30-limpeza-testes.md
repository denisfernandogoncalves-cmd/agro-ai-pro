# Limpeza autorizada do ambiente local — 30/08/2026

Pedido explícito: remover os dados inseridos para começar novos testes.

Ambiente confirmado: projeto Docker `agro-ai-pro`, PostgreSQL `agro_ai_pro`,
backend em `8000`, frontend em `5174`, checkout `.worktrees/runtime-origin-main`,
branch `codex/remover-grupos-colheita`.

Foram removidos 902 registros de 39 tabelas operacionais e de histórico/cache:
propriedades, CAD/PRO, talhões, cargas, saldos, reservas, movimentos, vendas,
importações, financeiro, insumos, máquinas, operações, clima, mercado e log do
admin. Os dois usuários, senhas, permissões e sessões foram preservados.

O aplicativo foi pausado durante a operação. Antes da limpeza foi salvo um
`pg_dump` completo em formato custom, validado por `pg_restore --list` e pela
leitura integral com `pg_restore --file=/dev/null`. A limpeza usou transação,
lista explícita de tabelas, bloqueios, `TRUNCATE ... RESTART IDENTITY RESTRICT`
(sem CASCADE) e comparação dos dados das tabelas protegidas antes/depois.
Não foram apagados volumes, bancos, código ou backups anteriores.

Backup local, fora da área pública e ignorado pelo Git:
`backups/limpeza-2026-08-30/antes-da-limpeza.dump` neste checkout.
SHA-256: `7e65d2aa93ae73a648981623f268009d4a4725cb92a568cfdc5f890352d434a4`.
O inventário de contagens e o script de uso único ficam na mesma pasta.
O backup contém dados privados e de autenticação: não publicar ou versionar.

Verificações: zero registros nas tabelas operacionais após a limpeza; dois
usuários mantidos; `manage.py check` aprovado; migrations consistentes;
`/api/health/` respondeu `ok`; telas Propriedades e Vendas verificadas sem
registros e com sessão autenticada. Nenhum upload estava presente em
`backend/media`. Caches de clima/mercado podem voltar a ser preenchidos ao
consultar esses módulos. Os testes posteriores usam banco de testes separado.

Ao reiniciar, o backend aplicou as migrations comerciais 0003 e 0004 que já
estavam preparadas; o cadastro de contratos permaneceu vazio. A migration 0005
adiciona produto e quantidade, sem inserir registros de demonstração.

Recuperação exige parar escritas e restaurar o dump em ambiente isolado antes
de qualquer substituição do banco ativo; não restaurar automaticamente sobre
novos testes do usuário. A restauração completa não foi ensaiada nesta operação.

Sem commit, push, merge ou publicação em produção.
