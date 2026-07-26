# Roadmap do AGRO-AI-PRO

## Versão 1.0 — concluída

- [x] infraestrutura, propriedades, talhões e geoprocessamento;
- [x] previsão climática por propriedade;
- [x] mercado e clima no Corn Belt;
- [x] financeiro;
- [x] estoque e insumos;
- [x] operações agrícolas;
- [x] máquinas;
- [x] relatórios e dashboards;
- [x] inteligência artificial e automação;
- [x] aplicativo PWA.

## Versão 1.1 — em desenvolvimento

### Sprint 13 — Gestão Integrada da Produção Agrícola

- [x] modelagem de culturas, safras e múltiplos CAD/PRO;
- [x] autorização por propriedade e CAD/PRO;
- [x] recebimento e qualidade;
- [x] saldo de grãos por dimensões produtivas e armazenagem;
- [x] entradas, saídas, transferências, ajustes e estornos;
- [x] contratos e embarques;
- [x] integração transacional com o Financeiro;
- [x] auditoria imutável;
- [x] dashboard e relatórios JSON, CSV, XLSX e PDF;
- [x] assistente de importação CSV/XLSX/XLSM;
- [x] interface Enterprise responsiva;
- [x] insights explicáveis de produção;
- [ ] validação completa em CI e homologação local;
- [ ] revisão e autorização para Pull Request e merge.

### Evolução do módulo Clima

- [x] atualização automática com frequência padrão de três horas;
- [x] configuração individual por propriedade;
- [x] estado atual, previsão horária e sete dias;
- [x] cache Redis e deduplicação por propriedade;
- [x] lock contra atualização simultânea;
- [x] coordenadas por cadastro ou geometria processada;
- [x] indicadores para pulverização e colheita;
- [x] alertas internos configuráveis;
- [x] tolerância a falhas e backoff progressivo;
- [x] auditoria e contagem de chamadas;
- [x] worker local no Docker Compose;
- [x] testes de serviços, API, permissões e interface;
- [ ] validação completa em CI e homologação Docker local;
- [ ] definição autorizada da estratégia de provedor para uso comercial.

## Evoluções posteriores

- estação meteorológica local e ingestão de observações reais;
- comparação previsto x observado com fonte licenciada ou equipamento próprio;
- tabelas versionadas de classificação e descontos de qualidade;
- camadas de imagens de satélite mediante solução gratuita e autorizada;
- conciliação fiscal avançada;
- planejamento de comercialização com cenários configuráveis;
- aplicativo de balança e operação offline transacional.
