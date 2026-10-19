# Grupos de colheita em aba própria e exclusão com histórico

## Comportamento

- Grupos retirados da tela de Talhões e disponibilizados em Cadastros → Grupos de colheita.
- A página própria reutiliza as permissões existentes de Talhões, inclusive a ação excluir; não cria nem amplia permissões. Catálogo administrativo de permissões preservado; somente a navegação inclui a nova página.
- Excluir grupo exige confirmação no aplicativo e executa exclusão lógica: guarda `excluido_em`, desativa o grupo e preserva os vínculos.
- `historico_area` copia propriedade, nome, CAD/PRO e área em hectares na data da exclusão. A consulta posterior não recalcula essa cópia quando a propriedade muda de área ou de nome.
- Mostrar grupos excluídos e histórico das áreas permite consulta, sem edição nem reativação de um grupo excluído.
- Grupos excluídos saem das seleções de novas cargas e da busca geral. A exclusão repetida não altera o histórico original.
- Contextos, áreas, rateios e saldos de cargas já registradas são preservados. Nenhuma carga é excluída ou recalculada.

## Arquivos

Backend: `apps/talhoes/models.py`, `grupos.py`, migration 0009, testes de grupos e integração com carga; destino de grupos na busca geral.
Frontend: `App.tsx`, navegação/áreas, tipos e autorização de página, API de grupos e painel de grupos; remoção do painel em Talhões e orientação atualizada em Cargas colhidas.

## Preservação e validação

Backups verificados: `D:/PROJETOS/AGRO-AI-PRO/backups/visual-20261018-220220` e `visual-20261019-065035`. Código, uploads, patch e dump com integridade e hashes. Uma tentativa anterior falhou durante a inicialização do PostgreSQL; a repetição foi verificada antes de iniciar o backend.

Migration aditiva `talhoes.0009_grupopropriedadescolheita_excluido_em_and_more` aplicada. Sem alteração ou exclusão automática dos grupos reais existentes.

Suíte PostgreSQL pertinente: 60 casos, com uma expectativa antiga de área com duas casas corrigida para comparação Decimal; reteste dessa expectativa e teste integrado de exclusão/carga aprovados (2 casos). Testes de grupo cobrem exclusão lógica, repetição, bloqueio de edição, permissões e área histórica após mudança da propriedade. Teste integrado verifica que contexto/rateios/saldos da carga não mudam.

Frontend: `npm test` e TypeScript/Vite aprovados no build Docker. Verificação inicial detectou que a página derivada aparecia indevidamente na matriz de permissões; navegação separada do catálogo administrativo, sem mudança de acesso. Django/migrations/diff consistentes. Aplicativo atualizado em 5174 com serviços saudáveis e readiness ok.

Conferência autenticada: página própria visível no menu Cadastros, nenhum painel de grupos dentro de Talhões, botão Excluir grupo e consulta de grupos excluídos disponíveis. Grupo real existente preservado; nenhuma exclusão real realizada durante a conferência. Captura da página em `grupos-colheita-excluir.png` na pasta privada de evidências desta conversa.

Branch `codex/modernizacao-visual-runtime`, árvore `.worktrees/runtime-origin-main`. Alterações anteriores preservadas. Sem commit, push ou merge.

## Apelidos na seleção de propriedades (19/10/2026)

Lista de propriedades e seleção do CAD/PRO no grupo exibem nome oficial seguido dos apelidos manuais/históricos disponíveis, sem repetir valores idênticos. A busca dessa lista considera os apelidos exibidos. Propriedades sem apelido mantêm o nome oficial. Alteração localizada em `GruposPropriedadesPanel.tsx`, sem migration ou alteração dos históricos. Backup verificado `visual-20261019-081046`; testes frontend, TypeScript/Vite e diff aprovados; interface atualizada em 5174.
