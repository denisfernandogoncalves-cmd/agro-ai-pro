# Extrato, duplicidades, romaneios, estoque físico e backup

Cinco melhorias autorizadas pelo Product Owner em 07/10/2026.
Branch: codex/melhorias-gestao-transferencias-20261003. Mudanças anteriores preservadas.
Backup completo verificado e restaurado em PostgreSQL isolado:
`backups/agro-ai-pro-2026-10-07-091328-332106`.

Aceite: extrato cronológico paginado por terceiro com saldo por produto/safra;
duplicidade informativa na conferência antes de salvar; busca de entradas com
produto, terceiro, placa, número e período; contagem física persistida com
saldo próprio/terceiros, diferença, data, responsável e justificativa, sem ajuste
automático; situação administrativa do backup completo com atraso após sete dias.
Reutilizar confirmação compacta, exportadores, movimentos e permissões.
Testar saldo acumulado e paginação, correções/estornos, filtros, permissões,
contagens e reenvio, ausência/atraso de backup, frontend e migrations.

## Implementação e limites

- Extrato: `GET /api/graos/terceiros/extrato/`, terceiro obrigatório,
  produto/safra opcionais, 25 movimentos por página. Saldo acumulado por
  produto/safra inclui todos os armazéns e estornos, inclusive antes da página.
  A classificação atual do recebimento define o agrupamento; os snapshots de
  correções e movimentos originais continuam preservados no histórico.
- Duplicidades: adicionadas à prévia de pesagem existente, considerando
  produtor/terceiro, placa normalizada, data, produto, safra e bruto.
  Cancelados/substituídos e o registro em edição são excluídos. Aviso permite
  confirmação e não substitui a idempotência nem os bloqueios existentes.
- Romaneios de entrada: filtros combinados por produto, terceiro, período e
  origem, além da busca existente por número/placa. Período inclusivo,
  limpeza de filtros e paginação preservados.
- Estoque físico de grãos: prévia `GET /api/core/conferencia-estoque/previa/`;
  consulta e registro `GET/POST /api/core/conferencia-estoque/`. Armazém,
  produto, safra, data, peso e justificativa obrigatórios. Guarda snapshot dos
  saldos próprio e de terceiros atuais na gravação, diferença, responsável e
  horário. A data informada não transforma o snapshot em saldo histórico.
  Trava de armazém, chave de reenvio e registros imutáveis. Nenhum ajuste
  automático de saldo. Disponível em Cargas/Terceiros e Produção e saldos;
  exige consultar/cadastrar em uma dessas áreas conforme a ação.
- Backup: `GET /api/core/backup-status/`, apenas administradores; situação
  no painel inicial e na tela de backup. Usa manifesto, arquivos presentes
  com tamanho esperado e prova de hashes/CRC/restauração isolada. Mostra as
  datas da cópia e da verificação; revalidar cópia antiga não renova sua idade.
  Atraso após sete dias da cópia. Não restaura, não recalcula hashes em cada
  consulta e não expõe caminhos privados absolutos. A tela não agenda backups.

Arquivos principais: graos/extrato_terceiros.py, conferencia_pesagem.py,
conferencia_estoque.py, models.py e migration 0020; core/backup_status.py e URLs;
ExtratoTerceiro, ConferenciaEstoque, StatusBackup, ListaRomaneiosEntrada;
integração nas páginas existentes; testes backend/frontend.
Nenhuma dependência adicionada.

## Evidências de validação

- Backup inicial e pré-migration completos, hashes/CRC e restauração isolada
  aprovados. Pré-migration: `backups/agro-ai-pro-2026-10-07-092617-857106`.
- Migration `graos.0020_conferenciaestoque` aditiva aplicada localmente.
- Django check aprovado; `makemigrations --check --dry-run`: sem alterações.
- Backend direcionado: extrato/contagem, backup, conferência de pesagem,
  terceiros, painel e documentos/Excel: 64 casos SQLite (60 aprovados,
  quatro ignorados de concorrência) e **64 aprovados em PostgreSQL** novo
  e isolado. Banco operacional e uploads preservados.
- Comando SQLite: `docker compose -p agro-ai-pro exec -T -w /app/backend
  backend python manage.py test apps.graos.test_extrato_contagem
  apps.core.test_backup_status apps.graos.test_conferencia_resumo
  apps.graos.test_terceiros apps.core.test_evolucao
  apps.core.test_documentos_excel --settings=config.settings.test --noinput`.
- PostgreSQL: runner privado `backups/testar_melhorias_postgres.py`, com banco
  de testes exclusivo criado pelo Django, incluindo os quatro casos de concorrência.
- Frontend: `npm test`, TypeScript/Vite `npm run build` e build Docker aprovados;
  `git diff --check` aprovado. Não há script de lint separado.
- Conferência autenticada: backup em dia, cinco movimentos com estornos e
  saldo acumulado de 47.160 kg; físico 94.000 kg versus sistema 94.200 kg,
  diferença -200 kg, somente prévia. Filtros DENIS/Soja/06–06 de outubro
  retornaram o romaneio #3. Largura 360 px sem transbordamento horizontal.
  Nenhum recebimento ou contagem de teste gravado no banco operacional.

As cinco melhorias foram aplicadas localmente. Sem commit, push ou merge.
