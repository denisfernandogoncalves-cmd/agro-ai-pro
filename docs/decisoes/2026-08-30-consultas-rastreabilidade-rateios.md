# Consultas e rastreabilidade de rateios — 30/08/2026

## Contexto e critérios de aceite

Continuação da entrega de 29/08, após as correções de Produção/Saldos,
integridade dos rateios e Vendas. Branch `codex/remover-grupos-colheita`,
worktree `runtime-origin-main`. Não foi aberta uma nova Sprint: o índice
operacional já marca todas como concluídas.

Esta etapa deve permitir localizar uma carga pela propriedade ou CAD/PRO de
qualquer parcela, exigir correspondência à mesma parcela quando esses filtros
forem combinados, evitar cargas duplicadas e preservar a rastreabilidade dos
créditos e estornos secundários. Deve manter compatibilidade com cargas sem
rateios persistidos, sem reescrever dados históricos ou alterar saldos.

## Problemas reproduzidos e solução

A listagem filtrava apenas a propriedade e o CAD/PRO principais. A busca textual
também ignorava os produtores secundários. O relatório reconhecia somente a
relação direta `carga_colhida`, fazendo créditos e estornos secundários aparecerem
sem carga, produtor ou placa. A execução anterior à correção apresentou nove
falhas de asserção nos oito testes inicialmente criados.

O selector de cargas passa a consultar as parcelas persistidas, combinando as
duas dimensões na mesma condição. Cargas sem parcelas usam as dimensões diretas
como compatibilidade; vínculos cadastrais atuais não são usados para inferir
participação na produção. A consulta elimina duplicatas. A busca textual também
considera os nomes e códigos dos produtores secundários.

O relatório resolve o rateio do crédito original, inclusive quando recebe seu
estorno. Identidade do produtor vem da parcela, placa e estado vêm da carga, e
quantidade e snapshots continuam vindo do movimento. A carga substituída e sua
substituta permanecem identificadas separadamente. As relações são carregadas
na consulta inicial, sem consultas adicionais por linha para montar o contexto.

Os pesos da listagem de cargas continuam representando a carga inteira; o filtro
não os converte em pesos parciais. Os totais dos relatórios continuam baseados
nos movimentos e posições oficiais, sem multiplicar o peso da carga.

## Arquivos desta etapa

- `backend/apps/graos/selectors.py`: filtro por produtor e relações dos rateios;
- `backend/apps/graos/views.py`: integração dos filtros e busca textual;
- `backend/apps/relatorios/selectors.py`: origem e produtor de cada movimento;
- `backend/apps/graos/test_consultas_rateios.py`: nove testes novos;
- `docs/api/CARGAS_COLHIDAS.md` e `docs/api/RELATORIOS.md`: contratos atualizados;
- este relatório.

Não foram alterados models, migrations, dependências ou código frontend nesta
etapa. As alterações de etapas anteriores continuam preservadas no worktree.

## Validações direcionadas e frontend

Na pasta `backend`, com `DJANGO_SETTINGS_MODULE=config.settings.test`:

```powershell
python manage.py test apps.graos.test_consultas_rateios apps.graos.test_cargas_colhidas apps.relatorios.test_operacionais --noinput
```

Resultado: **41 testes aprovados** no SQLite. Incluem filtros secundários,
filtros combinados, CAD/PRO compartilhado, busca sem duplicatas, totais,
paginação do histórico, cancelamento, retificação, legado e consultas por linha.
O cenário legado é montado apenas no teste, sem excluir registros operacionais.

Na pasta `frontend`:

```powershell
npm.cmd test
npm.cmd run build
```

Resultado: **26 cenários de componentes/submissão/geometria/PWA e 13 de
autenticação aprovados**. TypeScript e build aprovados. Não existe script
`lint`. Permanece o aviso não bloqueante de bundle acima de 500 kB.
Não foi necessária reconstrução da imagem do frontend, pois seu código não
mudou nesta etapa. A validação funcional das consultas foi feita pelas APIs
autenticadas nos testes, sem nova conferência visual no navegador.

## Regressão completa e banco

Na raiz do worktree:

```powershell
docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py check
docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py makemigrations --check --dry-run
docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py migrate --check
docker compose -p agro-ai-pro exec -T -w /app/backend backend python manage.py test --noinput --keepdb
git -c core.safecrlf=false diff --check
docker compose -p agro-ai-pro ps
```

As verificações de sistema e migrations passaram, sem mudança de esquema
detectada ou migrations pendentes. A suíte PostgreSQL encontrou **293 testes:
288 aprovados e 5 ignorados**, em 113,835 segundos. Os testes usam banco separado
do operacional. A revisão final do diff e a verificação de espaços passaram.

## Auditoria operacional e limites

A consulta somente leitura aos movimentos com rateio direto ou pelo crédito
estornado encontrou **12 movimentos**, **zero sem carga** e **zero sem produtor**
na representação corrigida do relatório. Isso não constitui uma auditoria
completa dos dados históricos nem comprova a correção de todos os seus valores.
Não foram gravados, reconciliados ou excluídos dados operacionais.

Os quatro serviços Docker estão saudáveis, com frontend na porta 5174. As
consultas preservam autenticação, formato das respostas e regras de saldo.
O tratamento de cargas sem parcelas permanece limitado ao vínculo direto já
existente; não se inventam movimentações secundárias para esse legado.

Não foram realizados commit, push, merge ou publicação em produção. As migrations
0010–0012 e demais alterações preexistentes continuam pendentes de entrega no Git.
A publicação remota depende das autorizações previstas em `AGENTS.md`.
