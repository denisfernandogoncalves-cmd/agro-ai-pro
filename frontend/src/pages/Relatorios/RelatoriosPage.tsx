import { FormEvent, useEffect, useState } from "react";
import { FiltrosRelatorio, ItemRelatorio, obterOpcoesRelatorio, obterRelatorioOperacional, OpcoesRelatorio, PosicaoRelatorio, RelatorioOperacional, SecaoRelatorio } from "../../api/relatorios";
import { Propriedade } from "../../api/propriedades";

const SECOES: { id: SecaoRelatorio; nome: string }[] = [
  { id: "saldos", nome: "Estoque e saldos" }, { id: "producao", nome: "Produção" },
  { id: "reservas", nome: "Reservas" }, { id: "vendas", nome: "Vendas" },
  { id: "entregas", nome: "Entregas" }, { id: "movimentacoes", nome: "Histórico" },
  { id: "rastreabilidade", nome: "Rastreabilidade" },
];
const vazio: FiltrosRelatorio = { secao: "saldos", pagina: 1, por_pagina: 25 };
const kg = (valor: unknown) => `${Number(valor || 0).toLocaleString("pt-BR", { minimumFractionDigits: 3, maximumFractionDigits: 3 })} kg`;
const texto = (valor: unknown) => valor === null || valor === undefined || valor === "" ? "—" : String(valor);

function Posicao({ item }: { item?: PosicaoRelatorio }) {
  return item ? <span>{item.cad_pro_codigo} · {item.propriedade_nome} · {item.cultura} · {item.safra} · {item.classificacao_codigo} · {item.armazem_nome}</span> : null;
}

export function TabelaRelatorio({ secao, itens }: { secao: SecaoRelatorio; itens: ItemRelatorio[] }) {
  if (!itens.length) return <div className="card vazio">Nenhum registro encontrado para os filtros informados.</div>;
  return <div className="tabela-responsiva"><table className="tabela-relatorio"><thead><tr><th>Referência</th><th>Contexto oficial</th><th>Quantidade</th><th>Situação / data</th></tr></thead><tbody>{itens.map((item) => {
    const posicao = (secao === "saldos" ? item : item.posicao) as PosicaoRelatorio | undefined;
    const referencia = item.numero_contrato ?? item.lote_operacional_codigo ?? item.referencia_externa ?? `#${item.id}`;
    const quantidade = secao === "saldos" ? `Físico ${kg(item.saldo_fisico_kg)} · comprometido ${kg(item.saldo_comprometido_kg)} · disponível ${kg(item.saldo_disponivel_kg)}` : kg(item.quantidade_kg ?? item.saldo_reservado_kg);
    return <tr key={`${secao}-${item.id}`}><td><strong>{texto(referencia)}</strong>{item.cliente_nome ? <small>{texto(item.cliente_nome)}</small> : null}</td><td><Posicao item={posicao} /></td><td>{quantidade}</td><td>{texto(item.status ?? item.operacao)}<small>{texto(item.data ?? item.data_contrato ?? item.criado_em)}</small></td></tr>;
  })}</tbody></table></div>;
}

