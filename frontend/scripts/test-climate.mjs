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
  const { default: ClimaPage } = await servidor.ssrLoadModule(
    "/src/pages/Clima/ClimaPage.tsx",
  );
  const propriedade = {
    id: 1,
    nome: "Fazenda Clima",
    proprietario: "",
    municipio: "Ivaiporã",
    uf: "PR",
    area_hectares: "100.00",
    latitude: "-24.245000",
    longitude: "-51.675000",
    arquivo_kml: null,
    geometria_geojson: null,
    area_calculada_hectares: null,
    diferenca_area_hectares: null,
    divergencia_area_percentual: null,
    observacoes: "",
    criado_em: "2026-07-27T00:00:00Z",
    papel_usuario: "operador",
    pode_editar: false,
    pode_excluir: false,
    pode_operar: true,
  };
  const html = renderToStaticMarkup(
    React.createElement(ClimaPage, { propriedades: [propriedade] }),
  );
  assert.match(html, /Atualização automática/);
  assert.match(html, /Atualizar previsão/);
  assert.match(html, /Previsão horária/);
  assert.match(html, /Operação agrícola/);
  assert.match(html, /Sincronização/);

  const api = await readFile(new URL("../src/api/clima.ts", import.meta.url), "utf8");
  assert.match(api, /\/clima\/previsoes\/status\//);
  assert.match(api, /\/clima\/horarias\//);
  assert.match(api, /\/clima\/alertas\//);
  assert.doesNotMatch(api, /apikey|api_key|Authorization:\s*["']/i);

  const css = await readFile(new URL("../src/pages/Clima/clima.css", import.meta.url), "utf8");
  assert.match(css, /@media \(max-width: 760px\)/);
  assert.match(css, /\[data-theme="dark"\]/);

  const compose = await readFile(new URL("../../docker-compose.yml", import.meta.url), "utf8");
  assert.match(compose, /clima-worker:/);
  assert.match(compose, /atualizar_clima --continuous/);
  assert.match(compose, /CLIMA_UPDATE_INTERVAL_SECONDS:-10800/);

  console.log("12 verificações do clima automático aprovadas.");
} finally {
  await servidor.close();
}
