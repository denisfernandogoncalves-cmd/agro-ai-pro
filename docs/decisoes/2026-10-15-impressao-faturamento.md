# Impressão de faturamento de insumos — 15/10/2026

- Corrigida a aba intermediária oculta pelo CSS de impressão: o painel ativo mantém o relatório visível; formulário, ações e histórico ficam ocultos.
- Nome do arquivo e metadado de título do PDF: `PRODUTO - TOTAL EMBALAGEM DE CONTEÚDO UNIDADE - SAFRA - DD-MM-AAAA`, conforme o exemplo do Product Owner. Caracteres incompatíveis com nomes de arquivo são substituídos por hífen.
- Total de embalagens e safra exibidos no cabeçalho da impressão e do PDF exportado.
- Safra opcional no envio, preservada no snapshot JSON. Registros antigos mostram “Não informada”; nenhuma safra é presumida e nenhuma migration é necessária. Safra vazia não altera a assinatura anterior de idempotência.
- Backup prévio verificado de código, alterações locais, uploads e banco: `D:/PROJETOS/AGRO-AI-PRO/backups/agro-ai-pro-2026-10-15-073201-514424`, manifesto SHA256, ZIP CRC e leitura integral do dump.

## Verificação

- 26 testes PostgreSQL de faturamento e coordenadas aprovados; banco de testes separado.
- Suite frontend aprovada; testes adicionais de título exato e total de embalagens aprovados.
- TypeScript e Vite aprovados com saída separada: a pasta dist anterior tem restrições ACL no Windows.
- Edge headless em mídia print: relatório/tabela visíveis e formulário/histórico ocultos. PDF fictício renderizado e inspecionado.
- PDF ReportLab fictício: uma página, título exato e total no cabeçalho conferidos por extração e renderização visual.
- Revisão do diff restrita aos arquivos da tarefa; sem alteração de regras de baixa, dados reais ou migrations.
- Alguns arquivos existentes recusaram gravação por ACL do Windows. A conta DENIS recebeu permissão Modify nos arquivos de código editáveis e no script de testes frontend; o teste backend foi atualizado por substituição no diretório autorizado. Nenhuma permissão de acesso ao aplicativo foi alterada.

Sem commit, push ou merge. Impressão física e diálogo nativo de salvar PDF dependem do navegador do usuário; verificação automatizada realizada com dados fictícios.
