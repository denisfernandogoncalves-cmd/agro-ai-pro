# Conferência de pesagem e resumo por terceiro — 07/10/2026

## Escopo autorizado e aceite

Implementar as cinco sugestões autorizadas: conferir a equação de pesagem antes
de salvar, alertar desvios históricos com opção de confirmar, identificar o
responsável/data/número dos romaneios, consultar/exportar o resumo por terceiro,
produto e safra, e testar a retificação de cargas próprias com total e tara.

Reutilizar o cálculo de descontos, a confirmação compacta, os movimentos
imutáveis, as permissões e os geradores Excel/PDF existentes. Sem novas
dependências ou migrations previstas. Arquivos afetados: graos/pesagem,
terceiros, URLs, serializers/exportadores/testes e componentes/páginas de cargas.

Alertas são informativos: mínimo de cinco lançamentos ativos comparáveis,
mediana dos vinte últimos, mesma cultura/safra/armazém e produtor/terceiro.
Com placa, restringir ao mesmo veículo. Tara é comparada apenas para o mesmo
veículo, acima de 30% de diferença; bruto do produto, acima de 50%.
Registros encerrados e a própria entrada em edição não entram na comparação.
Esses limiares reduzem alertas com pouca base e não alteram limites de carga.

Resumo usa entradas líquidas vigentes, saídas/transferências não estornadas e
saldo atual. Não soma a pesagem original de entradas retificadas ou canceladas.
Nome do terceiro identifica o agrupamento, pois esse é o cadastro existente;
nomes iguais, desconsiderando maiúsculas/espaços, são agrupados.

Testar cálculos, desvios/ausência de histórico, cancelamento, permissões,
filtros/exportação, retificações e rollback sem saldo suficiente, além de
frontend, build, migrations e inspeção visual dos romaneios.

Backup anterior às alterações:
`backups/agro-ai-pro-2026-10-07-085058-870997`, no checkout
`.worktrees/runtime-origin-main`. Código pendente, banco e uploads preservados;
hashes/CRC e restauração PostgreSQL isolada aprovados.

## Resultado

As cinco melhorias foram implementadas. A conferência ocorre antes da gravação,
pode ser cancelada sem movimentos e permite confirmar desvios históricos.
Na edição de terceiros, reutiliza o serializer de entrada para preservar as
regras de desconto originais. O resumo respeita filtros e permissão de impressão;
o Excel mantém pesos numéricos e textos protegidos contra fórmulas.

Rotas adicionadas:
- `POST /api/graos/cargas-colhidas/conferencia-pesagem/previa/`;
- `GET /api/graos/terceiros/resumo/`;
- `GET /api/graos/terceiros/resumo/excel/`.

Verificações: testes backend dos módulos `test_conferencia_resumo`,
`test_pesagem`, `test_cargas_colhidas` e `test_terceiros`: 60 testes,
56 aprovados e quatro ignorados por dependerem de concorrência PostgreSQL;
frontend `npm test`
e `npm run build`; Django `check` e `makemigrations --check --dry-run`;
`git diff --check`. Os testes de concorrência exclusivos do PostgreSQL são
ignorados pelo ambiente SQLite de testes. Nenhuma migration adicional necessária.

Inspeção visual: confirmação com total 1.500 kg, tara 500 kg, bruto 1.000 kg,
desconto 20 kg e líquido 980 kg; cancelamento preservou a lista existente.
Resumo e identificação do responsável/data nas duas vias conferidos na aplicação.
PDF sintético de trigo, incluindo PH e identificação, renderizado e conferido
em uma folha A4 com duas vias. Artefatos de QA ficam em pasta ignorada
`backups/qa-melhorias-pesagem-20261007`; nenhum dado sintético foi registrado.

Serviços locais atualizados e saudáveis. Sem commit, push ou merge nesta entrega.
