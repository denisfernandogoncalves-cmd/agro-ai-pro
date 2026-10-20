# Reutilizar nome de grupo excluído

Causa: o campo nome ainda tinha unicidade global, mesmo com exclusão lógica. Grupos excluídos reservavam o nome e impediam novos cadastros.

Substituída por unicidade condicional para grupos não excluídos. Grupos ativos/inativos não excluídos continuam com nomes únicos; nomes dos excluídos podem ser usados em novos grupos com novos IDs. Histórico anterior, áreas, vínculos e exclusão permanecem intactos. Validação de nome no serializer fornece mensagem clara; constraint no banco protege também gravações concorrentes. Savepoints permitem converter conflitos concorrentes em erro de validação sem ocultar outras falhas de integridade.

Migration `talhoes.0011_grupo_nome_unico_nao_excluido` aplicada, sem remoção ou renomeação de registros. Backup anterior: `D:/PROJETOS/AGRO-AI-PRO/backups/visual-20261019-224525`, código/banco/uploads verificados. Onze testes de grupos e histórico aprovados em banco isolado, incluindo exclusão/recriação com ID diferente, histórico anterior idêntico e rejeição de duplicidades na criação/edição de grupos atuais. Migrations consistentes e diff conferido. Sem alterações frontend nem novo cadastro real automático.
