import { FormEvent, useEffect, useState } from "react";
import { FiltrosRelatorio, ItemRelatorio, obterOpcoesRelatorio, obterRelatorioOperacional, OpcoesRelatorio, PosicaoRelatorio, RelatorioOperacional, SecaoRelatorio, TotaisProducaoPropriedade } from "../../api/relatorios";
import { Propriedade } from "../../api/propriedades";
import { areaEmAlqueires, HECTARES_POR_ALQUEIRE_PAULISTA } from "../../utils/areas";

const SECOES: { id: SecaoRelatorio; nome: string }[] = [
  { id: "saldos", nome: "Estoque e saldos" }, { id: "producao", nome: "Produção" },
  { id: "produtividade", nome: "Produção por propriedade" },
  { id: "producao_propriedade", nome: "Produção por Propriedade/CAD-PRO" },
  { id: "motoristas", nome: "Transporte por motorista" },
  { id: "reservas", nome: "Reservas" }, { id: "vendas", nome: "Vendas" },
  { id: "entregas", nome: "Entregas" }, { id: "movimentacoes", nome: "Histórico" },
  { id: "rastreabilidade", nome: "Rastreabilidade" },
];
const vazio: FiltrosRelatorio = { secao: "saldos", pagina: 1, por_pagina: 25 };
const formatoDecimal = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
const formatoInteiro = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
function numeroRelatorio(valor: unknown, inteiro = false) {
  if ((typeof valor !== "string" && typeof valor !== "number") || String(valor).trim() === "") return "—";
  const numero = Number(valor);
  return Number.isFinite(numero) ? (inteiro ? formatoInteiro : formatoDecimal).format(numero) : "—";
}
const kg = (valor: unknown) => `${numeroRelatorio(valor)} kg`;
const texto = (valor: unknown) => valor === null || valor === undefined || valor === "" ? "—" : String(valor);

const COLUNAS_PRODUCAO = [
  ["propriedade", "Propriedade"], ["proprietario", "Proprietário"], ["cad_pro", "CAD/PRO"],
  ["cultura", "Cultura / safra"], ["area", "Área em alqueires"], ["kg", "Quantidade total (kg)"],
  ["sacas", "Sacas de 60 kg"], ["outros", "Outros locais"], ["semente", "Destinada a semente"],
  ["media", "Média por alqueire"], ["armazenagens", "Armazenagens"],
] as const;
type ColunaProducao = typeof COLUNAS_PRODUCAO[number][0];
const COLUNAS_PADRAO = COLUNAS_PRODUCAO.map(([id]) => id);

function Posicao({ item }: { item?: PosicaoRelatorio }) {
  return item ? <span>{item.cad_pro_codigo} · {item.propriedade_nome} · {item.cultura} · {item.safra} · {item.classificacao_codigo} · {item.armazem_nome}</span> : null;
}

function objeto(valor: unknown): Record<string, unknown> {
  return valor !== null && typeof valor === "object" && !Array.isArray(valor)
    ? valor as Record<string, unknown>
    : {};
}

function SnapshotSaldo({ titulo, valor }: { titulo: string; valor: unknown }) {
  const snapshot = objeto(valor);
  const possuiSaldo = ["saldo_fisico_kg", "saldo_comprometido_kg", "saldo_disponivel_kg"]
    .some((campo) => snapshot[campo] !== null && snapshot[campo] !== undefined);
  return <div className="snapshot-rastreabilidade"><strong>{titulo}</strong>{possuiSaldo
    ? <span>Físico {kg(snapshot.saldo_fisico_kg)} · comprometido {kg(snapshot.saldo_comprometido_kg)} · disponível {kg(snapshot.saldo_disponivel_kg)}</span>
    : <span>—</span>}</div>;
}

