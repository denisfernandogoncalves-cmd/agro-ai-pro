# Demonstrativo mensal de salário e comissão — 13/10/2026

## Objetivo e critérios

Imprimir salário e comissão de cada motorista, escolhendo mês/ano, em apresentação
semelhante a holerite. Critérios: respeitar competência e histórico do motorista,
reutilizar a comissão existente, somar todas as placas, não limitar aos 30 registros
visíveis da consulta, exigir impressão autorizada e preservar dados cadastrados.

## Uso e implementação

Transportes → Holerite por motorista → mês → motorista → Conferir e imprimir
holerite → Imprimir / salvar PDF. Seleção inclui motoristas históricos presentes
na competência, mesmo que o motorista atual do caminhão tenha mudado.

Modelo A4 retrato com motorista, mês/ano, salário, comissão, total, detalhe por
placa/base/percentual, data de recebimento e assinatura. Na ausência de registros,
mostra mensagem, sem gerar salário fictício. Meses/seleções alterados e falhas
limpam a prévia anterior; consultas canceladas não substituem a seleção atual.

GET /api/transportes/remuneracoes/imprimir/?mes=AAAA-MM retorna demonstrativos
mensais agrupados por nome do motorista (ignorando diferenças de caixa), usando
RemuneracaoSerializer e cálculo vigente. Exige autenticação e permissão imprimir
em transportes; mes inválido/ausente: 400, sem permissão: 403, anônimo: 401.
Todos os registros da competência são incluídos, sem a paginação da listagem.

Arquivos: backend/apps/transportes/{views,tests}.py;
frontend/src/api/transportes.ts;
frontend/src/pages/Transportes/{HoleriteMotorista,TransportesPage}.tsx;
frontend/src/pages/Transportes/transportes.css;
frontend/scripts/test-components.mjs; docs/SPRINTS.md.

## Verificação e preservação

- Backup antes de editar: backups/agro-ai-pro-2026-10-13-214306-390181.
- Backup antes de atualizar frontend: backups/agro-ai-pro-2026-10-13-214644-136747.
  Código, uploads e dump PostgreSQL verificados, hashes registrados; sem restauração.
- 23 casos Transportes: 21 aprovados, um skip de planilha privada e uma falha
  inicial na proteção de impressão. Causa corrigida com verificação explícita
  de acesso na ação, depois da autenticação DRF.
- Reteste dos quatro casos novos: OK. Cobertura: mês/ano, histórico, múltiplas
  placas, comissão percentual, mês vazio, 35 motoristas, validação e permissões.
- Docker build frontend: testes de componentes/autenticação/rascunhos/usabilidade/
  coordenadas/romaneios, TypeScript e Vite aprovados. Documento renderizado em
  teste com competência, valores, placa, assinatura e escape de HTML.
- Django check e makemigrations --check --dry-run aprovados; sem migration.
- Frontend 5174 atualizado e saudável; revisão do diff sem erros.

## Limites

A comissão percentual continua recalculada conforme receitas e despesas registradas;
comissão histórica sem percentual permanece com seu valor cadastrado. O demonstrativo
é consulta, não registra pagamento nem adiciona descontos/tributos. Salários de várias
placas são somados exatamente como cadastrados. Impressão física e conferência visual
integral no navegador não executadas; salvar PDF usa o diálogo de impressão do navegador.
Sem nova dependência, serviço pago, mudança de regras, merge ou produção.
