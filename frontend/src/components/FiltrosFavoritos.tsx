import { useEffect, useRef, useState } from "react";
import { api } from "../api/propriedades";
import { Modulo } from "../api/usuarios";
import { useDestinoConsulta } from "./AcoesContext";
type Valores = Record<string, string | number | boolean | undefined>;
type Configuracao = {colunas?:string[]; orientacao?:string; densidade?:string};
type Favorito = { id: number; nome: string; filtros: Valores; configuracao?:Configuracao };
export default function FiltrosFavoritos({ contexto, filtros, aplicar, configuracao, aplicarConfiguracao }: { contexto: Modulo; filtros: Valores; aplicar: (filtros: Valores) => void; configuracao?:Configuracao; aplicarConfiguracao?:(config:Configuracao)=>void }) {
  const [itens, setItens] = useState<Favorito[]>([]); const [nome, setNome] = useState(""); const [selecionado, setSelecionado] = useState("");
  const [erro, setErro] = useState(""); const [ocupado, setOcupado] = useState(false); const trava = useRef(false);
  useDestinoConsulta(contexto, valores => aplicar(valores));
  useEffect(() => { let ativo = true; api.get<Favorito[]>("/core/favoritos/", { params: { contexto } }).then(({data}) => { if (ativo) setItens(data); }).catch(() => { if (ativo) setErro("Não foi possível carregar os filtros favoritos."); }); return () => { ativo = false; }; }, [contexto]);
  async function salvar() { if (trava.current || !nome.trim()) return; trava.current = true; setOcupado(true); setErro("");
    try { const {data} = await api.post<Favorito>("/core/favoritos/", { contexto, nome: nome.trim(), filtros, configuracao:configuracao||{} }); setItens(atual => [...atual, data]); setNome(""); setSelecionado(String(data.id)); }
    catch { setErro("Não foi possível salvar. Verifique se o nome já existe."); } finally { trava.current = false; setOcupado(false); }
  }
  async function excluir() { if (!selecionado || trava.current) return; if (!window.confirm("Excluir este filtro favorito?")) return; trava.current = true; setOcupado(true); setErro("");
    try { await api.delete(`/core/favoritos/${selecionado}/`); setItens(atual => atual.filter(item => String(item.id) !== selecionado)); setSelecionado(""); }
    catch { setErro("Não foi possível excluir o favorito."); } finally { trava.current = false; setOcupado(false); }
  }
  return <details className="card filtros-favoritos nao-imprimir"><summary>Meus filtros favoritos <small>({itens.length})</small></summary>
    <div className="favoritos-campos"><label>Filtro salvo<select value={selecionado} onChange={e => setSelecionado(e.target.value)}><option value="">Selecione um favorito</option>{itens.map(item => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
      <button type="button" disabled={!selecionado || ocupado} onClick={() => { const item = itens.find(item => String(item.id) === selecionado); if (item) {aplicar(item.filtros);aplicarConfiguracao?.(item.configuracao||{});} }}>Aplicar favorito</button>
      <button className="secundario" type="button" disabled={!selecionado || ocupado} onClick={() => void excluir()}>Excluir favorito</button>
      <label>Nome para salvar a consulta<input value={nome} maxLength={80} placeholder="Ex.: Soja 2026 · C.Vale" onChange={e => setNome(e.target.value)} /></label>
      <button className="secundario" type="button" disabled={!nome.trim() || ocupado} onClick={() => void salvar()}>{ocupado ? "Aguarde..." : "Salvar filtros atuais"}</button>
    </div>{erro && <p role="alert" className="erro">{erro}</p>}<small>Estes favoritos pertencem à sua conta.</small>
  </details>;
}
