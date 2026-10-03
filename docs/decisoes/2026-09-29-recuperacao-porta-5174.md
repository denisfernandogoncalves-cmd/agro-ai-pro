# Recuperação de acesso à porta 5174 — 29/09/2026

Relato: aplicativo não carrega dados. Os quatro containers existentes estavam
parados (Exited 255), e a porta recusava conexões. Branch de execução:
`codex/propriedades-impressao-a4-20260921`; alterações locais preservadas.

Backup antes da inicialização: `backups/agro-ai-pro-2026-09-29-171009-049281`
neste checkout, com código, uploads, banco físico parado, CRC dos ZIPs e hashes.

Executado `docker compose -p agro-ai-pro start --wait --wait-timeout 180 postgres
redis backend frontend`. O frontend tentou resolver o backend antes de este
estar disponível e encerrou com erro de upstream. Aguardado o backend com
`start --wait --wait-timeout 180 backend`, depois iniciado o frontend com
`start --wait --wait-timeout 120 frontend`. Nenhum container ou volume recriado.
Backend: system check sem problemas e nenhuma migration pendente.

Validação: interface HTTP 200, `/api/health/` com status ok e quatro serviços
saudáveis. Consultas autenticadas de leitura pelo proxy do frontend retornaram
HTTP 200 para propriedades, lançamentos financeiros, produtos e compras.
Contagens confirmadas diretamente no banco `agro_ai_pro`: uma propriedade,
um produto, zero lançamentos financeiros e zero compras.

O usuário informou esperar dados de todos os módulos. Encontrado o registro
`2026-09-27-usuarios-limpeza.md`: limpeza anterior autorizada de 458 registros em
44 tabelas de domínio, preservando contas. O backup anterior à limpeza existe
na pasta principal `backups/agro-ai-pro-2026-09-27-135934-380937`; hashes do
dump e dos uploads conferem com o manifesto. Não houve exclusão nem restauração
nesta tarefa. Recuperação dos dados antigos depende de decisão explícita e
ensaio isolado, conforme AGENTS.md. Não foi alterado código funcional.
Sem commit, push ou merge.
