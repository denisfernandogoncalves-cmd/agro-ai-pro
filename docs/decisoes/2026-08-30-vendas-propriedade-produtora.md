# Vendas por propriedade produtora — 30/08/2026

## Contexto e falhas reproduzidas

Continuação da entrega de 29/08 e das correções de Produção/Saldos e rateios,
na branch `codex/remover-grupos-colheita`, worktree `runtime-origin-main`.
Todas as Sprints já estavam marcadas como concluídas; esta etapa corrige a
integração comercial com a propriedade produtora introduzida na migration 0012.

A seleção do lote operacional desconsiderava a propriedade da posição. Duas
propriedades com o mesmo CAD/PRO, cultura, safra, classificação e armazém podiam
usar o lote da outra propriedade. Além disso, o filtro e a identidade da venda
usavam a propriedade do armazém. Tentar entregar um rascunho consultava uma
reserva inexistente antes de validar o estado, causando erro interno.
Os testes novos reproduziram esses defeitos antes da correção.

## Critérios de aceite e implementação

- Selecionar o lote pelas mesmas dimensões da posição, incluindo propriedade.
- Reservar, entregar, devolver e cancelar sem afetar outra propriedade que
  compartilhe as demais dimensões.
- Filtrar e identificar vendas pela propriedade produtora da posição, inclusive
  quando a armazenagem é externa. Preservar `null` nos registros históricos sem
  propriedade, sem inferir dados pelo armazém ou pelo CAD/PRO.
- Rejeitar vínculos incompatíveis entre lote, posição e reserva com HTTP 409,
  sem alterar saldos. Validar também a posição retornada pelo ledger na
  confirmação e devolução, revertendo a transação se houver divergência.
- Retornar conflito controlado para entrega de rascunho ou venda sem reserva.
- Exibir a propriedade nas opções de posição oficial no formulário comercial.

Foram preservados os serviços transacionais e a idempotência existentes.
Rascunhos inconsistentes continuam canceláveis sem movimentar estoque.
Não houve alteração de model, migration, dependência ou regra de alocação física.

## Arquivos desta etapa

- `backend/apps/vendas/services.py`: seleção e validação do contexto comercial;
- `backend/apps/vendas/serializers.py`, `selectors.py` e `views.py`: identidade,
  carregamento relacionado e filtro pela propriedade produtora;
- `backend/apps/vendas/test_propriedade_produtora.py`: nove testes de regressão;
- `backend/apps/graos/serializers.py`: nome da propriedade na posição de saldo;
- `frontend/src/api/producaoSaldos.ts` e `frontend/src/api/vendas.ts`: contrato
  tipado e compatibilidade com propriedade ausente;
- `frontend/src/pages/Vendas/VendasPage.tsx` e
  `frontend/scripts/test-components.mjs`: identificação das posições e testes;
- `docs/api/VENDAS.md` e este relatório.

## Validação

Na pasta `backend`, com `DJANGO_SETTINGS_MODULE=config.settings.test`:

```powershell
python manage.py test apps.vendas.test_propriedade_produtora apps.vendas.tests --noinput
```

Resultado: 28 testes encontrados, 23 aprovados e 5 ignorados no SQLite.
Os cenários incluem ciclo comercial completo, isolamento de saldos, armazém
externo, legado sem propriedade, filtro, vínculos inconsistentes e rascunho.

Na raiz do worktree:

```powershell
docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py check
docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py makemigrations --check --dry-run
docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py migrate --check
docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py test --noinput --keepdb
git -c core.safecrlf=false diff --check
```

Resultado: verificações aprovadas, sem mudanças de esquema ou migrations
pendentes; **284 testes encontrados, 279 aprovados e 5 ignorados**, em
110,955 segundos no PostgreSQL. Banco de testes separado do operacional.

Na pasta `frontend`:

```powershell
npm.cmd test
npm.cmd run build
```

Resultado: 26 cenários de componentes/submissão/geometria/PWA e 13 cenários de
autenticação aprovados; TypeScript e build aprovados. Não existe script `lint`.
Permanece o aviso não bloqueante de bundle acima de 500 kB.

A imagem do frontend foi reconstruída e o serviço local recriado na porta 5174.
A conferência no navegador confirmou opções com os nomes das propriedades
produtoras e o texto explícito para posições históricas sem propriedade.
Nenhum contrato foi criado ou movimentado nessa conferência.

## Dados operacionais, riscos e Git

A auditoria somente leitura encontrou duas vendas, nenhuma com divergência
entre a propriedade do lote e da posição, nem entre a posição da reserva e da
venda. Essas contagens não constituem auditoria completa dos dados históricos.
Não houve reconciliação ou gravação de dados operacionais. Os quatro serviços
Docker estão saudáveis.

As alterações e migrations preexistentes foram preservadas. A etapa não muda
os relatórios ou filtros de cargas; sua validação não afirma cobertura de todas
as integrações da migration 0012. Os resultados anteriores permanecem nos
relatórios de retomada de Produção/Saldos e integridade de rateios.

Não foram realizados commit, push, merge ou publicação em produção. A entrega
remota depende das autorizações previstas em `AGENTS.md`.
