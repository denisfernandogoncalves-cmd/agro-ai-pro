export type ModuleId =
  | "dashboard"
  | "propriedades"
  | "talhoes"
  | "geoprocessamento"
  | "clima"
  | "mercado"
  | "financeiro"
  | "estoque"
  | "operacoes"
  | "maquinas"
  | "relatorios"
  | "insights";

export type NavigationIcon =
  | "dashboard"
  | "property"
  | "field"
  | "map"
  | "weather"
  | "market"
  | "finance"
  | "stock"
  | "operations"
  | "machines"
  | "reports"
  | "assistant";

export type NavigationItem = {
  id: ModuleId;
  label: string;
  icon: NavigationIcon;
  requiresProperty?: boolean;
};

export const NAVIGATION_ITEMS: NavigationItem[] = [
  { id: "dashboard", label: "Dashboard", icon: "dashboard" },
  { id: "propriedades", label: "Propriedades", icon: "property" },
  { id: "talhoes", label: "Talhões", icon: "field", requiresProperty: true },
  { id: "geoprocessamento", label: "Geoprocessamento", icon: "map", requiresProperty: true },
  { id: "clima", label: "Clima", icon: "weather", requiresProperty: true },
  { id: "mercado", label: "Mercado", icon: "market" },
  { id: "financeiro", label: "Financeiro", icon: "finance", requiresProperty: true },
  { id: "estoque", label: "Estoque", icon: "stock", requiresProperty: true },
  { id: "operacoes", label: "Operações", icon: "operations", requiresProperty: true },
  { id: "maquinas", label: "Máquinas", icon: "machines", requiresProperty: true },
  { id: "relatorios", label: "Relatórios", icon: "reports", requiresProperty: true },
  { id: "insights", label: "Assistente", icon: "assistant", requiresProperty: true },
];

export const MODULE_LABELS = Object.fromEntries(
  NAVIGATION_ITEMS.map((item) => [item.id, item.label]),
) as Record<ModuleId, string>;
