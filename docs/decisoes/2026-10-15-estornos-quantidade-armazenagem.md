# Compras, quantidade do faturamento e ativação de armazenagem — 15/10/2026

## Escopo e critérios de aceite

- Cancelar compras ou retirar parte da quantidade comprada, preservando a origem.
- Exigir motivo, registrar usuário/data/quantidade e rejeitar saldo insuficiente.
- Impedir duplicação por reenvio, solicitações obsoletas, exclusão/edição do histórico.
- Corrigir sugestão de embalagens para dosagem decimal sem zero inicial.
- Expor Ativar em armazenagens de grãos inativas, com permissão de edição.

## Implementação

Em Estoque → Compras, a coluna Situação / estornos apresenta Ativa,
Estorno parcial ou Cancelada. Estornar quantidade recebe litros/kg; Cancelar
compra retira todo o restante ainda não estornado. Se houve consumo e o lote
não possui esse saldo, o cancelamento é bloqueado; o parcial aceita até o saldo
disponível e o restante da compra. Compra original, valores e pagamentos são
preservados; não há estorno financeiro automático nem devolução de faturamento.

POST `/api/estoque/compras/{id}/estornar/` e `/cancelar/` recebem UUID `id`,
`motivo` (até 500 caracteres), `quantidade_estornada_original` e, no parcial,
`quantidade` (positiva, três casas). Mesma solicitação pode ser repetida sem
nova retirada. Mudanças concorrentes retornam 409. Acesso exige excluir em
Estoque, usando as regras JWT existentes. Histórico retornado em `estornos`;
original em `quantidade_total`, retiradas em `quantidade_estornada`, restante
em `quantidade_restante`, saldo atual do lote em `saldo_disponivel`.

Migration aditiva estoque.0008 cria EstornoCompraEstoque, ligada à compra e
à saída com PROTECT. Produto/lote/compra são bloqueados em transação, seguindo
a ordem do faturamento. A saída usa a data atual ou da compra, se futura.
Tentativa de apagar ou corrigir o movimento de estorno pela tela genérica
é bloqueada. Compras totalmente canceladas não recebem novo pagamento.

No faturamento, dosagens `.25` ou `,25` eram rejeitadas pela conversão decimal
exata, deixando a sugestão vazia apesar da quantidade necessária calculada.
O parser agora aceita esses formatos e decimais com separador final; mantém
o arredondamento de embalagens para cima e as alterações manuais do usuário.

Cadastros agrícolas → Armazéns e locais apresenta Ativar somente nos inativos.
Reutiliza PATCH `/api/graos/armazens/{id}/` com `{ativo:true}`, sem mudar nome,
capacidade ou histórico. Nenhuma armazenagem real foi ativada automaticamente.

## Backups e validação

Backups privados com ZIP CRC, catálogo pg_restore e SHA-256:
`backups/visual-20261015-100101` (início), `visual-20261015-101203` (antes da
migration), `visual-20261015-101814` (antes da ativação de armazenagem).
Migration 0008 aplicada após testes em PostgreSQL temporário exclusivo.
71 verificações iniciais de compras/faturamento/correções aprovadas;
12 testes finais de estornos aprovados, com permissão JWT, rollback,
concorrência real, consumo anterior, reenvio e proteção do histórico.
Django check e makemigrations --check --dry-run aprovados.
npm test e TypeScript/Vite aprovados na imagem Docker com a correção da
quantidade e interface de estornos.
Após incluir Ativar, três testes PostgreSQL de armazenagem/capacidade aprovados;
suíte frontend e TypeScript/Vite finais aprovados novamente. Frontend local
atualizado na porta 5174, resposta HTTP 200; diff sem erros.

SHA-256 das compras/movimentações reais antes/depois da migration idêntico:
`1f34c39018f2c0af34d3dcfaa55600508661a233cf70137ad4c91af471397e2e`.
API de compras autenticada HTTP 200 e nenhum estorno real criado.

Arquivos principais: backend/apps/estoque/{compras,models,views}.py,
test_estornos_compra.py, migrations/0008_estorno_compra.py;
frontend/src/api/{estoque,cadastrosAgricolas}.ts,
pages/Estoque/{ComprasEstoque.tsx,embalagensFaturamento.ts},
pages/CadastrosAgricolas/CadastrosAgricolasPage.tsx e scripts/test-components.mjs;
backend/apps/graos/test_ativar_armazem.py.

Sem commit, push, merge ou produção. Não houve teste visual autenticado nem
gravação de cancelamento/estorno em dados operacionais.

## Complemento — campo de embalagens sugeridas e editáveis

Backup privado verificado `backups/visual-20261015-102622`.
Campo Embalagens a enviar com sugestão explícita e arredondamento para cima
de área × dosagem ÷ conteúdo por embalagem. Mantém edição manual; Usar sugestão
retoma o cálculo automático. Apagar e sair do campo também retoma a sugestão.
Quando faltam dados para calcular, a interface indica área/dosagem/conteúdo
necessários, evitando um campo vazio sem explicação.

Testes renderizam o próprio campo com as áreas da imagem: 1,450413, 3,752066
e 19 alqueires, dose 0,25 e embalagem de 1 L, resultando em 1, 1 e 5 embalagens.
Também verificam embalagem de 5 L, edição manual preservada, botão de retorno,
conteúdo ausente e recuperação ao apagar. npm test, TypeScript/Vite e diff
aprovados. Sem alteração de dados, API ou migrations nesta continuação.
