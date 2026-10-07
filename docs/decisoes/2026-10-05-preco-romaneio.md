# Preço negociado e modelo do romaneio de venda

## Escopo

O cadastro de contratos comerciais passou a aceitar, opcionalmente, o valor negociado e a unidade do valor: quilograma ou saca de 60 kg. Contratos antigos permanecem válidos sem preço. Quando há preço, a API da venda expõe o valor e a unidade para o romaneio sem alterar saldo, estoque, médias ou cálculos de quantidade. Na via do arquivo, o valor apresentado é o total da saída: peso líquido em kg multiplicado pelo preço por kg; para preço por saca, o peso líquido é dividido por 60 antes da multiplicação.

O romaneio de saída mantém duas vias completas em uma página A4. A primeira via é identificada como **Via do cliente** e a segunda como **Via do arquivo**. O valor negociado aparece somente na via do arquivo. O modelo segue a folha de referência: cabeçalho com romaneio e saída, blocos para destinatário, data, produto/safra e contrato, pesagem em **Peso bruto**, **Tara**, **Peso líquido** e **Sacas/60**, painel lateral de qualidade e campos de nota do produtor, motorista, placa, armazenagem, observações e assinaturas. A classificação padrão e a nota da empresa foram removidas do romaneio.

## Implementação

- `ContratoComercial.preco_venda` é decimal opcional com duas casas e validação positiva.
- `ContratoComercial.unidade_preco` usa `kg` ou `sc`, com `kg` como padrão para registros existentes.
- A migration `vendas.0010_contratocomercial_preco_venda_unidade_preco` é aditiva.
- O formulário de Cadastros agrícolas permite editar, limpar e selecionar a unidade do valor; a listagem mostra o preço quando preenchido.
- `VendaGraosSerializer` expõe o preço do contrato como campos somente leitura para o frontend.
- `DadosComprovante.camposViaArquivo` acrescenta o total calculado exclusivamente à segunda via, preservando todos os comprovantes existentes.
- O modelo especializado de romaneio é aplicado tanto à prévia quanto ao HTML baixado, com as duas vias na ordem cliente e arquivo.
- O Localizador de romaneios também omite a nota da empresa nos detalhes resumidos.

## Verificações

## Continuação — downloads PDF/Excel e tema preto no branco

- A prévia do romaneio oferece downloads PDF e Excel (`.xlsx`) reais nos botões de cada saída, tanto no cadastro da venda quanto no localizador.
- Os arquivos são gerados no backend a partir dos dados persistidos; a saída deve pertencer à venda indicada. Ambos contêm duas vias; o total negociado fica só na via do arquivo.
- O PDF usa A4 retrato. A planilha configura impressão em uma página A4 e aplica fundo branco com texto preto.
- Os downloads usam endpoints autenticados da ação `imprimir` do módulo Vendas. Foram acrescentados testes de formato, fórmula/kg, duas vias e vínculo venda/saída.
- O tema das telas passa a usar letras pretas, superfícies brancas, bordas cinza e foco visível de alto contraste. Os estilos de impressão existentes são preservados.
- Validação desta continuação: 83 testes do app Vendas passaram em SQLite isolado (9 skips por exigirem PostgreSQL real); quatro testes específicos dos downloads passaram, incluindo A4/uma página, `.xlsx` ajustado a uma página, fórmulas por kg e saca e permissão de imprimir; `makemigrations --check --dry-run` sem mudanças; `npm test`, `tsc --noEmit` e build Vite passaram.
- Uma execução do banco PostgreSQL de testes persistente não foi usada como evidência: falhou por duplicidade de usuário de execuções anteriores. O banco não foi apagado nem limpo. O build padrão com `tsc -b` também encontrou bloqueio de escrita no `tsconfig.tsbuildinfo` preexistente; os comandos equivalentes sem arquivo incremental (`tsc --noEmit` e Vite build) passaram.
- Backup validado antes de atualizar os serviços locais: `backups/agro-ai-pro-2026-10-05-223851-206768`; relatório de restauração isolada: `verificacao-restauracao-20261005-223859-690962.json`.
- Após a atualização, frontend `127.0.0.1:5174` e API `/api/health/` responderam com sucesso; o painel autenticado carregou no navegador. Não foram abertos romaneios nem baixados documentos de registros reais; os endpoints PDF/Excel foram exercitados em fixtures isoladas.
- Commit enviado à branch da PR #29; CI frontend e backend concluíram com sucesso. A descrição da PR foi preservada, sem merge ou publicação em produção.

- Backup verificado antes da migration: `backups/agro-ai-pro-2026-10-05-175703-223245`.
- Relatório de restauração isolada: `verificacao-restauracao-20261005-175713-586650.json`; SHA256/CRC e PostgreSQL isolado aprovados.
- `docker compose -p agro-ai-pro exec backend sh -c "cd /app/backend && python manage.py migrate"` aplicou a migration sem tocar em registros operacionais.
- `docker compose -p agro-ai-pro exec backend sh -c "cd /app/backend && python manage.py test apps.vendas.test_alteracoes --keepdb --verbosity 2"`: 14 testes aprovados.
- `npm.cmd --prefix frontend test`: quatro conjuntos de testes aprovados, incluindo o modelo de romaneio, a ordem das vias, as duas seções A4, qualidade e valor exclusivo da via do arquivo.
- `docker compose -p agro-ai-pro build frontend`: TypeScript e Vite aprovados; o build direto no Windows encontrou apenas a permissão do cache `tsconfig.tsbuildinfo` preexistente.
- Navegador local 5174: campos Valor vendido e Valor por conferidos em Cadastros agrícolas; Vendas/Romaneios exibiu lista paginada e a legenda de detalhes deixou de apresentar nota da empresa.

Nenhum usuário, permissão ou registro real foi criado, editado ou excluído para teste. A impressão nativa/PDF não foi acionada; a garantia de uma página A4 permanece coberta pelo ajuste automático e pelos testes DOM existentes. O frontend local respondeu com HTTP 200; a sessão autenticada do navegador integrado havia expirado antes da conferência visual final da nova prévia.
