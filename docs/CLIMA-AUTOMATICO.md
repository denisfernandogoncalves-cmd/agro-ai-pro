# Previsão do Clima Automática

## Objetivo

O AGRO-AI-PRO mantém previsões climáticas atualizadas por propriedade sem exigir
consulta manual. O backend consulta o provedor, persiste a última resposta válida,
calcula indicadores agronômicos e disponibiliza notificações internas no Dashboard
e no módulo Clima.

A atualização manual continua disponível para perfis autorizados e não substitui o
agendamento automático.

## Provedor

O provedor padrão é o Open-Meteo Forecast API, configurado por
`CLIMA_PROVIDER_BASE_URL`.

Características técnicas:

- não usa chave ou token no frontend;
- as chamadas partem exclusivamente do backend;
- oferece previsão atual, horária e diária para o Brasil;
- permite configurar outra URL compatível, inclusive uma instância auto-hospedada;
- não foi ativado plano, teste gratuito conversível ou serviço pago.

### Restrição de licenciamento

O endpoint público gratuito do Open-Meteo é destinado a uso não comercial. Nesta
branch ele deve ser usado somente para desenvolvimento, homologação e uso privado
compatível com os termos publicados pelo provedor.

Antes de uma implantação comercial, escolha uma das alternativas:

1. hospedar localmente uma instância compatível do Open-Meteo; ou
2. solicitar autorização expressa para avaliar um plano comercial.

Nenhuma dessas opções foi ativada automaticamente.

Referências oficiais:

- https://open-meteo.com/en/docs
- https://open-meteo.com/en/pricing
- https://open-meteo.com/en/terms
- https://github.com/open-meteo/open-meteo

## Localização

A coordenada é resolvida nesta ordem:

1. latitude e longitude cadastradas na propriedade;
2. centro da caixa envolvente do GeoJSON processado da propriedade;
3. centro cadastrado de um talhão;
4. centro da caixa envolvente do GeoJSON processado de um talhão.

A altitude é estimada pela média das altitudes cadastradas nos talhões quando
existirem dados suficientes.

Município e UF permanecem metadados de identificação. O sistema não geocodifica
nomes nem inventa coordenadas. Sem localização válida, registra o estado
`sem_localizacao`, preserva previsões anteriores e apresenta alerta ao usuário.

## Agendamento

O serviço Docker `clima-worker` executa:

```bash
python manage.py atualizar_clima --continuous --interval-seconds 300
```

O processo verifica pendências a cada cinco minutos. A frequência padrão de chamada
por propriedade é de 180 minutos. Cada ciclo lê a configuração individual e consulta
somente propriedades cuja `proxima_atualizacao` esteja vencida.

Essa separação permite configurar uma propriedade para intervalos menores ou maiores
sem gerar chamadas a cada verificação do worker.

Para executar um único ciclo:

```bash
python manage.py atualizar_clima
```

Para alterar somente o intervalo de verificação do processo:

```bash
python manage.py atualizar_clima --continuous --interval-seconds 600
```

O intervalo do processo não força chamadas. A propriedade só é consultada quando
`proxima_atualizacao` estiver vencida.

## Cache e deduplicação

- Redis local é utilizado quando `REDIS_CACHE_URL` estiver configurada.
- Testes e execução sem Redis usam `LocMemCache`.
- Respostas do provedor ficam em cache por 900 segundos por padrão.
- A chave usa SHA-256 dos parâmetros normalizados e não contém credenciais.
- Um lock por propriedade evita atualizações concorrentes.
- A atualização dentro da janela configurada é ignorada e auditada.
- O contador `total_chamadas` aumenta somente quando há chamada real ao provedor.

## Tolerância a falhas

Quando a consulta falha:

1. nenhuma previsão armazenada é apagada;
2. a configuração passa para `erro`;
3. os dados são marcados como desatualizados;
4. a próxima tentativa usa espera progressiva;
5. a falha é registrada sem URL completa, token ou conteúdo sensível;
6. o restante do ERP continua disponível.

