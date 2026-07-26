import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

const read = (path) => readFile(new URL(path, import.meta.url), "utf8");
const [shellSource, navigation, theme, modules, dashboardSource, productionSource, map, shared, enterprise, tokens] = await Promise.all([
  read("../src/components/layout/AppShell.tsx"),
  read("../src/app/navigation.ts"),
  read("../src/hooks/useTheme.ts"),
  read("../src/app/ModuleRenderer.tsx"),
  read("../src/pages/Dashboard/DashboardPage.tsx"),
  read("../src/pages/Producao/ProducaoPage.tsx"),
  read("../src/components/maps/AgriculturalMap.tsx"),
  read("../src/components/shared/ui.tsx"),
  read("../src/styles/enterprise.css"),
  read("../src/styles/tokens.css"),
]);

assert.match(shellSource, /app-sidebar--mobile-open/);
assert.match(shellSource, /aria-current/);
assert.match(shellSource, /ThemeToggle/);
assert.match(shellSource, /Todas autorizadas/);
assert.match(shellSource, /production:/);
assert.match(navigation, /"dashboard"/);
assert.match(navigation, /"geoprocessamento"/);
assert.match(navigation, /"producao"/);
assert.match(theme, /prefers-color-scheme: dark/);
assert.match(theme, /localStorage\.setItem\(THEME_STORAGE_KEY/);
assert.match(modules, /lazy\(\(\) => import/);
assert.match(modules, /Suspense fallback/);
assert.match(modules, /ModuleErrorBoundary/);
assert.match(modules, /ProducaoPage/);
assert.match(dashboardSource, /Promise\.allSettled/);
assert.match(dashboardSource, /Indicadores gerenciais indisponíveis/);
assert.match(dashboardSource, /Nenhum resumo de mercado disponível/);
assert.match(dashboardSource, /Indicadores de produção ainda não disponíveis/);
assert.match(productionSource, /Operação ainda não habilitada nesta entrega/);
assert.match(productionSource, /Nenhum dado foi inventado ou duplicado/);
assert.match(map, /ScaleControl/);
assert.match(map, /Polygon/);
assert.match(map, /FitFeatures/);
assert.match(map, /OpenStreetMap/);
assert.match(map, /"armazenagem"/);
assert.match(map, /bounds\.extend\(limitesGeometria/);
assert.match(shared, /function PermissionGuard/);
assert.match(shared, /function ConfirmDialog/);
assert.match(shared, /function DataTable/);
assert.match(enterprise, /@media \(max-width: 860px\)/);
assert.match(enterprise, /app-sidebar--mobile-open/);
assert.match(enterprise, /agricultural-map__canvas/);
assert.match(tokens, /:root\[data-theme="dark"\]/);
assert.match(tokens, /--color-focus/);
assert.match(tokens, /--map-production/);

const server = await createServer({
  appType: "custom",
  configLoader: "runner",
  logLevel: "silent",
  server: { middlewareMode: true },
});

try {
  const { Sidebar, default: AppShell } = await server.ssrLoadModule(
    "/src/components/layout/AppShell.tsx",
  );
  const {
    PermissionGuard,
    ThemeToggle,
  } = await server.ssrLoadModule("/src/components/shared/ui.tsx");
  const { default: DashboardPage } = await server.ssrLoadModule(
    "/src/pages/Dashboard/DashboardPage.tsx",
  );
  const { default: ProducaoPage } = await server.ssrLoadModule(
    "/src/pages/Producao/ProducaoPage.tsx",
  );
  const { NAVIGATION_ITEMS } = await server.ssrLoadModule(
    "/src/app/navigation.ts",
  );

  const property = {
    id: 1,
    nome: "Fazenda Modelo",
    proprietario: "Produtor",
    municipio: "Ivaiporã",
    uf: "PR",
    area_hectares: "100.00",
    latitude: "-24.24",
    longitude: "-51.68",
    arquivo_kml: null,
    geometria_geojson: null,
    area_calculada_hectares: null,
    diferenca_area_hectares: null,
    divergencia_area_percentual: null,
    observacoes: "",
    criado_em: "2026-07-26T00:00:00Z",
    papel_usuario: "administrador",
    pode_editar: true,
    pode_excluir: true,
    pode_operar: true,
  };

  const sidebarDesktop = renderToStaticMarkup(
    React.createElement(Sidebar, {
      items: NAVIGATION_ITEMS,
      activeModule: "dashboard",
      collapsed: false,
      mobileOpen: false,
      onNavigate() {},
      onToggleCollapsed() {},
      onCloseMobile() {},
    }),
  );
  assert.match(sidebarDesktop, /Navegação principal/);
  assert.match(sidebarDesktop, /aria-current="page"/);
  assert.match(sidebarDesktop, />Produção</);

  const sidebarCollapsed = renderToStaticMarkup(
    React.createElement(Sidebar, {
      items: NAVIGATION_ITEMS,
      activeModule: "propriedades",
      collapsed: true,
      mobileOpen: false,
      onNavigate() {},
      onToggleCollapsed() {},
      onCloseMobile() {},
    }),
  );
  assert.match(sidebarCollapsed, /app-sidebar--collapsed/);
  assert.match(sidebarCollapsed, /title="Dashboard"/);

  const sidebarMobile = renderToStaticMarkup(
    React.createElement(Sidebar, {
      items: NAVIGATION_ITEMS,
      activeModule: "producao",
      collapsed: false,
      mobileOpen: true,
      onNavigate() {},
      onToggleCollapsed() {},
      onCloseMobile() {},
    }),
  );
  assert.match(sidebarMobile, /app-sidebar--mobile-open/);
  assert.match(sidebarMobile, /aria-label="Fechar menu"/);

  const shell = renderToStaticMarkup(
    React.createElement(
      AppShell,
      {
        items: NAVIGATION_ITEMS,
        activeModule: "dashboard",
        onNavigate() {},
        properties: [property],
        selectedPropertyId: "1",
        onSelectedPropertyChange() {},
        safra: "2026/2027",
        onSafraChange() {},
        userLabel: "Usuário teste",
        roleLabel: "Administrador",
        theme: "light",
        onToggleTheme() {},
        onLogout() {},
      },
      React.createElement("div", null, "Conteúdo principal"),
    ),
  );
  assert.match(shell, /id="main-content"/);
  assert.match(shell, /Fazenda Modelo/);
  assert.match(shell, /2026\/2027/);
  assert.match(shell, /Usuário teste/);

  const themeLight = renderToStaticMarkup(
    React.createElement(ThemeToggle, { theme: "light", onToggle() {} }),
  );
  const themeDark = renderToStaticMarkup(
    React.createElement(ThemeToggle, { theme: "dark", onToggle() {} }),
  );
  assert.match(themeLight, /Ativar tema escuro/);
  assert.match(themeDark, /Ativar tema claro/);

  const denied = renderToStaticMarkup(
    React.createElement(
      PermissionGuard,
      { allowed: false, fallback: React.createElement("span", null, "Bloqueado") },
      React.createElement("button", null, "Editar"),
    ),
  );
  const allowed = renderToStaticMarkup(
    React.createElement(
      PermissionGuard,
      { allowed: true },
      React.createElement("button", null, "Editar"),
    ),
  );
  assert.doesNotMatch(denied, /Editar/);
  assert.match(denied, /Bloqueado/);
  assert.match(allowed, /Editar/);

  const dashboardLoading = renderToStaticMarkup(
    React.createElement(DashboardPage, {
      properties: [property],
      selectedProperty: property,
      safra: "2026/2027",
    }),
  );
  assert.match(dashboardLoading, /Consolidando dados autorizados do ERP/);
  assert.match(dashboardLoading, /skeleton/);

  const production = renderToStaticMarkup(
    React.createElement(ProducaoPage, {
      selectedProperty: property,
      safra: "2026/2027",
    }),
  );
  assert.match(production, /Gestão da Produção Agrícola/);
  assert.match(production, /Fazenda Modelo/);
  assert.match(production, /Operação ainda não habilitada nesta entrega/);

  console.log("52 verificações da interface enterprise aprovadas.");
} finally {
  await server.close();
}