export default function RelatoriosPage({ propriedades }: { propriedades: Propriedade[] }) {
  const [filtros, setFiltros] = useState<FiltrosRelatorio>(vazio);
  const [dados, setDados] = useState<RelatorioOperacional | null>(null);
  const [opcoes, setOpcoes] = useState<OpcoesRelatorio | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  async function carregar(proximos = filtros) { setCarregando(true); setErro(""); try { setDados(await obterRelatorioOperacional(proximos)); } catch { setErro("Não foi possível carregar os relatórios operacionais."); } finally { setCarregando(false); } }
  useEffect(() => { void obterOpcoesRelatorio().then(setOpcoes).catch(() => setErro("Não foi possível carregar as opções dos relatórios.")); void carregar(vazio); }, []);
  function alterar(campo: keyof FiltrosRelatorio, valor: string | number) { setFiltros((atual) => ({ ...atual, [campo]: valor || undefined, pagina: 1 })); }
  function trocarSecao(secao: SecaoRelatorio) { const proximos = { ...filtros, secao, pagina: 1 }; setFiltros(proximos); void carregar(proximos); }
  function paginar(pagina: number) { const proximos = { ...filtros, pagina }; setFiltros(proximos); void carregar(proximos); }
  return <section className="modulo-relatorios-operacionais">
    <div className="card cabecalho-relatorio"><div><span className="kicker">Consulta oficial somente leitura</span><h2>Relatórios operacionais</h2><p>Produção, saldos, reservas e fluxo comercial consolidados diretamente do ledger.</p></div><span className="selo-leitura">Somente leitura</span></div>
    <form className="card filtros-operacionais" onSubmit={(e: FormEvent) => { e.preventDefault(); void carregar({ ...filtros, pagina: 1 }); }}>
      <label>CAD/PRO<select value={filtros.cad_pro ?? ""} onChange={(e) => alterar("cad_pro", e.target.value)}><option value="">Todos</option>{opcoes?.cadpros.map((item) => <option key={item.id} value={item.id}>{item.codigo} — {item.descricao}</option>)}</select></label>
      <label>Propriedade<select value={filtros.propriedade ?? ""} onChange={(e) => alterar("propriedade", e.target.value)}><option value="">Todas</option>{propriedades.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
      <label>Cultura<select value={filtros.cultura ?? ""} onChange={(e) => alterar("cultura", e.target.value)}><option value="">Todas</option>{opcoes?.culturas.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>Safra<select value={filtros.safra ?? ""} onChange={(e) => alterar("safra", e.target.value)}><option value="">Todas</option>{opcoes?.safras.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>Classificação<select value={filtros.classificacao_codigo ?? ""} onChange={(e) => alterar("classificacao_codigo", e.target.value)}><option value="">Todas</option>{opcoes?.classificacoes.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>Armazenagem<select value={filtros.armazem ?? ""} onChange={(e) => alterar("armazem", e.target.value)}><option value="">Todas</option>{opcoes?.armazens.filter((item) => !filtros.propriedade || String(item.propriedade_id) === filtros.propriedade).map((item) => <option key={item.id} value={item.id}>{item.nome} — {item.propriedade__nome}</option>)}</select></label>
      <label>De<input type="date" value={filtros.data_inicio ?? ""} onChange={(e) => alterar("data_inicio", e.target.value)} /></label><label>Até<input type="date" value={filtros.data_fim ?? ""} onChange={(e) => alterar("data_fim", e.target.value)} /></label>
      <div className="acoes-filtros"><button disabled={carregando}>Aplicar filtros</button><button type="button" className="secundario" onClick={() => { setFiltros(vazio); void carregar(vazio); }}>Limpar</button></div>
    </form>
    {erro && <p className="erro card" role="alert">{erro}</p>}
    {carregando && !dados ? <div className="card vazio">Carregando relatórios operacionais...</div> : null}
    {dados ? <><section className="resumos-operacionais">
      <article className="card"><span>Saldo físico</span><strong>{kg(dados.totais.saldo_fisico_kg)}</strong></article><article className="card"><span>Comprometido</span><strong>{kg(dados.totais.saldo_comprometido_kg)}</strong></article><article className="card"><span>Disponível</span><strong>{kg(dados.totais.saldo_disponivel_kg)}</strong></article><article className="card"><span>Produção no período</span><strong>{kg(dados.totais.producao_kg)}</strong></article><article className="card"><span>Reservas abertas</span><strong>{kg(dados.totais.reservas_abertas_kg)}</strong></article><article className="card"><span>Entregas no período</span><strong>{kg(dados.totais.entregas_kg)}</strong></article>
    </section><nav className="abas-relatorios" aria-label="Seções dos relatórios">{SECOES.map((item) => <button key={item.id} className={filtros.secao === item.id ? "" : "secundario"} onClick={() => trocarSecao(item.id)}>{item.nome}</button>)}</nav><div className={carregando ? "conteudo-atualizando" : ""}><TabelaRelatorio secao={dados.secao} itens={dados.dados.resultados} /></div><div className="paginacao"><button className="secundario" disabled={carregando || dados.dados.pagina <= 1} onClick={() => paginar(dados.dados.pagina - 1)}>Anterior</button><span>Página {dados.dados.pagina} de {Math.max(1, dados.dados.total_paginas)} · {dados.dados.total} registros</span><button className="secundario" disabled={carregando || dados.dados.pagina >= dados.dados.total_paginas} onClick={() => paginar(dados.dados.pagina + 1)}>Próxima</button></div><p className="kicker">Posição autoritativa por CAD/PRO + cultura + safra + classificação + armazenagem · gerado em {new Date(dados.gerado_em).toLocaleString("pt-BR")}</p></> : null}
  </section>;
}
