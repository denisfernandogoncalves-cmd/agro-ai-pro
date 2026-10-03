# Documentos e Excel

Todas as rotas exigem autenticação. Respostas privadas usam `no-store`.

| Rota | Acesso e comportamento |
| --- | --- |
| `GET /api/core/backup-excel/` | Administrador ativo. Dados de negócio em XLSX com índice, históricos e cancelamentos; sem usuários, senhas, tokens, favoritos, rascunhos privados ou conteúdo binário dos documentos. |
| `GET /api/relatorios/operacionais/exportar/` | Permissões consultar e imprimir em relatórios. Mesmos filtros do relatório operacional, todas as páginas; abas de filtros, resultados e totais. |
| `GET/POST /api/core/anexos/{entidade}/{registro}/` | Consultar/cadastrar no módulo do lançamento. POST multipart, campo `arquivo`; PDF, PNG ou JPEG até 5 MB, máximo 20 ativos. Reenvio do mesmo conteúdo não duplica. |
| `GET/DELETE /api/core/anexos/arquivo/{id}/` | Consultar/excluir no módulo. Download autenticado como attachment; exclusão lógica auditada preserva o conteúdo no banco. |
| `POST /api/core/duplicidades/{entidade}/` | Consultar no módulo. Apenas conferência; não cria lançamentos. Retorna total, até cinco referências e aviso. Entidades: carga, venda e financeiro. |
| `GET /api/core/conferencia/{posicao}/?operacao=...` | Permissão existente de conferência. Filtra a lista de operações, preservando totais e saldo acumulado da posição inteira. |

Entidades dos documentos: carga, venda, transferencia, financeiro, compra e faturamento. IDs inteiros e UUID são normalizados. Não há URL pública. Validação compara extensão, assinatura e terminador do arquivo; não substitui análise antivírus. Documentos ficam no banco e são abrangidos pelo backup completo do banco.

Excel é uma cópia para consulta, sem função de restauração. Limite de 100.000 linhas incluindo metadados; excesso rejeita a geração, sem arquivo parcial. Texto iniciado por fórmula permanece texto; IDs são texto; números acima da precisão de 15 dígitos permanecem texto exato; textos extensos têm partes na aba Textos longos. Datas usam formato brasileiro, timestamps são UTC. Consulta PostgreSQL usa snapshot consistente somente leitura.

Na interface: Gestão → Backup em Excel → Baixar backup em Excel (somente administradores). Relatórios oferece exportação dos filtros aplicados. Nenhuma dessas ações altera os registros de negócio.
