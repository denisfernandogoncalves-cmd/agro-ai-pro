# Cultura e safra nos grupos de colheita

Campos textuais Cultura (50 caracteres) e Safra (20 caracteres), alinhados aos tamanhos usados nos talhões. Disponíveis na criação, edição e listagem dos grupos; formulário limpa os campos ao salvar/cancelar. Permanecem opcionais para preservar grupos existentes, sem inferir informações históricas. Grupos excluídos mantêm os valores somente para consulta.

Migration `talhoes.0010_grupo_cultura_safra` adiciona os dois campos com texto vazio como padrão. Não altera vínculos CAD/PRO, rateios, áreas ou cargas existentes. Selecionar um grupo em Cargas colhidas conserva o comportamento anterior.

Backup anterior às alterações/migration: `D:/PROJETOS/AGRO-AI-PRO/backups/visual-20261019-222615`, código, banco e uploads com integridade verificada. Migration aplicada localmente; makemigrations --check sem alterações pendentes. Dez testes de grupos/histórico aprovados em banco isolado, incluindo criação, edição, limites, compatibilidade antiga e preservação após exclusão. Testes frontend, TypeScript/Vite e revisão do diff aprovados. Frontend local atualizado na porta 5174 e readiness OK. Conferência visual no navegador não executada.
