# Integrações sem serviços pagos — 10/10/2026

Autorização: continuar as limitações do layout, desde que não haja custos.
Checkout operacional `runtime-origin-main`, branch `codex/modernizacao-visual-runtime`.
Critérios: consultas reais, dados privados limitados às permissões, nenhuma
API paga, nenhum ajuste operacional, indicadores financeiros sem dupla soma,
datas científicas reais, erro explícito quando a fonte ou modelo falha.

Backup anterior: `backups/visual-20261010-081105`, código incluindo mudanças
locais, banco e uploads; ZIP, catálogo PostgreSQL e hashes verificados.

## Recursos

- Resumo Executivo: entradas e saídas liquidadas, saldo realizado e saldo
  previsto pendente, reutilizando `resumo_financeiro` com propriedade/safra e
  permissão financeira. Cancelados excluídos; sem somar novamente contratos,
  compras ou vínculos de acerto. Liquidações sem valor efetivo são identificadas.
  Caixa não é faturamento nem lucro; não presumir custos ou área produtiva.
- Clima: catálogo público NASA GIBS, cache de seis horas, timeout e limite de
  resposta; satélite MODIS e NDVI regional 250 m, data padrão do catálogo real,
  composição de 16 dias do NDVI e legenda oficial. Consulta manual sob demanda.
  Não converte GMS automaticamente, não cria média NDVI ou produtividade de
  talhão. Requer coordenadas decimais previamente cadastradas/conversão explícita.
- Assistente: conversa generativa local de leitura, modelo Qwen3 0.6B via
  runtime oficial Ollama. Sem chaves de API e sem provedor pago; nenhuma
  ferramenta capaz de executar operações. O contexto contém apenas totais
  permitidos pelo painel, propriedade/safra e horário; evidência oficial
  apresentada separadamente do texto gerado. Modelo pequeno, sujeito a erros;
  não substituir evidências por recomendações geradas.
- Perfil Docker `ia-local`: serviço limitado a 2 GB/2 CPUs, sem portas
  publicadas, rede `ia_interna` com `internal: true` e `OLLAMA_NO_CLOUD=1`.
  Download inicial de runtime/modelo pela internet; durante conversas o
  container não possui rota externa. A conexão backend/modelo é interna.
  Volumes operacionais preservados; `ollama_data` contém modelo derivado,
  sem histórico de perguntas. Estado visual da pergunta existe somente na sessão.

## Execução

Após baixar o modelo gratuito para o volume `agro-ai-pro_ollama_data`, ativar:
`docker compose -p agro-ai-pro --profile ia-local up -d --no-deps ia-local backend`.
Frontend em 5174 pelo procedimento existente. Desativar o perfil não remove
modelo nem dados. Sem runtime/modelo disponível, chat retorna 503 e as
análises explicáveis existentes continuam funcionando.

## Limites e fontes

Radar não ativado: a API RainViewer consultada limita o serviço gratuito a
uso pessoal/educacional e requer negociação para integração comercial. Não
assumir licença de uso de um ERP. Nenhum contrato ou conta foi criado.
NDVI de 250 m tem uso regional, não resolução adequada para diagnóstico de
pequenos talhões; composição não é imagem ao vivo. Faturamento, margem e
custo/ha exigem registros classificados/vinculados suficientes.

Fontes oficiais consultadas:
- https://nasa-gibs.github.io/gibs-api-docs/access-basics/
- https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.1.1
- https://www.rainviewer.com/api.html
- https://docs.ollama.com/faq
- https://docs.ollama.com/api/chat
- https://ollama.com/library/qwen3:0.6b

Arquivos: core/painel.py, clima/satelite.py e urls.py, ai/chat_local.py e
urls.py, accounts/access.py, docker-compose.yml, ResumoExecutivo.tsx,
ClimaPage.tsx, InsightsPage.tsx, ChatLocal.tsx e SatelitePublico.tsx; testes
backend em ai/test_sem_custos.py. Sem mudança de models ou migrations.

## Validação

- 28 testes PostgreSQL isolado aprovados: cálculos financeiros com cancelados,
  filtros, valores efetivamente liquidados, permissões, autenticação, validação,
  trava de concorrência, resposta indisponível e catálogo NASA inválido.
  Uma falha inicial revelou a necessidade de reforço explícito da permissão
  Clima na view; corrigida e suíte revalidada.
- Frontend: testes de componentes, 16 cenários de autenticação, seis de rascunho
  e usabilidade aprovados; TypeScript/Vite/build Docker aprovados. Corrigida a
  tipagem WMS encontrada no primeiro build.
- Django check, makemigrations sem alterações e diff check aprovados.
- Consulta real do Resumo Executivo: quatro indicadores financeiros em reais
  renderizados, com indicação de base e ausência de rentabilidade estimada.
- NASA real: catálogo informa cor natural 10/10/2026 e NDVI 14/09/2026; imagens
  e legenda carregadas. NDVI apresenta áreas sem pixels nesta data/região;
  não foram preenchidas artificialmente. Navegador móvel com 396 px e documento
  de 382 px, sem transbordamento horizontal. Evidência em
  `backups/visual-20261010-082315/ndvi-publico.png`.
- Novo backup antes da atualização: `backups/visual-20261010-082315`, verificado.
- Modelo qwen3:0.6b (522 MB) baixado e digest verificado pelo runtime. Imagem
  oficial Ollama (9,36 GB em disco) fixada por digest no Compose; versão 0.40.2.
  Rede interna confirmada sem gateway ou portas publicadas. O runtime usa CPU.

- Resposta generativa real validada no navegador: pergunta sobre diferença
  entre saldo realizado e lucro respondeu corretamente em português,
  com evidência oficial dos indicadores e nenhum efeito operacional. A
  primeira consulta ultrapassou 55 segundos no carregamento inicial do modelo;
  exibiu 503 com preservação das análises. Repetição com modelo carregado
  respondeu com sucesso. Modelos locais pequenos continuam sujeitos a erros.
  Captura em `backups/visual-20261010-082315/ia-local.png`.
- Serviço local ativo, frontend e backend saudáveis. Conversas executadas em
  CPU; modelo carregado com aproximadamente 781 MB. Nenhum recurso pago usado.

Radar, rentabilidade e média NDVI por talhão permanecem pendentes nos limites acima. Nenhum registro
operacional fictício criado. Sem commit, push, merge ou publicação em produção.
