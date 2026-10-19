# Área de propriedades com quatro casas em alqueires — 18/10/2026

Solicitação: aceitar valores como 14,1405 no campo Área (alqueires paulistas).

- Entrada com passo/mínimo 0,0001 e listagem de propriedades com quatro casas.
- Conversão da API mantém seis casas em hectares: 14,1405 alq. = 34,220010 ha; 0,0001 alq. = 0,000242 ha.
- Campo de banco ampliado de Decimal(10,2) para Decimal(14,6), preservando as oito casas inteiras anteriores. Migration propriedades.0009 aditiva aplicada, sem arredondar nem recalcular registros antigos. A precisão anteriormente perdida não é recuperada automaticamente.
- Formulário de edição já reconverte hectares para quatro casas em alqueires.
- Relatórios e impressão existentes mantêm seus formatos próprios; a alteração é da entrada, persistência e listagem do cadastro de propriedades.

Backup privado verificado: `D:/PROJETOS/AGRO-AI-PRO/backups/visual-20261018-215635` (código/uploads, patch, dump, CRC/catálogo e hashes SHA-256).

Validações: 55 testes PostgreSQL de propriedades, talhões e busca aprovados em banco exclusivo preservado; testes frontend, TypeScript/Vite/build Docker aprovados; Django check e migrations consistentes. Casos de 14,1405 e 0,0001 cobertos na conversão e gravação/leitura.

Árvore operacional `.worktrees/runtime-origin-main`, branch `codex/modernizacao-visual-runtime`, porta 5174. Alterações anteriores preservadas; sem commit, push ou merge.
