# Sprint 2 — Talhões

**Status:** concluída

**Conclusão validada em:** 25/07/2026

## Objetivo

Disponibilizar a gestão completa de talhões vinculados às propriedades, com
dados agronômicos atuais e históricos, consulta eficiente e visualização dos
perímetros já processados.

## Entregas

- model e CRUD REST autenticado de talhões;
- vínculo protegido com Propriedade;
- nome, área, cultura, safra, tipo de solo, altitude e declividade;
- produtividade esperada e produtividade realizada não negativas;
- histórico agronômico por data, cultura, safra e produtividade;
- validação da soma das áreas contra a área da propriedade;
- upload KML seguro, limitado a 5 MB;
- GeoJSON e centroide para visualização;
- busca textual, filtros por propriedade, cultura e safra;
- ordenação e paginação configurável;
- interface React para cadastro, edição, exclusão, filtros e paginação;
- mapa OpenStreetMap do talhão e interface do histórico agronômico;
- administração Django e documentação da API;
- testes de models, serializers, serviços, regras de negócio e endpoints.

## Endpoints

- `GET|POST /api/talhoes/talhoes/`;
- `GET|PUT|PATCH|DELETE /api/talhoes/talhoes/{id}/`;
- `GET|POST /api/talhoes/historicos-agronomicos/`;
- `GET|PUT|PATCH|DELETE /api/talhoes/historicos-agronomicos/{id}/`.

Todos os endpoints exigem autenticação JWT.

## Banco de dados

As migrations da Sprint são:

- `0005_historicoagronomico_talhao_atualizado_em_and_more.py`: adiciona
  produtividade realizada, controle de atualização, histórico agronômico e
  restrições contra produtividades negativas;
- `0006_alter_historicoagronomico_talhao.py`: protege o talhão contra exclusão
  enquanto existirem registros históricos.

## Critérios de aceite validados

- [x] CRUD autenticado;
- [x] vínculo e integridade de área;
- [x] dados agronômicos atuais;
- [x] produtividade esperada e realizada;
- [x] histórico agronômico;
- [x] busca, filtros, ordenação e paginação;
- [x] interface dedicada e mapa;
- [x] migrations consistentes;
- [x] testes backend com PostgreSQL;
- [x] build de produção do frontend;
- [x] documentação atualizada.

## Validação final

- `docker compose config --quiet`: aprovado;
- `docker compose build backend`: aprovado;
- `docker compose up -d`: aprovado;
- `python manage.py migrate`: nenhuma migration pendente;
- `python manage.py check`: aprovado;
- `python manage.py makemigrations --check --dry-run`: nenhuma alteração;
- `python manage.py test`: 32 testes aprovados com PostgreSQL;
- fluxo HTTP real: autenticação JWT, CRUD, filtro paginado, produtividade,
  histórico e proteção de exclusão aprovados;
- `npm.cmd test`: três testes de componentes aprovados;
- `npm.cmd run build`: aprovado.

Durante a auditoria, o endpoint JWT foi corrigido para usar objetos `timedelta`
nos tempos de vida dos tokens. A configuração de desenvolvimento também passou
a usar uma chave padrão longa o suficiente para HMAC SHA-256, sem substituir a
obrigação de definir uma chave secreta própria em ambientes reais.

## Limite de escopo

O GeoJSON e o centroide são utilizados somente para visualização. Cálculo
geodésico de área, comparação com a área declarada e tratamento geoespacial
avançado permanecem na Sprint 3.
