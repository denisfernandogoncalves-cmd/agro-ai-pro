# Identificação CAD/PRO no faturamento de insumos — 19/10/2026

- Seleção da propriedade mostra `cad_pro_identificacao`, conforme cadastro: Principal, Secundário ou texto livre. Campo vazio aparece como Não informado.
- Prévia e confirmação copiam a identificação para o resumo histórico, junto do CAD/PRO. Mudanças posteriores na propriedade não alteram esse documento; repetição idempotente mantém o resumo confirmado.
- Impressão e PDF mostram a identificação abaixo do número CAD/PRO. Apelidos permanecem somente na seleção, sem inclusão nos documentos.
- Exportar Excel disponível no lançamento confirmado e no histórico de envios: `GET /api/estoque/faturamentos/{id}/excel/`, usando o mesmo resumo histórico e a permissão imprimir. Reutiliza PlanilhaExportacao existente; identificadores textuais, valores numéricos e proteção contra fórmulas preservados.
- Faturamentos antigos sem o campo exibem Não informado. Não se consulta o cadastro atual para preencher retroativamente nem se alteram documentos reais.

Arquivos: backend `faturamento.py`, `faturamento_pdf.py`, novo `faturamento_excel.py` e testes; frontend API de faturamento, tela/relatório/histórico e testes de componentes. Sem migration, dependência nova ou alteração de regras de estoque.

Backup privado verificado: `D:/PROJETOS/AGRO-AI-PRO/backups/visual-20261019-085108`.

Validações: 31 testes PostgreSQL aprovados, incluindo identificação congelada, reenvio, PDF sem apelido, Excel com identificação e CAD/PRO com zeros iniciais, histórico antigo e permissão de impressão. Testes frontend/TypeScript/Vite/build Docker e Django/migrations/diff aprovados. PDF sintético com Principal/Secundário e BEP renderizado por Poppler e conferido visualmente em uma página; Excel sintético reaberto e células/tipos conferidos. Sem faturamento real criado durante os testes.

Aplicativo local atualizado em 5174; branch `codex/modernizacao-visual-runtime`. Trabalho anterior preservado; sem commit, push ou merge.
