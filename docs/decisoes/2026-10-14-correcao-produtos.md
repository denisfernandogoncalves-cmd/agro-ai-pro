# Recuperação da consulta de produtos — 14/10/2026

## Exibição da classe salva — 15/10/2026

A lista de Cadastros agrícolas → Produtos mostrava apenas a categoria genérica,
mesmo com classe agronômica preenchida. Consulta de leitura confirmou ABADIN
72 EC com categoria insumo e classe INSETICIDA ACARICIDA já persistida.
O rótulo agora prioriza a classe agronômica, usando categoria quando vazia.
Alteração localizada em CadastrosAgricolasPage.tsx; sem edição de dados,
modelos, migrations ou regras de classificação.

Backup privado verificado: backups/visual-20261015-091310, código/uploads,
banco, diff e hashes. npm test e npm run build aprovados no Docker; diff
verificado. Frontend local 5174 atualizado. Sem validação visual autenticada,
commit, push ou merge.

Erro observado: GET /api/estoque/produtos/?ordering=nome retornava 500 porque
estoque_produtoestoque.classe_agronomica não existia. Sete campos agronômicos
já estavam no model/serializer, mas sem migration correspondente.

Correção: migration 0007_campos_agronomicos_produto, somente AddField, aplicada
no aplicativo local depois de testes isolados e backup verificado. Campos antigos
não foram editados; nenhum produto, lote ou movimento foi excluído.

O import de pdfplumber passou para a extração da publicação ADAPAR. Importar
o SALT para validar um cadastro comum não deve exigir leitor PDF. Se o leitor
não estiver instalado, a consulta ADAPAR retorna indisponibilidade explícita;
cadastro manual e consulta de produtos continuam funcionando.

Frontend: mantém a lista anterior quando a consulta falha e diferencia falha de
consulta de catálogo vazio. Edição mantém os campos agronômicos; consulta_adapar
é um token write-only transitório e não é lido do cadastro retornado pela API.

## Evidências

- Backups privados preservados: visual-20261014-230707 e, imediatamente antes
  da migration, visual-20261014-231210; código/uploads/dump e manifesto de hashes.
- PostgreSQL temporário exclusivo: apps.estoque e apps.core.test_correcoes_historico,
  98 testes aprovados, incluindo cadastro de produto e efeitos no saldo.
- Frontend Docker: npm test, TypeScript e Vite aprovados; frontend local saudável
  na porta 5174 após atualização. Não inclui a implantação do layout do PR 30.
- Consulta autenticada no aplicativo, sem gravação de registros: HTTP 200,
  60 produtos retornados.
- SHA-256 dos campos originais de todas as linhas, em ordem de ID, igual antes
  e depois: 4542bde651c44c22bf001f9e76db6a08b688f4ed51cf6938c505e8278ccf873a.
- A verificação autenticada usou APIClient com usuário existente; não criou
  senha/token/sessão nem expôs nomes dos produtos.
- Migrations/modelos e diff verificados após a aplicação. Sem commit, push,
  merge ou alteração de outras worktrees nesta correção operacional.

Limite: consulta externa ADAPAR não validada. O leitor PDF ainda precisa estar
instalado na imagem para usar a extração automática. A consulta manual de produtos
foi validada independentemente desse serviço externo.
