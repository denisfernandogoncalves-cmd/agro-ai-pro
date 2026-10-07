# Retomada da pesagem e dos romaneios — 07/10/2026

Branch: `codex/melhorias-gestao-transferencias-20261003`, checkout
`.worktrees/runtime-origin-main`. Retomada da solicitação interrompida em
06/10/2026: reduzir o título, mostrar a composição de pesagem nas cargas
próprias e de terceiros e oferecer PDF/Excel no recebimento de terceiros.

## Comportamento e critérios de aceite

- Peso total menos tara produz o peso bruto do produto. Quando informados,
  ambos são obrigatórios em conjunto; tara não negativa e total maior que tara.
- O backend recalcula o bruto, independentemente do valor enviado pelo cliente.
  A classificação e os descontos existentes recebem esse bruto e geram o líquido.
- Formulários, cartões e romaneios exibem total, tara, bruto do produto e líquido.
- Registros anteriores continuam com total/tara nulos, sem inventar pesagens
  ou recalcular seu histórico. O lançamento direto do bruto permanece disponível
  quando total e tara não forem informados.
- Correções usam o fluxo existente de retificação e auditoria; terceiros
  recalculam o saldo no fluxo existente de edição.
- Título principal menor. Downloads de terceiros disponíveis na aba Terceiros
  e no localizador de romaneios, com duas vias em A4.

## API e arquivos

Campos adicionados: `peso_total_kg`, `tara_kg`, Decimal(16,3), opcionais/nulos,
nos modelos, serializers e tipos de cargas próprias e recebimentos de terceiros.
Migration `graos.0019_cargacolhida_peso_total_kg_cargacolhida_tara_kg_and_more`
criada e aplicada no banco local; nenhum dado antigo alterado.

Endpoints GET autenticados, sujeitos à permissão `cargas/imprimir`:

- `/api/graos/terceiros/entradas/{id}/pdf/`
- `/api/graos/terceiros/entradas/{id}/excel/`

Excel usa `.xlsx`, como as exportações existentes de vendas. Células de dados
são texto para evitar execução de fórmulas provenientes dos campos cadastrados.
PDF usa ReportLab já declarado pelo projeto, com escape e quebra de linhas.
Conteúdo que não cabe em duas vias A4 retorna HTTP 400 com mensagem explicativa;
o Excel preserva o texto completo. Nenhum truncamento silencioso no PDF.

Arquivos principais: `backend/apps/graos/pesagem.py`, `cargas_services.py`,
`models.py`, `serializers.py`, `terceiros.py`, `romaneios_terceiros.py`, `urls.py`,
respectiva migration e `test_pesagem.py`; frontend em `api/cargasColhidas.ts`,
`api/terceiros.ts`, `components/ComprovanteLancamento.tsx`, páginas de
`CargasColhidas/`, `styles.css` e `scripts/test-components.mjs`.

## Preservação e validação

Backup privado ignorado pelo Git:
`backups/agro-ai-pro-2026-10-07-082740-513736` deste checkout.
Inclui código com alterações pendentes, uploads, estado/diff Git e cópia física
do PostgreSQL parado. Leitura integral do TAR (8.830 arquivos), CRC dos ZIPs,
tamanhos e SHA-256 registrados em `manifesto.json`. Não houve restauração.
Docker estava parado; foi iniciado, com os serviços locais retomados após backup.

Validações:

- `npm run build`: TypeScript/Vite aprovados.
- `npm test`: componentes/romaneios, autenticação, rascunhos e usabilidade aprovados.
- Docker: `python manage.py test apps.graos.test_pesagem
  apps.graos.test_cargas_colhidas apps.graos.test_terceiros
  --settings=config.settings.test --noinput`: 47 testes aprovados, 4 ignorados
  por exigirem PostgreSQL para concorrência.
- Dois testes adicionais de permissão de impressão e observações extensas
  incluídos posteriormente; os 7 testes de `test_pesagem` aprovados.
- `python manage.py check` e `makemigrations --check --dry-run`: aprovados.
- PDF sintético renderizado com Poppler e inspecionado visualmente: uma A4,
  duas vias legíveis, sem sobreposição. Excel reaberto com OpenPyXL e verificado
  quanto a campos, duas vias, configuração A4 e ausência de fórmulas.
- Build Docker da interface aprovado, com a versão final disponibilizada em
  `http://127.0.0.1:5174/`. Interface e `/api/health/` pelo proxy: HTTP 200.
  Backend, frontend, PostgreSQL e Redis saudáveis.
- `git diff --check`: aprovado; diff e arquivos novos revisados.

O Python virtual local não tem ReportLab instalado; os testes de exportação
foram executados no Docker, que possui as dependências reais do aplicativo.
Não foram criados registros de teste no banco operacional. Sem commit, push,
merge ou publicação em produção. Esta entrega é melhoria da funcionalidade
existente de cargas; nenhum status de Sprint foi alterado.
