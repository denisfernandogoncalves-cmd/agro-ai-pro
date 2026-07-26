import assert from "node:assert/strict";

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
  const { default: MaquinasPage } = await servidor.ssrLoadModule(
    "/src/pages/Maquinas/MaquinasPage.tsx",
  );
  const { default: RelatoriosPage } = await servidor.ssrLoadModule(
    "/src/pages/Relatorios/RelatoriosPage.tsx",
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

  const htmlMaquinas = renderToStaticMarkup(
    React.createElement(MaquinasPage, { propriedades: [propriedade] }),
  );
  assert.match(htmlMaquinas, /Nova mÃ¡quina|Nova máquina/);
  assert.match(htmlMaquinas, /Uso, combustÃ­vel e manutenÃ§Ã£o|Uso, combustível e manutenção/);

  const htmlRelatorios = renderToStaticMarkup(
    React.createElement(RelatoriosPage, { propriedades: [propriedade] }),
  );
  assert.match(htmlRelatorios, /Gerando indicadores/);

  console.log("13 testes de componentes e geometria aprovados.");
} finally {
  await servidor.close();
}
