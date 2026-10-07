import { useEffect, useMemo, useState } from "react";
import { MovimentoVenda, VendaGraos } from "../../api/vendas";
import { api } from "../../api/propriedades";
import ComprovanteLancamento from "../../components/ComprovanteLancamento";
import { formatarNumero } from "../../utils/numeros";
import { dadosRomaneioVenda } from "./RomaneioVenda";

type ItemRomaneio = { venda: VendaGraos; saida: MovimentoVenda };
export type FiltrosRomaneios = { busca: string; inicio: string; fim: string; historico: boolean; ordem: "recentes" | "antigos" };
const normalizar = (texto: string) => texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
export function localizarRomaneios(vendas: VendaGraos[], filtros: FiltrosRomaneios): ItemRomaneio[] {
  const busca = normalizar(filtros.busca.trim());
  const numero = busca.replace(/^#/, "");
  return vendas.flatMap(venda => venda.entregas.map(saida => ({ venda, saida })))
    .filter(({ venda, saida }) => {
      if (!filtros.historico && (venda.excluida_em || saida.cancelado_em)) return false;
      const data = saida.data_entrega?.slice(0, 10) || "";
      if ((filtros.inicio && (!data || data < filtros.inicio)) || (filtros.fim && (!data || data > filtros.fim))) return false;
      if (!busca) return true;
      if (/^\d+$/.test(numero)) return String(saida.id) === numero || String(venda.id) === numero || [saida.nota_produtor, saida.nota_empresa, venda.cad_pro_codigo].includes(numero);
      return normalizar([`Romaneio #${saida.id}`, `Venda #${venda.id}`, venda.cliente_nome, saida.destino, venda.numero_contrato, venda.propriedade_nome, venda.cad_pro_codigo, venda.cultura, venda.safra, saida.placa, saida.motorista, saida.nota_produtor, saida.nota_empresa].filter(Boolean).join(" ")).includes(busca);
    }).sort((a, b) => {
      const diferenca = (b.saida.data_entrega || "").localeCompare(a.saida.data_entrega || "") || b.saida.id - a.saida.id;
      return filtros.ordem === "recentes" ? diferenca : -diferenca;
    });
}
const iniciais: FiltrosRomaneios = { busca: "", inicio: "", fim: "", historico: false, ordem: "recentes" };
export function paginarRomaneios(resultados: ItemRomaneio[], pagina: number, tamanho: number) {
  const porPagina = [5, 10, 20].includes(tamanho) ? tamanho : 5;
  const paginas = Math.max(1, Math.ceil(resultados.length / porPagina));
  const atual = Math.max(0, Math.min(pagina, paginas - 1));
  return { paginas, atual, itens: resultados.slice(atual * porPagina, (atual + 1) * porPagina), inicio: resultados.length ? atual * porPagina + 1 : 0, fim: Math.min((atual + 1) * porPagina, resultados.length) };
}
export default function LocalizadorRomaneios({ revisao }: { revisao: VendaGraos[] }) {
  const [vendas, setVendas] = useState<VendaGraos[]>([]);
  const [filtros, setFiltros] = useState(iniciais);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [atualizacao, setAtualizacao] = useState(0);
  const [pagina, setPagina] = useState(0);
  const [porPagina, setPorPagina] = useState(5);
  useEffect(() => {
    let atual = true;
    setCarregando(true); setErro("");
    void api.get<VendaGraos[]>("/comercial/vendas/", { params: { mostrar_excluidas: String(filtros.historico) } })
      .then(resposta => { if (atual) setVendas(resposta.data); })
      .catch(() => { if (atual) setErro("Não foi possível carregar os romaneios. Tente atualizar a lista."); })
      .finally(() => { if (atual) setCarregando(false); });
    return () => { atual = false; };
  }, [revisao, filtros.historico, atualizacao]);
  const resultados = useMemo(() => localizarRomaneios(vendas, filtros), [vendas, filtros]);
  useEffect(() => { setPagina(0); }, [filtros, vendas, porPagina]);
  const { paginas, atual, itens, inicio, fim } = paginarRomaneios(resultados, pagina, porPagina);
  return <section className="card localizador-romaneios nao-imprimir" aria-label="Localizar romaneios">
    <header><div><h3>Localizar romaneios</h3><p>Busque e imprima saídas de qualquer venda.</p></div><button type="button" className="secundario" disabled={carregando} onClick={() => setAtualizacao(v => v + 1)}>Atualizar</button></header>
    <label>Buscar romaneio<input type="search" placeholder="Número, comprador, placa ou propriedade" value={filtros.busca} onChange={e => setFiltros({ ...filtros, busca: e.target.value })}/></label>
    <details className="romaneios-filtros-avancados"><summary>Filtros e histórico</summary><div className="romaneios-filtros"><label>Saída de<input type="date" max={filtros.fim || undefined} value={filtros.inicio} onChange={e => setFiltros({ ...filtros, inicio: e.target.value })}/></label><label>Saída até<input type="date" min={filtros.inicio || undefined} value={filtros.fim} onChange={e => setFiltros({ ...filtros, fim: e.target.value })}/></label><label>Ordem dos romaneios<select value={filtros.ordem} onChange={e => setFiltros({ ...filtros, ordem: e.target.value as FiltrosRomaneios["ordem"] })}><option value="recentes">Mais recentes</option><option value="antigos">Mais antigos</option></select></label></div>
    <div className="acoes"><label className="romaneios-historico"><input type="checkbox" checked={filtros.historico} onChange={e => setFiltros({ ...filtros, historico: e.target.checked })}/> Incluir cancelados e excluídos</label><button type="button" className="secundario" onClick={() => setFiltros(iniciais)}>Limpar busca</button></div></details>
    {carregando ? <p role="status">Carregando romaneios…</p> : erro ? <p className="erro" role="alert">{erro}</p> : <>
      <div className="romaneios-contagem"><span role="status">{inicio}–{fim} de {resultados.length} romaneios</span><label>Por página<select value={porPagina} onChange={e => setPorPagina(Number(e.target.value))}><option value={5}>5</option><option value={10}>10</option><option value={20}>20</option></select></label></div>
      <div className="romaneios-resultados">{itens.map(({ venda, saida }) => <article className="romaneio-resultado" key={`${venda.id}-${saida.id}`}>
        <div className="romaneio-linha">
          <div className="romaneio-numero"><strong>#{saida.id}</strong><span>{saida.data_entrega?.slice(0, 10).split("-").reverse().join("/") || "Sem data"}</span></div>
          <div className="romaneio-comprador"><strong>{saida.destino || venda.cliente_nome || "Comprador não informado"}</strong><span>{saida.placa || "Sem placa"} · {formatarNumero(saida.quantidade_kg)} kg</span></div>
          <ComprovanteLancamento duasVias dados={dadosRomaneioVenda(venda, saida)} rotulo={`Imprimir #${saida.id}`} tipoDocumento="romaneio" downloadRomaneio={{vendaId:venda.id,saidaId:saida.id}}/>
        </div>
        {(venda.excluida_em || saida.cancelado_em) && <strong className="romaneio-historico">Cancelado/excluído — histórico</strong>}
        <details className="romaneio-dados"><summary>Detalhes do romaneio #{saida.id}</summary><p>Venda #{venda.id} · {venda.propriedade_nome || "Sem propriedade"} · CAD/PRO {venda.cad_pro_codigo} · {venda.cultura} {venda.safra}</p><p>Motorista: {saida.motorista || "Não informado"} · Nota produtor: {saida.nota_produtor || "—"}</p></details>
      </article>)}</div>
      {!resultados.length && <p>Nenhum romaneio encontrado. Confira a busca e as datas ou inclua o histórico.</p>}
      {paginas > 1 && <nav className="acoes" aria-label="Páginas de romaneios"><button type="button" className="secundario" disabled={!atual} onClick={() => setPagina(atual - 1)}>Anteriores</button><span>Página {atual + 1} de {paginas}</span><button type="button" className="secundario" disabled={atual >= paginas - 1} onClick={() => setPagina(atual + 1)}>Próximos</button></nav>}
    </>}
  </section>;
}
