import { Icon } from "./ModuloIcon";
import MarcaAgro from "./MarcaAgro";
import { autorizado } from "./AcoesContext";
import { useEffect, useRef, useState } from "react";
import { Pagina, UsuarioAtual } from "../api/usuarios";
import { AREAS_MODULOS, nomeModulo } from "./gruposModulos";

export function correspondeBuscaModulo(nome: string, busca: string) {
  const normalizar = (texto: string) => texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR").trim();
  return normalizar(nome).includes(normalizar(busca));
}

const nomesAdministracao = { usuarios: "Usuários", historico: "Histórico de alterações", backup: "Backup em Excel" } as const;

export default function NavegacaoModulos({ acesso, modulo, onSelecionar }: { acesso: UsuarioAtual | null; modulo: Pagina; onSelecionar: (id: Pagina) => void }) {
  const areas = AREAS_MODULOS.filter(area => area.modulos.some(id => autorizado(acesso, id, "consultar")) || (area.nome === "Gestão" && acesso?.is_staff));
  const areaAtual = AREAS_MODULOS.find(area => ["usuarios", "historico", "backup"].includes(modulo) ? area.nome === "Gestão" : area.modulos.some(id => id === modulo))?.nome;
  const [aberto, setAberto] = useState(false);
  const buscaRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLElement>(null);
  const alternarRef = useRef<HTMLButtonElement>(null);
  const fecharMenu = () => { setAberto(false); alternarRef.current?.focus(); };
  const [recolhido, setRecolhido] = useState(false);
  useEffect(() => {
    const buscar = () => { setRecolhido(false); setAberto(true); window.requestAnimationFrame(() => buscaRef.current?.focus()); };
    const atalho = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); buscar(); } };
    window.addEventListener("agro:buscar-modulo", buscar);
    window.addEventListener("keydown", atalho);
    return () => { window.removeEventListener("agro:buscar-modulo", buscar); window.removeEventListener("keydown", atalho); };
  }, []);
  useEffect(() => {
    if (!aberto) return;
    buscaRef.current?.focus();
    const fechar = (e: KeyboardEvent) => {
      if (e.key === "Escape") { setAberto(false); alternarRef.current?.focus(); }
      if (e.key !== "Tab" || !window.matchMedia("(max-width:999px)").matches) return;
      const controles = Array.from(menuRef.current?.querySelectorAll<HTMLElement>("button:not(:disabled), input:not(:disabled)") ?? []).filter(item => item.getClientRects().length > 0);
      const primeiro = controles[0], ultimo = controles[controles.length - 1];
      if (!primeiro || !ultimo) return;
      const foraDoMenu = !menuRef.current?.contains(document.activeElement);
      if (e.shiftKey && (document.activeElement === primeiro || foraDoMenu)) { e.preventDefault(); ultimo.focus(); }
      else if (!e.shiftKey && (document.activeElement === ultimo || foraDoMenu)) { e.preventDefault(); primeiro.focus(); }
    };
    window.addEventListener("keydown", fechar);
    return () => window.removeEventListener("keydown", fechar);
  }, [aberto]);
  const [busca, setBusca] = useState("");
  const gruposVisiveis = areas.map(grupo => ({ ...grupo, modulos: grupo.modulos.filter(id => autorizado(acesso, id, "consultar") && correspondeBuscaModulo(nomeModulo(id), busca)) })).filter(grupo => grupo.modulos.length > 0);
  const administracaoVisivel = acesso?.is_staff ? (["usuarios", "historico", "backup"] as const).filter(id => correspondeBuscaModulo(nomesAdministracao[id], busca)) : [];
  const totalResultados = (acesso && correspondeBuscaModulo("Dashboard Início", busca) ? 1 : 0) + gruposVisiveis.reduce((total, grupo) => total + grupo.modulos.length, 0) + administracaoVisivel.length;
  const [areaSelecionada, setAreaSelecionada] = useState(areaAtual);
  useEffect(() => { setAreaSelecionada(areaAtual); }, [areaAtual]);
  const area = areas.find(item => item.nome === areaSelecionada) ?? areas[0];
  return <>{acesso && <button type="button" ref={alternarRef} className="alternar-menu-lateral nao-imprimir" aria-expanded={aberto} aria-controls="menu-lateral-agro" onClick={()=>setAberto(!aberto)}>☰ Menu</button>}{aberto && <button className="fundo-menu-lateral nao-imprimir" aria-label="Fechar menu" onClick={fecharMenu} />}<nav ref={menuRef} id="menu-lateral-agro" className={`navegacao-modulos navegacao-por-area ${aberto ? "menu-aberto" : ""}`} aria-label="Módulos agrícolas">
    <div className="marca-lateral"><MarcaAgro /></div>
    {acesso && <button className="recolher-menu" type="button" aria-expanded={!recolhido} onClick={() => setRecolhido(!recolhido)}>{recolhido ? "Expandir menu" : "Recolher menu"}</button>}
    <span className="estado-menu" data-recolhido={recolhido} hidden />
    {acesso && <label className="busca-navegacao">Buscar módulo<input ref={buscaRef} type="search" value={busca} onChange={e=>setBusca(e.target.value)} placeholder="Ex.: talhoes, maquinas…" onKeyDown={e => { if (e.key === "Escape" && busca) { e.stopPropagation(); setBusca(""); } }} /></label>}
    <div className="navegacao-areas" aria-label="Áreas do sistema">
      {acesso && <button type="button" aria-current={modulo === "inicio" ? "page" : undefined} className={modulo === "inicio" ? "" : "secundario"} onClick={() => onSelecionar("inicio")}>Início</button>}
      {areas.map(item => <button type="button" key={item.nome} aria-pressed={area?.nome === item.nome} className={area?.nome === item.nome ? "" : "secundario"} onClick={() => setAreaSelecionada(item.nome)}>{item.nome}</button>)}
    </div>
    <div className="menu-lateral-completo">{acesso && correspondeBuscaModulo("Dashboard Início", busca) && <button type="button" title="Dashboard" aria-current={modulo === "inicio" ? "page" : undefined} onClick={()=>{onSelecionar("inicio");setAberto(false);}}><Icon name="home" />Dashboard</button>}{gruposVisiveis.map(grupo=><section key={grupo.nome}><h2>{grupo.nome}</h2>{grupo.modulos.map(id=><button type="button" key={id} title={nomeModulo(id)} aria-current={modulo===id?"page":undefined} onClick={()=>{onSelecionar(id);setAberto(false);}}><Icon name={id === "clima" ? "sun" : id === "mercado" || id === "financeiro" ? "chart" : id === "talhoes" ? "map" : id === "vendas" ? "cart" : id === "estoque" ? "box" : id === "cargas" || id === "maquinas" || id === "operacoes" ? "truck" : id === "insights" ? "leaf" : "file"} />{nomeModulo(id)}</button>)}</section>)}{administracaoVisivel.length > 0 && <section><h2>Administração</h2>{administracaoVisivel.map(id=><button type="button" key={id} title={nomesAdministracao[id]} aria-current={modulo===id?"page":undefined} onClick={()=>{onSelecionar(id);setAberto(false);}}><Icon name="file" />{nomesAdministracao[id]}</button>)}</section>}</div>
    {acesso && busca.trim() && <div className="resultado-busca-menu" role="status"><span>{totalResultados === 0 ? "Nenhum módulo encontrado." : `${totalResultados} módulo(s) encontrado(s).`}</span><button type="button" className="secundario" onClick={() => setBusca("")}>Limpar busca</button></div>}
    <div className="navegacao-itens" aria-label={area ? `Módulos de ${area.nome}` : "Nenhum módulo permitido"}>
      {area?.modulos.filter(id => autorizado(acesso, id, "consultar")).map(id => <button type="button" key={id} aria-current={modulo === id ? "page" : undefined} className={modulo === id ? "" : "secundario"} onClick={() => onSelecionar(id)}>{nomeModulo(id)}</button>)}
      {area?.nome === "Gestão" && acesso?.is_staff && <button type="button" aria-current={modulo === "usuarios" ? "page" : undefined} className={modulo === "usuarios" ? "" : "secundario"} onClick={() => onSelecionar("usuarios")}>Usuários</button>}
      {area?.nome === "Gestão" && acesso?.is_staff && <button type="button" aria-current={modulo === "historico" ? "page" : undefined} className={modulo === "historico" ? "" : "secundario"} onClick={() => onSelecionar("historico")}>Histórico de alterações</button>}
      {area?.nome === "Gestão" && acesso?.is_staff && <button type="button" aria-current={modulo === "backup" ? "page" : undefined} className={modulo === "backup" ? "" : "secundario"} onClick={() => onSelecionar("backup")}>Backup em Excel</button>}
    </div>
    {acesso && <div className="usuario-lateral"><span aria-hidden="true">{acesso.username.slice(0,2).toUpperCase()}</span><div><strong>{acesso.username}</strong><small>{acesso.is_staff?"Administrador":"Gestão rural"}</small></div></div>}
  </nav></>;
}
