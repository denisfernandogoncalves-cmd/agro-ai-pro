# Layout, ações financeiras e impressão — 26/09/2026

## Contexto e escopo

Correções solicitadas pelo Product Owner a partir das telas locais: sobreposição
em Talhões, espaçamento em Cadastros agrícolas, edição/exclusão financeira,
impressão financeira compacta, estoque agrupado por fornecedor, impressão de
Relatórios somente com o conteúdo selecionado e filtros de impressão de propriedades.

A porta 5174 executa a worktree `runtime-origin-main`, branch
`codex/propriedades-impressao-a4-20260921`. As alterações locais anteriores foram
preservadas. A pasta raiz usa outra branch e não foi usada para editar a aplicação.

## Entrega e critérios de aceite

- Grupos de colheita permanecem no fluxo normal durante a rolagem. Formulário,
  propriedades integrantes e grupos salvos têm regiões separadas e responsivas.
- Cadastros agrícolas usam duas colunas no desktop e uma em telas estreitas,
  sem esticar campos ou distribuir espaços vazios pela altura dos painéis.
- Lançamentos financeiros oferecem Editar e Excluir, inclusive os liquidados.
  Edição usa PATCH apenas dos campos apresentados. Número do boleto, grupo,
  categoria, parceiro vinculado, propriedade e liquidação não são alterados.
  A exclusão definitiva exige confirmação na interface e atualiza lista e totais.
  Proteções de vínculos existentes na API continuam válidas.
- Impressão financeira usa Arial, A4 retrato com margens de 12 mm, resumo em
  uma linha e tabela com situação, descrição/favorecido, boleto, vencimento,
  liquidação, valor nominal e liquidado. Os filtros são os efetivamente aplicados.
- Estoque agrupa os produtos em tabelas por fornecedor. Unidades e custos
  incompletos são preservados; não se somam quantidades de unidades diferentes.
  Compras, saídas e lotes por data continuam disponíveis em seção expansível.
- Relatórios imprimem somente título da seção, tabela, paginação e geração.
  Cabeçalho do aplicativo, apresentação da central e cartões de resumo são
  ocultados exclusivamente na impressão.
- Propriedades oferece seleção combinável por proprietário, nome, CAD/PRO e
  município/UF. Contagem e totais da impressão refletem a interseção dos filtros.
  Os filtros operam sobre as propriedades da consulta atual e também são
  respeitados pelo botão global Imprimir A4. Limpar seleção volta à consulta toda.

## Arquivos da entrega

- `frontend/src/pages/Talhoes/GruposPropriedadesPanel.tsx`
- `frontend/src/pages/CadastrosAgricolas/ContratosComerciais.tsx`
- `frontend/src/pages/Estoque/DisponibilidadeEstoque.tsx`
- `frontend/src/pages/Financeiro/FinanceiroPage.tsx`
- `frontend/src/pages/Financeiro/EditorLancamento.tsx` (novo)
- `frontend/src/pages/Financeiro/FinanceiroImpressao.tsx` (novo)
- `frontend/src/components/PropriedadesImpressao.tsx` (preexistente não rastreado)
- `frontend/src/api/financeiro.ts`
- `frontend/src/styles.css` e `frontend/src/print.css`
- `frontend/scripts/test-components.mjs`
- `backend/apps/financeiro/tests_edicao.py` (novo)

Não houve mudança de models, novas migrations ou alteração de registros reais
para validar edição e exclusão. Os endpoints PATCH e DELETE já existiam.

## Preservação

Backup inicial completo de código, alterações locais e uploads das 13 worktrees:
`D:/PROJETOS/AGRO-AI-PRO/backups/sincronizacao-20260926-073348`.
O diretório inclui `dados.dump`, validado por `pg_restore --list`, e SHA-256.
ZIPs foram verificados por CRC e arquivos registrados no manifesto com hashes.
Checkpoint adicional do código antes dos ajustes de impressão:
`D:/PROJETOS/AGRO-AI-PRO/backups/sincronizacao-20260926-074054`.
Os diretórios são privados e ignorados pelo Git; nenhum backup foi restaurado.

## Validação

- `docker compose -p agro-ai-pro exec -T backend python backend/manage.py test apps.financeiro --noinput`:
  47 testes aprovados em banco de teste, incluindo 6 novos cenários de edição,
  exclusão, autenticação e preservação dos demais boletos/liquidação.
- `docker compose -p agro-ai-pro exec -T backend python backend/manage.py check`:
  nenhuma ocorrência.
- `docker compose -p agro-ai-pro exec -T backend python backend/manage.py makemigrations --check --dry-run`:
  nenhuma alteração detectada.
- `npm.cmd run build` e `npm.cmd test` em frontend: aprovados, incluindo
  agrupamento de múltiplos produtos, dados de impressão, filtros combinados de
  propriedades e 13 cenários de autenticação.
- `docker compose -p agro-ai-pro build frontend`: aprovado. Atualização local
  somente do frontend, com `FRONTEND_PORT=5174` e `up -d --no-deps frontend`.
- Revisão visual no navegador de Talhões após rolagem, Cadastros agrícolas,
  estoque agrupado e editor de lançamento liquidado (fechado sem salvar).
- Layouts financeiros e de relatórios revisados em largura A4 usando fixtures
  sintéticas renderizadas pelos componentes reais com as regras de impressão.
  Essa revisão não substitui teste físico de impressora nem verifica paginação
  de relatórios extensos. Cabeçalhos/rodapés extras do navegador dependem das
  configurações de impressão do usuário.
- `git diff --check`: aprovado. Não existe script lint no package.json.

O build mantém o aviso de bundle JavaScript acima de 500 kB, sem falha.
Sem commit, push, merge ou publicação em produção.
