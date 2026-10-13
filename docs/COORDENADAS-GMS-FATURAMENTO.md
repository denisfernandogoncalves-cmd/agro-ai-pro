# Coordenadas GMS e faturamento — 09/10/2026

Decisão do Product Owner: **salvar em GMS; converter somente pelo botão**.

## Comportamento

- Em Propriedades, selecionar graus decimais ou graus, minutos e segundos (GMS).
- GMS conserva o texto informado, com hemisfério N/S na latitude e E/O/W na longitude. Exemplo: `24°18'28,97"S`, `51°42'47,98"O`.
- Salvar, abrir o cadastro, trocar o formato ou emitir faturamento não calcula conversões. Validam-se limites de graus, minutos, segundos e o preenchimento das duas coordenadas.
- **Converter GMS para decimal** solicita explicitamente o cálculo para posicionar o ponto no mapa. O cadastro e o faturamento continuam exibindo o GMS original.
- **Converter decimal para GMS** preenche os campos GMS por solicitação explícita. Salvar confirma a alteração.
- Editar um GMS invalida a posição decimal anterior; nova conversão exige outro clique. Edições de outros dados preservam conversões já solicitadas.
- Faturamento exibe latitude e longitude na seleção, na prévia, no relatório confirmado e no PDF, conforme o formato cadastrado.
- A confirmação guarda as coordenadas daquele envio. Alterações futuras da propriedade não reescrevem relatórios antigos. Envios antigos sem coordenadas no resumo mostram informação ausente.
- Não há conversão em massa nem alteração das coordenadas existentes pela migration. O comportamento existente de importação de KML permanece independente do preenchimento GMS.

## Arquivos e aplicação

Backend: propriedades/models.py, serializers.py, coordenadas.py, migration e test_coordenadas.py. Frontend: App.tsx, api/propriedades.ts, components/CoordenadasInput.tsx, utils/coordenadas.ts e scripts/test-coordenadas.mjs.

O aplicativo local usa `.worktrees/runtime-origin-main`, com os mesmos campos GMS e alterações adicionais em estoque/faturamento.py, faturamento_pdf.py, test_faturamento_coordenadas.py, api/faturamentoInsumos.ts e pages/Estoque/FaturamentoInsumos.tsx.

Migration principal: propriedades/0004_coordenadas_gms; runtime: propriedades/0005_coordenadas_gms, após 0004_bp_cvale. A migration do runtime foi aplicada no banco local. Frontend compilado e disponibilizado na porta 5174.

Backups privados verificados antes das alterações: `backups/visual-20261009-151555` e `backups/visual-20261009-151600`, incluindo código, banco e uploads do runtime. Nenhum commit, push ou merge nesta tarefa.

## Verificações

- Backend isolado: 35 testes de coordenadas, faturamento e BP/embalagens aprovados, com dois cenários de concorrência específicos de PostgreSQL ignorados pelo SQLite; mais três testes de coordenadas no faturamento aprovados.
- Migration: `makemigrations --check --dry-run` sem alterações pendentes no runtime.
- Frontend: script dedicado valida conversões explícitas, limites, zero e renderização GMS sem conversão. Suíte existente de componentes, autenticação, rascunhos e usabilidade aprovada durante o build Docker; TypeScript e Vite aprovados.
- PDF sintético renderizado e inspecionado: GMS original, decimais, propriedade com nome longo e histórico sem coordenadas legíveis, sem sobreposição.
- Revisão localizada do diff e `git diff --check` aprovados.

O build direto no Windows encontrou um tsconfig.tsbuildinfo protegido; a compilação e os testes pelo Docker passaram. A árvore principal possui uma dependência de migration CAD/PRO preexistente ausente, por isso a validação integrada foi realizada na árvore ativa do aplicativo. Não se modificou essa dependência nesta tarefa.
