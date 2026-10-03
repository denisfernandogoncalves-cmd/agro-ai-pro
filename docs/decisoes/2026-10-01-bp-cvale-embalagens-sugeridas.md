# BP C.Vale e embalagens sugeridas — 01/10/2026

Branch: `codex/propriedades-impressao-a4-20260921`, checkout
`.worktrees/runtime-origin-main`. Alterações locais anteriores preservadas.

## Comportamento solicitado e implementado

Embalagens a enviar são sugeridas por `área × dosagem / conteúdo da embalagem`,
arredondando para cima até a próxima embalagem inteira. Quando a divisão é
exata, não se adiciona embalagem extra. Exemplo: 72 alq. × 0,2 l/alq. = 14,4 l;
embalagens de 5 l sugerem três unidades. O campo permanece editável. Após uma
edição manual, alterar área, dosagem ou conteúdo não sobrescreve o valor escolhido.
Desmarcar e selecionar novamente a propriedade retoma a sugestão automática.
O cálculo usa aritmética decimal exata para evitar arredondar indevidamente
valores como `3 × 0,1 / 0,3`. Os dados efetivos são enviados à prévia e confirmação.
A API também calcula a sugestão quando a quantidade de embalagens é omitida,
mantendo o valor informado manualmente quando presente.

Propriedades agora possuem `bp_cvale`, campo textual opcional com até 40 dígitos,
preservando zeros à esquerda. O formulário permite cadastrar, editar e limpar.
O BP preenche o campo BEP já existente no faturamento somente para C.Vale,
incluindo o relatório e o PDF. O código do envio pode ser ajustado sem alterar
o cadastro. Outras empresas não recebem esse código; a API continua rejeitando
BEP enviado explicitamente para outra empresa. Snapshots anteriores permanecem
com os valores originais, mesmo se o BP da propriedade for alterado depois.

Migration aditiva `propriedades.0004_bp_cvale` aplicada localmente; propriedades
existentes receberam campo vazio. Nenhum BP foi inventado ou preenchido para o usuário.

## Arquivos

- `backend/apps/propriedades/models.py` e migration `0004_bp_cvale.py`.
- `backend/apps/estoque/faturamento.py` e `test_bp_embalagens.py`.
- `frontend/src/App.tsx` e `frontend/src/api/propriedades.ts`.
- `frontend/src/pages/Estoque/FaturamentoInsumos.tsx` e `embalagensFaturamento.ts`.
- `frontend/scripts/test-components.mjs`.

## Backup e validações

Backup privado `D:/PROJETOS/AGRO-AI-PRO/backups/sincronizacao-20261001-095335/`:
histórico, código e mudanças dos 13 worktrees, configuração e uploads, com
ZIPs/bundle verificados e hashes registrados. Dumps `postgres.dump` e
`postgres-pre-migration.dump` verificados por `pg_restore --list`, com SHA-256
nos manifestos próprios; o segundo foi realizado antes da atualização do ambiente.

- SQLite: 38 cenários executados; duas falhas na exportação de PDF porque o
  contêiner antigo não tinha `reportlab`, e dois cenários de concorrência ignorados.
  Reconstruída a imagem com as dependências já declaradas nos requirements.
- PostgreSQL isolado `test_bp_embalagens_20261001`: todos os 38 testes aprovados,
  cobrindo propriedades, faturamento, BP, arredondamento, overrides, snapshots,
  PDF e concorrência. Não foram criados envios reais para validar.
- `npm test` e `npm run build`: aprovados; cálculos exatos, edição manual,
  limpeza do BP e envio de zeros à esquerda cobertos no frontend.
- `manage.py check`: aprovado; `makemigrations --check --dry-run`: sem mudanças.
- `docker compose -p agro-ai-pro build backend` e `build frontend`: aprovados.
  Serviços atualizados com `up -d --no-deps --wait --wait-timeout 60`, usando
  `FRONTEND_PORT=5174` no frontend. Os quatro serviços estão saudáveis.
- Interface, bundle atualizado, health pelo proxy e API de propriedades: HTTP 200;
  as três propriedades existentes expõem o campo BP. Migration confirmada aplicada.
- `git diff --check` e revisão dos arquivos da tarefa: aprovados.

Não há script de lint. Permanece o aviso de bundle maior que 500 kB.
Não foi feita validação visual na sessão particular do navegador do usuário.
Sem commit, push ou merge. Para usar o BP, o usuário deve preencher o código
real em Propriedades e atualizar a página do faturamento.
