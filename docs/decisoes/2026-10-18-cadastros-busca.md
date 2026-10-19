# Cadastros de propriedades, grupos e buscas — 18/10/2026

Branch operacional: `codex/modernizacao-visual-runtime`, em `.worktrees/runtime-origin-main`, que atende a porta 5174. Árvore principal e suas alterações anteriores preservadas; sem commit, push ou merge.

## Entregas e critérios

- Novas propriedades usam GMS por padrão. Coordenadas já cadastradas mantêm seu formato e precisão; conversão continua explícita. Integrações com coordenadas decimais sem GMS não perdem a posição.
- `cad_pro_identificacao`: texto livre opcional, com sugestões Principal/Secundário. Não modifica vínculos nem saldos.
- `tipo_imovel`: seleção opcional de Imóvel arrendado/Imóvel próprio. Não informado nos registros antigos, sem classificação presumida.
- `apelido`: texto editável opcional, apresentado junto dos apelidos históricos. Nome oficial preservado. Pesquisa local por apelido, identificação e número CAD/PRO.
- Talhões: seleção múltipla de propriedades por caixas de marcação, busca e contagem. CAD/PRO individual por propriedade, compartilhado ou diferente. Propriedades sem vínculo ativo aparecem com orientação; não se inventa vínculo. Edição preserva pendências de membros indisponíveis. Rateio por área preservado.
- Produtos: filtro local imediato por nome/princípio ativo, sem distinção de caixa/acentos, com contagem e princípios visíveis na lista.
- Menu: Buscar no programa consulta `GET /api/core/busca/?q=...`, além dos nomes de módulos. Textos, identificadores, números e datas editáveis dos modelos de negócio são consultados conforme permissão do setor. Busca sem acentos no PostgreSQL, até 100 caracteres e cinco resultados por tipo, com aviso para refinar. Cancelamento e descarte de respostas antigas; atraso de 450 ms evita requisição a cada tecla. Resultados abrem o setor; filtros são aplicados nas telas que suportam destino de consulta.

## Limites

A busca geral não indexa o conteúdo de anexos/PDF/KML, JSON de importações, credenciais, configurações internas, rascunhos, contas de usuário ou histórico de auditoria. Não é mecanismo de busca dentro de arquivos. Datas usam representação de banco e números não incluem formatação monetária. Permissões não foram ampliadas. O limite de cinco por tipo é indicado na interface.

## Preservação e migrations

Backups privados em `D:/PROJETOS/AGRO-AI-PRO/backups/`:
`visual-20261018-214143-737148` (árvore principal), `visual-20261018-214153` (operacional inicial),
`visual-20261018-214614`, `visual-20261018-214709`, `visual-20261018-214903`, `visual-20261018-215035`.
ZIP/código/uploads, patch e dump PostgreSQL com CRC/catálogo e hashes SHA-256 verificados nos manifestos. Nenhum backup anterior sobrescrito.

Migrations aditivas aplicadas: propriedades.0006 (identificação e padrão GMS), 0007 (tipo do imóvel), 0008 (apelido). Nenhum registro classificado ou apelidado automaticamente.

## Verificações

Testes pertinentes de propriedades, grupos e busca em PostgreSQL isolado, com banco exclusivo preservado (`keepdb`). Testes frontend incluem pesquisa por princípio ativo e aplicação de três propriedades com CAD/PROs distintos. Build Docker executa `npm test` e `npm run build` (TypeScript/Vite).

Resultado final: 29 testes backend aprovados; testes frontend/TypeScript/Vite aprovados; Django check, migrations e diff sem inconsistências. Duas fixtures anteriores de apelidos foram atualizadas com o novo atributo. Consulta real de CAD/PRO retornou HTTP 200 em 0,634 s, sem gravações. Interface ativada explicitamente em 5174; frontend/backend/PostgreSQL/Redis saudáveis e readiness `ok`.

Conferência autenticada no navegador: novos campos visíveis e GMS selecionado no formulário novo; busca numérica pelo menu abre as três propriedades vinculadas ao CAD/PRO consultado; seleção simultânea de FAZENDA ELECTRA (CAD/PRO 1) e SAGRILO (123456) habilita o grupo. Seleção de teste desmarcada, sem gravar grupo ou propriedade real.

Produtos: busca por `abamectina` retornou ABADIN 72 EC e ABAMEX MAXX (2 de 62 produtos), comprovando filtro pelo princípio ativo.

Build local em Windows encontrou EPERM em arquivo antigo de `frontend/dist`; a compilação Docker usa saída isolada. A primeira execução de autenticação sob sandbox encontrou EACCES no servidor de teste; reexecução fora do isolamento aprovada. Sem alteração de dependências.
