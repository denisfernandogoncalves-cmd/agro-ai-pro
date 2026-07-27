import { useEffect, useState, type ReactNode } from "react";

import type { Propriedade } from "../../api/propriedades";
import type { ModuleId, NavigationIcon, NavigationItem } from "../../app/navigation";
import { MODULE_LABELS } from "../../app/navigation";
import type { Theme } from "../../hooks/useTheme";
import { Badge, ThemeToggle } from "../shared/ui";

const ICON_PATHS: Record<NavigationIcon, string> = {
  dashboard: "M4 4h6v6H4zM14 4h6v4h-6zM14 12h6v8h-6zM4 14h6v6H4z",
  property: "M3 20V9l9-6 9 6v11h-6v-6H9v6z",
  field: "M4 18c4-6 8-9 16-12M4 12c5-2 10-3 16-2M4 6h.01M4 22h16",
  map: "M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3zM9 3v15M15 6v15",
  weather: "M8 17h9a4 4 0 0 0 0-8 6 6 0 0 0-11-2 5 5 0 0 0 2 10z",
  market: "M4 19V9M10 19V5M16 19v-7M22 19H2",
  finance: "M12 2v20M17 6H9a3 3 0 0 0 0 6h6a3 3 0 0 1 0 6H6",
  stock: "M4 7l8-4 8 4-8 4zM4 7v10l8 4 8-4V7M12 11v10",
  operations: "M4 6h16M4 12h16M4 18h10M2 6h.01M2 12h.01M2 18h.01",
  production: "M3 19h18M5 16h14V9H5zM8 9V6h8v3M7 13h2M11 13h2M15 13h2",
  machines: "M5 16h14l2 3H3zM7 16V8h10v8M9 8V5h6v3M7 12h10",
  reports: "M5 3h14v18H5zM8 16l3-4 3 2 3-5",
  assistant: "M12 3a7 7 0 0 0-4 13v4l4-2 4 2v-4a7 7 0 0 0-4-13zM9 10h.01M15 10h.01M10 14h4",
};

function NavigationIconView({ name }: { name: NavigationIcon }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d={ICON_PATHS[name]} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Sidebar({
  items,
  activeModule,
  collapsed,
  mobileOpen,
  onNavigate,
  onToggleCollapsed,
  onCloseMobile,
}: {
  items: NavigationItem[];
  activeModule: ModuleId;
  collapsed: boolean;
  mobileOpen: boolean;
  onNavigate: (module: ModuleId) => void;
  onToggleCollapsed: () => void;
  onCloseMobile: () => void;
}) {
  return (
    <aside className={`app-sidebar ${collapsed ? "app-sidebar--collapsed" : ""} ${mobileOpen ? "app-sidebar--mobile-open" : ""}`} aria-label="Navegação principal">
      <div className="app-sidebar__brand">
        <span className="app-sidebar__brand-mark">A</span>
        <span className="app-sidebar__brand-copy"><strong>AGRO-AI-PRO</strong><small>Gestão agrícola</small></span>
        <button className="icon-button app-sidebar__mobile-close" type="button" aria-label="Fechar menu" onClick={onCloseMobile}>×</button>
      </div>
      <nav className="app-sidebar__nav">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`app-sidebar__item ${activeModule === item.id ? "is-active" : ""}`}
            aria-current={activeModule === item.id ? "page" : undefined}
            title={collapsed ? item.label : undefined}
            onClick={() => onNavigate(item.id)}
          >
            <NavigationIconView name={item.icon} />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
      <button className="app-sidebar__collapse" type="button" aria-expanded={!collapsed} onClick={onToggleCollapsed}>
        <span aria-hidden="true">{collapsed ? "›" : "‹"}</span>
        <span>{collapsed ? "Expandir" : "Recolher menu"}</span>
      </button>
    </aside>
  );
}