function Rastreabilidade({ itens }: { itens: ItemRelatorio[] }) {
  return <div className="rastreabilidade-lista">{itens.map((item) => {
    const posicao = item.posicao as PosicaoRelatorio | undefined;
    const possuiCarga = item.carga_colhida !== null && item.carga_colhida !== undefined && item.carga_colhida !== "";
    return <article className="card rastreabilidade-item" key={`rastreabilidade-${item.id}`}>
      <header className="rastreabilidade-topo"><div><span className="kicker">Movimentação #{item.id}</span><h3>{texto(item.operacao)}</h3></div><span>{texto(item.data)}</span></header>
      <div className="rastreabilidade-grade">
        <section><span>Origem</span><strong>{texto(item.origem_tipo)} · #{texto(item.origem)}</strong><small>Referência externa: {texto(item.referencia_externa)}</small></section>
        <section><span>Efeito no ledger</span><strong>Físico {kg(item.delta_fisico_kg)} · comprometido {kg(item.delta_comprometido_kg)}</strong><small>Quantidade registrada: {kg(item.quantidade_kg)}</small></section>
        <section><span>Lote operacional</span><strong>{texto(item.lote_operacional_codigo)}</strong><small>Identificador #{texto(item.lote_operacional)}</small></section>
        <section className="rastreabilidade-contexto"><span>Contexto oficial</span><strong><Posicao item={posicao} /></strong></section>
        <section className="rastreabilidade-snapshots"><span>Saldos auditáveis</span><div><SnapshotSaldo titulo="Antes" valor={item.snapshot_anterior} /><SnapshotSaldo titulo="Depois" valor={item.snapshot_posterior} /></div></section>
        <section><span>Carga colhida</span><strong>{possuiCarga ? `Carga #${texto(item.carga_colhida)}` : "Sem carga vinculada"}</strong><small>Placa: {possuiCarga ? texto(item.placa_carga) : "—"}</small></section>
      </div>
    </article>;
  })}</div>;
}

function TabelaProducaoPropriedade({ itens, totais, colunas }: { itens: ItemRelatorio[]; totais?: TotaisProducaoPropriedade; colunas: ColunaProducao[] }) {
  const exibe = (coluna: ColunaProducao) => colunas.includes(coluna);
  const celulas = (item: ItemRelatorio) => <>
    {exibe("propriedade") && <td>{texto(item.propriedade_nome)}</td>}
    {exibe("proprietario") && <td>{texto(item.proprietario)}</td>}
    {exibe("cad_pro") && <td>{texto(item.cad_pro_codigo)}</td>}
    {exibe("cultura") && <td>{texto(item.cultura)}<small>{texto(item.safra)}</small></td>}
    {exibe("area") && <td>{numeroRelatorio(item.area_alqueires)} alq.</td>}
    {exibe("kg") && <td>{kg(item.quantidade_kg)}</td>}
    {exibe("sacas") && <td>{numeroRelatorio(item.sacas_60kg)} sc</td>}
    {exibe("outros") && <td>{kg(item.outros_locais_kg)}</td>}
    {exibe("semente") && <td>{kg(item.semente_kg)}<small>{numeroRelatorio(item.semente_sacas_60kg)} sc</small></td>}
    {exibe("media") && <td>{numeroRelatorio(item.media_sacas_alqueire)} sc/alq.</td>}
    {exibe("armazenagens") && <td>{Array.isArray(item.armazenagens) ? item.armazenagens.join(", ") : "—"}</td>}
  </>;
  return <div className="tabela-responsiva"><table className="tabela-relatorio tabela-controle producao-propriedade-cadpro"><thead><tr>{COLUNAS_PRODUCAO.filter(([id]) => exibe(id)).map(([id, nome]) => <th key={id}>{nome}</th>)}</tr></thead><tbody>{itens.map(item => <tr key={`producao-propriedade-${item.id}`}>{celulas(item)}</tr>)}</tbody>{totais && <tfoot><tr>
    {exibe("propriedade") && <td><strong>TOTAL</strong></td>}{exibe("proprietario") && <td>—</td>}{exibe("cad_pro") && <td>—</td>}{exibe("cultura") && <td>—</td>}
    {exibe("area") && <td><strong>{numeroRelatorio(totais.area_alqueires)} alq.</strong></td>}{exibe("kg") && <td><strong>{kg(totais.quantidade_kg)}</strong></td>}{exibe("sacas") && <td><strong>{numeroRelatorio(totais.sacas_60kg)} sc</strong></td>}{exibe("outros") && <td><strong>{kg(totais.outros_locais_kg)}</strong></td>}{exibe("semente") && <td><strong>{kg(totais.semente_kg)}</strong><small>{numeroRelatorio(totais.semente_sacas_60kg)} sc</small></td>}{exibe("media") && <td><strong>{numeroRelatorio(totais.media_sacas_alqueire)} sc/alq.</strong></td>}{exibe("armazenagens") && <td>—</td>}
  </tr></tfoot>}</table></div>;
}

