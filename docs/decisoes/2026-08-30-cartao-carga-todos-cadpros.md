# Cartão de carga com todos os CAD/PROs — 30/08/2026

## Solicitação e causa

O usuário apresentou imagens da carga #41: o formulário e o controle da parcela
de `teste 2` estavam corretos, mas o cartão mostrava somente SÍTIO SAGRILO.
O cartão e a busca local usavam apenas `propriedade_nome` e `cad_pro_codigo`
principais, ignorando os demais participantes de `contexto_colheita.rateio_producao`.

Branch: `codex/remover-grupos-colheita`, worktree `runtime-origin-main`.
As alterações anteriores foram preservadas.

## Correção e critérios atendidos

- Cartão compartilhado lista todas as propriedades e seus CAD/PROs, com kg e
  sacas de cada parcela gravada, sem recalcular o rateio.
- Total da carga, bruto total e líquido total ficam explicitamente identificados.
- Busca local encontra a carga pelo nome ou código de produtores secundários.
- Edição e cancelamento continuam sendo ações únicas para a carga inteira.
- Histórico mantém os produtores, sem oferecer ações para cargas encerradas.
- Cargas sem snapshot de rateio mantêm a apresentação pelo produtor principal.

Arquivos: `frontend/src/pages/CargasColhidas/CargasColhidasPage.tsx`,
`frontend/src/styles.css`, `frontend/scripts/test-components.mjs`,
`docs/api/CARGAS_COLHIDAS.md` e este relatório. Não houve mudança no backend,
models, migrations, dependências ou dados operacionais.

## Caso conferido no banco e na interface

Consulta somente leitura à carga #41 confirmou:

| Propriedade | CAD/PRO | Peso líquido | Sacas |
| --- | --- | ---: | ---: |
| SÍTIO SAGRILO | 987654321 | 41.265 kg | 687,75 |
| teste 2 | 2056 | 17.685 kg | 294,75 |
| Total | — | 58.950 kg | 982,5 |

A imagem Docker do frontend foi reconstruída e o serviço local atualizado na
porta 5174. A conferência no navegador mostrou ambos os produtores no mesmo
cartão. As buscas por `2056` e `teste 2` encontraram a carga #41. A inspeção
visual confirmou os valores, sem erros ou avisos no console. Nenhum formulário
de gravação foi submetido; não é necessário editar ou salvar novamente a carga.

## Validação

Na pasta `frontend`:

```powershell
npm.cmd test
npm.cmd run build
```

Resultado: 29 cenários de componentes/submissão/geometria/PWA e 13 de
autenticação aprovados; TypeScript e build aprovados. A regressão do cartão usa
os valores do caso #41 e verifica produtores, parcelas, totais, busca, ações
únicas, histórico e compatibilidade sem rateio. Não existe script `lint`.
Permanece o aviso não bloqueante de bundle acima de 500 kB.

Na raiz do worktree:

```powershell
docker compose -p agro-ai-pro build frontend
$env:FRONTEND_PORT='5174'
docker compose -p agro-ai-pro up -d --no-deps frontend
git -c core.safecrlf=false diff --check
```

Build Docker, atualização local e verificação de espaços aprovados.
Os detalhes da última regressão PostgreSQL completa estão no relatório
`2026-08-30-consultas-rastreabilidade-rateios.md`; ela não foi repetida para esta
alteração exclusivamente visual. Na pasta `backend`, com
`DJANGO_SETTINGS_MODULE=config.settings.test`, foram executados:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.graos.test_consultas_rateios apps.graos.test_cargas_colhidas apps.relatorios.test_operacionais --noinput
```

Resultado: verificações aprovadas, sem mudança de esquema detectada e 41 testes
aprovados no SQLite. Revisão final das alterações e verificação de espaços
concluídas sem erros.

## Git e limites

Sem commit, push, merge ou publicação em produção. O cartão não altera a
identidade principal mantida pela API por compatibilidade. Ele apresenta as
parcelas já existentes no snapshot; não cria parcelas históricas ausentes.
