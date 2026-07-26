# Sprint 7 — Estoque

## Status

Concluída em 25/07/2026.

## Entregas

- cadastro autenticado de produtos e insumos;
- classificação de herbicidas, fungicidas, fertilizantes, sementes e outros;
- unidades em quilograma, litro, unidade, saca e tonelada;
- locais de armazenamento vinculáveis a propriedades;
- lotes com código, validade, localização e observações;
- entradas e saídas com quantidade, custo, data e documento fiscal opcional;
- vínculo opcional da movimentação com propriedade e safra;
- saldo calculado por lote e bloqueio de saída sem saldo disponível;
- alertas de lote vencido, vencimento em 30 dias e estoque abaixo do mínimo;
- rastreabilidade por usuário e data de criação;
- filtros, busca e ordenação;
- interface para movimentações, posição, alertas e cadastros auxiliares;
- administração, testes automatizados e documentação da API.

## Decisões de integridade

Movimentações são imutáveis pela API e pelo painel administrativo. Uma correção
deve ser feita com um novo movimento compensatório, preservando a trilha de
auditoria. A criação usa transação e bloqueio do lote para impedir duas saídas
concorrentes de consumirem o mesmo saldo.

Produtos, locais e lotes em uso possuem exclusão protegida. Cadastros antigos
podem ser desativados sem remover seus vínculos históricos.

## Migration

`estoque.0001_initial` cria somente as tabelas, índices e restrições do módulo.
Não modifica nem remove dados preexistentes.

## Validação

- Django Check;
- auditoria de migrations;
- testes completos do backend;
- testes de componentes do frontend;
- build de produção;
- Docker Compose;
- verificação do diff e de segredos.

Nenhuma dependência nova foi adicionada e nenhum serviço pago é utilizado.
