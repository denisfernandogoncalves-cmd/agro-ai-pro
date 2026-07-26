# Sprint 13 — Gestão Integrada da Produção Agrícola

## Objetivo

Substituir planilhas de produção por um domínio integrado, auditável e compatível com Propriedades, Talhões, Estoque, Financeiro, Relatórios, Mercado, Geoprocessamento e Assistente.

## Escopo implementado

- culturas e safras estruturadas;
- múltiplos CAD/PRO por propriedade;
- acesso adicional por CAD/PRO;
- recebimento com balança e qualidade;
- estoque físico de grãos e transferências;
- ajustes e estornos sem exclusão de histórico;
- compradores, contratos, motoristas, veículos e terceiros reutilizando parceiros existentes;
- embarques com integração financeira;
- auditoria imutável;
- dashboard e relatórios;
- exportações CSV, XLSX e PDF;
- importação de planilhas em duas fases;
- interface Enterprise responsiva;
- insights explicáveis;
- testes de domínio, API, permissões e frontend.

## Regras críticas

- saldo nunca negativo;
- contexto obrigatório de propriedade, CAD/PRO, cultura e safra;
- proteção principal no backend;
- confirmação transacional;
- movimentações imutáveis;
- estorno por movimento inverso;
- nenhum processamento de arquivo em serviço externo;
- nenhuma dependência ou integração paga.

## Estado

Em desenvolvimento. A implementação e a documentação foram produzidas na branch `codex/gestao-integrada-producao`. A Sprint só será marcada como concluída após aprovação de todos os jobs de CI e homologação local do fluxo visual.
