import { PropsWithChildren, useEffect, useState } from "react";
import { Propriedade } from "../api/propriedades";
import AplicativoStatus from "./AplicativoStatus";

export const modulos = [
  ["dashboard", "Dashboard", "home"], ["propriedades", "Propriedades", "building"],
  ["talhoes", "Talhões", "map"], ["cargas", "Cargas colhidas", "truck"],
  ["grupos", "Grupos de colheita", "leaf"], ["saldos", "CAD/PRO e saldos", "building"],
  ["estoque", "Estoque", "box"], ["vendas", "Vendas", "cart"],
  ["mercado", "Mercado", "chart"], ["clima", "Clima", "sun"],
  ["financeiro", "Financeiro", "chart"], ["operacoes", "Operações", "truck"],
  ["maquinas", "Máquinas", "truck"], ["relatorios", "Relatórios", "file"],
  ["insights", "IA agrícola", "leaf"],
] as const;
export type Modulo = typeof modulos[number][0];
const categorias: { titulo: string; ids: readonly Modulo[] }[] = [
  { titulo: "Visão executiva", ids: ["dashboard"] },
  { titulo: "Produção e território", ids: ["propriedades", "talhoes", "cargas", "grupos", "saldos", "operacoes", "maquinas"] },
  { titulo: "Gestão e negócios", ids: ["vendas", "estoque", "financeiro"] },
  { titulo: "Inteligência", ids: ["clima", "mercado", "relatorios", "insights"] },
];
export function Icon({ name }: { name: string }) {
  const paths: Record<string, string> = {
    home: "M3 10 12 3l9 7M5 9v12h14V9M9 21v-8h6v8",
    building: "M4 21V6l8-3 8 3v15ZM8 8h1m6 0h1M8 12h1m6 0h1M9 21v-5h6v5",
    map: "m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2ZM9 3v16M15 5v16",
    leaf: "M5 19C0 5 12 2 21 3c0 11-5 18-13 15M4 21 16 9",
    box: "m3 7 9-4 9 4v12l-9 3-9-3ZM3 7l9 4 9-4M12 11v11",
    cart: "M2 3h3l3 13h12l2-9H6M9 21h1m8 0h1",
    chart: "M4 21V12h4v9m4 0V8h4v13m4 0V3M3 8l6-4 5 1 7-4",
    sun: "M8 12a4 4 0 1 0 8 0 4 4 0 0 0-8 0M12 2v2m0 16v2M2 12h2m16 0h2M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2",
    truck: "M2 5h12v12H2ZM14 9h4l4 4v4h-8M5 17a2 2 0 1 0 4 0m7 0a2 2 0 1 0 4 0",
    file: "M5 2h9l5 5v15H5ZM14 2v6h5M8 12h8M8 16h8",
  };
  return <svg className="app-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name] || paths.leaf} /></svg>;
}
type Props = PropsWithChildren<{
  modulo: Modulo; navegar: (modulo: Modulo) => void;
  propriedades: Propriedade[]; selecionada: Propriedade | null;
  selecionar: (propriedade: Propriedade | null) => void; sair: () => void;
}>;
export default function AppShell({ children, modulo, navegar, propriedades, selecionada, selecionar, sair }: Props) {
  const [aberto, setAberto] = useState(false);
  const [recolhido, setRecolhido] = useState(false);
  const [busca, setBusca] = useState("");
  const [escuro, setEscuro] = useState(() => {
    try { return localStorage.getItem("agro-tema") === "escuro"; } catch { return false; }
  });
  useEffect(() => {
    try { localStorage.setItem("agro-tema", escuro ? "escuro" : "claro"); } catch { /* Preferência opcional em navegadores com armazenamento bloqueado. */ }
  }, [escuro]);
  useEffect(() => {
    if (!aberto) return;
    const fechar = (event: KeyboardEvent) => { if (event.key === "Escape") setAberto(false); };
    window.addEventListener("keydown", fechar);
    return () => window.removeEventListener("keydown", fechar);
  }, [aberto]);
  return <div className={`app-shell ${recolhido ? "sidebar-collapsed" : ""}`} data-theme={escuro ? "dark" : "light"}>
    <a className="skip-link" href="#conteudo-principal">Ir para o conteúdo</a>
    {aberto && <button className="sidebar-overlay" aria-label="Fechar menu" onClick={() => setAberto(false)} />}
    <aside className={`app-sidebar ${aberto ? "is-open" : ""}`} id="menu-principal">
      <div className="app-brand"><Icon name="leaf" /><span>AGRO-<b>AI</b>-PRO</span></div>
      <button className="sidebar-collapse" onClick={() => { setRecolhido(!recolhido); setBusca(""); }} aria-expanded={!recolhido} aria-label={recolhido ? "Expandir menu" : "Recolher menu"}>{recolhido ? "→" : "← Recolher menu"}</button>
      <label className="sidebar-search"><span>Encontrar módulo</span><input type="search" value={busca} onChange={e => setBusca(e.target.value)} placeholder="Buscar módulo…" /></label>
      <nav aria-label="Módulos agrícolas">{categorias.map(categoria => {
        const itens = modulos.filter(([id, label]) => categoria.ids.includes(id) && label.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().includes(busca.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()));
        return itens.length > 0 && <div className="sidebar-group" key={categoria.titulo}><h2>{categoria.titulo}</h2>{itens.map(([id, label, icon]) => <button key={id} title={label} aria-label={label} aria-current={modulo === id ? "page" : undefined} onClick={() => { navegar(id); setAberto(false); setBusca(""); }}><Icon name={icon} /><span>{label}</span></button>)}</div>;
      })}{busca && !modulos.some(([, label]) => label.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().includes(busca.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase())) && <p className="sidebar-no-results" role="status">Nenhum módulo encontrado.</p>}</nav>
      <div className="sidebar-footer"><small>Propriedade atual</small><strong>{selecionada?.nome || "Nenhuma propriedade"}</strong><span>{selecionada ? `${selecionada.municipio} · ${selecionada.uf}` : "Cadastre para começar"}</span><div className="sidebar-account"><Icon name="leaf" /><span>Sessão autenticada</span><button onClick={sair}>Sair</button></div></div>
    </aside>
    <main className="app-main" id="conteudo-principal">
      <header className="app-topbar"><div><button className="menu-toggle" aria-expanded={aberto} aria-controls="menu-principal" onClick={() => setAberto(!aberto)}>☰ Menu</button><h1>{modulo === "dashboard" ? "Olá, bem-vindo à sua gestão" : modulos.find(([id]) => id === modulo)?.[1]}</h1><p>{modulo === "dashboard" ? `Aqui está o panorama da sua operação em ${new Date().toLocaleDateString("pt-BR", { timeZone: "America/Sao_Paulo", day: "numeric", month: "long", year: "numeric" })}` : "Gestão agrícola · AGRO-AI-PRO"}</p></div><div className="topbar-controls"><AplicativoStatus /><label className="property-select"><span>Propriedade do dashboard</span><select value={selecionada?.id ?? ""} onChange={e => selecionar(propriedades.find(p => p.id === Number(e.target.value)) ?? null)}><option value="" disabled>Selecione uma propriedade</option>{propriedades.map(p => <option key={p.id} value={p.id}>{p.nome} · {p.uf}</option>)}</select></label></div></header>
      <div className="shell-preferences"><span>Sessão autenticada</span><button className="secundario" aria-pressed={escuro} onClick={() => setEscuro(!escuro)}>{escuro ? "☀ Tema claro" : "☾ Tema escuro"}</button></div>
      {children}
    </main>
  </div>;
}
