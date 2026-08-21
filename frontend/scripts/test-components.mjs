import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";


const servidor = await createServer({
  appType: "custom",
  configLoader: "runner",
  logLevel: "silent",
  server: { middlewareMode: true },
});

try {
  const { default: TalhaoForm } = await servidor.ssrLoadModule(
    "/src/pages/Talhoes/TalhaoForm.tsx",
  );
  const { default: TalhaoLista } = await servidor.ssrLoadModule(
    "/src/pages/Talhoes/TalhaoLista.tsx",
  );
  const { default: HistoricoAgronomicoPanel } =
    await servidor.ssrLoadModule(
      "/src/pages/Talhoes/HistoricoAgronomicoPanel.tsx",
    );
  const { default: ClimaPage } = await servidor.ssrLoadModule(
    "/src/pages/Clima/ClimaPage.tsx",
  );
  const { default: MercadoPage } = await servidor.ssrLoadModule(
    "/src/pages/Mercado/MercadoPage.tsx",
  );
  const { default: GraficoMercado } = await servidor.ssrLoadModule(
    "/src/pages/Mercado/GraficoMercado.tsx",
  );
  const { default: FinanceiroPage } = await servidor.ssrLoadModule(
    "/src/pages/Financeiro/FinanceiroPage.tsx",
  );
  const { default: EstoquePage } = await servidor.ssrLoadModule(
    "/src/pages/Estoque/EstoquePage.tsx",
  );
  const { default: OperacoesPage } = await servidor.ssrLoadModule(
    "/src/pages/Operacoes/OperacoesPage.tsx",
  );
  const { default: CargasColhidasPage } = await servidor.ssrLoadModule(
    "/src/pages/CargasColhidas/CargasColhidasPage.tsx",
  );
  const { default: GruposColheitaPage } = await servidor.ssrLoadModule(
    "/src/pages/GruposColheita/GruposColheitaPage.tsx",
  );
  const { default: ProducaoSaldosPage, BotaoCreditarProducao } = await servidor.ssrLoadModule(
    "/src/pages/ProducaoSaldos/ProducaoSaldosPage.tsx",
  );
  const { default: VendasPage, BotaoMutacaoVenda, RastreabilidadeVenda } = await servidor.ssrLoadModule(
    "/src/pages/Vendas/VendasPage.tsx",
  );
  const { criarControladorMutacaoVenda } = await servidor.ssrLoadModule(
    "/src/pages/Vendas/vendaMutationController.ts",
  );
  const { criarControladorCreditoProducao } = await servidor.ssrLoadModule(
    "/src/pages/ProducaoSaldos/creditoProducaoSubmission.ts",
  );
  const { default: MaquinasPage } = await servidor.ssrLoadModule(
    "/src/pages/Maquinas/MaquinasPage.tsx",
  );
  const { default: RelatoriosPage } = await servidor.ssrLoadModule(
    "/src/pages/Relatorios/RelatoriosPage.tsx",
  );
  const { TabelaRelatorio } = await servidor.ssrLoadModule(
    "/src/pages/Relatorios/RelatoriosPage.tsx",
  );
  const { default: InsightsPage } = await servidor.ssrLoadModule(
    "/src/pages/Insights/InsightsPage.tsx",
  );
  const { default: AplicativoStatus } = await servidor.ssrLoadModule(
    "/src/components/AplicativoStatus.tsx",
  );
  const { converterGeometria, limitesGeometria } =
    await servidor.ssrLoadModule("/src/utils/geometria.ts");

  const propriedade = {
    id: 1,
    nome: "Fazenda Modelo",
    proprietario: "",
    municipio: "Sorriso",
    uf: "MT",
    area_hectares: "100.00",
    latitude: null,
    longitude: null,
    arquivo_kml: null,
    geometria_geojson: null,
    area_calculada_hectares: null,
    diferenca_area_hectares: null,
    divergencia_area_percentual: null,
    observacoes: "",
    criado_em: "2026-07-25T00:00:00Z",
  };
  const formulario = {
    propriedade: "1",
    nome: "Talhão Norte",
    area_hectares: "20.00",
    cultura_atual: "Soja",
    safra: "2025/2026",
    tipo_solo: "Argiloso",
    altitude_media: "500.00",
    declividade_media: "2.00",
    produtividade_esperada: "65.00",
    produtividade_realizada: "62.50",
    observacoes: "",
    arquivo_kml: null,
  };
  const talhao = {
    id: 1,
    ...formulario,
    propriedade: 1,
    propriedade_nome: propriedade.nome,
    arquivo_kml: null,
    latitude_centro: null,
    longitude_centro: null,
    geometria_geojson: null,
    area_calculada_hectares: null,
    diferenca_area_hectares: null,
    divergencia_area_percentual: null,
    criado_em: "2026-07-25T00:00:00Z",
    atualizado_em: "2026-07-25T00:00:00Z",
  };
  const historico = {
    id: 1,
    talhao: 1,
    talhao_nome: talhao.nome,
    data_referencia: "2026-07-25",
    cultura: "Soja",
    safra: "2025/2026",
    produtividade_esperada: "65.00",
    produtividade_realizada: "62.50",
    observacoes: "Colheita encerrada",
    criado_em: "2026-07-25T00:00:00Z",
    atualizado_em: "2026-07-25T00:00:00Z",
  };

  const htmlFormulario = renderToStaticMarkup(
    React.createElement(TalhaoForm, {
      carregando: false,
      edicao: true,
      formulario,
      propriedades: [propriedade],
      onCancelar() {},
      onChange() {},
      onSubmit() {},
    }),
  );
  assert.match(htmlFormulario, /Editar talhão/);
  assert.match(htmlFormulario, /Produtividade realizada/);
  assert.match(htmlFormulario, /Fazenda Modelo/);

  const htmlLista = renderToStaticMarkup(
    React.createElement(TalhaoLista, {
      carregando: false,
      filtros: {
        search: "",
        propriedade: "",
        cultura: "",
        safra: "",
        ordering: "nome",
      },
      pagina: 1,
      propriedades: [propriedade],
      selecionado: talhao,
      talhoes: [talhao],
      total: 1,
      onAplicarFiltros() {},
      onEditar() {},
      onFiltrosChange() {},
      onPaginaChange() {},
      onRemover() {},
      onSelecionar() {},
    }),
  );
  assert.match(htmlLista, /Talhão Norte/);
  assert.match(htmlLista, /Página 1 de 1/);
  assert.match(htmlLista, /Filtrar por propriedade/);

  const htmlHistorico = renderToStaticMarkup(
    React.createElement(HistoricoAgronomicoPanel, {
      edicao: true,
      formulario: historico,
      historicos: [historico],
      onCancelar() {},
      onChange() {},
      onEditar() {},
      onRemover() {},
      onSubmit() {},
    }),
  );
  assert.match(htmlHistorico, /Atualizar histórico/);
  assert.match(htmlHistorico, /Realizada: 62.50/);
  assert.match(htmlHistorico, /Colheita encerrada|Soja/);

  const multipoligono = {
    type: "MultiPolygon",
    coordinates: [
      [[[-50, -20], [-49, -20], [-49, -19], [-50, -20]]],
      [[[-48, -18], [-47, -18], [-47, -17], [-48, -18]]],
    ],
  };
  const posicoes = converterGeometria(multipoligono);
  assert.equal(posicoes.length, 2);
  assert.deepEqual(posicoes[0][0][0], [-20, -50]);
  assert.deepEqual(limitesGeometria(multipoligono), [
    [-20, -50],
    [-17, -47],
  ]);

  const htmlClima = renderToStaticMarkup(
    React.createElement(ClimaPage, { propriedades: [propriedade] }),
  );
  assert.match(htmlClima, /Atualizar previsão/);
  assert.match(htmlClima, /precisa de latitude e longitude/);

  const htmlMercado = renderToStaticMarkup(React.createElement(MercadoPage));
  assert.match(htmlMercado, /Atualizar cotações/);
  assert.match(htmlMercado, /Não constituem recomendação/);

  const htmlGrafico = renderToStaticMarkup(
    React.createElement(GraficoMercado, {
      cotacoes: [
        {
          id: 1,
          produto: "soja",
          produto_nome: "Soja",
          data: "2026-05-01",
          valor: "400",
          unidade: "US$/tonelada métrica",
          fonte: "FRED / FMI",
        },
        {
          id: 2,
          produto: "soja",
          produto_nome: "Soja",
          data: "2026-06-01",
          valor: "420",
          unidade: "US$/tonelada métrica",
          fonte: "FRED / FMI",
        },
      ],
    }),
  );
  assert.match(htmlGrafico, /Evolução histórica/);
  assert.match(htmlGrafico, /400.00/);

  const htmlFinanceiro = renderToStaticMarkup(
    React.createElement(FinanceiroPage, { propriedades: [propriedade] }),
  );
  assert.match(htmlFinanceiro, /Novo lançamento/);
  assert.match(htmlFinanceiro, /Cadastros auxiliares/);

  const htmlEstoque = renderToStaticMarkup(
    React.createElement(EstoquePage, { propriedades: [propriedade] }),
  );
  assert.match(htmlEstoque, /Nova movimentaÃ§Ã£o|Nova movimentação/);
  assert.match(htmlEstoque, /Rastreabilidade/);
  assert.match(htmlEstoque, /Cadastros de produtos, locais e lotes/);

  const htmlOperacoes = renderToStaticMarkup(
    React.createElement(OperacoesPage),
  );
  assert.match(htmlOperacoes, /Planejar operaÃ§Ã£o|Planejar operação/);
  assert.match(htmlOperacoes, /Nenhuma operaÃ§Ã£o planejada|Nenhuma operação planejada/);

  const htmlCargas = renderToStaticMarkup(
    React.createElement(CargasColhidasPage, { propriedades: [propriedade] }),
  );
  assert.match(htmlCargas, /Registrar carga manual/);
  assert.match(htmlCargas, /Propriedades da colheita/);
  assert.match(htmlCargas, /Talhões da colheita/);
  assert.match(htmlCargas, /Nome do motorista/);
  assert.match(htmlCargas, /Peso líquido/);
  assert.match(htmlCargas, /Nenhuma carga colhida registrada/);

  const htmlGrupos = renderToStaticMarkup(
    React.createElement(GruposColheitaPage, { propriedades: [propriedade] }),
  );
  assert.match(htmlGrupos, /Novo grupo/);
  assert.doesNotMatch(htmlGrupos, /Armazenagem padrão/);
  assert.match(htmlGrupos, /CAD\/PRO da propriedade/);
  assert.match(htmlGrupos, /Quebrados/);
  assert.match(htmlGrupos, /PH mínimo/);
  assert.match(htmlGrupos, /Observações/);
  assert.match(htmlGrupos, /Filtrar por CAD\/PRO/);
  assert.doesNotMatch(htmlGrupos, /Filtrar por armazenagem/);
  assert.match(htmlGrupos, /Nenhum grupo de colheita encontrado/);

  const htmlProducaoSaldos = renderToStaticMarkup(
    React.createElement(ProducaoSaldosPage, { propriedades: [propriedade] }),
  );
  assert.match(htmlProducaoSaldos, /Registrar produção/);
  assert.match(htmlProducaoSaldos, /Saldo físico/);
  assert.match(htmlProducaoSaldos, /Comprometido/);
  assert.match(htmlProducaoSaldos, /Disponível/);
  assert.match(htmlProducaoSaldos, /classificação · armazenagem/);
  assert.match(htmlProducaoSaldos, /Rastreabilidade recente/);

  const htmlBotaoPendente = renderToStaticMarkup(
    React.createElement(BotaoCreditarProducao, { desabilitado: true }),
  );
  assert.match(htmlBotaoPendente, /disabled=""/);

  const chaves = ["tentativa-1", "tentativa-2", "tentativa-3"];
  const controlador = criarControladorCreditoProducao(() => chaves.shift());
  const payloadCredito = {
    lote: 1,
    quantidade_kg: "100.000",
    data_movimento: "2026-08-12",
    referencia_externa: "ROM-1",
    observacoes: "",
  };
  let liberarCredito;
  let chamadasCredito = 0;
  let efeitoLedger = 0;
  const enviarCreditoPendente = (dados) => {
    chamadasCredito += 1;
    assert.equal(dados.chave_idempotencia, "tentativa-1");
    return new Promise((resolve) => {
      liberarCredito = () => {
        efeitoLedger += 1;
        resolve({ idempotente: false });
      };
    });
  };
  const primeiroClique = controlador.enviar(payloadCredito, enviarCreditoPendente);
  const segundoClique = controlador.enviar(payloadCredito, enviarCreditoPendente);
  assert.equal(controlador.emAndamento(), true);
  assert.equal(chamadasCredito, 1);
  assert.equal(primeiroClique, segundoClique);
  liberarCredito();
  await primeiroClique;
  assert.equal(efeitoLedger, 1);
  assert.equal(controlador.emAndamento(), false);

  const erroEsperado = new Error("falha de rede");
  let chaveDoErro;
  await assert.rejects(
    controlador.enviar(payloadCredito, async (dados) => {
      chaveDoErro = dados.chave_idempotencia;
      throw erroEsperado;
    }),
    erroEsperado,
  );
  await controlador.enviar(payloadCredito, async (dados) => {
    assert.equal(dados.chave_idempotencia, chaveDoErro);
    return { idempotente: true };
  });

  const htmlVendas = renderToStaticMarkup(React.createElement(VendasPage));
  assert.match(htmlVendas, /Vendas com bloqueio por saldo/);
  assert.match(htmlVendas, /Novo contrato/);
  assert.match(htmlVendas, /Criar rascunho/);
  const htmlRastreabilidadeVenda = renderToStaticMarkup(
    React.createElement(RastreabilidadeVenda, {
      venda: { posicao: 17, lote_operacional_codigo: "COLH-2-PADRAO" },
    }),
  );
  assert.match(htmlRastreabilidadeVenda, /posição oficial #17/);
  assert.match(htmlRastreabilidadeVenda, /adaptador operacional do ledger/);
  assert.match(htmlRastreabilidadeVenda, /Nenhum lote ou carga representa origem física alocada/);
  assert.doesNotMatch(htmlRastreabilidadeVenda, /Cargas e grupos de origem do lote/);
  const htmlBotaoVenda = renderToStaticMarkup(
    React.createElement(BotaoMutacaoVenda, { processando: true }, "Confirmar"),
  );
  assert.match(htmlBotaoVenda, /disabled=""/);

  const chavesVenda = ["venda-tentativa-1", "venda-tentativa-2"];
  const controladorVenda = criarControladorMutacaoVenda(() => chavesVenda.shift());
  let liberarVenda;
  let chamadasVenda = 0;
  const primeiraVenda = controladorVenda.executar("confirmar:1", (chave) => {
    chamadasVenda += 1;
    assert.equal(chave, "venda-tentativa-1");
    return new Promise((resolve) => { liberarVenda = resolve; });
  });
  const segundaVenda = controladorVenda.executar("confirmar:1", () => {
    chamadasVenda += 1;
    return Promise.resolve();
  });
  assert.equal(chamadasVenda, 1);
  assert.equal(primeiraVenda, segundaVenda);
  assert.equal(controladorVenda.emAndamento(), true);
  liberarVenda({ status: "confirmada" });
  await primeiraVenda;
  assert.equal(controladorVenda.emAndamento(), false);

  let chaveComErro;
  await assert.rejects(controladorVenda.executar("entregar:1:100", async (chave) => {
    chaveComErro = chave;
    throw new Error("rede");
  }));
  await controladorVenda.executar("entregar:1:100", async (chave) => {
    assert.equal(chave, chaveComErro);
    return { status: "parcial" };
  });
  await controlador.enviar(payloadCredito, async (dados) => {
    assert.notEqual(dados.chave_idempotencia, chaveDoErro);
    return { idempotente: false };
  });

  const htmlMaquinas = renderToStaticMarkup(
    React.createElement(MaquinasPage, { propriedades: [propriedade] }),
  );
  assert.match(htmlMaquinas, /Nova mÃ¡quina|Nova máquina/);
  assert.match(htmlMaquinas, /Uso, combustÃ­vel e manutenÃ§Ã£o|Uso, combustível e manutenção/);

  const htmlRelatorios = renderToStaticMarkup(
    React.createElement(RelatoriosPage, { propriedades: [propriedade] }),
  );
  assert.match(htmlRelatorios, /Relatórios operacionais/);
  assert.match(htmlRelatorios, /Somente leitura/);
  assert.match(htmlRelatorios, /Classificação/);
  assert.match(htmlRelatorios, /Armazenagem/);
  const htmlTabelaRelatorios = renderToStaticMarkup(
    React.createElement(TabelaRelatorio, {
      secao: "saldos",
      itens: [{
        id: 17, cad_pro_codigo: "CAD-1", propriedade_nome: "Fazenda Modelo",
        cultura: "Soja", safra: "2026/2027", classificacao_codigo: "PADRAO",
        armazem_nome: "Silo 1", saldo_fisico_kg: "1000.000",
        saldo_comprometido_kg: "250.000", saldo_disponivel_kg: "750.000",
      }],
    }),
  );
  assert.match(htmlTabelaRelatorios, /CAD-1/);
  assert.match(htmlTabelaRelatorios, /Físico/);
  assert.match(htmlTabelaRelatorios, /disponível/);

  const htmlRastreabilidadeRelatorios = renderToStaticMarkup(
    React.createElement(TabelaRelatorio, {
      secao: "rastreabilidade",
      itens: [{
        id: 91,
        operacao: "credito_producao",
        tipo: "entrada",
        data: "2026-08-12",
        quantidade_kg: "800.000",
        delta_fisico_kg: "800.000",
        delta_comprometido_kg: "0.000",
        origem: 71,
        origem_tipo: "producao",
        referencia_externa: "ROM-2026-91",
        lote_operacional: 41,
        lote_operacional_codigo: "LOTE-NORTE",
        snapshot_anterior: { saldo_fisico_kg: "0.000", saldo_comprometido_kg: "0.000", saldo_disponivel_kg: "0.000" },
        snapshot_posterior: { saldo_fisico_kg: "800.000", saldo_comprometido_kg: "0.000", saldo_disponivel_kg: "800.000" },
        carga_colhida: 81,
        grupo_colheita: 61,
        grupo_colheita_nome: "Grupo Norte",
        placa_carga: "ABC1D23",
        posicao: {
          id: 17, cad_pro_codigo: "CAD-1", propriedade_nome: "Fazenda Modelo",
          cultura: "Soja", safra: "2026/2027", classificacao_codigo: "PADRAO", armazem_nome: "Silo 1",
        },
      }],
    }),
  );
  assert.match(htmlRastreabilidadeRelatorios, /Origem/);
  assert.match(htmlRastreabilidadeRelatorios, /#71/);
  assert.match(htmlRastreabilidadeRelatorios, /0,000 kg/);
  assert.match(htmlRastreabilidadeRelatorios, /800,000 kg/);
  assert.match(htmlRastreabilidadeRelatorios, /Carga #81/);
  assert.match(htmlRastreabilidadeRelatorios, /Grupo Norte/);
  assert.match(htmlRastreabilidadeRelatorios, /ABC1D23/);

  const htmlInsights = renderToStaticMarkup(
    React.createElement(InsightsPage, { propriedades: [propriedade] }),
  );
  assert.match(htmlInsights, /Assistente gerencial/);
  assert.match(htmlInsights, /Analisar dados atuais/);

  const htmlAplicativo = renderToStaticMarkup(React.createElement(AplicativoStatus));
  assert.match(htmlAplicativo, /Online|Offline/);
  const manifesto = JSON.parse(
    await readFile(new URL("../public/manifest.webmanifest", import.meta.url), "utf8"),
  );
  assert.equal(manifesto.display, "standalone");
  const serviceWorker = await readFile(
    new URL("../public/sw.js", import.meta.url),
    "utf8",
  );
  assert.match(serviceWorker, /pathname\.startsWith\(\"\/api\/\"\)/);

  console.log("24 testes de componentes, submissão, geometria e PWA aprovados.");
} finally {
  await servidor.close();
}
