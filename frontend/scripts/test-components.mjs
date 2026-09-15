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
  const { loteElegivel } = await servidor.ssrLoadModule("/src/api/importacoes.ts");
  const lotePronto = { pode_confirmar: true, total_erros: 0, total_linhas: 2, status: "pronto_confirmacao" };
  assert.equal(loteElegivel(lotePronto), true);
  for (const alteracao of [{ pode_confirmar: false }, { total_erros: 1 }, { total_linhas: 0 }, { status: "confirmado" }, { status: "confirmando" }]) {
    assert.equal(loteElegivel({ ...lotePronto, ...alteracao }), false);
  }
  const { default: ImportacoesPage } = await servidor.ssrLoadModule("/src/pages/Importacoes/ImportacoesPage.tsx");
  const importacoesHtml = renderToStaticMarkup(React.createElement(ImportacoesPage));
  assert.match(importacoesHtml, /Gerar prévia/);
  assert.doesNotMatch(importacoesHtml, /Confirmar importação/);
  const { aplicarGrupoNaCarga } = await servidor.ssrLoadModule("/src/api/gruposPropriedades.ts");
  const grupoTeste = { ativo: true, membros: [
    { propriedade: 1, cad_pro: "compartilhado", disponivel: true },
    { propriedade: 2, cad_pro: "compartilhado", disponivel: true },
  ] };
  const cargaOriginal = { peso_bruto_kg: "600", safra: "2026", talhoes_selecionados: [99], propriedades_selecionadas: [99] };
  const preenchida = aplicarGrupoNaCarga(cargaOriginal, grupoTeste);
  assert.deepEqual(preenchida.propriedades_selecionadas, [1, 2]);
  assert.deepEqual(preenchida.cadpros_por_propriedade, { 1: "compartilhado", 2: "compartilhado" });
  assert.equal(preenchida.propriedade, "1");
  assert.equal(preenchida.cad_pro, "compartilhado");
  assert.equal(preenchida.peso_bruto_kg, "600");
  assert.equal(preenchida.safra, "2026");
  assert.deepEqual(preenchida.talhoes_selecionados, []);
  assert.deepEqual(cargaOriginal.propriedades_selecionadas, [99]);
  assert.throws(() => aplicarGrupoNaCarga(cargaOriginal, { ...grupoTeste, ativo: false }));
  assert.throws(() => aplicarGrupoNaCarga(cargaOriginal, { ...grupoTeste, membros: [] }));
  assert.throws(() => aplicarGrupoNaCarga(cargaOriginal, { ...grupoTeste, membros: [{ ...grupoTeste.membros[0], disponivel: false }] }));
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
  const { default: LeitorCodigoFinanceiro, aplicarLeituraFinanceira, ResumoCodigoFinanceiro } = await servidor.ssrLoadModule(
    "/src/pages/Financeiro/LeitorCodigoFinanceiro.tsx",
  );
  const codigoFinanceiro = "00197100000000123451234567890123456789012345";
  const formularioFinanceiro = {
    tipo: "pagar", descricao: "Insumos", parceiro: "7", categoria: "3",
    propriedade: "2", safra: "2026/2027", valor: "900.00", data_vencimento: "2026-10-01",
    observacoes: "Conferir nota", codigo_barras: "anterior",
  };
  const leituraFinanceira = { codigo_barras: codigoFinanceiro, valor: "123.45" };
  const comDescricao = { ...leituraFinanceira, descricao_sugerida: "Boleto bancário · banco 001" };
  assert.equal(aplicarLeituraFinanceira({ ...formularioFinanceiro, descricao: "" }, comDescricao, "").descricao, comDescricao.descricao_sugerida);
  assert.equal(aplicarLeituraFinanceira({ ...formularioFinanceiro, descricao: "Compra de sementes" }, comDescricao, "").descricao, "Compra de sementes");
  assert.deepEqual(aplicarLeituraFinanceira(formularioFinanceiro, leituraFinanceira, "2025-02-22"), {
    ...formularioFinanceiro, codigo_barras: codigoFinanceiro, valor: "123.45", data_vencimento: "2025-02-22",
  });
  const semValorFinanceiro = aplicarLeituraFinanceira(formularioFinanceiro, { ...leituraFinanceira, valor: null }, "");
  assert.equal(semValorFinanceiro.valor, "");
  assert.equal(semValorFinanceiro.data_vencimento, "");
  assert.equal(formularioFinanceiro.valor, "900.00");
  let aplicacoesFinanceiras = 0;
  const htmlLeitorFinanceiro = renderToStaticMarkup(React.createElement(LeitorCodigoFinanceiro, {
    desabilitado: false, aplicar: () => { aplicacoesFinanceiras++; },
  }));
  assert.match(htmlLeitorFinanceiro, /leitor USB em modo teclado/);
  assert.match(htmlLeitorFinanceiro, /Extrair dados/);
  assert.match(htmlLeitorFinanceiro, /Posicionar leitor/);
  assert.doesNotMatch(htmlLeitorFinanceiro, /Salvar lançamento/);
  assert.equal(aplicacoesFinanceiras, 0);
  const resumoLeitura = renderToStaticMarkup(React.createElement(ResumoCodigoFinanceiro, {
    leitura: { ...leituraFinanceira, banco_codigo: "341", banco_nome: "ITAÚ UNIBANCO S.A.",
      detalhes: [{ campo: "Agência do beneficiário", valor: "0057" }], linha_digitavel_formatada: "linha de teste" },
  }));
  for (const texto of ["ITAÚ UNIBANCO S.A.", "341", "Agência do beneficiário", "0057", "linha de teste", "não disponível no código"]) assert.ok(resumoLeitura.includes(texto), texto);
  const { default: FinanceiroPage } = await servidor.ssrLoadModule(
    "/src/pages/Financeiro/FinanceiroPage.tsx",
  );
  const { default: EstoquePage } = await servidor.ssrLoadModule(
    "/src/pages/Estoque/EstoquePage.tsx",
  );
  const { default: OperacoesPage } = await servidor.ssrLoadModule(
    "/src/pages/Operacoes/OperacoesPage.tsx",
  );
  const {
    default: CargasColhidasPage,
    CartaoCargaColhida,
    TabelaImpressaoCargas,
    cargaCorrespondeBusca,
    dataPlanilhaCarga,
    identificacaoCargaColhida,
    numeroPlanilhaCarga,
  } = await servidor.ssrLoadModule(
    "/src/pages/CargasColhidas/CargasColhidasPage.tsx",
  );
  const { default: CadastrosAgricolasPage } = await servidor.ssrLoadModule(
    "/src/pages/CadastrosAgricolas/CadastrosAgricolasPage.tsx",
  );
  const { default: ProducaoSaldosPage, BotaoCreditarProducao, TabelaImpressaoSaldos, filtrarLotesProducao, identificacaoPosicaoSaldo, mesmosFiltrosSaldo, numeroPlanilhaSaldo } = await servidor.ssrLoadModule(
    "/src/pages/ProducaoSaldos/ProducaoSaldosPage.tsx",
  );
  const { default: VendasPage, AcoesLancamentoVenda, BotaoMutacaoVenda, RastreabilidadeVenda, TabelaImpressaoVendas, dataPlanilhaVenda, identificacaoCadProVenda, numeroPlanilhaVenda, rotuloPosicaoVenda } = await servidor.ssrLoadModule(
    "/src/pages/Vendas/VendasPage.tsx",
  );
  const { default: SeletorColunasImpressao, normalizarColunasImpressao } = await servidor.ssrLoadModule(
    "/src/components/SeletorColunasImpressao.tsx",
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
  const { rotuloPropriedade } = await servidor.ssrLoadModule(
    "/src/api/propriedades.ts",
  );

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
    cad_pro_numeros: ["9542825895"],
    criado_em: "2026-07-25T00:00:00Z",
  };
  assert.equal(
    rotuloPropriedade(propriedade),
    "Fazenda Modelo — CAD/PRO 9542825895",
  );
  assert.equal(
    rotuloPropriedade({ nome: "Fazenda sem cadastro", cad_pro_numeros: [] }),
    "Fazenda sem cadastro — CAD/PRO não informado",
  );
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
  assert.match(htmlFormulario, /Fazenda Modelo — CAD\/PRO 9542825895/);

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
  assert.match(htmlLista, /Fazenda Modelo — CAD\/PRO 9542825895/);

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
  assert.match(htmlClima, /Fazenda Modelo — CAD\/PRO 9542825895/);

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
  assert.match(htmlFinanceiro, /Quem vai receber/);
  assert.match(htmlFinanceiro, /Número deste boleto/);
  assert.match(htmlFinanceiro, /Total de boletos da compra/);
  assert.match(htmlFinanceiro, /Valor deste boleto/);
  assert.match(htmlFinanceiro, /Salvar boleto/);
  assert.doesNotMatch(htmlFinanceiro, /Salvar parcelas|Vencimentos mensais|Valor total/);
  const cssFinanceiro = await readFile(new URL("../src/styles.css", import.meta.url), "utf8");
  assert.match(cssFinanceiro, /\.modulo-financeiro \.formulario\s*\{\s*position:\s*static/);
  assert.doesNotMatch(htmlFinanceiro, /Cadastros auxiliares|<label>Categoria|<label>Parceiro|<label>Centro de custo|<label>Propriedade|<label>Safra/);
  const { calcularPreviaParcelas } = await servidor.ssrLoadModule("/src/pages/Financeiro/ParcelasPreview.tsx");
  const previaParcelas = calcularPreviaParcelas("100.00", 3, "2028-01-31");
  assert.deepEqual(previaParcelas.map(p => p.centavos), [3334, 3333, 3333]);
  assert.deepEqual(previaParcelas.map(p => p.vencimento), ["2028-01-31", "2028-02-29", "2028-03-31"]);
  assert.equal(previaParcelas.reduce((s, p) => s + p.centavos, 0), 10000);
  assert.deepEqual(calcularPreviaParcelas("100", 3, "2026-12-31").map(p => p.vencimento), ["2026-12-31", "2027-01-31", "2027-02-28"]);
  for (const entrada of [["0.02", 3, "2028-01-31"], ["100", 0, "2028-01-31"], ["100", 1.5, "2028-01-31"], ["100", 121, "2028-01-31"], ["100", 3, "2026-02-30"]]) assert.deepEqual(calcularPreviaParcelas(...entrada), []);

  const htmlEstoque = renderToStaticMarkup(
    React.createElement(EstoquePage, { propriedades: [propriedade] }),
  );
  assert.match(htmlEstoque, /Nova movimentaÃ§Ã£o|Nova movimentação/);
  assert.match(htmlEstoque, /Rastreabilidade/);
  assert.match(htmlEstoque, /Novo lote/);
  assert.doesNotMatch(htmlEstoque, /Cadastrar produto/);

  const htmlOperacoes = renderToStaticMarkup(
    React.createElement(OperacoesPage),
  );
  assert.match(htmlOperacoes, /Planejar operaÃ§Ã£o|Planejar operação/);
  assert.match(htmlOperacoes, /Nenhuma operaÃ§Ã£o planejada|Nenhuma operação planejada/);

  const htmlCargas = renderToStaticMarkup(
    React.createElement(CargasColhidasPage, { propriedades: [propriedade] }),
  );
  assert.match(htmlCargas, /Registrar carga manual/);
  assert.match(htmlCargas, /formulario-carga-horizontal/);
  assert.match(htmlCargas, /CAD\/PRO/);
  assert.match(htmlCargas, /Escolha as propriedades/);
  assert.doesNotMatch(htmlCargas, /<label>Propriedade<select/);
  assert.match(htmlCargas, /Talhões das propriedades/);
  assert.match(htmlCargas, /Nome do motorista/);
  assert.match(htmlCargas, /Peso líquido/);
  assert.doesNotMatch(htmlCargas, /Controle de estoque por propriedade/);
  assert.doesNotMatch(htmlCargas, /Propriedade consultada/);
  assert.doesNotMatch(htmlCargas, /Parcela da propriedade/);
  assert.doesNotMatch(htmlCargas, /<th>Peso bruto<\/th>/);
  assert.match(htmlCargas, /Nenhuma carga colhida ativa/);
  assert.doesNotMatch(htmlCargas, /Grupo de colheita/);
  const estilosTela = await readFile(new URL("../src/styles.css", import.meta.url), "utf8");
  assert.match(estilosTela, /\.cargas-grade\s*\{\s*grid-template-columns:\s*1fr/);
  assert.match(estilosTela, /\.formulario-carga-horizontal\s*\{[\s\S]*?grid-template-columns:\s*repeat\(4,/);
  assert.match(estilosTela, /@media\s*\(max-width:\s*860px\)[\s\S]*?\.formulario-carga-horizontal,[\s\S]*?grid-template-columns:\s*1fr/);

  const cargaRateada = {
    propriedade: 1,
    propriedade_nome: "Fazenda Modelo",
    cad_pro: "cad-principal",
    cad_pro_codigo: "CAD-1",
    destinado_semente: true,
    peso_liquido_kg: "975.000",
    sacas_60kg: "16.250",
    contexto_colheita: {
      rateio_producao: [
        {
          propriedade_id: 1,
          cad_pro_id: "cad-principal",
          cad_pro_numero: "CAD-1",
          peso_liquido_kg: "650.000",
          sacas_60kg: "10.833",
        },
        {
          propriedade_id: 2,
          cad_pro_id: "cad-associado",
          cad_pro_numero: "CAD-2",
          peso_liquido_kg: "325.000",
          sacas_60kg: "5.417",
        },
      ],
    },
  };
  const cargaDoisCadpros = {
    ...cargaRateada, id: 41, status: "ativa", data_colheita: "2026-08-30",
    propriedade: 8, propriedade_nome: "SÍTIO SAGRILO", cad_pro_codigo: "987654321",
    motorista: "DENIS", placa: "", cultura: "Milho", safra: "2026",
    armazem_nome: "teste", peso_bruto_kg: "60000.000", desconto_total_percentual: "1.750",
    peso_liquido_kg: "58950.000", sacas_60kg: "982.500", movimentacao: 56,
    destinado_semente: false, umidade_percentual: "15.00", impureza_percentual: "1.00",
    defeitos_percentual: "0.00", ph: "0.00", contexto_colheita: {
      rateio_producao: [
        { propriedade_id: 8, propriedade_nome: "SÍTIO SAGRILO", cad_pro_numero: "987654321", peso_liquido_kg: "41265.000", sacas_60kg: "687.750" },
        { propriedade_id: 7, propriedade_nome: "teste 2", cad_pro_numero: "2056", peso_liquido_kg: "17685.000", sacas_60kg: "294.750" },
      ],
    },
  };
  const renderizarCarga = (item) => renderToStaticMarkup(React.createElement(CartaoCargaColhida, {
    item, carregando: false, onEditar() {}, onExcluir() {},
  }));
  const htmlCargaCompartilhada = renderizarCarga(cargaDoisCadpros);
  assert.match(htmlCargaCompartilhada, /Carga compartilhada · 2 propriedades/);
  assert.match(htmlCargaCompartilhada, /SÍTIO SAGRILO[\s\S]*?CAD\/PRO 987654321[\s\S]*?41\.265 kg[\s\S]*?687,75 sc/);
  assert.match(htmlCargaCompartilhada, /teste 2[\s\S]*?CAD\/PRO 2056[\s\S]*?17\.685 kg[\s\S]*?294,75 sc/);
  assert.match(htmlCargaCompartilhada, /Total da carga[\s\S]*?982,5 sc/);
  assert.match(htmlCargaCompartilhada, /Líquido total[\s\S]*?58\.950 kg/);
  assert.equal((htmlCargaCompartilhada.match(/>Editar</g) || []).length, 1);
  assert.equal((htmlCargaCompartilhada.match(/>Excluir</g) || []).length, 1);
  assert.equal(cargaCorrespondeBusca(cargaDoisCadpros, " TESTE 2 "), true);
  assert.equal(cargaCorrespondeBusca(cargaDoisCadpros, "2056"), true);
  assert.equal(cargaCorrespondeBusca(cargaDoisCadpros, "SAGRILO"), true);
  assert.equal(cargaCorrespondeBusca(cargaDoisCadpros, "milho"), true);
  assert.equal(cargaCorrespondeBusca(cargaDoisCadpros, "inexistente"), false);
  const htmlCargaHistorica = renderizarCarga({ ...cargaDoisCadpros, status: "cancelada" });
  assert.match(htmlCargaHistorica, /CAD\/PRO 2056/);
  assert.match(htmlCargaHistorica, /Cancelada/);
  assert.doesNotMatch(htmlCargaHistorica, /<button/);
  const htmlCargaLegada = renderizarCarga({ ...cargaDoisCadpros, contexto_colheita: {} });
  assert.match(htmlCargaLegada, /SÍTIO SAGRILO/);
  assert.match(htmlCargaLegada, /CAD\/PRO 987654321/);
  assert.doesNotMatch(htmlCargaLegada, /Carga compartilhada|CAD\/PRO 2056/);
  const propriedadesCarga = [
    { id: 8, proprietario: "Denis" },
    { id: 7, proprietario: "Conrado" },
  ];
  assert.equal(dataPlanilhaCarga("2026-08-30"), "30/08/2026");
  assert.equal(numeroPlanilhaCarga("58950.000"), "58.950,000");
  assert.equal(identificacaoCargaColhida(cargaDoisCadpros, propriedadesCarga), "SÍTIO SAGRILO - 987654321 - Denis · teste 2 - 2056 - Conrado");
  const htmlTabelaCargas = renderToStaticMarkup(React.createElement(TabelaImpressaoCargas, {
    cargas: [cargaDoisCadpros], propriedades: propriedadesCarga,
  }));
  for (const valor of ["Propriedade / CAD-PRO / proprietário", "30/08/2026", "60.000,000", "58.950,000", "982,500", "Total das linhas impressas"]) assert.ok(htmlTabelaCargas.includes(valor), valor);

  const htmlCadastrosAgricolas = renderToStaticMarkup(
    React.createElement(CadastrosAgricolasPage, { propriedades: [propriedade] }),
  );
  assert.match(htmlCadastrosAgricolas, /Silos e armazéns de grãos/);
  assert.match(htmlCadastrosAgricolas, /Destinos independentes de propriedades/);
  assert.match(htmlCadastrosAgricolas, /Depósitos de insumos/);
  assert.match(htmlCadastrosAgricolas, /Produtos agrícolas/);
  assert.match(htmlCadastrosAgricolas, /Fornecedores/);
  assert.match(htmlCadastrosAgricolas, /modulo-cadastros-agricolas/);
  assert.match(htmlCadastrosAgricolas, /Silos e armazéns de grãos[\s\S]*?<form class="conteudo"><label>Nome/);

  const htmlProducaoSaldos = renderToStaticMarkup(
    React.createElement(ProducaoSaldosPage, { propriedades: [propriedade] }),
  );
  assert.match(htmlProducaoSaldos, /Registrar produção/);
  assert.match(htmlProducaoSaldos, /Saldo físico/);
  assert.match(htmlProducaoSaldos, /Comprometido/);
  assert.match(htmlProducaoSaldos, /Disponível/);
  assert.match(htmlProducaoSaldos, /classificação · armazenagem/);
  assert.match(htmlProducaoSaldos, /Rastreabilidade recente/);

  const lotesMesmoCadpro = [
    { id: 1, propriedade_id: 1, cad_pro: "cad-compartilhado", armazem: 10, ativo: true },
    { id: 2, propriedade_id: 2, cad_pro: "cad-compartilhado", armazem: 10, ativo: true },
    { id: 3, propriedade_id: null, cad_pro: "cad-compartilhado", armazem: 10, ativo: true },
    { id: 4, propriedade_id: 1, cad_pro: "cad-compartilhado", armazem: 20, ativo: true },
    { id: 5, propriedade_id: 1, cad_pro: "cad-compartilhado", armazem: 10, ativo: false },
    { id: 6, propriedade_id: 1, cad_pro: null, armazem: 10, ativo: true },
  ];
  assert.deepEqual(filtrarLotesProducao(lotesMesmoCadpro, { propriedade: "1" }).map((lote) => lote.id), [1, 4]);
  assert.deepEqual(filtrarLotesProducao(lotesMesmoCadpro, { propriedade: "2" }).map((lote) => lote.id), [2]);
  assert.deepEqual(filtrarLotesProducao(lotesMesmoCadpro).map((lote) => lote.id), [1, 2, 3, 4]);
  assert.deepEqual(filtrarLotesProducao(lotesMesmoCadpro, { propriedade: "99" }), []);
  const loteCredito = {
    id: 10, propriedade_id: 1, cad_pro: "cad-1", armazem: 10, ativo: true,
    cultura: "Soja", safra: "2026/2027", classificacao_codigo: "PADRAO",
  };
  const filtrosCredito = {
    propriedade: "1", cad_pro: "cad-1", armazem: "10",
    cultura: " soja ", safra: " 2026/2027 ", classificacao_codigo: " padrao ",
  };
  const lotesOutrasDimensoes = [
    loteCredito,
    { ...loteCredito, id: 11, cad_pro: "cad-2" },
    { ...loteCredito, id: 12, cultura: "Milho" },
    { ...loteCredito, id: 13, safra: "2025/2026" },
    { ...loteCredito, id: 14, classificacao_codigo: "AVARIADO" },
    { ...loteCredito, id: 15, armazem: 20 },
    { ...loteCredito, id: 16, propriedade_id: 2 },
  ];
  assert.deepEqual(filtrarLotesProducao(lotesOutrasDimensoes, filtrosCredito).map(l => l.id), [10]);
  for (const [campo, esperado] of [
    ["propriedade", [10, 11, 12, 13, 14, 15]],
    ["cad_pro", [10, 12, 13, 14, 15, 16]],
    ["cultura", [10, 11, 13, 14, 15, 16]],
    ["safra", [10, 11, 12, 14, 15, 16]],
    ["classificacao_codigo", [10, 11, 12, 13, 15, 16]],
    ["armazem", [10, 11, 12, 13, 14, 16]],
  ]) {
    assert.deepEqual(filtrarLotesProducao(lotesOutrasDimensoes, { [campo]: filtrosCredito[campo] }).map(l => l.id), esperado);
  }
  assert.equal(filtrarLotesProducao(lotesOutrasDimensoes, { cad_pro: "cad-2" }).some(l => l.id === loteCredito.id), false);
  assert.deepEqual(filtrarLotesProducao(lotesOutrasDimensoes).map(l => l.id), [10, 11, 12, 13, 14, 15, 16]);
  assert.equal(mesmosFiltrosSaldo({ propriedade: "3", cultura: "Trigo" }, { cultura: "Trigo", propriedade: "3" }), true);
  assert.equal(mesmosFiltrosSaldo({ propriedade: "3" }, { propriedade: "1" }), false);
  assert.equal(mesmosFiltrosSaldo({ propriedade: "3", cultura: "Trigo" }, { propriedade: "3", cultura: "Milho" }), false);
  assert.match(htmlProducaoSaldos, /controle-planilha-producao/);
  assert.match(htmlProducaoSaldos, /Controle de produção e estoque/);
  assert.equal(numeroPlanilhaSaldo("37440.000"), "37.440,000");
  const posicaoImpressao = {
    id: 1, propriedade_id: 1, propriedade_nome: "Fazenda Modelo",
    cad_pro: "cad-1", cad_pro_codigo: "CAD-1", cultura: "Soja", safra: "2026/2027",
    classificacao_codigo: "PADRAO", armazem: 1, armazem_nome: "Silo Central",
    saldo_fisico_kg: "1000.000", saldo_comprometido_kg: "250.000",
    saldo_disponivel_kg: "750.000", versao: 1, atualizado_em: "2026-09-02T12:00:00Z",
  };
  const propriedadeImpressao = { ...propriedade, proprietario: "Produtor Modelo" };
  assert.equal(identificacaoPosicaoSaldo(posicaoImpressao, [propriedadeImpressao]), "Fazenda Modelo - CAD-1 - Produtor Modelo");
  const htmlTabelaSaldos = renderToStaticMarkup(React.createElement(TabelaImpressaoSaldos, {
    posicoes: [posicaoImpressao, { ...posicaoImpressao, id: 2, saldo_fisico_kg: "500.000", saldo_comprometido_kg: "100.000", saldo_disponivel_kg: "400.000" }],
    propriedades: [propriedadeImpressao],
  }));
  for (const valor of ["Propriedade / CAD-PRO / proprietário", "Silo Central", "1.500,000", "350,000", "1.150,000", "Total das posições impressas"]) assert.ok(htmlTabelaSaldos.includes(valor), valor);
  assert.doesNotMatch(htmlTabelaSaldos, /Classificação|PADRAO/);
  const estilosImpressao = await readFile(new URL("../src/print.css", import.meta.url), "utf8");
  assert.match(estilosImpressao, /@page\s+planilha\s*\{[\s\S]*?size:\s*A4\s+landscape/);
  assert.match(estilosImpressao, /\.modulo-producao-saldos\s*>\s*\.controle-planilha-producao\s*\{\s*display:\s*block\s*!important/);
  assert.match(estilosImpressao, /\.modulo-cargas\s*>\s*\.controle-planilha-cargas\s*\{\s*display:\s*block\s*!important/);
  assert.match(estilosImpressao, /\.modulo-transferencias-saldo\s*>\s*\.controle-planilha-transferencias\s*\{\s*display:\s*block\s*!important/);
  assert.match(estilosImpressao, /\.controle-planilha-impressao\s+\.titulo-impressao-planilha/);
  assert.match(estilosImpressao, /\.controle-planilha-producao\s+\.producao-saldos-planilha/);


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
  assert.match(htmlVendas, /Vendas de grãos/);
  assert.match(htmlVendas, /Nova venda/);
  assert.match(htmlVendas, /Venda com saldo negativo permitida por sobra técnica/);
  assert.ok(htmlVendas.includes("Propriedade / CAD/PRO / Proprietário"));
  assert.match(htmlVendas, /Contrato \/ empresa/);
  assert.match(htmlCadastrosAgricolas, /Nº do contrato/);
  assert.match(htmlCadastrosAgricolas, /Quantidade \(kg\)/);
  assert.match(htmlCadastrosAgricolas, /Cadastrar contrato/);
  assert.match(htmlVendas, /Registrar venda e saída/);
  assert.match(htmlVendas, /formulario-venda-horizontal/);
  const estilosVendas = await readFile(new URL("../src/styles.css", import.meta.url), "utf8");
  const regraFormularioVendas = estilosVendas.match(/\.formulario-venda-horizontal\s*\{([^}]*)\}/);
  assert.ok(regraFormularioVendas, "Estilos do formulário horizontal de vendas devem existir");
  assert.match(regraFormularioVendas[1], /position:\s*static/);
  assert.doesNotMatch(regraFormularioVendas[1], /position:\s*sticky/);
  assert.match(htmlVendas, /Apenas rascunho/);
  assert.match(htmlVendas, /Sem contrato/);
  const seletorContrato = htmlVendas.match(/Contrato \/ empresa \(Nº do contrato, opcional\)<select([^>]*)>/);
  assert.ok(seletorContrato, "Contrato opcional deve estar disponível");
  assert.doesNotMatch(seletorContrato[1], /required/);
  for (const campo of ["Data", "Destino", "Placa", "Motorista", "CAD/PRO", "Nº do contrato", "Nº nota produtor", "Nº nota empresa", "Peso líquido (kg)"]) assert.ok(htmlVendas.includes(campo), campo);
  assert.match(htmlVendas, /Placa \/ Motorista/);
  assert.match(htmlVendas, /controle-planilha-vendas/);
  assert.match(htmlVendas, /vendas-planilha/);
  assert.match(htmlVendas, /Quantidade \(sacas de 60 kg\)/);
  assert.equal(dataPlanilhaVenda("2026-08-29"), "29/08/2026");
  assert.equal(dataPlanilhaVenda(""), "—");
  assert.equal(numeroPlanilhaVenda("37440.000", 3), "37.440,000");
  assert.equal(numeroPlanilhaVenda(661.833), "661,83");
  assert.equal(identificacaoCadProVenda(
    { propriedade: 1, propriedade_nome: "Sítio 2 Irmãos", cad_pro_codigo: "9602264537" },
    [{ id: 1, proprietario: "Gilsonei" }],
  ), "Sítio 2 Irmãos - 9602264537 - Gilsonei");
  const { quantidadeContrato } = await servidor.ssrLoadModule("/src/pages/CadastrosAgricolas/ContratosComerciais.tsx");
  assert.equal(quantidadeContrato("35.000,500"), "35000.500");
  assert.equal(quantidadeContrato("1.234.567,89"), "1234567.89");
  assert.equal(quantidadeContrato("30,5"), "30.5");
  assert.equal(quantidadeContrato("30.000"), "30000");
  for (const invalido of ["0", "-1", "1.5", "1,000.50", "abc", "Infinity", "1,1234"]) assert.throws(() => quantidadeContrato(invalido));
  const acoesLivres = renderToStaticMarkup(React.createElement(AcoesLancamentoVenda, { desabilitado: false, editar() {}, excluir() {} }));
  assert.match(acoesLivres, /Editar/);
  assert.match(acoesLivres, /Excluir/);
  assert.doesNotMatch(acoesLivres, /disabled/);
  const acoesOcupadas = renderToStaticMarkup(React.createElement(AcoesLancamentoVenda, { desabilitado: true, editar() {}, excluir() {} }));
  assert.equal((acoesOcupadas.match(/disabled/g) || []).length, 2);

  const posicaoCompartilhada = {
    cad_pro_codigo: "CAD-COMPARTILHADO", cultura: "Soja", safra: "2026/2027",
    classificacao_codigo: "PADRAO", armazem_nome: "Silo externo",
    saldo_disponivel_kg: "1000.000",
  };
  const rotuloNorte = rotuloPosicaoVenda({ ...posicaoCompartilhada, propriedade_nome: "Produtora Norte" });
  const rotuloSul = rotuloPosicaoVenda({ ...posicaoCompartilhada, propriedade_nome: "Produtora Sul" });
  assert.match(rotuloNorte, /^Produtora Norte · CAD-COMPARTILHADO/);
  assert.match(rotuloSul, /^Produtora Sul · CAD-COMPARTILHADO/);
  assert.notEqual(rotuloNorte, rotuloSul);
  assert.match(rotuloPosicaoVenda({ ...posicaoCompartilhada, propriedade_nome: null }), /^Produção histórica sem propriedade/);
  const { opcoesOrigemVenda, posicoesDaOrigemVenda } = await servidor.ssrLoadModule("/src/pages/Vendas/origemVenda.ts");
  const posicoesVenda = [
    { ...posicaoCompartilhada, id: 1, cad_pro: "CAD-A", propriedade_id: 1, propriedade_nome: "Produtora Norte" },
    { ...posicaoCompartilhada, id: 2, cad_pro: "CAD-A", propriedade_id: 2, propriedade_nome: "Produtora Sul" },
    { ...posicaoCompartilhada, id: 3, cad_pro: "CAD-A", propriedade_id: 1, cultura: "Trigo" },
    { ...posicaoCompartilhada, id: 4, cad_pro: "CAD-B", propriedade_id: 3, saldo_disponivel_kg: "0" },
  ];
  const propriedadesVenda = [
    { id: 1, nome: "Produtora Norte", proprietario: "Ana" },
    { id: 2, nome: "Produtora Sul", proprietario: "João" },
  ];
  const origensVenda = opcoesOrigemVenda(posicoesVenda, propriedadesVenda);
  assert.deepEqual(origensVenda.map(o => o.rotulo), [
    "Produtora Norte / CAD/PRO CAD-COMPARTILHADO / Ana",
    "Produtora Sul / CAD/PRO CAD-COMPARTILHADO / João",
    "Propriedade #3 / CAD/PRO CAD-COMPARTILHADO / Proprietário não informado",
  ]);
  assert.deepEqual(posicoesDaOrigemVenda(posicoesVenda, origensVenda[0].chave).map(p => p.id), [1, 3]);
  assert.deepEqual(posicoesDaOrigemVenda(posicoesVenda, origensVenda[1].chave).map(p => p.id), [2]);
  assert.equal(posicoesDaOrigemVenda(posicoesVenda, "").length, 0);
  const historicoVenda = { ...posicaoCompartilhada, cad_pro: "CAD-A", propriedade_id: null };
  const origensHistoricas = opcoesOrigemVenda([...posicoesVenda, historicoVenda], []);
  assert.equal(origensHistoricas.length, 4);
  assert.deepEqual(posicoesDaOrigemVenda(posicoesVenda, "CAD-B:3").map(p => p.id), [4]);
  assert.equal(opcoesOrigemVenda([{ ...posicoesVenda[0], saldo_disponivel_kg: "-100" }], propriedadesVenda).length, 1);
  const origemSemEntrada = opcoesOrigemVenda([], propriedadesVenda, [{ id: "CAD-NOVO", codigo: "NOVO", ativo: true, propriedades: [1, 2] }]);
  assert.equal(origemSemEntrada.length, 2);
  assert.notEqual(origemSemEntrada[0].chave, origemSemEntrada[1].chave);
  assert.ok(origensHistoricas.some(o => o.rotulo === "Produção histórica sem propriedade / CAD/PRO CAD-COMPARTILHADO / Proprietário não informado"));
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
  assert.match(htmlRelatorios, /Todos os relatórios/);
  assert.match(htmlRelatorios, /Gestão rural, produção, comercial, financeiro, estoque, operações, máquinas, clima, mercado e auditoria/);
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
  const htmlEstruturaRelatorios = renderToStaticMarkup(
    React.createElement(TabelaRelatorio, {
      secao: "estrutura",
      itens: [{
        id: 1, proprietario: "Denis", propriedade_nome: "Fazenda Modelo",
        localizacao: "Cascavel / PR", area_alqueires: "10.000",
        area_talhoes_alqueires: "8.000", area_disponivel_alqueires: "2.000",
        quantidade_talhoes: 2, culturas: ["Soja"], safras: ["2026/2027"],
        possui_mapa: true,
      }],
    }),
  );
  for (const valor of ["Fazenda Modelo", "10,000 alq.", "Soja", "Sim"]) assert.ok(htmlEstruturaRelatorios.includes(valor), valor);
  const htmlFinanceiroRelatorios = renderToStaticMarkup(
    React.createElement(TabelaRelatorio, {
      secao: "financeiro",
      itens: [{
        id: 1, tipo: "Conta a receber", descricao: "Venda", categoria: "Receita",
        propriedade_nome: "Fazenda Modelo", safra: "2026/2027", status: "Liquidado",
        valor: "2000.00", valor_liquidado: "2000.00",
      }],
    }),
  );
  for (const valor of ["Conta a receber", "Venda", "Liquidado", "R$ 2.000,00"]) assert.ok(htmlFinanceiroRelatorios.includes(valor), valor);

  const produtividade = {
    id: 41, data: "2026-08-30", propriedade_nome: "SÍTIO SAGRILO",
    cad_pro_codigo: "987654321", cultura: "Milho", safra: "2026",
    area_hectares: "70.000", quantidade_kg: "41265.000", sacas_60kg: "687.750",
    media_sacas_hectare: "9.825", destinado_semente: true, semente_sacas_60kg: "687.750",
  };
  const htmlProdutividade = renderToStaticMarkup(React.createElement(TabelaRelatorio, {
    secao: "produtividade", itens: [produtividade, {
      ...produtividade, id: 42, propriedade_nome: "teste 2", cad_pro_codigo: "2056",
      area_hectares: "30.000", quantidade_kg: "17685.000", sacas_60kg: "294.750",
      destinado_semente: false,
    }],
  }));
  for (const valor of ["28,926 alq.", "12,397 alq.", "41.265,000 kg", "17.685,000 kg", "687,750 sc", "294,750 sc", "23,777 sc/alq."]) {
    assert.ok(htmlProdutividade.includes(valor), valor);
  }
  assert.doesNotMatch(htmlProdutividade, /70\.000 ha|30\.000 ha|687\.750 sc|9\.825 sc/);
  assert.match(htmlProdutividade, />987654321</);
  assert.match(htmlProdutividade, />2056</);
  assert.match(htmlProdutividade, />2026</);
  const htmlTransporte = renderToStaticMarkup(React.createElement(TabelaRelatorio, {
    secao: "motoristas", itens: [{ id: 1, motorista: "Teste", quantidade_cargas: 1234,
      quantidade_kg: "100000.000", sacas_60kg: "1666.667", semente_kg: "0.000" }],
  }));
  assert.match(htmlTransporte, />1\.234</);
  assert.match(htmlTransporte, /1\.666,667 sc/);
  assert.match(htmlTransporte, /100\.000,000 kg/);
  const htmlDecimaisPequenos = renderToStaticMarkup(React.createElement(TabelaRelatorio, {
    secao: "produtividade", itens: [{ ...produtividade, quantidade_kg: "-1250.125",
      sacas_60kg: "0.000", media_sacas_hectare: "0.151", area_hectares: null }],
  }));
  assert.match(htmlDecimaisPequenos, /-1\.250,125 kg/);
  assert.match(htmlDecimaisPequenos, /0,000 sc/);
  assert.match(htmlDecimaisPequenos, /0,365 sc\/alq\./);
  assert.match(htmlDecimaisPequenos, /0,000 alq\./);

  const totaisProducao = { area_alqueires: "10.000", quantidade_kg: "6000.000", sacas_60kg: "100.000", semente_kg: "600.000", semente_sacas_60kg: "10.000", outros_locais_kg: "1200.000", media_sacas_alqueire: "10.000" };
  const htmlProducaoPropriedade = renderToStaticMarkup(React.createElement(TabelaRelatorio, {
    secao: "producao_propriedade", totaisProducao,
    colunasProducao: ["propriedade", "cad_pro", "area", "kg", "media"],
    itens: [{ id: "1:cad", propriedade_nome: "Fazenda Modelo", cad_pro_codigo: "CAD-1", area_alqueires: "10.000", quantidade_kg: "6000.000", sacas_60kg: "100.000", media_sacas_alqueire: "10.000" }],
  }));
  for (const valor of ["Fazenda Modelo", "CAD-1", "10,000 alq.", "6.000,000 kg", "10,000 sc/alq.", "TOTAL"]) assert.ok(htmlProducaoPropriedade.includes(valor), valor);
  assert.doesNotMatch(htmlProducaoPropriedade, /Outros locais|Armazenagens/);

  const htmlTotalSemPropriedade = renderToStaticMarkup(React.createElement(TabelaRelatorio, {
    secao: "producao_propriedade", totaisProducao,
    colunasProducao: ["kg", "sacas"],
    itens: [{ id: "1:cad", quantidade_kg: "6000.000", sacas_60kg: "100.000" }],
  }));
  assert.match(htmlTotalSemPropriedade, /Total geral filtrado/);
  assert.match(htmlTotalSemPropriedade, /6\.000,000 kg/);
  assert.match(htmlTotalSemPropriedade, /100,000 sc/);
  assert.doesNotMatch(htmlTotalSemPropriedade, /Propriedade<\/th>/);

  assert.deepEqual(normalizarColunasImpressao(["data", "peso", "invalida", "peso"], ["data", "peso", "sacas"]), ["data", "peso"]);
  assert.deepEqual(normalizarColunasImpressao([], ["data", "peso"]), ["data", "peso"]);
  const htmlSeletorUmaColuna = renderToStaticMarkup(React.createElement(SeletorColunasImpressao, {
    definicoes: [["data", "Data"], ["peso", "Peso"]], selecionadas: ["peso"], alterar: () => {}, descricao: "Teste",
  }));
  assert.match(htmlSeletorUmaColuna, /1 de 2 colunas/);
  assert.match(htmlSeletorUmaColuna, /disabled="" checked=""/);
  assert.match(htmlSeletorUmaColuna, /Imprimir com estas colunas/);

  const vendaImpressao = { id: 1, propriedade: 10, propriedade_nome: "Fazenda Modelo", cad_pro_codigo: "CAD-1", numero_contrato: "8", cliente_nome: "C.VALE" };
  const linhasVendas = [
    { venda: vendaImpressao, entrega: { id: 1, data_entrega: "2026-08-30", destino: "C.VALE", placa: "ABC1D23", motorista: "João", nota_produtor: "123", nota_empresa: "456", quantidade_kg: "1500" } },
    { venda: vendaImpressao, entrega: { id: 2, data_entrega: "2026-08-31", destino: "C.VALE", placa: "DEF4G56", motorista: "Maria", nota_produtor: "124", nota_empresa: "457", quantidade_kg: "2500" } },
  ];
  const htmlVendasSelecionadas = renderToStaticMarkup(React.createElement(TabelaImpressaoVendas, {
    linhas: linhasVendas, propriedades: [{ id: 10, proprietario: "Denis" }],
    colunas: ["data", "destino", "placa", "cad_pro", "contrato", "nota_produtor", "nota_empresa", "peso", "sacas"],
  }));
  for (const valor of ["Data", "Destino", "Placa / Motorista", "Propriedade / CAD-PRO / proprietário", "Contrato", "Nº da nota de produtor", "Nº da nota da empresa", "Peso líquido (kg)", "Quantidade (sacas de 60 kg)", "4.000,000", "66,67", "Total das linhas impressas"]) assert.ok(htmlVendasSelecionadas.includes(valor), valor);

  const { alqueiresDeHectares, hectaresDeAlqueires } = await servidor.ssrLoadModule("/src/utils/areas.ts");
  assert.equal(alqueiresDeHectares("2.42"), 1);
  assert.equal(hectaresDeAlqueires("1"), "2.42");
  const mapaTalhaoFonte = await readFile(new URL("../src/components/MapaTalhao.tsx", import.meta.url), "utf8");
  const mapaPropriedadeFonte = await readFile(new URL("../src/components/MapaPropriedade.tsx", import.meta.url), "utf8");
  for (const fonteMapa of [mapaTalhaoFonte, mapaPropriedadeFonte]) {
    assert.match(fonteMapa, /World_Imagery/);
    assert.match(fonteMapa, /Satélite/);
    assert.match(fonteMapa, /Mapa convencional/);
  }

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
        carga_status: "ativa",
        propriedade: 1,
        propriedade_nome: "Fazenda Modelo",
        cad_pro: "cad-1",
        cad_pro_codigo: "CAD-1",
        cultura: "Soja",
        safra: "2026/2027",
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
  assert.doesNotMatch(htmlRastreabilidadeRelatorios, /Grupo/);
  assert.match(htmlRastreabilidadeRelatorios, /CAD-1/);
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

  const appFonte = await readFile(
    new URL("../src/App.tsx", import.meta.url),
    "utf8",
  );
  assert.match(appFonte, /Cadastros agrícolas/);
  assert.match(appFonte, /className="grade modulo-propriedades"/);
  assert.match(appFonte, /className="lista propriedades-lista"/);
  assert.match(estilosImpressao, /\.modulo-propriedades\s+\.propriedades-lista\s*\{[\s\S]*?grid-template-columns:\s*repeat\(2,/);
  assert.match(estilosImpressao, /\.modulo-cadastros-agricolas\s*\{\s*page:\s*planilha/);
  assert.match(estilosImpressao, /\.modulo-cadastros-agricolas\s*>\s*\.auxiliares-grade\s*>\s*\.card\s*>\s*\.lista\s*\{[\s\S]*?grid-template-columns:\s*repeat\(3,/);
  const { default: TransferenciasSaldoPage, TabelaImpressaoTransferencias, agruparHistoricoTransferencias, culturasTransferencia, nomePropriedadeTransferencia, numeroPlanilhaTransferencia, opcoesPosicaoTransferencia, posicaoDestinoCompativel, rotuloPosicaoTransferencia, safrasTransferencia } = await servidor.ssrLoadModule("/src/pages/TransferenciasSaldo/TransferenciasSaldoPage.tsx");
  const htmlTransferencia = renderToStaticMarkup(React.createElement(TransferenciasSaldoPage));
  for (const rotulo of ["Cultura", "Ano / safra", "Propriedade / CAD/PRO de origem / Proprietário", "Propriedade / CAD/PRO de destino / Proprietário", "Quantidade (kg)", "Transferir saldo", "Referência / documento", "Observações", "Registro"]) assert.ok(htmlTransferencia.includes(rotulo));
  assert.doesNotMatch(htmlTransferencia, /Lote de origem|Lote de destino/);
  const posicaoCerta = { id: 1, cad_pro: "A", cad_pro_codigo: "123", propriedade_id: 1, propriedade_nome: "Sítio São Silvestre", cultura: "Soja", safra: "2026", classificacao_codigo: "PADRAO", armazem: 1, armazem_nome: "Silo", saldo_fisico_kg: "100", saldo_comprometido_kg: "0", saldo_disponivel_kg: "100", versao: 1, atualizado_em: "2026-08-31" };
  assert.equal(posicaoDestinoCompativel(posicaoCerta, { ...posicaoCerta, id: 2, cad_pro: "B" }), true);
  assert.equal(posicaoDestinoCompativel(posicaoCerta, posicaoCerta), false);
  assert.equal(posicaoDestinoCompativel(posicaoCerta, { ...posicaoCerta, id: 2, cultura: "Trigo" }), false);
  assert.match(rotuloPosicaoTransferencia(posicaoCerta, [{ id: 1, nome: "Sítio A", proprietario: "Maria" }]), /^Sítio A \/ CAD\/PRO 123 \/ Maria/);
  const origensCompartilhadas = opcoesPosicaoTransferencia([
    posicaoCerta,
    { ...posicaoCerta, id: 2, propriedade_id: 2, propriedade_nome: "Lote 27 - Conrado" },
    { ...posicaoCerta, id: 3, propriedade_id: 3, saldo_disponivel_kg: "0" },
  ], [], true);
  assert.equal(origensCompartilhadas.length, 2);
  assert.notEqual(origensCompartilhadas[0].chave, origensCompartilhadas[1].chave);
  const posicoesSafras = [posicaoCerta, { ...posicaoCerta, id: 2, cultura: "Milho", safra: "2025" }, { ...posicaoCerta, id: 3, safra: "2024" }, { ...posicaoCerta, id: 4, cultura: "Trigo", saldo_disponivel_kg: "0" }];
  assert.deepEqual(culturasTransferencia(posicoesSafras), ["Milho", "Soja"]);
  assert.deepEqual(safrasTransferencia(posicoesSafras, "Soja"), ["2026", "2024"]);
  const movimentosTransferencia = [
    { id: 1, origem_chave_idempotencia: "t-1", operacao: "transferencia_saida", propriedade_id: 1, cad_pro_codigo: "123", armazem_nome: "Silo A", cultura: "Soja", safra: "2026", classificacao_codigo: "PADRAO", quantidade_kg: "1000.500", data_movimento: "2026-09-01", referencia_externa: "TRANSF-1", observacoes: "Ajuste interno", criado_por_nome: "Denis", criado_em: "2026-09-01T10:00:00Z" },
    { id: 2, origem_chave_idempotencia: "t-1", operacao: "transferencia_entrada", propriedade_id: 2, cad_pro_codigo: "456", armazem_nome: "Silo B", cultura: "Soja", safra: "2026", classificacao_codigo: "PADRAO", quantidade_kg: "1000.500", data_movimento: "2026-09-01", referencia_externa: "TRANSF-1", observacoes: "Ajuste interno", criado_por_nome: "Denis", criado_em: "2026-09-01T10:00:00Z" },
  ];
  const historicoTransferencia = agruparHistoricoTransferencias(movimentosTransferencia);
  assert.equal(historicoTransferencia.length, 1);
  assert.equal(historicoTransferencia[0].saida.id, 1);
  assert.equal(historicoTransferencia[0].entrada.id, 2);
  assert.equal(numeroPlanilhaTransferencia("1000.500"), "1.000,500");
  assert.equal(nomePropriedadeTransferencia(movimentosTransferencia[0], [{ id: 1, nome: "Sítio A", proprietario: "Maria" }]), "Sítio A");
  const htmlTabelaTransferencias = renderToStaticMarkup(React.createElement(TabelaImpressaoTransferencias, {
    historico: historicoTransferencia,
    propriedades: [{ id: 1, nome: "Sítio A", proprietario: "Maria" }, { id: 2, nome: "Sítio B", proprietario: "João" }],
  }));
  for (const valor of ["Transferências registradas", "Sítio A", "CAD/PRO 123", "Sítio B", "CAD/PRO 456", "1.000,500", "Total das linhas impressas"]) assert.ok(htmlTabelaTransferencias.includes(valor), valor);
  assert.ok(appFonte.indexOf('onClick={() => setModulo("transferencias")}') < appFonte.indexOf('onClick={() => setModulo("vendas")}'));

  assert.doesNotMatch(appFonte, /Grupos de colheita/);

  console.log("40 testes de componentes, submissão, geometria e PWA aprovados.");
} finally {
  await servidor.close();
}
