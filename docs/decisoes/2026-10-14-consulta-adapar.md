# Consulta ADAPAR — leitor e extração seletiva

Solicitação: recuperar a busca automática que mostrava leitor PDF indisponível ao
digitar FOLICUR. A dependência pdfplumber já estava declarada, mas não existia na
imagem ativa. Backend reconstruído pelo Dockerfile do projeto, sem instalar pacotes
manualmente dentro do contêiner nem modificar cadastros.

A primeira validação real expôs outro problema: extrair texto/layout de todas as
142 páginas com pdfplumber retinha mais de 2 GiB e demorava excessivamente. Somente
o contêiner temporário desse teste foi interrompido; o backend ativo permaneceu
separado. A extração passou a localizar páginas por texto nativo com PDFium e ler
as tabelas apenas nas páginas correspondentes. Recursos são fechados explicitamente;
lock local protege o acesso concorrente à biblioteca nativa. Pypdfium2 já vinha como
dependência de pdfplumber e agora também consta como dependência direta declarada.

Fonte: lista oficial vinculada pelo portal ADAPAR, atualização 09/10/2026,
https://www.adapar.pr.gov.br/sites/adapar/arquivos_restritos/files/documento/2026-10/lista_0.pdf.
Nenhuma composição foi inferida pelo nome nem alterada manualmente na consulta.

## Verificações

- Backup anterior à atualização: visual-20261014-231951. Novo backup verificado
  antes da ativação final: visual-20261014-233431. Backups anteriores preservados.
- Imagem com pdfplumber 0.11.10 e pypdfium2 5.14.0: 136 testes de estoque,
  correções e autenticação aprovados em PostgreSQL temporário exclusivo.
- Três testes novos da extração seletiva aprovados: página correspondente apenas,
  nome ausente sem extração de tabelas e rejeição de cabeçalho desconhecido.
- Consulta real autenticada na imagem candidata: HTTP 200 em 9,44 s, um resultado,
  FOLICUR 200 EC, FUNGICIDA, TEBUCONAZOL, 200 g/L, registro 2895, lista de 09/10/2026.
- Token de seleção aceito pelo serializer, sem executar save. Quantidade de produtos
  igual antes/depois: 60. Nenhum produto foi criado ou modificado por essa validação.
- Backend local atualizado e saudável. Consulta autenticada repetida no serviço ativo:
  HTTP 200 em 6,66 s para FOLICUR 200 EC; seleção validada e 60 produtos preservados.

Arquivos: backend/apps/estoque/adapar.py, test_adapar.py e requirements/base.txt.
Sem alteração de schema, frontend, permissões ou regras de negócio nesta tarefa.
Sem commit/push/merge. A publicação oficial é informativa; a aplicação mantém o
link da origem e a seleção explícita antes de preencher/salvar os campos.

## Complemento — empresa e teste online

Backup verificado visual-20261014-234442 antes das alterações. A seleção agora
copia `empresa` para `fabricante`, preservando o valor manual quando a fonte não
informar empresa. Rótulo ajustado para “Fabricante / empresa registrante”: a
empresa registrante informada pela ADAPAR não comprova o fabricante industrial.
Cadastros existentes não foram alterados. Testes frontend, TypeScript e Vite
aprovados; imagem frontend ativada na porta 5174 e saudável. Diff sem erros.

Teste público online: formulário pesquisar.asp usa facapesquisa.asp e envia POST
para resultadoPesquisa.asp em https://celepar07web.pr.gov.br/agrotoxicos/.
Consulta por numeroRegistro=2895 e filtros restantes null retornou HTTP 200 em
0,86 s, FOLICUR 200 EC e empresa registrante Bayer S.A., com link listar.asp Cod=486.
O formulário inicial traz listas extensas. O acesso apresentou falha de resolução
na rede restrita; o teste foi concluído com acesso externo autorizado.
Não foi implementada integração automática com essas páginas nesta etapa:
extração completa dos detalhes e estabilidade ainda precisam ser validadas.
A busca automática existente continua baseada no PDF oficial.
