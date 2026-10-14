# Conferência de fretes por placa e mês — 13/10/2026

## Decisão e critérios

O Product Owner escolheu cruzar cargas/entregas por placa e mês, preenchendo valor
do frete e comissão manualmente. Critérios: preservar documentos e históricos,
consultar apenas origens autorizadas, não criar salários ou tarifas fictícios,
impedir repetição da mesma origem e adicionar somente comissões explicitamente
conferidas para o holerite; origens canceladas não participam do cálculo.

## Uso

1. Transportes → Conferir cargas e vendas → mês e, opcionalmente, placa.
2. Conferir a carga/entrega e selecionar motorista/remuneração do mês.
3. Informar frete e comissão em reais; escolher obrigatoriamente:
   - adicionar ao holerite, se ainda não estiver incluída;
   - já incluída em Transportes, para não somar novamente.
4. Salvar e consultar Transportes → Holerite por motorista.

Cadastre primeiro a remuneração mensal em Salário e comissão. Se a remuneração
usar exclusivamente comissões manuais de fretes, o percentual de Transportes pode
ser informado como zero; a comissão de fretes será somada separadamente.
Placa/motorista ausentes na origem exigem associação manual; o documento original
não é alterado. A correspondência automática normaliza hífen/espaços/caixa da placa
na consulta e preserva o nome histórico do motorista. Não usa o motorista atual
do caminhão para substituir o nome da viagem.

## Implementação

FreteConferido vincula exatamente uma carga colhida ou entrega de venda a uma
remuneração. OneToOne em cada origem evita repetir a mesma viagem; valores não
negativos e origem exclusiva possuem constraints. Ja_contabilizado é decisão
obrigatória na API. PATCH exige atualizado_em_original e conflito retorna 409.
A exclusão não está disponível; alterações possuem histórico de campos permitido.
Remuneração com vínculos não pode ser excluída ou mudar motorista/placa/competência.

A comissão final é a comissão existente de Transportes mais as comissões manuais
marcadas para adicionar, somente de origens ativas. Salário histórico e comissão
base não são sobrescritos. Relatórios e holerite reutilizam valor_comissao; a parte
manual aparece separada no holerite e na API. O frete é informativo neste fluxo:
não cria receita duplicada em Transportes e não vira valor de venda de grãos.
Não considera valor de venda do grão como receita de frete.

GET /api/transportes/fretes/cruzamento/?mes=AAAA-MM&placa=ABC1D23 retorna viagens
ativas e remunerações do mês. Origem cargas exige consultar em cargas; entregas
exigem consultar em vendas; consultar em transportes é obrigatório. POST/PATCH
em /api/transportes/fretes/ respeitam cadastrar/editar e acesso à origem.
Sem origem válida, mês/placa incompatível, negativos ou decisão ausente: 400.
Sem permissão: 403; anônimo: 401. Reenvio não duplica o vínculo.

Arquivos principais: transportes/{models,serializers,views,urls,fretes,test_fretes}.py;
transportes/migrations/0005_freteconferido.py; core/auditoria.py;
frontend/src/api/transportes.ts; Transportes/{ConferenciaFretes,HoleriteMotorista,
TransportesPage}.tsx; frontend/scripts/test-components.mjs.

## Preservação e validações

- Backup inicial: backups/agro-ai-pro-2026-10-13-215359-669931.
- Antes da migration/atualização: backups/agro-ai-pro-2026-10-13-215957-619265.
  Código, uploads e dump verificados com hashes; nenhuma restauração.
- 23 testes preexistentes de Transportes: OK, um skip de planilha privada.
- 111 casos transportes/financeiro/relatórios: quatro erros nos casos novos de
  valores históricos recebidos como string. Corrigida a conversão para Decimal.
  Reteste com 30 casos: um erro de fixture tentando editar carga imutável; fixture
  passou a cancelar pelo serviço oficial. Reteste desse caso: OK. Os demais casos
  do reteste e os casos antigos aprovados não foram repetidos desnecessariamente.
- Os sete casos novos cobrem cruzamento de cargas e entregas, competência/placa,
  motorista histórico, comissão manual, reenvio, já contabilizado, cancelamento,
  mês/placa inválidos, valores negativos, edição obsoleta e permissões.
- Testes frontend, TypeScript/Vite e Docker build aprovados, incluindo o holerite
  com comissão de fretes e escape de HTML. Execução pelo Node 24 do Windows teve
  falha de carregamento SSR de React; validação foi feita no Node 22 do Docker.
- Django check e makemigrations --check --dry-run aprovados.
- Plano mostrou somente CreateModel FreteConferido; transportes.0005 aplicada.
- Frontend 5174 atualizado e saudável. Cruzamento e impressão operacionais
  retornaram 200 em consulta administrativa somente de leitura; contagens de
  cargas, entregas, remunerações e conferências preservadas.
- Nenhum cadastro de frete, motorista ou pagamento fictício no banco operacional.
  Não houve alteração de cargas, vendas, estoque ou salários cadastrados.

## Limites

Comissões de fretes continuam abertas a alterações enquanto seus dados/origens
forem editados; não é fechamento mensal imutável nem confirmação de pagamento.
A decisão de já contabilizado é manual: documentos diferentes podem corresponder
à mesma viagem física, exigindo conferência antes de marcar ambos como adicionais.
Motoristas são identificados pelo cadastro mensal existente; não há novo cadastro
unificado de pessoas. Valor do frete e comissão não são inferidos do peso ou da venda.
A leitura do mês não tem teste de carga com grande volume; não foi feita conferência
visual integral de formulários nem impressão física. Sem dependências/serviços pagos,
commit, push, merge ou produção nesta etapa. Alterações anteriores de holerite preservadas.
