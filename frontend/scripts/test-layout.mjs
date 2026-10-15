import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

const server = await createServer({ appType: "custom", configLoader: "runner", logLevel: "silent", server: { middlewareMode: true } });
try {
  const { proporcoesSaldo } = await server.ssrLoadModule("/src/components/ComposicaoSaldo.tsx");
  assert.deepEqual(proporcoesSaldo("28000", "7000", "21000"), { comprometido: 25, disponivel: 75 });
  assert.deepEqual(proporcoesSaldo("28000", "0", "28000"), { comprometido: 0, disponivel: 100 });
  for (const dados of [["0","0","0"], ["-1","0","-1"], ["10","20","-10"], ["10","2","7"], ["", "0", "0"], ["NaN","0","0"]]) assert.equal(proporcoesSaldo(...dados), null);
  const { default: FluxoVenda } = await server.ssrLoadModule("/src/components/FluxoVenda.tsx");
  const fluxo = renderToStaticMarkup(React.createElement(FluxoVenda, { status: "parcial", reservada: "7000", entregue: "5000", devolvida: "1000", excluida: false }));
  assert.match(fluxo, /Baixa física líquida/); assert.match(fluxo, /4\.000 kg/); assert.match(fluxo, /nao-imprimir/);
  const { default: Navegacao } = await server.ssrLoadModule("/src/components/NavegacaoModulos.tsx");
  const nav = renderToStaticMarkup(React.createElement(Navegacao, { acesso: { id: 1, username: "teste", is_staff: false, modulos: ["mercado"], permissoes: {mercado:["consultar"]} }, modulo: "mercado", onSelecionar() {} }));
  assert.match(nav, /Mercado/); assert.doesNotMatch(nav, /title="Máquinas"/); assert.doesNotMatch(nav, /Histórico de alterações/);
  console.log("Layout: proporções válidas/inválidas, baixa física com devolução e navegação por permissão aprovados.");
} finally { await server.close(); }
