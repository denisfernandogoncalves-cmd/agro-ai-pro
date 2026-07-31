# API de Importações

O módulo `importacoes` recebe planilhas XLSX e persiste somente um preview de
staging auditável. Ele não cria `MovimentacaoGraos`, não altera saldos e não
modifica o arquivo enviado.

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

## Idempotência e auditoria

O SHA-256 do arquivo completo é único em `LoteImportacao`. Reenviar exatamente
o mesmo conteúdo retorna `409 Conflict` com o lote existente. Linhas repetidas
dentro de um arquivo não são descartadas: permanecem auditáveis e recebem uma
advertência que aponta para a primeira ocorrência.

Lotes e linhas são somente leitura pela API e pelo admin. As chaves estrangeiras
usam `PROTECT`, preservando o histórico associado.

## Dados normalizados e estrutura

O preview tambem normaliza `cadpro_numero`, cultura, safra e a classificacao
provisoria `PADRAO`. Como o dominio atual de graos ainda nao possui entidades
proprias de CAD/PRO e classificacao, esses valores permanecem no JSON de
staging para confirmacao humana; nenhuma entidade definitiva e criada.
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

## Limite funcional

Esta versão encerra o fluxo no preview. A associação com `graos` é apenas uma
referência preliminar para revisão: nenhum serviço de movimentação é chamado,
nenhuma entrada ou saída definitiva é gerada e nenhum saldo é recalculado ou
alterado.

## Migration e validação

A migration inicial é:

```text
backend/apps/importacoes/migrations/0001_initial.py
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