O backoff começa em 15 minutos e cresce até o limite da frequência configurada.

## Dados persistidos

### Estado atual

Persistido em `ConfiguracaoClima.dados_atuais`:

- temperatura;
- sensação térmica;
- umidade;
- precipitação;
- condição;
- cobertura de nuvens;
- pressão;
- vento, direção e rajadas.

### Previsão horária

`PrevisaoHoraria` registra:

- temperatura e sensação;
- umidade e ponto de orvalho;
- precipitação e probabilidade;
- vento, direção e rajadas;
- pressão e nebulosidade;
- radiação e evapotranspiração;
- condição para pulverização e colheita;
- riscos de deriva e lavagem.

### Previsão diária

`PrevisaoClima` mantém o histórico persistido. O frontend seleciona exatamente os
próximos sete dias para a previsão operacional.

Cada dia inclui:

- temperaturas mínima e máxima;
- sensações mínima e máxima;
- chuva e probabilidade;
- umidade;
- vento, rajadas e direção;
- pressão, nuvens, radiação e ponto de orvalho;
- evapotranspiração;
- nascer e pôr do sol;
- alertas e condições agronômicas.

## Alertas e indicadores agronômicos

Os limites ficam em `ConfiguracaoClima` e podem ser alterados por administrador ou
gestor da propriedade.

O processamento inclui:

- geada, frio, calor, chuva intensa e vento forte;
- excesso ou baixa umidade;
- tempestade e granizo quando o código meteorológico indicar;
- ausência prolongada de chuva;
- risco de deriva;
- risco de lavagem por chuva;
- condição para pulverização;
- condição para colheita;
- risco simplificado de estresse hídrico;
- evapotranspiração de referência quando fornecida pelo provedor.

Os indicadores são apoio operacional. Não substituem avaliação agronômica local,
bula, receituário ou decisão do responsável técnico.

## Permissões

A proteção da PR #16 permanece no backend:

- listagens são filtradas pelas propriedades autorizadas;
- IDs externos são ocultados;
- administrador e gestor configuram limites e frequência;
- administrador, gestor e operador solicitam atualização manual;
- somente leitura consulta previsões e marca notificação interna como lida;
- superusuário mantém acesso completo.

## Variáveis de ambiente

```dotenv
REDIS_CACHE_URL=redis://redis:6379/1
CLIMA_PROVIDER_BASE_URL=https://api.open-meteo.com/v1/forecast
CLIMA_PROVIDER_TIMEOUT_SECONDS=15
CLIMA_PROVIDER_CACHE_SECONDS=900
CLIMA_UPDATE_LOCK_SECONDS=180
CLIMA_UPDATE_INTERVAL_SECONDS=300
CLIMA_MAX_UPDATES_PER_CYCLE=100
CLIMA_AUTOMATIC_UPDATE_ENABLED=True
```

Nenhuma variável contém chave de API porque o provedor padrão não utiliza chave.

## Ativação no Docker

```bash
docker compose up --build
```

O Compose inicia PostgreSQL, Redis, backend, frontend e `clima-worker`.

Verificações úteis:

```bash
docker compose ps
docker compose logs clima-worker
docker compose exec backend python manage.py atualizar_clima
docker compose config --quiet
```

## Limitações atuais

- não existe observação meteorológica própria na fazenda;
- a comparação previsto x observado depende de dados do provedor, não de estação
  física local;
- o centro de uma geometria extensa pode não representar microclimas internos;
- agrupamento de propriedades próximas não é aplicado, pois poderia misturar
  altitude e microclima sem validação segura;
- notificações são somente internas;
- e-mail, SMS, WhatsApp e push externo não foram ativados;
- o endpoint público padrão não deve ser usado comercialmente sem solução de
  licenciamento autorizada.