export function TabelaRelatorio({ secao, itens, totaisProducao, colunasProducao = COLUNAS_PADRAO }: { secao: SecaoRelatorio; itens: ItemRelatorio[]; totaisProducao?: TotaisProducaoPropriedade; colunasProducao?: ColunaProducao[] }) {
  if (secao === "rastreabilidade" && itens.length) return <Rastreabilidade itens={itens} />;
  if (!itens.length) return <div className="card vazio">Nenhum registro encontrado para os filtros informados.</div>;
  if (secao === "producao_propriedade") return <TabelaProducaoPropriedade itens={itens} totais={totaisProducao} colunas={colunasProducao} />;
  if (secao === "produtividade") return <div className="tabela-responsiva"><table className="tabela-relatorio tabela-controle"><thead><tr><th>Data</th><th>Proprietário / propriedade</th><th>CAD/PRO</th><th>Grão / safra</th><th>Área</th><th>Produção rateada</th><th>Média</th><th>Semente</th><th>Silo</th><th>Placa / motorista</th></tr></thead><tbody>{itens.map((item) => <tr key={`produtividade-${item.id}`}><td>{texto(item.data)}</td><td>{texto(item.proprietario)}<small>{texto(item.propriedade_nome)}</small></td><td>{texto(item.cad_pro_codigo)}</td><td>{texto(item.cultura)}<small>{texto(item.safra)}</small></td><td>{areaEmAlqueires(item.area_hectares as string)} alq.</td><td>{kg(item.quantidade_kg)}<small>{numeroRelatorio(item.sacas_60kg)} sc</small></td><td>{numeroRelatorio(Number(item.media_sacas_hectare) * HECTARES_POR_ALQUEIRE_PAULISTA)} sc/alq.</td><td>{item.destinado_semente ? `${numeroRelatorio(item.semente_sacas_60kg)} sc` : "Não"}</td><td>{texto(item.armazem_nome)}</td><td>{texto(item.placa)}<small>{texto(item.motorista)}</small></td></tr>)}</tbody></table></div>;
  if (secao === "motoristas") return <div className="tabela-responsiva"><table className="tabela-relatorio"><thead><tr><th>Motorista</th><th>Placas</th><th>Cargas</th><th>Quantidade transportada</th><th>Sementes</th><th>Silos</th></tr></thead><tbody>{itens.map((item) => <tr key={`motorista-${item.id}`}><td><strong>{texto(item.motorista)}</strong></td><td>{Array.isArray(item.placas) ? item.placas.join(", ") || "—" : "—"}</td><td>{numeroRelatorio(item.quantidade_cargas, true)}</td><td>{kg(item.quantidade_kg)}<small>{numeroRelatorio(item.sacas_60kg)} sc</small></td><td>{kg(item.semente_kg)}</td><td>{Array.isArray(item.armazens) ? item.armazens.join(", ") : "—"}</td></tr>)}</tbody></table></div>;
  return <div className="tabela-responsiva"><table className="tabela-relatorio"><thead><tr><th>Referência</th><th>Contexto oficial</th><th>Quantidade</th><th>Situação / data</th></tr></thead><tbody>{itens.map((item) => {
    const posicao = (secao === "saldos" ? item : item.posicao) as PosicaoRelatorio | undefined;
    const referencia = item.numero_contrato === "" ? `Sem contrato · #${item.id}` : item.numero_contrato ?? item.lote_operacional_codigo ?? item.referencia_externa ?? `#${item.id}`;
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
  const [colunasProducao, setColunasProducao] = useState<ColunaProducao[]>(COLUNAS_PADRAO);
  async function carregar(proximos = filtros) { setCarregando(true); setErro(""); try { setDados(await obterRelatorioOperacional(proximos)); } catch { setErro("Não foi possível carregar os relatórios operacionais."); } finally { setCarregando(false); } }
  useEffect(() => { void obterOpcoesRelatorio().then(setOpcoes).catch(() => setErro("Não foi possível carregar as opções dos relatórios.")); void carregar(vazio); }, []);
  function alterar(campo: keyof FiltrosRelatorio, valor: string | number) { setFiltros((atual) => ({ ...atual, [campo]: valor || undefined, pagina: 1 })); }
  function trocarSecao(secao: SecaoRelatorio) { const proximos = { ...filtros, secao, pagina: 1, por_pagina: secao === "producao_propriedade" ? 100 : 25 }; setFiltros(proximos); void carregar(proximos); }
  function paginar(pagina: number) { const proximos = { ...filtros, pagina }; setFiltros(proximos); void carregar(proximos); }
  return <section className="modulo-relatorios-operacionais">
    <div className="card cabecalho-relatorio"><div><span className="kicker">Consulta oficial somente leitura</span><h2>Relatórios operacionais</h2><p>Produção, saldos, reservas e fluxo comercial consolidados diretamente do ledger.</p></div><span className="selo-leitura">Somente leitura</span></div>
    <form className="card filtros-operacionais" onSubmit={(e: FormEvent) => { e.preventDefault(); void carregar({ ...filtros, pagina: 1 }); }}>
      <label>Proprietário<select value={filtros.proprietario ?? ""} onChange={(e) => alterar("proprietario", e.target.value)}><option value="">Todos</option>{opcoes?.proprietarios.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>CAD/PRO<select value={filtros.cad_pro ?? ""} onChange={(e) => alterar("cad_pro", e.target.value)}><option value="">Todos</option>{opcoes?.cadpros.map((item) => <option key={item.id} value={item.id}>{item.codigo} — {item.descricao}</option>)}</select></label>
      <label>Propriedade<select value={filtros.propriedade ?? ""} onChange={(e) => alterar("propriedade", e.target.value)}><option value="">Todas</option>{propriedades.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
      <label>Cultura<select value={filtros.cultura ?? ""} onChange={(e) => alterar("cultura", e.target.value)}><option value="">Todas</option>{opcoes?.culturas.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>Safra<select value={filtros.safra ?? ""} onChange={(e) => alterar("safra", e.target.value)}><option value="">Todas</option>{opcoes?.safras.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>Classificação<select value={filtros.classificacao_codigo ?? ""} onChange={(e) => alterar("classificacao_codigo", e.target.value)}><option value="">Todas</option>{opcoes?.classificacoes.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>Armazenagem<select value={filtros.armazem ?? ""} onChange={(e) => alterar("armazem", e.target.value)}><option value="">Todas</option>{opcoes?.armazens.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
      <label>Destinação<select value={filtros.destinado_semente ?? ""} onChange={(e) => alterar("destinado_semente", e.target.value)}><option value="">Todas</option><option value="true">Semente</option><option value="false">Grão comercial</option></select></label>
      <label>Motorista<select value={filtros.motorista ?? ""} onChange={(e) => alterar("motorista", e.target.value)}><option value="">Todos</option>{opcoes?.motoristas.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>Placa<select value={filtros.placa ?? ""} onChange={(e) => alterar("placa", e.target.value)}><option value="">Todas</option>{opcoes?.placas.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>Contrato<select value={filtros.numero_contrato ?? ""} onChange={(e) => alterar("numero_contrato", e.target.value)}><option value="">Todos</option>{opcoes?.contratos.filter(Boolean).map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>Comprador<select value={filtros.comprador ?? ""} onChange={(e) => alterar("comprador", e.target.value)}><option value="">Todos</option>{opcoes?.compradores.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>De<input type="date" value={filtros.data_inicio ?? ""} onChange={(e) => alterar("data_inicio", e.target.value)} /></label><label>Até<input type="date" value={filtros.data_fim ?? ""} onChange={(e) => alterar("data_fim", e.target.value)} /></label>
      <div className="acoes-filtros"><button disabled={carregando}>Aplicar filtros</button><button type="button" className="secundario" onClick={() => { setFiltros(vazio); void carregar(vazio); }}>Limpar</button></div>
    </form>
    {erro && <p className="erro card" role="alert">{erro}</p>}
    {carregando && !dados ? <div className="card vazio">Carregando relatórios operacionais...</div> : null}
    {dados ? <><section className="resumos-operacionais">
      <article className="card"><span>Saldo físico</span><strong>{kg(dados.totais.saldo_fisico_kg)}</strong></article><article className="card"><span>Comprometido</span><strong>{kg(dados.totais.saldo_comprometido_kg)}</strong></article><article className="card"><span>Disponível</span><strong>{kg(dados.totais.saldo_disponivel_kg)}</strong></article><article className="card"><span>Produção rateada</span><strong>{kg(dados.totais.producao_rateada_kg)}</strong></article><article className="card"><span>Destinada a semente</span><strong>{kg(dados.totais.semente_kg)}</strong></article><article className="card"><span>Entregas no período</span><strong>{kg(dados.totais.entregas_kg)}</strong></article>
    </section>{dados.secao === "saldos" && dados.por_cad_pro.length ? <section className="resumos-operacionais saldos-por-cadpro">{dados.por_cad_pro.map((item) => <article className="card" key={String(item.cad_pro)}><span>Saldo CAD/PRO {texto(item.cad_pro_nome)}</span><strong>{kg(item.saldo_disponivel_kg)}</strong><small>Físico {kg(item.saldo_fisico_kg)} · comprometido {kg(item.saldo_comprometido_kg)}</small></article>)}</section> : null}<nav className="abas-relatorios" aria-label="Seções dos relatórios">{SECOES.map((item) => <button key={item.id} className={filtros.secao === item.id ? "" : "secundario"} onClick={() => trocarSecao(item.id)}>{item.nome}</button>)}</nav>{dados.secao === "producao_propriedade" && <section className="card seletor-colunas nao-imprimir"><h3>Informações da impressão</h3><p>Marque as colunas que devem aparecer na tela e na impressão.</p><div>{COLUNAS_PRODUCAO.map(([id, nome]) => <label key={id}><input type="checkbox" checked={colunasProducao.includes(id)} onChange={e => setColunasProducao(atuais => e.target.checked ? [...atuais, id] : atuais.filter(item => item !== id))} /> {nome}</label>)}</div></section>}<h2 className="somente-impressao">{SECOES.find(item => item.id === dados.secao)?.nome}</h2><div className={carregando ? "conteudo-atualizando" : ""}><TabelaRelatorio secao={dados.secao} itens={dados.dados.resultados} totaisProducao={dados.totais_producao_propriedade} colunasProducao={colunasProducao} /></div><div className="paginacao"><button className="secundario" disabled={carregando || dados.dados.pagina <= 1} onClick={() => paginar(dados.dados.pagina - 1)}>Anterior</button><span>Página {dados.dados.pagina} de {Math.max(1, dados.dados.total_paginas)} · {dados.dados.total} registros</span><button className="secundario" disabled={carregando || dados.dados.pagina >= dados.dados.total_paginas} onClick={() => paginar(dados.dados.pagina + 1)}>Próxima</button></div><p className="kicker">Posição autoritativa por CAD/PRO + cultura + safra + classificação + armazenagem · gerado em {new Date(dados.gerado_em).toLocaleString("pt-BR")}</p></> : null}
  </section>;
}
