# API de Importações

O módulo `importacoes` recebe planilhas XLSX, persiste um preview de staging
auditável e permite sua confirmação definitiva por ação explícita. Upload e
preview nunca criam `MovimentacaoGraos`; somente o endpoint de confirmação pode
fazê-lo.

Todas as rotas exigem autenticação JWT.

## Referencia homologada

A planilha operacional de referencia desta entrega possui SHA-256:

```text
03BA0C45422BF5C88657090838CF762D4508159A3AB66E73BD83AC4BA4A1D42A
```

Este hash substitui formalmente a referencia anterior, indisponivel no
historico local. A alteracao foi registrada explicitamente para preservar a
rastreabilidade; a planilha nao faz parte do repositorio Git.

## Formato suportado

O leitor reconhece o layout operacional da planilha de soja:

- abas numeradas de `1` a `45`: recebimentos de produção por propriedade;
- aba `SAÍDA`: expedições;
- aba `TERCEIROS`: recebimentos de terceiros.

As demais abas são registradas em `metadados.planilhas_ignoradas`. Linhas sem
data e sem peso são tratadas como vazias e não integram o preview.

O arquivo deve possuir extensão `.xlsx` e tamanho máximo de 10 MB. O container
ZIP interno é validado, não pode ser criptografado, pode conter no máximo 5.000
entradas e até 100 MB descompactados. A leitura usa `openpyxl`, declarado como
dependência normal do backend.

## Preview

```text
POST /api/importacoes/lotes/preview/
Content-Type: multipart/form-data

arquivo=<planilha.xlsx>
```

A resposta `201 Created` contém o lote, até 100 linhas iniciais e o indicador
`preview_limitado`. O conjunto integral fica disponível nos endpoints de
consulta.

Um preview sem erros bloqueantes recebe o estado `pronto_confirmacao`. O estado
legado `concluido` continua elegível para preservar a compatibilidade dos lotes
criados antes desta entrega. Lotes com erro permanecem em `com_erros`.

Cada linha preserva:

- aba e número da linha original;
- tipo `producao`, `saida` ou `terceiros`;
- dados originais e normalizados;
- hash SHA-256 do conteúdo normalizado;
- status `valida`, `advertencia` ou `erro`;
- listas de erros e advertências;
- associação preliminar, quando inequívoca, com propriedade e lote de grãos.

Erros incluem datas e pesos inválidos, campos obrigatórios ausentes, peso
líquido maior que o bruto e percentuais fora de 0 a 100. Advertências incluem
safra atípica, contrato ausente, linha potencialmente duplicada e associação
não encontrada ou ambígua.

## Confirmação definitiva

```text
POST /api/importacoes/lotes/{id}/confirmar/
Content-Type: application/json
```

Corpo obrigatório:

```json
{
  "confirmar": true,
  "idempotency_key": "confirmacao-safra-2026-0001"
}
```

`confirmar=true` impede confirmação implícita. A chave deve ter entre 8 e 100
caracteres, começar por letra ou número e usar somente letras, números, ponto,
dois-pontos, sublinhado ou hífen.

Além de autenticação JWT, o usuário precisa da permissão Django
`importacoes.confirmar_loteimportacao`. Usuários sem essa permissão recebem
`403 Forbidden`.

A resposta inicial usa `201 Created` e contém lote, estado, chave, usuário e
horário da confirmação, totais, IDs das movimentações, linhas rejeitadas,
indicador de replay e o saldo calculado dos lotes de grãos afetados.

Repetir a mesma chave no mesmo lote confirmado devolve a resposta persistida
com `200 OK` e `replay_idempotente=true`, sem novo lançamento. Uma chave
diferente em lote confirmado ou uma chave já usada por outro lote recebe
`409 Conflict`.

## Validações bloqueantes

Todas as linhas são validadas antes do primeiro lançamento:

- lote e linha em estado elegível, sem erros bloqueantes;
- propriedade e lote de grãos associados;
- coerência de propriedade, cultura e safra com o lote de grãos;
- tipo mapeável para entrada ou saída;
- data válida, quantidade Decimal positiva e unidade em quilogramas;
- origem para produção/terceiros e destino para saídas;
- ausência de movimentação vinculada;
- ausência de hash funcional duplicado no lote ou já confirmado.

A confirmação exige CAD/PRO ativo e vínculo ativo com a propriedade produtora
do lote de grãos. Se a planilha informa CAD/PRO, seu código deve coincidir com
o cadastro. Classificação, cultura e safra também devem coincidir. A associação
usa `LoteGraos.propriedade`, independente da propriedade da armazenagem;
armazenagem externa é suportada. Lotes históricos sem propriedade produtora
explícita exigem revisão cadastral antes de nova importação.