export function Header({
  activeModule,
  properties,
  selectedPropertyId,
  onSelectedPropertyChange,
  safra,
  onSafraChange,
  userLabel,
  roleLabel,
  theme,
  onToggleTheme,
  onLogout,
  onOpenMobile,
  statusSlot,
}: {
  activeModule: ModuleId;
  properties: Propriedade[];
  selectedPropertyId: string;
  onSelectedPropertyChange: (id: string) => void;
  safra: string;
  onSafraChange: (value: string) => void;
  userLabel: string;
  roleLabel: string;
  theme: Theme;
  onToggleTheme: () => void;
  onLogout: () => void;
  onOpenMobile: () => void;
  statusSlot?: ReactNode;
}) {
  return (
    <header className="app-header">
      <div className="app-header__title">
        <button className="icon-button app-header__menu" type="button" aria-label="Abrir menu" onClick={onOpenMobile}>☰</button>
        <div><span>ERP agrícola</span><h1>{MODULE_LABELS[activeModule]}</h1></div>
      </div>
      <div className="app-header__context">
        {properties.length > 0 && (
          <label className="context-field">
            <span>Propriedade</span>
            <select value={selectedPropertyId} onChange={(event) => onSelectedPropertyChange(event.target.value)}>
              <option value="">Todas autorizadas</option>
              {properties.map((property) => <option key={property.id} value={property.id}>{property.nome}</option>)}
            </select>
          </label>
        )}
        <label className="context-field context-field--harvest">
          <span>Safra</span>
          <input value={safra} onChange={(event) => onSafraChange(event.target.value)} placeholder="2026/2027" />
        </label>
      </div>
      <div className="app-header__actions">
        {statusSlot}
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
        <div className="user-chip">
          <span className="user-chip__avatar" aria-hidden="true">{userLabel.slice(0, 1).toUpperCase()}</span>
          <span><strong>{userLabel}</strong><Badge tone="info">{roleLabel}</Badge></span>
        </div>
        <button className="secundario app-header__logout" type="button" onClick={onLogout}>Sair</button>
      </div>
    </header>
  );
}

export default function AppShell({
  items,
  activeModule,
  onNavigate,
  properties,
  selectedPropertyId,
  onSelectedPropertyChange,
  safra,
  onSafraChange,
  userLabel,
  roleLabel,
  theme,
  onToggleTheme,
  onLogout,
  statusSlot,
  children,
}: {
  items: NavigationItem[];
  activeModule: ModuleId;
  onNavigate: (module: ModuleId) => void;
  properties: Propriedade[];
  selectedPropertyId: string;
  onSelectedPropertyChange: (id: string) => void;
  safra: string;
  onSafraChange: (value: string) => void;
  userLabel: string;
  roleLabel: string;
  theme: Theme;
  onToggleTheme: () => void;
  onLogout: () => void;
  statusSlot?: ReactNode;
  children: ReactNode;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => setMobileOpen(false), [activeModule]);

  return (
    <div className={`app-shell ${collapsed ? "app-shell--collapsed" : ""}`}>
      <a className="skip-link" href="#main-content">Ir para o conteúdo</a>
      <Sidebar
        items={items}
        activeModule={activeModule}
        collapsed={collapsed}
        mobileOpen={mobileOpen}
        onNavigate={onNavigate}
        onToggleCollapsed={() => setCollapsed((value) => !value)}
        onCloseMobile={() => setMobileOpen(false)}
      />
      {mobileOpen && <button className="app-shell__overlay" aria-label="Fechar menu" onClick={() => setMobileOpen(false)} />}
      <div className="app-shell__workspace">
        <Header
          activeModule={activeModule}
          properties={properties}
          selectedPropertyId={selectedPropertyId}
          onSelectedPropertyChange={onSelectedPropertyChange}
          safra={safra}
          onSafraChange={onSafraChange}
          userLabel={userLabel}
          roleLabel={roleLabel}
          theme={theme}
          onToggleTheme={onToggleTheme}
          onLogout={onLogout}
          onOpenMobile={() => setMobileOpen(true)}
          statusSlot={statusSlot}
        />
        <main id="main-content" className="app-content">{children}</main>
      </div>
    </div>
  );
}
