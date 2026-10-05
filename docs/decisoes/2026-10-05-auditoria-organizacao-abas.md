# Auditoria de organização por abas

05/10/2026. Escopo solicitado: analisar quais temas se beneficiam de abas. Auditoria da composição atual dos componentes de páginas e conferência visual autenticada de Vendas. As demais recomendações se baseiam no código atual, não em conferência visual completa de cada módulo. Recomendações não implementadas neste incremento; nenhum menu/permissão alterado.

| Prioridade | Módulo | Organização recomendada | Fundamentação atual |
| --- | --- | --- | --- |
| Alta | Vendas | Nova venda; Vendas registradas; Romaneios | Cadastro, consulta, detalhe e documentos disputam a mesma página. Romaneios precisam busca independente e lista paginada. |
| Alta | Cargas colhidas | Cargas próprias; Terceiros; Romaneios | ProducaoTerceiros é inserido antes do cadastro/lista próprios. Recebimentos, saldos e saídas de terceiros merecem área clara sem confundir médias. Registrar nova carga deve ser botão/formulário da aba pertinente. |
| Alta | Estoque | Disponibilidade; Compras; Movimentações; Lotes | ComprasEstoque, DisponibilidadeEstoque, movimentação, posições e cadastro de lotes compartilham conteúdo longo/recolhível. |
| Alta | Cadastros agrícolas | Armazéns; Produtos; Parceiros; Contratos | Vários cadastros independentes na mesma página. Locais de estoque agrupados com armazéns, mantendo diferenças claras. |
| Média | Faturamento de insumos | Novo faturamento; Envios realizados | Formulário, prévia e HistoricoFaturamento na mesma tela. Prévia continua no fluxo do novo faturamento, sem aba extra. |
| Média | Financeiro | A pagar; A receber; Liquidados | Consulta hoje depende de filtros tipo/status. Abas seriam atalhos dos mesmos filtros, mantendo busca/período e botão Novo lançamento. Atrasados como filtro rápido, não outra aba. |
| Média | Máquinas | Frota; Uso e combustível; Manutenções | Cadastro/registro, frota/horímetros e manutenções coexistem na página. |
| Média | Produção e saldos | Resumo; Posições; Movimentações | Consolidado por propriedade, dimensões e rastreabilidade recente têm usos distintos. |
| Baixa | Transferências | Manter cadastro recolhível e histórico paginado | Apenas duas tarefas principais; não precisa ampliar navegação neste momento. |
| Baixa | Usuários | Lista com edição contextual e permissões no editor | Permissões dependem do usuário selecionado; aba global separada pode perder contexto. |
| Baixa | Relatórios | Refinar agrupamento existente | Já existe catálogo agrupado com seleção de relatório e paginação. Evitar duplicar mais níveis de abas. |
| Baixa | Painel, Clima, Mercado, Backup | Manter navegação atual | Finalidade única; mais abas não resolvem problema concreto identificado. |

Critérios para eventual implementação: abas internas ao módulo (não navegador), nomes claros, até quatro visíveis quando possível, foco/teclado acessíveis, seleção identificada, busca/paginação preservadas por aba e proteção contra perda de formulário ao trocar. Não desmontar formulários sujos silenciosamente. Respeitar permissões por módulo/ação em consulta, edição e impressão. Montar/carregar apenas conteúdo necessário sem revelar dados de setores não autorizados. Impressão somente do documento/aba pertinente, sem misturar conteúdo oculto.

Ordem prática: Vendas, Cargas, Estoque e Cadastros primeiro; demais conforme uso. Abas não substituem paginação: mil romaneios precisam limite de linhas e busca direta. A paginação atual dos romaneios é no cliente; volumes muito maiores justificam endpoint paginado no servidor em escopo posterior.

Fontes locais: frontend/src/pages/Vendas/VendasPage.tsx; CargasColhidas/CargasColhidasPage.tsx e ProducaoTerceiros.tsx; Estoque/EstoquePage.tsx e FaturamentoInsumos.tsx; CadastrosAgricolas/CadastrosAgricolasPage.tsx; Financeiro/FinanceiroPage.tsx; Maquinas/MaquinasPage.tsx; ProducaoSaldos/ProducaoSaldosPage.tsx; Usuarios/UsuariosPage.tsx; Relatorios/RelatoriosPage.tsx.


## Resultado da implementação autorizada

Os sete módulos prioritários (Vendas, Cargas, Estoque, Cadastros, Faturamento, Financeiro e Máquinas) receberam as abas recomendadas, com Todos adicional no Financeiro para preservar consultas completas. Validações, preservação de permissões/formulários, compactação do espaço e limitações registradas em docs/decisoes/2026-10-05-abas-modulos.md. A descrição inicial acima corresponde à auditoria anterior à implementação; demais propostas seguem futuras.
