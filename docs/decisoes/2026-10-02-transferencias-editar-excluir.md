# Editar/excluir transferências e bloqueio de carga

Escopo autorizado: editar ou excluir transferências de saldo entre CAD/PROs; investigar e corrigir a dificuldade ao excluir cargas.

Critérios: estorno conjunto das duas posições, correção atômica com reaplicação, motivo obrigatório, original preservado, idempotência, proteção contra saldo consumido/reservado e permissões editar/excluir independentes. Histórico deve distinguir ativas, editadas e excluídas, com impressão sem duplicar transferências encerradas. Erro da carga deve aparecer próximo ao cartão e indicar transferências vinculadas.

Backup anterior: runtime-origin-main/backups/agro-ai-pro-2026-10-02-150739-427962, com restauração isolada aprovada.

Diagnóstico da carga #50: entrada de 15.000 kg na posição #57, transferida integralmente pelos movimentos #126/#127 à posição #58. Excluir a transferência devolve esse saldo à origem; somente então a carga pode ser cancelada se não houver outro consumo/reserva. Nenhum dado real foi excluído pelo agente.

Status: implementação e validação concluídas em 03/10/2026; envio ao GitHub autorizado pelo Product Owner, sem merge ou produção.

## Resultado e validação final

- Histórico com Editar/Excluir, motivo obrigatório, estorno atômico das duas pontas e registro imutável da correção. A impressão considera somente transferências ativas no total.
- Permissão de exclusão de transferências exigida também nas rotas antigas de estorno, impedindo contorno pela permissão de produção.
- Exclusão da carga apresenta prévia somente leitura e explica bloqueios antes da confirmação. Nenhuma carga ou transferência real foi excluída para testar.
- Nova venda permite escolher Cultura e filtra as posições da origem selecionada.
- Migration graos0014 aplicada; makemigrations --check --dry-run sem alterações pendentes.
- Suíte completa: 540 casos, 500 aprovados e 40 pulados no SQLite. PostgreSQL: 34 testes aprovados de transferências, conferência e venda particular, incluindo concorrência e permissões.
- Frontend: testes, TypeScript e build aprovados com dependências atualizadas; npm audit sem vulnerabilidades. Cache antigo de node_modules no host apresentou EPERM: validação foi feita em instalação limpa privada e no build Docker, sem alterar permissões do sistema.
- Navegador: botões e formulários verificados sem gravações reais; larguras 360, 768 e 1366 sem transbordamento da página. Prévia da carga #50 identifica a transferência #126 de 15.000 kg.
- Backup da retomada: backups/agro-ai-pro-2026-10-03-073329-457606, código, uploads e dump PostgreSQL com hashes e restauração isolada aprovada. A cópia física anterior foi preservada; o ensaio automático suporta dumps, não cópias físicas offline.

Contrato e arquivos principais: docs/api/TRANSFERENCIAS_CORRECOES.md; backend/apps/graos/transferencias_correcoes.py, cargas_previas.py e test_transferencias_correcoes.py; frontend/src/pages/TransferenciasSaldo, CargasColhidas e Vendas.
