import { useEffect, useState } from "react";
import { Propriedade } from "../../api/propriedades";
import { listarTalhoes, Talhao } from "../../api/talhoes";
import { carregarPainelMercado } from "../../api/mercado";
import { listarPrevisoes, PrevisaoClima } from "../../api/clima";
import { consultarPainelSaldos, PainelSaldos } from "../../api/producaoSaldos";
import { obterInsights, Insight } from "../../api/insights";
import { Icon, Modulo } from "../../components/AppShell";
import MapaTalhao from "../../components/MapaTalhao";
import GraficoMercado from "../Mercado/GraficoMercado";

const numero = (valor: number | string) => Number(valor).toLocaleString("pt-BR", { maximumFractionDigits: 2 });
type Dados = {
  talhoes?: Talhao[]; mercado?: Awaited<ReturnType<typeof carregarPainelMercado>>;
  clima?: PrevisaoClima[]; saldos?: PainelSaldos; insights?: Insight[];
};
export default function DashboardPage({ propriedade, navegar }: { propriedade: Propriedade | null; navegar: (modulo: Modulo) => void }) {
  const [dados, setDados] = useState<Dados>({});
  const [carregando, setCarregando] = useState(false);
  const [falhas, setFalhas] = useState<string[]>([]);
  const [safra, setSafra] = useState("");
  const [produto, setProduto] = useState("soja");
  const [revisao, setRevisao] = useState(0);
  const [atualizado, setAtualizado] = useState<string | null>(null);
  useEffect(() => {
    let ativo = true;
    setDados({}); setFalhas([]); setAtualizado(null);
    if (!propriedade) { setCarregando(false); return; }
    setCarregando(true);
    async function talhoesCompletos() {
      const itens: Talhao[] = [];
      let page = 1;
      while (true) {
        const resposta = await listarTalhoes({ propriedade: String(propriedade!.id), safra, page, pageSize: 100 });
        itens.push(...resposta.results);
        if (!resposta.next) return itens;
        page++;
      }
    }
    void Promise.allSettled([
      talhoesCompletos(), carregarPainelMercado(), listarPrevisoes(propriedade.id),
      consultarPainelSaldos({ propriedade: String(propriedade.id), safra: safra || undefined }),
      obterInsights(String(propriedade.id)),
    ]).then(([talhoes, mercado, clima, saldos, insights]) => {
      if (!ativo) return;
      setDados({
        talhoes: talhoes.status === "fulfilled" ? talhoes.value : undefined,
        mercado: mercado.status === "fulfilled" ? mercado.value : undefined,
        clima: clima.status === "fulfilled" ? clima.value : undefined,
        saldos: saldos.status === "fulfilled" ? saldos.value : undefined,
        insights: insights.status === "fulfilled" ? insights.value.insights : undefined,
      });
      setFalhas([talhoes, mercado, clima, saldos, insights].flatMap((r, i) => r.status === "rejected" ? [["Talhões", "Mercado", "Clima", "Saldos", "Assistente"][i]] : []));
      setCarregando(false);
      setAtualizado(new Date().toLocaleTimeString("pt-BR", { timeZone: "America/Sao_Paulo" }));
    });
    return () => { ativo = false; };
  }, [propriedade?.id, safra, revisao]);
  const vazio = carregando ? "Carregando…" : "Dados indisponíveis";
  const hoje = new Date().toLocaleDateString("en-CA", { timeZone: "America/Sao_Paulo" });
  const previsoes = dados.clima?.filter(p => p.data >= hoje) ?? [];
  const atual = previsoes[0];
  const talhaoMapa = dados.talhoes?.find(t => t.geometria_geojson && t.latitude_centro != null && t.longitude_centro != null);
  const painel = (titulo: string, modulo: Modulo) => <div className="dashboard-panel-heading"><h2>{titulo}</h2><button onClick={() => navegar(modulo)}>Ver mais →</button></div>;
  return <section className="dashboard" aria-label="Panorama agrícola" aria-busy={carregando}>
    <div className="dashboard-welcome"><div><span className="eyebrow">CENTRAL DE GESTÃO</span><h2>Uma visão integrada da sua operação.</h2><p>Produção, estoque e inteligência para acompanhar o campo com clareza.</p></div><Icon name="leaf" /></div>
    <nav className="dashboard-shortcuts" aria-label="Atalhos operacionais">{([ ["cargas", "Cargas colhidas", "truck"], ["saldos", "Consultar CAD/PRO", "box"], ["vendas", "Acessar vendas", "cart"], ["relatorios", "Ver relatórios", "file"] ] as const).map(([id, label, icon]) => <button className="secundario" key={id} onClick={() => navegar(id)}><Icon name={icon} /><span>{label}</span><span aria-hidden="true">↗</span></button>)}</nav>
    <div className="dashboard-toolbar"><span>{propriedade?.nome || "Selecione ou cadastre uma propriedade para consultar o panorama."}</span><form onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); setSafra(String(f.get("safra") || "")); }}><input name="safra" aria-label="Filtrar dashboard por safra" placeholder="Safra (todas)" /><button type="submit">Filtrar</button><button type="button" className="secundario" onClick={() => setRevisao(r => r + 1)}>Atualizar</button></form></div>
    <p className="dashboard-note" role="status">{carregando ? "Consultando dados…" : atualizado ? `${falhas.length ? "Consulta parcial" : "Consulta concluída"} às ${atualizado} · horário de Brasília` : "Aguardando seleção de propriedade"}</p>
    {falhas.length > 0 && <p className="erro card" role="alert">Não foi possível consultar: {falhas.join(", ")}. Tente atualizar o painel.</p>}
    <div className="dashboard-stock-summary">{([
      ["Estoque físico", "saldo_fisico_kg"],
      ["Estoque comprometido", "saldo_comprometido_kg"],
      ["Estoque disponível", "saldo_disponivel_kg"],
    ] as const).map(([label, campo]) => <article className="dashboard-panel" key={campo}><h2>{label}</h2><strong>{dados.saldos ? `${numero(dados.saldos.resumo[campo])} kg` : vazio}</strong><p className="dashboard-note">{safra || "Todas as safras"} · {propriedade?.nome || "Sem propriedade"}</p></article>)}</div>
    <div className="dashboard-metrics">{["Soja", "Milho", "Trigo"].map((cultura, i) => <article className={`dashboard-metric crop-${i}`} key={cultura}><div className="metric-icon"><Icon name="leaf" /></div><div><h2>{cultura}</h2><strong>{dados.talhoes ? `${numero(dados.talhoes.filter(t => t.cultura_atual.toLocaleLowerCase("pt-BR") === cultura.toLocaleLowerCase("pt-BR")).reduce((total, t) => total + Number(t.area_hectares), 0))} ha` : vazio}</strong><small>Área cadastrada nos talhões</small><div className="metric-accent" /></div></article>)}
      <article className="dashboard-metric"><div className="metric-icon"><Icon name="building" /></div><div><h2>Estoque agrícola</h2><strong>{dados.saldos ? `${numero(dados.saldos.resumo.saldo_fisico_kg)} kg` : vazio}</strong><small>Físico · {safra || "todas as safras"}</small></div></article>
      <article className="dashboard-metric"><div className="metric-icon"><Icon name="cart" /></div><div><h2>Vendas</h2><button className="metric-link" onClick={() => navegar("vendas")}>Consultar contratos →</button><small>Indicador agregado nesta prévia indisponível</small></div></article>
      <article className="dashboard-metric"><div className="metric-icon weather-icon"><Icon name="sun" /></div><div><h2>Clima</h2><strong>{atual?.temperatura_max != null ? `${numero(atual.temperatura_max)}°C` : vazio}</strong><small>{atual ? `Máxima prevista · ${atual.data}` : "Sem previsão vigente"}</small></div></article>
    </div>
    <div className="dashboard-grid">
      <article className="dashboard-panel">{painel("Preços de mercado", "mercado")}<div className="market-rows">{["soja", "milho", "trigo"].map(c => { const r = dados.mercado?.resumos.find(r => r.produto === c); return <div className="market-row" key={c}><Icon name="leaf" /><b>{c}</b><strong>{r ? `${numero(r.valor)} ${r.unidade}` : vazio}</strong><span className={Number(r?.variacao_percentual) < 0 ? "variacao-negativa" : "variacao-positiva"}>{r?.variacao_percentual != null ? `${numero(r.variacao_percentual)}%` : "—"}</span>{r && <small>{r.data} · {r.aviso}</small>}</div>; })}</div><p className="dashboard-note">Cotações registradas na integração de mercado.</p></article>
      <article className="dashboard-panel">{painel("Evolução dos preços", "mercado")}<label className="chart-select"><span>Cultura</span><select value={produto} onChange={e => setProduto(e.target.value)}><option value="soja">Soja</option><option value="milho">Milho</option><option value="trigo">Trigo</option></select></label>{dados.mercado ? <GraficoMercado cotacoes={dados.mercado.cotacoes.filter(c => c.produto === produto)} /> : <p className="dashboard-empty">{vazio}</p>}</article>
      <article className="dashboard-panel">{painel(`Clima · ${propriedade?.municipio || "propriedade"}`, "clima")}{atual ? <><div className="weather-current"><Icon name="sun" /><div><strong>{atual.temperatura_min == null ? "—" : numero(atual.temperatura_min)}° / {atual.temperatura_max == null ? "—" : numero(atual.temperatura_max)}°C</strong><p>{atual.condicao}</p><small>Previsão · {atual.data} · {atual.fonte}</small></div></div><div className="weather-days">{previsoes.slice(0, 5).map(p => <div key={p.id}><b>{new Date(`${p.data}T12:00:00`).toLocaleDateString("pt-BR", { weekday: "short" })}</b><Icon name="sun" /><span>{p.temperatura_max ?? "—"}° / {p.temperatura_min ?? "—"}°</span><small>{p.chuva_mm ?? "—"} mm</small></div>)}</div></> : <p className="dashboard-empty">{carregando ? vazio : "Nenhuma previsão vigente. Consulte o módulo Clima para atualizar."}</p>}</article>
      <article className="dashboard-panel fields-panel">{painel("Talhões", "talhoes")}{talhaoMapa ? <MapaTalhao geometria={talhaoMapa.geometria_geojson!} latitude={Number(talhaoMapa.latitude_centro)} longitude={Number(talhaoMapa.longitude_centro)} nome={talhaoMapa.nome} /> : <div className="dashboard-empty map-empty"><Icon name="map" /><p>{dados.talhoes ? "Nenhum talhão com geometria KML disponível." : vazio}</p></div>}<p className="dashboard-note">{dados.talhoes ? `${dados.talhoes.length} talhões · mapa do primeiro talhão com geometria. Sem integração NDVI nesta prévia.` : "Mapa baseado nas geometrias reais cadastradas."}</p></article>
      <article className="dashboard-panel">{painel("IA agrícola", "insights")}<div className="insight-list">{dados.insights ? dados.insights.filter(i => i.nivel === "informativo").slice(0, 3).map(i => <div key={i.codigo}><Icon name="leaf" /><div><b>{i.titulo}</b><p>{i.evidencia}</p></div></div>) : <p className="dashboard-empty">{vazio}</p>}{dados.insights && !dados.insights.some(i => i.nivel === "informativo") && <p>Nenhum insight informativo disponível.</p>}</div><button className="insight-action" onClick={() => navegar("insights")}><Icon name="leaf" /><span>Análise completa do assistente<small>Consulte evidências e recomendações</small></span>→</button><p className="dashboard-note">Análise por propriedade · independente do filtro de safra.</p></article>
      <div className="dashboard-stack"><article className="dashboard-panel">{painel("CAD/PRO e estoque", "saldos")}<div className="dashboard-table-scroll"><table className="dashboard-table"><thead><tr><th>Cultura / safra / CAD/PRO</th><th>Físico kg</th><th>Comprometido kg</th><th>Disponível kg</th></tr></thead><tbody>{dados.saldos?.posicoes.map(p => <tr key={p.id}><td><b>{p.cultura}</b><small>{p.safra} · {p.cad_pro_codigo}<br />{p.armazem_nome} · {p.classificacao_codigo}</small></td><td>{numero(p.saldo_fisico_kg)}</td><td>{numero(p.saldo_comprometido_kg)}</td><td>{numero(p.saldo_disponivel_kg)}</td></tr>)}</tbody></table></div>{!dados.saldos?.posicoes.length && <p className="dashboard-empty">{dados.saldos ? "Nenhuma posição encontrada." : vazio}</p>}</article><article className="dashboard-panel">{painel("Alertas operacionais", "insights")}{dados.insights?.filter(i => i.nivel !== "informativo").slice(0, 3).map(i => <div className={`dashboard-alert ${i.nivel}`} key={i.codigo}><Icon name="file" /><div><b>{i.titulo}</b><p>{i.evidencia}</p></div></div>)}<p className="dashboard-note">{dados.insights ? "Alertas da análise por propriedade. Veja todos no assistente." : vazio}</p></article></div>
    </div>
  </section>;
}