## Atomicidade, saldos e rollback

A operação inteira executa em `transaction.atomic()`, bloqueia o lote e suas
linhas e adota política tudo ou nada. Cada linha chama exclusivamente
`apps.graos.services.registrar_movimentacao`. O importador não cria
`MovimentacaoGraos` diretamente e não atualiza saldos: o adaptador oficial
encaminha entradas para crédito de produção e saídas para ajuste, atualizando
as posições e o ledger na mesma transação. A restrição parcial
`importacao_hash_confirmado_unico` impede duplicidade funcional também no banco.

Se qualquer chamada intermediária falhar, o banco reverte todas as
movimentações, vínculos e a transição `confirmando`. Depois do rollback, uma
transação independente registra somente a tentativa de auditoria e marca o
lote como `falhou`; nenhum efeito parcial permanece em `graos`.

As transições controladas são:

```text
concluido (legado) ─┐
pronto_confirmacao ─┼─> confirmando ─> confirmado
falhou ─────────────┘          └─────> falhou
```

`com_erros` não pode entrar no fluxo.

## Idempotência e auditoria do preview

O SHA-256 do arquivo completo é único em `LoteImportacao`. Reenviar exatamente
o mesmo conteúdo retorna `409 Conflict` com o lote existente. Linhas repetidas
dentro de um arquivo não são descartadas: permanecem auditáveis e recebem uma
advertência que aponta para a primeira ocorrência.

Lotes e linhas são somente leitura pela API e pelo admin. As chaves estrangeiras
usam `PROTECT`, preservando o histórico associado.

## Dados normalizados e estrutura

O preview também normaliza `cadpro_numero`, cultura, safra e a classificação
provisória `PADRAO`. Esses valores permanecem no JSON de staging para revisão,
sem criar entidades definitivas. A confirmação compara os valores com o lote
e o CAD/PRO existentes.
Cabecalhos obrigatorios sao validados por aba, e formulas de peso liquido sao
preservadas junto ao valor calculado usado no preview.

Os metadados do lote registram abas processadas e ignoradas, cabecalhos
reconhecidos e totais de linhas duplicadas e ignoradas.

## Consultas

```text
GET /api/importacoes/lotes/
GET /api/importacoes/lotes/{id}/
GET /api/importacoes/linhas/
GET /api/importacoes/linhas/{id}/
```

Lotes aceitam filtro `status`, busca por nome/hash e ordenação. Linhas aceitam
filtros `lote`, `status`, `tipo`, `planilha`, `propriedade` e `lote_graos`,
além de busca e ordenação.

Cada confirmação registra o lote, a chave, o usuário, o horário, o resultado e
eventual falha em `ConfirmacaoImportacao`. A linha confirmada guarda um vínculo
protegido e individual com `MovimentacaoGraos`. Nome, SHA-256, dados originais,
dados normalizados, erros e advertências do preview não são alterados.

## Migration e validação

A migration inicial e a migration de confirmação são:

```text
backend/apps/importacoes/migrations/0001_initial.py
backend/apps/importacoes/migrations/0002_alter_loteimportacao_options_and_more.py
backend/apps/importacoes/migrations/0003_linhaimportacao_importacao_hash_confirmado_unico.py
```

Comandos principais:

```powershell
python manage.py makemigrations --check --dry-run
python manage.py test apps.importacoes
python manage.py test apps.graos
python manage.py test
python manage.py check
```

O contrato OpenAPI está disponível em `GET /api/schema.json`, Swagger e ReDoc.

## Interface

Em **Importações**, envie o XLSX, revise o lote e consulte os dados, associações,
erros e advertências de cada linha. Para confirmar, marque a declaração de
revisão e use **Confirmar importação**. A permissão é informada pelo campo
`pode_confirmar`; o endpoint sempre revalida a autorização.

A tela consulta lotes e linhas com `?page=1`, em páginas de 50 itens. Sem `page`,
a API preserva a resposta legada em lista. Um lote pode exigir revisão cadastral
mesmo sem erros de leitura; as validações definitivas continuam no endpoint.

Uma tentativa mantém sua chave na sessão do navegador quando a resposta é
incerta, permitindo recuperar o resultado sem duplicação. Uma rejeição `409`
permite uma nova tentativa. A tela não confirma automaticamente após upload.
Não foi acrescentada edição dos dados de staging.
