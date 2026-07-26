import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const read = (path) => readFile(new URL(path, import.meta.url), "utf8");
const [shell, navigation, theme, modules, dashboard, production, map, shared, enterprise, tokens] = await Promise.all([
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

assert.match(shell, /app-sidebar--mobile-open/);
assert.match(shell, /aria-current/);
assert.match(shell, /ThemeToggle/);
assert.match(shell, /Todas autorizadas/);
assert.match(shell, /production:/);
assert.match(navigation, /"dashboard"/);
assert.match(navigation, /"geoprocessamento"/);
assert.match(navigation, /"producao"/);
assert.match(theme, /prefers-color-scheme: dark/);
assert.match(theme, /localStorage\.setItem\(THEME_STORAGE_KEY/);
assert.match(modules, /lazy\(\(\) => import/);
assert.match(modules, /Suspense fallback/);
assert.match(modules, /ModuleErrorBoundary/);
assert.match(modules, /ProducaoPage/);
assert.match(dashboard, /Promise\.allSettled/);
assert.match(dashboard, /Indicadores gerenciais indisponíveis/);
assert.match(dashboard, /Nenhum resumo de mercado disponível/);
assert.match(dashboard, /Indicadores de produção ainda não disponíveis/);
assert.match(production, /Operação ainda não habilitada nesta entrega/);
assert.match(production, /Nenhum dado foi inventado ou duplicado/);
assert.match(map, /ScaleControl/);
assert.match(map, /Polygon/);
assert.match(map, /FitFeatures/);
assert.match(map, /OpenStreetMap/);
assert.match(map, /"armazenagem"/);
assert.match(shared, /function PermissionGuard/);
assert.match(shared, /function ConfirmDialog/);
assert.match(shared, /function DataTable/);
assert.match(enterprise, /@media \(max-width: 860px\)/);
assert.match(enterprise, /app-sidebar--mobile-open/);
assert.match(enterprise, /agricultural-map__canvas/);
assert.match(tokens, /:root\[data-theme="dark"\]/);
assert.match(tokens, /--color-focus/);
assert.match(tokens, /--map-production/);

console.log("34 verificações da interface enterprise aprovadas.");
