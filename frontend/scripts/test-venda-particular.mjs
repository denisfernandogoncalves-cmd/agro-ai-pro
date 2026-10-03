import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

const servidor = await createServer({ appType: "custom", configLoader: "runner", logLevel: "silent", server: { middlewareMode: true } });
try {
  const { ehVendaParticular, PreviaRateioParticular } = await servidor.ssrLoadModule("/src/pages/Vendas/VendasPage.tsx");
  for (const destino of ["PARTICULAR", "particular", "  Particular  "]) assert.equal(ehVendaParticular("saida", destino), true);
  for (const destino of ["Cooperativa", "Venda particular João", ""]) assert.equal(ehVendaParticular("saida", destino), false);
  assert.equal(ehVendaParticular("rascunho", "PARTICULAR"), false);
  const html = renderToStaticMarkup(React.createElement(PreviaRateioParticular, { previa: {
    quantidade_total_kg: "50.000", area_total_hectares: "100.00", hash_previa: "teste",
    parcelas: [
      { propriedade: 1, propriedade_nome: "Fazenda A", cad_pro_codigo: "CAD-A", area_hectares: "60.00", quantidade_kg: "30.000" },
      { propriedade: 2, propriedade_nome: "Fazenda <B>", cad_pro_codigo: "CAD-B", area_hectares: "40.00", quantidade_kg: "20.000" },
    ],
  } }));
  for (const texto of ["Rateio por área", "50 kg", "Fazenda A", "Fazenda &lt;B&gt;", "CAD-A", "CAD-B", "60,00", "40,00", "30,000", "20,000"]) assert.ok(html.includes(texto), texto);
  assert.equal((html.match(/<tr>/g) || []).length, 3);
  assert.doesNotMatch(html, /<B>/);
  console.log("Venda PARTICULAR: detecção do destino e prévia por área aprovadas.");
} finally {
  await servidor.close();
}
