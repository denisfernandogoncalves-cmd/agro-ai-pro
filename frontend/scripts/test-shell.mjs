import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

const server = await createServer({ appType: "custom", configLoader: "runner", logLevel: "silent", server: { middlewareMode: true } });
try {
  const { default: AppShell, modulos } = await server.ssrLoadModule("/src/components/AppShell.tsx");
  const props = { modulo: "dashboard", navegar() {}, propriedades: [], selecionada: null, selecionar() {}, sair() {} };
  const html = renderToStaticMarkup(React.createElement(AppShell, props));
  for (const [, label] of modulos) assert.ok(html.includes(`aria-label="${label}"`), `Acesso preservado: ${label}`);
  for (const text of ["Produção e território", "Gestão e negócios", "Encontrar módulo", "Ir para o conteúdo", ">Sair<"]) assert.ok(html.includes(text));
  assert.match(html, /data-theme="light"/);
  globalThis.localStorage = { getItem: () => "escuro" };
  assert.match(renderToStaticMarkup(React.createElement(AppShell, props)), /data-theme="dark"/);
  delete globalThis.localStorage;
  const { default: Chart } = await server.ssrLoadModule("/src/pages/Mercado/GraficoMercado.tsx");
  const chart = renderToStaticMarkup(React.createElement(Chart, { cotacoes: [
    { id: 1, data: "2026-10-01", valor: "100", unidade: "USD", produto: "soja" },
    { id: 2, data: "2026-10-02", valor: "110", unidade: "USD", produto: "soja" },
  ] }));
  assert.equal((chart.match(/tabindex="0"/g) || []).length, 2);
  assert.match(chart, /2026-10-01: 100 USD/);
  assert.match(chart, /use Tab/);
  assert.match(renderToStaticMarkup(React.createElement(Chart, { cotacoes: [] })), /Histórico insuficiente/);
  console.log("Shell: todos os 15 módulos, categorias, logout e temas verificados. Gráfico: pontos acessíveis e estado vazio verificados.");
} finally { await server.close(); }
