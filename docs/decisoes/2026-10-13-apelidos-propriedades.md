# Apelidos na consulta de propriedades — 13/10/2026

Os nomes conhecidos/comerciais estavam preservados nas linhas históricas de
Importações, mas ausentes do contrato da API e dos cartões de Propriedades.
As duas planilhas INSUMOS usam a coluna D para esse dado. A associação existente
da linha à propriedade é respeitada; nomes oficiais e registros permanecem intactos.

O serializer retorna `apelidos` somente para leitura, sem duplicações por caixa
ou espaços. Variantes diferentes são preservadas. A view carrega as linhas em
lote para evitar consultas por propriedade. A tela exibe os apelidos abaixo do
nome oficial. Sem campo novo no banco ou migration.

Arquivos: backend/apps/propriedades/{serializers,views,test_apelidos}.py;
frontend/src/{App.tsx,api/propriedades.ts}.

Validação: 17 testes de propriedades em PostgreSQL isolado aprovados; Django
check e makemigrations --check --dry-run aprovados; npm test, TypeScript e Vite
aprovados pelo build Docker. Consulta real identificou 74 propriedades com
apelidos. Frontend local 5174 atualizado e saudável; readiness aprovado.
Conferência visual autenticada não realizada.

Backup verificado antes das alterações: backups/agro-ai-pro-2026-10-13-222047-759917,
incluindo código com alterações locais, uploads, dump e manifesto SHA-256.
Alterações preexistentes de Transportes preservadas. Sem commit, push ou merge.

A impressão de propriedades permanece com o nome oficial: a tentativa de edição
de PropriedadesImpressao.tsx foi impedida pelas permissões do arquivo e não foi
aplicada. Nenhum arquivo temporário foi mantido. Busca continua pelos campos
originais; apelidos exibidos são os preservados nas importações vinculadas.
