# Ajustes operacionais — 14/10/2026

## Comissão e propriedades

Comissão das viagens mantida manual em reais, conforme escolha do Product Owner.
Conferência usa peso bruto do produto de CargaColhida, em vez do líquido após
qualidade: peso total menos tara. Exemplo conferido: 48.000 − 20.000 = 28.000 kg.
Venda mantém quantidade_kg, que já exclui tara e não tem descontos de qualidade.
Não alterados valores de comissões salvos, estoque, rateios ou ranking operacional.

Seleção de propriedades em Cargas colhidas compactada em menu nativo details,
com busca por nome/CAD-PRO e lista com rolagem de até 260 px. Seleção múltipla e
funções existentes preservadas. Apenas selecionadas aparecem abaixo com CAD/PRO
obrigatório e botão Remover; campos exigidos ficam fora do menu fechado.

Arquivos: transportes/fretes.py e test_fretes.py; ConferenciaFretes.tsx;
CargasColhidasPage.tsx e styles.css. Sem migrations nestes dois ajustes.
Oito testes de fretes aprovados em PostgreSQL exclusivo (3,802 s), incluindo peso
bruto, tara, descontos, valores manuais, histórico, cancelamentos e permissões.
Uma expectativa inicial de desconto no exemplo foi corrigida: a regra cadastrada
admitia a impureza de 1%; a comparação antes/depois usa a carga com desconto real.
Testes frontend, TypeScript e Vite no Docker aprovados. Django check/migrations OK.

## Nome do motorista

Correção autorizada de TIAGO ATESTADO para TIAGO DE SOUZA BESSOLOTE no único
registro divergente: RemuneracaoMotorista #94, competência 2026-04-01.
Operação transacional, apenas campo motorista. Salário e comissão permanecem
0,00; percentual ausente. Caminhão, demais remunerações e lançamentos já tinham
o nome correto; origens de grãos/vendas sem esse motorista. Nome antigo restante: 0.

Backups completos com manifesto/hashes: visual-20261014-122509,
visual-20261014-122708, visual-20261014-123354, visual-20261014-123501,
visual-20261014-123732, todos dentro de backups/ privada e ignorada pelo Git.
Alterações anteriores preservadas. Sem commit, push, merge ou produção.

## Aba de motoristas

A aba Caminhões foi apresentada como Motoristas e caminhões, reutilizando
cadastro e edição existentes de nome, placa e veículo, sem novo modelo ou endpoint.
Histórico permanece com nomes registrados por período. Product Owner escolheu
desvincular e preservar histórico. Botão Desvincular motorista confirma a placa e
o nome; DELETE /api/transportes/caminhoes/{id}/motorista/ exige permissão excluir,
confere motorista_original e usa bloqueio transacional contra troca concorrente.
Somente limpa motorista do caminhão, sem apagar veículo, lançamentos ou holerites.
Novo motorista pode ser cadastrado depois pela edição. Migration 0006 permite
nome vazio no caminhão; nenhum vínculo operacional foi removido automaticamente.

21 casos de Transportes em PostgreSQL exclusivo: OK, um skip de planilha privada
(4,368 s). Testes de histórico, comissão preservada, nome divergente, reassociação
e permissão. Frontend/test/TypeScript/Vite aprovados; migrations consistentes.
Backups antes de alterar e aplicar: visual-20261014-125049 e 125525, verificados.
Arquivos adicionais: transportes/models.py, views.py, tests.py,
migrations/0006_caminhao_motorista_opcional.py; api/transportes.ts e
pages/Transportes/TransportesPage.tsx. Conferência visual autenticada pendente.

## Percentual na conferência da viagem

Carga #59: 28.000 kg e Cesar na placa RHS3E18. Remuneração #10 no mês tem
comissao_percentual 8,0000. O percentual já era recebido pela API, mas a tela
somente oferecia comissão manual; acrescentada sua exibição em campo de leitura
que acompanha a remuneração selecionada. Sem alterar valores gravados.
Product Owner confirmou R$20 por tonelada. Campo Frete por tonelada (R$/t)
preenche frete total pelo peso bruto / 1.000 e comissão pelo percentual selecionado.
Exemplo: 28 toneladas × R$20 = R$560; 8% = R$44,80. Cálculo decimal por inteiros
BigInt: arredondamento monetário de meio para cima, primeiro frete total e depois
comissão. Tarifa negativa, precisão excedente ou percentual acima de 100 rejeitados.
Percentual ausente não vira zero: comissão permanece manual com aviso explícito.
Valor de comissão pode ser ajustado manualmente antes de salvar; trocar tarifa ou
motorista recalcula a sugestão. Frete persistido continua sendo total em reais.
Conferências existentes não são reinterpretadas como tarifas: preço unitário fica
vazio até o usuário informar para recalcular. Nenhum valor operacional atualizado
automaticamente. Tarifa é auxiliar da tela, não novo campo persistente.
Sete casos de cálculo incluídos na suíte frontend; testes/TypeScript/Vite aprovados.
Backups anteriores: visual-20261014-134029 e visual-20261014-135926.
Backup final: visual-20261014-140155. Frontend local atualizado e saudável,
HTTP 200. Sem conferência visual autenticada nesta etapa.
Sem migration adicional; sem commit, push ou merge.
