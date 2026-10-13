import { useEffect, useState } from "react";
import { MovimentoVenda, VendaGraos } from "../../api/vendas";
import { useConsultaRomaneios } from "../../api/romaneios";
import { formatarData, formatarDataHora, periodoInvertido } from "../../utils/datas";
import ComprovanteLancamento from "../../components/ComprovanteLancamento";
import { formatarNumero } from "../../utils/numeros";
import { dadosRomaneioVenda, VendaDoRomaneio } from "./RomaneioVenda";

type ItemRomaneio = { venda: VendaDoRomaneio; saida: MovimentoVenda };
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
      return normalizar([`Romaneio ${saida.id}`, `Venda #${venda.id}`, venda.cliente_nome, saida.destino, venda.numero_contrato, venda.propriedade_nome, venda.cad_pro_codigo, venda.cultura, venda.safra, saida.placa, saida.motorista, saida.nota_produtor, saida.nota_empresa].filter(Boolean).join(" ")).includes(busca);
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
export default function LocalizadorRomaneios({ revisao, ativo, onContagem }: { revisao: VendaGraos[]; ativo:boolean; onContagem?: (valor:string|undefined)=>void }) {
  const [filtros, setFiltros] = useState(iniciais);
  const [pagina, setPagina] = useState(1);
  const [porPagina, setPorPagina] = useState(5);
  const periodoInvalido=periodoInvertido(filtros.inicio,filtros.fim);
  const params:Record<string,string|number|boolean>={busca:filtros.busca,historico:filtros.historico,ordem:filtros.ordem,pagina,por_pagina:porPagina};
  if(filtros.inicio)params.inicio=filtros.inicio;
  if(filtros.fim)params.fim=filtros.fim;
  const {dados,erro,carregando,atualizar}=useConsultaRomaneios<ItemRomaneio>("/comercial/romaneios/",params,ativo,revisao,periodoInvalido);
  useEffect(()=>{onContagem?.(dados ? String(dados.total) : undefined);},[dados,onContagem]);
  function mudarFiltros(novos:FiltrosRomaneios){setFiltros(novos);setPagina(1);}
  return <section className="card localizador-romaneios nao-imprimir" aria-label="Localizar romaneios">
    <header><div><h3>Localizar romaneios</h3><p>Busque e imprima saídas de qualquer venda.</p></div><button type="button" className="secundario" disabled={carregando||periodoInvalido} onClick={atualizar}>Atualizar</button></header>
    <label>Buscar romaneio<input type="search" maxLength={160} placeholder="Número, comprador, placa ou propriedade" value={filtros.busca} onChange={e => mudarFiltros({ ...filtros, busca: e.target.value })}/></label>
    <details className="romaneios-filtros-avancados"><summary>Filtros e histórico</summary><div className="romaneios-filtros"><label>Saída de<input type="date" aria-invalid={periodoInvalido} aria-describedby={periodoInvalido?"erro-periodo-saida":undefined} max={filtros.fim || undefined} value={filtros.inicio} onChange={e => mudarFiltros({ ...filtros, inicio: e.target.value })}/></label><label>Saída até<input type="date" aria-invalid={periodoInvalido} aria-describedby={periodoInvalido?"erro-periodo-saida":undefined} min={filtros.inicio || undefined} value={filtros.fim} onChange={e => mudarFiltros({ ...filtros, fim: e.target.value })}/></label><label>Ordem dos romaneios<select value={filtros.ordem} onChange={e => mudarFiltros({ ...filtros, ordem: e.target.value as FiltrosRomaneios["ordem"] })}><option value="recentes">Mais recentes</option><option value="antigos">Mais antigos</option></select></label></div>
    <div className="acoes"><label className="romaneios-historico"><input type="checkbox" checked={filtros.historico} onChange={e => mudarFiltros({ ...filtros, historico: e.target.checked })}/> Incluir cancelados e excluídos</label><button type="button" className="secundario" onClick={() => mudarFiltros(iniciais)}>Limpar busca</button></div></details>
    <p>Filtros ativos: {[filtros.busca&&`busca “${filtros.busca}”`,filtros.inicio&&`desde ${formatarData(filtros.inicio)}`,filtros.fim&&`até ${formatarData(filtros.fim)}`,filtros.historico&&"inclui histórico"].filter(Boolean).join(" · ")||"nenhum; somente saídas ativas"}.</p>
    {periodoInvalido&&<p id="erro-periodo-saida" role="alert" className="erro">A data final deve ser igual ou posterior à inicial. Corrija o período para consultar.</p>}
    {carregando&&<p role="status">Carregando romaneios…</p>}{erro&&<p className="erro" role="alert">{erro}</p>}
    {dados&&<>
      <p>Peso das saídas ativas dos romaneios filtrados, em todas as páginas: <strong>{formatarNumero(dados.peso_ativo_kg)} kg</strong>. Histórico não somado; devoluções não abatidas neste total de saídas.</p>
      <p>Consulta concluída em {formatarDataHora(dados.consultado_em)}.</p>
      <div className="romaneios-contagem"><span role="status">{dados.inicio}–{dados.fim} de {dados.total} romaneios</span><label>Por página<select value={porPagina} onChange={e => {setPorPagina(Number(e.target.value));setPagina(1);}}><option value={5}>5</option><option value={10}>10</option><option value={20}>20</option></select></label></div>
      <div className="romaneios-resultados">{dados.itens.map(({ venda, saida }) => <article className="romaneio-resultado" key={`${venda.id}-${saida.id}`}>
        <div className="romaneio-linha">
          <div className="romaneio-numero"><strong>{saida.id}</strong><span>{saida.data_entrega?.slice(0, 10).split("-").reverse().join("/") || "Sem data"}</span></div>
          <div className="romaneio-comprador"><strong>{saida.destino || venda.cliente_nome || "Comprador não informado"}</strong><span>{saida.placa || "Sem placa"} · {formatarNumero(saida.quantidade_kg)} kg</span></div>
          <ComprovanteLancamento duasVias dados={dadosRomaneioVenda(venda, saida)} rotulo={`Imprimir ${saida.id}`} tipoDocumento="romaneio" downloadRomaneio={{vendaId:venda.id,saidaId:saida.id}}/>
        </div>
        {(venda.excluida_em || saida.cancelado_em) && <strong className="romaneio-historico">Cancelado/excluído — histórico</strong>}
        <details className="romaneio-dados"><summary>Detalhes do romaneio {saida.id}</summary><p>Venda #{venda.id} · {venda.propriedade_nome || "Sem propriedade"} · CAD/PRO {venda.cad_pro_codigo} · {venda.cultura} {venda.safra}</p><p>Motorista: {saida.motorista || "Não informado"} · Nota produtor: {saida.nota_produtor || "—"}</p></details>
      </article>)}</div>
      {!dados.total && <p>Nenhum romaneio encontrado. Confira a busca e as datas ou inclua o histórico.</p>}
      {dados.paginas > 1 && <nav className="acoes" aria-label="Páginas de romaneios"><button type="button" className="secundario" disabled={dados.pagina===1} onClick={() => setPagina(dados.pagina - 1)}>Anteriores</button><span>Página {dados.pagina} de {dados.paginas}</span><button type="button" className="secundario" disabled={dados.pagina===dados.paginas} onClick={() => setPagina(dados.pagina + 1)}>Próximos</button></nav>}
    </>}
  </section>;
}
