# Aba de cálculo e impressão de prestações — 16/10/2026

## Critérios atendidos

- Financeiro dividido em **Lançamentos financeiros** e **Cálculo de prestações**, com os componentes acessíveis de abas já existentes. A calculadora saiu da seção recolhível acima dos indicadores.
- Consultas, filtros e formulários financeiros preservados; a simulação permanece ao alternar as duas abas. As abas de situação dos lançamentos continuam dentro da seção financeira.
- Após simular, **Conferir e imprimir simulação** abre uma prévia exclusiva. **Imprimir / salvar PDF** usa o diálogo do navegador. Acesso respeita a permissão existente de impressão do Financeiro.
- Documento contém compra, entrada, taxa efetiva anual, carência, número de parcelas com amortização, periodicidade, datas, horário de geração em Brasília, moeda, critérios, totais e cronograma completo. A média continua identificada como média, sem tratá-la como parcela fixa.
- A impressão da prévia isola o documento via portal e o fluxo de comprovantes existente. Estilo A4 retrato nomeado, cabeçalho de tabela repetível, valores alinhados, sem cortar a tabela por rolagem na impressão e sem quebrar linhas de parcela entre páginas. Impressos de outros módulos não recebem o tamanho de página nomeado.
- Estilos próprios da calculadora, sem depender do carregamento prévio de Transportes. Formulário responsivo e parâmetros da prévia sem quebra indevida dos valores monetários.

## Verificações

- `docker compose -p agro-ai-pro build frontend`: `npm test`, TypeScript e Vite aprovados. Teste de renderização da folha verifica parâmetros, data de geração, vencimentos, juros, totais, unidades e ausência de controles/formulários e lançamentos financeiros no conteúdo impresso.
- Conferência autenticada local: abas separadas, alternância com simulação preservada, cálculo de referência e abertura da prévia com o botão de impressão/PDF.
- Desktop sem extravasamento, 1265/1265 px. Celular 360 × 800: página 345/345 px; prévia com largura aproximada de 307 px e rolagem da tabela contida. Captura móvel final indisponível na ferramenta; a conferência móvel foi de DOM e dimensões. Tamanho padrão restaurado.
- Impressão física e geração final pelo diálogo nativo de PDF não executadas; conteúdo da folha, prévia visual e regras de impressão validados. Cálculos/backend mantidos, sem necessidade de migrations ou repetição da suíte PostgreSQL nesta alteração de interface.
- Revisão de alterações e `git diff --check` aprovados. Frontend local 5174 saudável; `/api/ready/` retorna `{"status":"ok"}`.

## Arquivos e preservação

`frontend/src/pages/Financeiro/FinanceiroModulo.tsx`, `CalculoPrestacoes.tsx`, `prestacoes.css`, `frontend/src/App.tsx`, `frontend/scripts/test-components.mjs` e documentação. Sem novas dependências ou serviços pagos.

Checkout `.worktrees/runtime-origin-main`, branch `codex/modernizacao-visual-runtime`, alterações anteriores preservadas. Backups privados completos com hashes e restauração isolada aprovada: `backups/agro-ai-pro-2026-10-16-175754-731171` e `backups/agro-ai-pro-2026-10-16-180419-742640`. Evidências desktop em `C:/Users/DENIS/.codex/visualizations/2026/10/07/01a1161b-d4ff-7dc0-aad5-aafa0a65dae7/emprestimos-20261016/aba-prestacoes-final.png` e `prestacoes-impressao-desktop.png`. Sem alterações de dados operacionais, commit, push, merge ou produção.
