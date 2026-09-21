# Grupos de propriedades para colheita

Continuação da solicitação de 06/09/2026, implementada em 07/09/2026.

## Uso

Em **Talhões → Grupos de colheita**, informe um nome e selecione um CAD/PRO
para cada propriedade participante. Um CAD/PRO pode atender várias propriedades;
um grupo também pode conter CAD/PROs diferentes. É possível editar e inativar grupos.

Em **Cargas colhidas → Usar grupo de colheita**, selecione o grupo para preencher
as propriedades e seus CAD/PROs. A lista manual permanece editável. O seletor
é uma ação de preenchimento e retorna ao texto inicial depois de aplicar.
Talhões previamente selecionados são limpos para permitir a revisão do novo conjunto.
Peso, cultura, safra, armazenagem e demais campos da carga são preservados.

O grupo não guarda percentuais: o rateio continua proporcional às áreas declaradas
atuais das propriedades, usando o serviço existente, inclusive o ajuste do resíduo
de arredondamento. O compartilhamento de CAD/PRO não elimina parcelas por propriedade.
A carga conserva o contexto e o rateio calculados ao salvar. Editar o grupo depois
não modifica cargas anteriores. Não há associação obrigatória da carga ao grupo.

## API autenticada

Base: `/api/talhoes/grupos-colheita/`.

- `GET` e `POST` na base: listar e cadastrar.
- `GET` e `PATCH` em `{id}/`: consultar e editar/inativar.
- `GET opcoes/`: vínculos ativos de propriedades com CAD/PROs ativos.
- Exclusão não disponível; use `ativo: false`.

Corpo de criação: `nome`, `ativo` (opcional, padrão verdadeiro), `vinculos`
(lista não vazia de UUIDs retornados por `opcoes/`). Nomes são únicos.
A mesma propriedade não pode aparecer duas vezes. Vínculos inexistentes ou inativos
são rejeitados. A resposta inclui `membros`, com propriedade, nome, CAD/PRO, código e
`disponivel`. Um vínculo inativado continua visível no grupo, mas impede sua aplicação
ao formulário. A API de cargas mantém sua própria validação dos vínculos ao salvar.

## Arquivos e banco

- `backend/apps/talhoes/models.py`: `GrupoPropriedadesColheita`.
- `backend/apps/talhoes/grupos.py`: validação, API e opções.
- `backend/apps/talhoes/urls.py`: rotas.
- `backend/apps/talhoes/migrations/0008_grupopropriedadescolheita.py`: tabela nova
  e relação com vínculos CAD/PRO; não reescreve registros existentes.
- `frontend/src/api/gruposPropriedades.ts`: cliente e aplicação ao formulário.
- `frontend/src/pages/Talhoes/GruposPropriedadesPanel.tsx`: cadastro.
- `frontend/src/pages/Talhoes/TalhoesPage.tsx`: integração do cadastro.
- `frontend/src/pages/CargasColhidas/CargasColhidasPage.tsx`: seletor.
- Testes em `backend/apps/talhoes/tests/test_grupos_colheita.py` e
  `frontend/scripts/test-components.mjs`.

## Preservação

Branch: `codex/grupos-propriedades-colheita`, a partir de `489f66a`.
Backups privados ignorados pelo Git no checkout `runtime-origin-main`:

- `backups/retomada-2026-09-07-075613-124599`: código inicial, uploads e banco
  físico parado; leitura integral, CRC dos ZIPs e SHA-256.
- `backups/retomada-2026-09-07-080159-924450`: código alterado, uploads e dump
  PostgreSQL antes da migration; leitura integral do dump e hashes no manifesto.

Sem novas dependências. Sem commit, push ou merge nesta entrega.

## Validação em 07/09/2026

- `python manage.py check`: aprovado.
- `python manage.py makemigrations --check --dry-run`: nenhuma alteração pendente.
- `python manage.py test --settings=config.settings.test`: 343 testes, aprovado,
  com 36 cenários ignorados pela suíte nessa configuração SQLite.
- `python manage.py test apps.talhoes.tests.test_grupos_colheita apps.graos.test_consultas_rateios --keepdb`:
  14 testes aprovados em PostgreSQL. Foi usado `POSTGRES_DB=grupos_20260907_0805`
  para isolar a execução; `test_grupos_20260907_0805` foi preservado.
  A primeira tentativa encontrou `test_agro_ai_pro` existente e foi interrompida
  sem excluir nem modificar esse banco.
- `npm.cmd test`: testes de componentes e 13 cenários de autenticação aprovados,
  incluindo verificações novas de preenchimento, preservação dos campos e grupo inválido.
- `npm.cmd run build` e `docker compose -p agro-ai-pro build frontend`: aprovados.
  Permanece aviso de bundle JavaScript acima de 500 kB.
- Não há script de lint configurado no frontend.
- Migration `talhoes.0008_grupopropriedadescolheita` aplicada no ambiente local.
- `git diff --check`: aprovado.

Os testes de interface são automatizados por renderização e funções; não foi
realizada uma sessão visual autenticada de ponta a ponta nesta entrega.
