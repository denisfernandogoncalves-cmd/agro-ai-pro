# Mercado Automático Enterprise

## Objetivo

O módulo mantém cotações atuais e séries históricas para soja, milho, trigo, farelo de
soja, óleo de soja, petróleo Brent e dólar. As chamadas ocorrem somente no backend.
A última cotação válida permanece disponível quando uma fonte externa falha.

## Arquitetura

A implementação preserva `CotacaoMercado` e seus endpoints mensais para
compatibilidade. A camada Enterprise é aditiva:

- `enterprise_models.py`: ativos, OHLC, configurações e auditoria de atualizações;
- `enterprise_providers.py`: adaptadores Stooq e PTAX/BCB;
- `enterprise_update.py`: cache, lock, frequência, backoff e persistência;
- `enterprise_analysis.py`: séries, Corn Belt, estoque, contratos e recomendação;
- `enterprise_views.py`: painel, séries, atualização manual e configuração;
- `management/commands/atualizar_mercado.py`: worker local;
- `frontend/src/pages/Mercado`: painel responsivo e gráfico SVG.

## Ativos

| Ativo | Símbolo configurado | Unidade |
| --- | --- | --- |
| Soja CBOT | `zs.f` | US¢/bushel |
| Milho CBOT | `zc.f` | US¢/bushel |
| Trigo CBOT | `zw.f` | US¢/bushel |
| Farelo de soja | `zm.f` | US$/short ton |
| Óleo de soja | `zl.f` | US¢/lb |
| Petróleo Brent | `co.f` | US$/barril |
| Dólar PTAX | `USD/BRL` | R$/US$ |

Cada ponto registra abertura, máxima, mínima, fechamento, volume quando disponível,
horário, unidade, moeda, fonte e símbolo de origem.

## Fontes, custo e licenciamento

### PTAX

O dólar utiliza o Portal de Dados Abertos do Banco Central do Brasil, por API OData.
O conjunto é publicado como dado aberto sob ODbL. Não usa chave, token ou cartão.

### Commodities

O padrão de desenvolvimento utiliza os arquivos CSV públicos do Stooq. O próprio site
informa que as cotações de commodities são fornecidas pela Barchart. Como a licença de
redistribuição ou uso comercial automatizado não está definida de forma suficiente na
fonte pública consultada, esta integração fica autorizada somente para desenvolvimento,
homologação e uso privado compatível com os termos aplicáveis.

Antes de implantação comercial deve-se obter licença expressa da fonte ou substituir o
adaptador por uma fonte gratuita/local cuja licença permita o uso pretendido. Nenhum
plano, teste gratuito conversível ou serviço pago foi ativado.

## Atualização automática

O serviço Docker `mercado-worker` executa:

```bash
python manage.py atualizar_mercado --continuous --interval-seconds 300
```

O processo verifica pendências a cada cinco minutos. Cada ativo possui frequência
própria, quinze minutos por padrão. O polling não força chamada: configurações ainda
válidas são ignoradas.

Ciclo único:

```bash
python manage.py atualizar_mercado
```

## Cache, deduplicação e consumo

- Redis local quando `REDIS_CACHE_URL` estiver configurada;
- fallback para `LocMemCache` em testes;
- cache do provedor por dez minutos;
- chave SHA-256 sem credenciais;
- lock por ativo;
- contagem de chamadas reais;
- snapshots e dados diários persistidos;
- atualização manual reutiliza o mesmo serviço.

## Tolerância a falhas

Quando uma fonte falha:

1. nenhum ponto anterior é apagado;
2. o ativo passa para estado `erro`;
3. o painel marca dados desatualizados;
4. a próxima tentativa usa backoff progressivo;
5. a mensagem é sanitizada;
6. os outros ativos e módulos continuam funcionando.

## Análise integrada

A análise automática considera:

- tendência de cinco dias dos grãos;
- previsão e alertas cadastrados do Corn Belt;
- variação do Brent;
- variação da PTAX;
- estoque por CAD/PRO autorizado;
- saldo conjunto ainda não distribuído;
- saldo de contratos abertos.

A recomendação é operacional e explica fatores de alta e baixa. Não constitui garantia
de preço, recomendação financeira nem ordem automática de venda.

## Permissões e segurança

- todas as rotas exigem JWT;
- dados globais de mercado permanecem compartilhados, conforme a PR #16;
- ao informar propriedade no painel, estoque e contratos são filtrados pelo escopo do
  usuário;
- filtro de propriedade externo retorna HTTP 404;
- configuração do ativo aceita somente consulta e `PATCH` de usuário administrativo;
- nenhuma chave é exposta ao frontend;
- notícias permanecem cadastro interno, sem coleta automática não autorizada.

## Variáveis de ambiente

```dotenv
MERCADO_PROVIDER_CACHE_SECONDS=600
MERCADO_UPDATE_LOCK_SECONDS=300
MERCADO_UPDATE_INTERVAL_SECONDS=300
MERCADO_UPDATE_FREQUENCY_MINUTES=15
MERCADO_MAX_UPDATES_PER_CYCLE=20
MERCADO_AUTOMATIC_UPDATE_ENABLED=True
```

## Limitações

- a fonte pública de commodities não oferece garantia formal de SLA;
- a fonte padrão não está autorizada nesta branch para implantação comercial;
- PTAX é diária e não representa câmbio negociado em tempo real;
- o histórico intradiário é formado pelos snapshots persistidos pelo sistema;
- notícias não são buscadas automaticamente;
- nenhuma ordem comercial é executada pelo sistema.
