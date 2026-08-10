# API CAD/PRO V1

O módulo `cadpro` mantém o cadastro de CAD/PROs e seus vínculos com propriedades
rurais. A operação atual permanece de usuário único: os registros não possuem
campo de proprietário/tenant e todas as rotas exigem autenticação JWT.

## Entidades e integridade

`CADPro` usa UUID como chave primária e contém `codigo`, `codigo_normalizado`,
`descricao`, `ativo`, `criado_em` e `atualizado_em`. O código normalizado é
gerado pelo backend de forma determinística: remove acentos, espaços e sinais e
converte letras para maiúsculas. A chave resultante é única.

`CADProPropriedade` também usa UUID, protege as duas chaves estrangeiras com
`PROTECT` e impõe unicidade para `(cad_pro, propriedade)`. Um CAD/PRO inativo
não aceita novos vínculos. Inativar um CAD/PRO não remove nem altera os vínculos
existentes, preservando o histórico.

Não existe DELETE público. O campo `ativo` do CAD/PRO é somente leitura na API;
a inativação ocorre exclusivamente pela ação específica e não há reativação
pública nesta versão.

## Serviços públicos

Em `apps.cadpro.services`:

- `obter_cadpro_ativo(cad_pro_id)` retorna o cadastro ativo ou levanta
  `CADPro.DoesNotExist`;
- `validar_vinculo(cad_pro_id, propriedade_id)` retorna o vínculo ativo ou
  levanta `VinculoCADProInvalido`; este é o ponto obrigatório para uma origem de
  produção validar CAD/PRO e propriedade;
- `listar_propriedades_vinculadas(cad_pro_id)` retorna um QuerySet ordenado das
  propriedades ativamente vinculadas a um CAD/PRO ativo.

## Endpoints autenticados

```text
GET  /api/cadpros/
POST /api/cadpros/
GET  /api/cadpros/{id}/
PATCH /api/cadpros/{id}/
GET  /api/cadpros/{id}/propriedades/
POST /api/cadpros/{id}/propriedades/
POST /api/cadpros/{id}/inativar/
```

A listagem aceita `ativo=true|false`, `search` e `ordering`. O POST de vínculo
recebe `{"propriedade": <id>}`. DELETE e PUT respondem `405 Method Not Allowed`.

## Limites da V1

O módulo não altera os domínios de grãos, comercial, relatórios ou frontend.
Integrações de produção devem chamar `validar_vinculo` antes de persistir sua
entidade produtiva; a introdução de um campo CAD/PRO em outros domínios depende
do contrato específico dessas entregas.

## Validação

```powershell
python manage.py test apps.cadpro --settings=config.settings.test
python manage.py check --settings=config.settings.test
python manage.py makemigrations --check --dry-run --settings=config.settings.test
```
