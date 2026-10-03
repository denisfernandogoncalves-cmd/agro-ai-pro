import { baixarArquivo, erroArquivo } from "../../api/arquivos";
import { BotaoAcao } from "../../components/AcoesContext";
import { useEntradaPainel } from "../../components/AcoesContext";
import FiltrosFavoritos from "../../components/FiltrosFavoritos";
import { FormEvent, useEffect, useRef, useState } from "react";
import { formatarData } from "../../utils/datas";
import { FiltrosRelatorio, ItemRelatorio, obterOpcoesRelatorio, obterRelatorioOperacional, OpcoesRelatorio, PosicaoRelatorio, RelatorioOperacional, SecaoRelatorio, TotaisProducaoPropriedade } from "../../api/relatorios";
import { Propriedade, rotuloPropriedade } from "../../api/propriedades";
import { areaEmAlqueires, HECTARES_POR_ALQUEIRE_PAULISTA } from "../../utils/areas";
import SeletorColunasImpressao, { useColunasImpressao } from "../../components/SeletorColunasImpressao";

const SECOES: { id: SecaoRelatorio; nome: string }[] = [
  { id: "estrutura", nome: "Estrutura rural" },
  { id: "saldos", nome: "Estoque e saldos" }, { id: "producao", nome: "Produção" },
  { id: "produtividade", nome: "Produção detalhada por carga" },
  { id: "producao_propriedade", nome: "Produção por Propriedade/CAD-PRO" },
  { id: "motoristas", nome: "Transporte por motorista" },
  { id: "reservas", nome: "Reservas" }, { id: "vendas", nome: "Vendas" },
  { id: "entregas", nome: "Entregas" }, { id: "movimentacoes", nome: "Histórico" },
  { id: "rastreabilidade", nome: "Rastreabilidade" },
  { id: "financeiro", nome: "Financeiro" },
  { id: "estoque_insumos", nome: "Estoque de insumos" },
  { id: "operacoes_agricolas", nome: "Operações agrícolas" },
  { id: "maquinas", nome: "Máquinas e custos" },
  { id: "clima", nome: "Clima das propriedades" },
  { id: "mercado", nome: "Mercado e Corn Belt" },
  { id: "importacoes", nome: "Importações" },
];
const GRUPOS_RELATORIOS: { nome: string; secoes: SecaoRelatorio[] }[] = [
  { nome: "Gestão rural", secoes: ["estrutura", "financeiro", "estoque_insumos", "operacoes_agricolas", "maquinas"] },
  { nome: "Produção e comercial", secoes: ["saldos", "producao", "produtividade", "producao_propriedade", "motoristas", "reservas", "vendas", "entregas", "movimentacoes", "rastreabilidade"] },
  { nome: "Inteligência e auditoria", secoes: ["clima", "mercado", "importacoes"] },
];
const SECOES_GRAOS = new Set<SecaoRelatorio>(["saldos", "producao", "produtividade", "producao_propriedade", "motoristas", "reservas", "vendas", "entregas", "movimentacoes", "rastreabilidade"]);
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
const moeda = (valor: unknown) => Number(valor || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const simNao = (valor: unknown) => valor ? "Sim" : "Não";

const COLUNAS_PRODUCAO = [
  ["propriedade", "Propriedade"], ["proprietario", "Proprietário"], ["cad_pro", "CAD/PRO"],
  ["cultura", "Cultura / safra"], ["area", "Área em alqueires"], ["kg", "Quantidade total (kg)"],
  ["sacas", "Sacas de 60 kg"], ["outros", "Outros locais"], ["semente", "Destinada a semente"],
  ["media", "Média por alqueire"], ["armazenagens", "Armazenagens"],
] as const;
type ColunaProducao = typeof COLUNAS_PRODUCAO[number][0];
const COLUNAS_PADRAO = COLUNAS_PRODUCAO.map(([id]) => id);
const CHAVE_COLUNAS_PRODUCAO = "agro-ai-pro:impressao:producao-propriedade";

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
      <header className="rastreabilidade-topo"><div><span className="kicker">Movimentação #{item.id}</span><h3>{texto(item.operacao)}</h3></div><span>{formatarData(texto(item.data))}</span></header>
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
  const visiveis = COLUNAS_PRODUCAO.filter(([id]) => exibe(id));
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
  const totalDaColuna = (id: ColunaProducao, indice: number) => {
    const rotulo = indice === 0 ? <small>Total geral filtrado</small> : null;
    if (id === "area") return <td key={id}><strong>{numeroRelatorio(totais?.area_alqueires)} alq.</strong>{rotulo}</td>;
    if (id === "kg") return <td key={id}><strong>{kg(totais?.quantidade_kg)}</strong>{rotulo}</td>;
    if (id === "sacas") return <td key={id}><strong>{numeroRelatorio(totais?.sacas_60kg)} sc</strong>{rotulo}</td>;
    if (id === "outros") return <td key={id}><strong>{kg(totais?.outros_locais_kg)}</strong>{rotulo}</td>;
    if (id === "semente") return <td key={id}><strong>{kg(totais?.semente_kg)}</strong><small>{numeroRelatorio(totais?.semente_sacas_60kg)} sc</small>{rotulo}</td>;
    if (id === "media") return <td key={id}><strong>{numeroRelatorio(totais?.media_sacas_alqueire)} sc/alq.</strong>{rotulo}</td>;
    return <td key={id}><strong>{indice === 0 ? "TOTAL GERAL" : "—"}</strong></td>;
  };
  return <div className="tabela-responsiva"><table className="tabela-relatorio tabela-controle producao-propriedade-cadpro"><caption>Produção agrupada e totais de todos os registros filtrados</caption><thead><tr>{visiveis.map(([id, nome]) => <th key={id}>{nome}</th>)}</tr></thead><tbody>{itens.map(item => <tr key={`producao-propriedade-${item.id}`}>{celulas(item)}</tr>)}</tbody>{totais && <tfoot><tr>{visiveis.map(([id], indice) => totalDaColuna(id, indice))}</tr></tfoot>}</table></div>;
}

export function TabelaRelatorio({ secao, itens, totaisProducao, colunasProducao = COLUNAS_PADRAO }: { secao: SecaoRelatorio; itens: ItemRelatorio[]; totaisProducao?: TotaisProducaoPropriedade; colunasProducao?: ColunaProducao[] }) {
  if (secao === "rastreabilidade" && itens.length) return <Rastreabilidade itens={itens} />;
  if (!itens.length) return <div className="card vazio">Nenhum registro encontrado para os filtros informados.</div>;
  if (secao === "producao_propriedade") return <TabelaProducaoPropriedade itens={itens} totais={totaisProducao} colunas={colunasProducao} />;
  if (secao === "produtividade") return <div className="tabela-responsiva"><table className="tabela-relatorio tabela-controle"><thead><tr><th>Data</th><th>Proprietário / propriedade</th><th>CAD/PRO</th><th>Grão / safra</th><th>Área</th><th>Produção rateada</th><th>Média</th><th>Semente</th><th>Silo</th><th>Placa / motorista</th></tr></thead><tbody>{itens.map((item) => <tr key={`produtividade-${item.id}`}><td>{formatarData(texto(item.data))}</td><td>{texto(item.proprietario)}<small>{texto(item.propriedade_nome)}</small></td><td>{texto(item.cad_pro_codigo)}</td><td>{texto(item.cultura)}<small>{texto(item.safra)}</small></td><td>{areaEmAlqueires(item.area_hectares as string)} alq.</td><td>{kg(item.quantidade_kg)}<small>{numeroRelatorio(item.sacas_60kg)} sc</small></td><td>{numeroRelatorio(Number(item.media_sacas_hectare) * HECTARES_POR_ALQUEIRE_PAULISTA)} sc/alq.</td><td>{item.destinado_semente ? `${numeroRelatorio(item.semente_sacas_60kg)} sc` : "Não"}</td><td>{texto(item.armazem_nome)}</td><td>{texto(item.placa)}<small>{texto(item.motorista)}</small></td></tr>)}</tbody></table></div>;
  if (secao === "motoristas") return <div className="tabela-responsiva"><table className="tabela-relatorio"><thead><tr><th>Motorista</th><th>Placas</th><th>Cargas</th><th>Quantidade transportada</th><th>Sementes</th><th>Silos</th></tr></thead><tbody>{itens.map((item) => <tr key={`motorista-${item.id}`}><td><strong>{texto(item.motorista)}</strong></td><td>{Array.isArray(item.placas) ? item.placas.join(", ") || "—" : "—"}</td><td>{numeroRelatorio(item.quantidade_cargas, true)}</td><td>{kg(item.quantidade_kg)}<small>{numeroRelatorio(item.sacas_60kg)} sc</small></td><td>{kg(item.semente_kg)}</td><td>{Array.isArray(item.armazens) ? item.armazens.join(", ") : "—"}</td></tr>)}</tbody></table></div>;
  if (secao === "estrutura") return <div className="tabela-responsiva"><table className="tabela-relatorio"><thead><tr><th>Proprietário / propriedade</th><th>Localização</th><th>Área declarada</th><th>Área em talhões</th><th>Área disponível</th><th>Talhões</th><th>Culturas / safras</th><th>Mapa</th></tr></thead><tbody>{itens.map((item) => <tr key={`estrutura-${item.id}`}><td><strong>{texto(item.proprietario)}</strong><small>{texto(item.propriedade_nome)}</small></td><td>{texto(item.localizacao)}</td><td>{numeroRelatorio(item.area_alqueires)} alq.</td><td>{numeroRelatorio(item.area_talhoes_alqueires)} alq.</td><td>{numeroRelatorio(item.area_disponivel_alqueires)} alq.</td><td>{numeroRelatorio(item.quantidade_talhoes, true)}</td><td>{Array.isArray(item.culturas) ? item.culturas.join(", ") || "—" : "—"}<small>{Array.isArray(item.safras) ? item.safras.join(", ") || "—" : "—"}</small></td><td>{simNao(item.possui_mapa)}</td></tr>)}</tbody></table></div>;
  if (secao === "financeiro") return <div className="tabela-responsiva"><table className="tabela-relatorio"><thead><tr><th>Tipo / descrição</th><th>Categoria / parceiro</th><th>Propriedade / safra</th><th>Emissão</th><th>Vencimento</th><th>Status</th><th>Valor</th><th>Liquidado</th></tr></thead><tbody>{itens.map((item) => <tr key={`financeiro-${item.id}`}><td><strong>{texto(item.tipo)}</strong><small>{texto(item.descricao)}</small></td><td>{texto(item.categoria)}<small>{texto(item.parceiro)}</small></td><td>{texto(item.propriedade_nome)}<small>{texto(item.safra)}</small></td><td>{formatarData(texto(item.data_emissao))}</td><td>{formatarData(texto(item.data_vencimento))}</td><td>{texto(item.status)}{item.atrasado ? <small>Em atraso</small> : null}</td><td>{moeda(item.valor)}</td><td>{moeda(item.valor_liquidado)}</td></tr>)}</tbody></table></div>;
  if (secao === "estoque_insumos") return <div className="tabela-responsiva"><table className="tabela-relatorio"><thead><tr><th>Produto</th><th>Lote</th><th>Local / propriedade</th><th>Validade</th><th>Saldo</th><th>Mínimo</th><th>Situação</th></tr></thead><tbody>{itens.map((item) => <tr key={`estoque-${item.id}`}><td><strong>{texto(item.produto)}</strong><small>{texto(item.categoria)}</small></td><td>{texto(item.lote)}</td><td>{texto(item.local)}<small>{texto(item.propriedade_nome)}</small></td><td>{formatarData(texto(item.data_validade))}</td><td>{numeroRelatorio(item.saldo)} {texto(item.unidade)}</td><td>{numeroRelatorio(item.estoque_minimo)} {texto(item.unidade)}</td><td>{item.vencido ? "Vencido" : item.abaixo_minimo ? "Abaixo do mínimo" : item.ativo ? "Regular" : "Inativo"}</td></tr>)}</tbody></table></div>;
  if (secao === "operacoes_agricolas") return <div className="tabela-responsiva"><table className="tabela-relatorio"><thead><tr><th>Operação</th><th>Propriedade / talhão</th><th>Cultura / safra</th><th>Planejamento</th><th>Status</th><th>Área</th><th>Responsável</th><th>Custo estimado</th><th>Custo realizado</th></tr></thead><tbody>{itens.map((item) => <tr key={`operacao-${item.id}`}><td><strong>{texto(item.tipo)}</strong><small>{texto(item.descricao)}</small></td><td>{texto(item.propriedade_nome)}<small>{texto(item.talhao)}</small></td><td>{texto(item.cultura)}<small>{texto(item.safra)}</small></td><td>{formatarData(texto(item.data_planejada))}<small>{formatarData(texto(item.data_inicio))} → {formatarData(texto(item.data_conclusao))}</small></td><td>{texto(item.status)}</td><td>{numeroRelatorio(item.area_alqueires)} alq.</td><td>{texto(item.responsavel)}</td><td>{moeda(item.custo_estimado)}</td><td>{moeda(item.custo_realizado)}</td></tr>)}</tbody></table></div>;
  if (secao === "maquinas") return <div className="tabela-responsiva"><table className="tabela-relatorio"><thead><tr><th>Máquina</th><th>Tipo / modelo</th><th>Propriedade</th><th>Status</th><th>Horímetro</th><th>Horas trabalhadas</th><th>Combustível</th><th>Custo combustível</th><th>Manutenções / custo</th></tr></thead><tbody>{itens.map((item) => <tr key={`maquina-${item.id}`}><td><strong>{texto(item.identificacao)}</strong><small>{texto(item.ano)}</small></td><td>{texto(item.tipo)}<small>{texto(item.marca_modelo)}</small></td><td>{texto(item.propriedade_nome)}</td><td>{texto(item.status)}</td><td>{numeroRelatorio(item.horimetro_atual)} h</td><td>{numeroRelatorio(item.horas_trabalhadas)} h</td><td>{numeroRelatorio(item.litros)} L</td><td>{moeda(item.custo_combustivel)}</td><td>{numeroRelatorio(item.manutencoes_pendentes, true)} pendentes<small>{moeda(item.custo_manutencoes)}</small></td></tr>)}</tbody></table></div>;
  if (secao === "clima") return <div className="tabela-responsiva"><table className="tabela-relatorio"><thead><tr><th>Data / propriedade</th><th>Condição</th><th>Temperatura</th><th>Chuva</th><th>Umidade</th><th>Vento</th><th>Alerta</th><th>Fonte</th></tr></thead><tbody>{itens.map((item) => <tr key={`clima-${item.id}`}><td><strong>{formatarData(texto(item.data))}</strong><small>{texto(item.propriedade_nome)}</small></td><td>{texto(item.condicao)}</td><td>{numeroRelatorio(item.temperatura_min)} a {numeroRelatorio(item.temperatura_max)} °C</td><td>{numeroRelatorio(item.chuva_mm)} mm<small>{numeroRelatorio(item.probabilidade_chuva, true)}%</small></td><td>{numeroRelatorio(item.umidade, true)}%</td><td>{numeroRelatorio(item.vento_kmh)} km/h</td><td>{texto(item.alerta)}</td><td>{texto(item.fonte)}</td></tr>)}</tbody></table></div>;
  if (secao === "mercado") return <div className="tabela-responsiva"><table className="tabela-relatorio"><thead><tr><th>Tipo</th><th>Referência</th><th>Data</th><th>Valor / condição</th><th>Unidade / chuva</th><th>Detalhe / alerta</th><th>Fonte</th></tr></thead><tbody>{itens.map((item) => <tr key={`mercado-${item.id}`}><td>{texto(item.tipo_registro)}</td><td><strong>{texto(item.referencia)}</strong></td><td>{formatarData(texto(item.data))}</td><td>{texto(item.valor_principal)}</td><td>{texto(item.unidade)}</td><td>{texto(item.detalhe)}<small>{texto(item.alerta)}</small></td><td>{texto(item.fonte)}</td></tr>)}</tbody></table></div>;
  if (secao === "importacoes") return <div className="tabela-responsiva"><table className="tabela-relatorio"><thead><tr><th>Arquivo</th><th>Status</th><th>Planilhas</th><th>Linhas</th><th>Válidas</th><th>Advertências</th><th>Erros</th><th>Usuário / data</th><th>SHA-256</th></tr></thead><tbody>{itens.map((item) => <tr key={`importacao-${item.id}`}><td><strong>{texto(item.arquivo)}</strong><small>{numeroRelatorio(item.tamanho_bytes, true)} bytes</small></td><td>{texto(item.status)}</td><td>{numeroRelatorio(item.planilhas, true)}</td><td>{numeroRelatorio(item.linhas, true)}</td><td>{numeroRelatorio(item.validas, true)}</td><td>{numeroRelatorio(item.advertencias, true)}</td><td>{numeroRelatorio(item.erros, true)}</td><td>{texto(item.usuario)}<small>{texto(item.criado_em)}</small></td><td className="hash-relatorio">{texto(item.sha256)}</td></tr>)}</tbody></table></div>;
  return <div className="tabela-responsiva"><table className="tabela-relatorio"><thead><tr><th>Referência</th><th>Contexto oficial</th><th>Quantidade</th><th>Situação / data</th></tr></thead><tbody>{itens.map((item) => {
    const posicao = (secao === "saldos" ? item : item.posicao) as PosicaoRelatorio | undefined;
    const referencia = item.numero_contrato === "" ? `Sem contrato · #${item.id}` : item.numero_contrato ?? item.lote_operacional_codigo ?? item.referencia_externa ?? `#${item.id}`;
    const quantidade = secao === "saldos" ? `Físico ${kg(item.saldo_fisico_kg)} · comprometido ${kg(item.saldo_comprometido_kg)} · disponível ${kg(item.saldo_disponivel_kg)}` : kg(item.quantidade_kg ?? item.saldo_reservado_kg);
    return <tr key={`${secao}-${item.id}`}><td><strong>{texto(referencia)}</strong>{item.cliente_nome ? <small>{texto(item.cliente_nome)}</small> : null}</td><td><Posicao item={posicao} /></td><td>{quantidade}</td><td>{texto(item.status ?? item.operacao)}<small>{formatarData(texto(item.data ?? item.data_contrato ?? item.criado_em))}</small></td></tr>;
  })}</tbody></table></div>;
}

export default function RelatoriosPage({ propriedades }: { propriedades: Propriedade[] }) {
  const [orientacao,setOrientacao] = useState<"retrato"|"paisagem">("retrato");
  const [densidade,setDensidade] = useState<"normal"|"compacta">("normal");
  const entradaPainel = useEntradaPainel("relatorios");
  const [filtros, setFiltros] = useState<FiltrosRelatorio>(vazio);
  const [dados, setDados] = useState<RelatorioOperacional | null>(null);
  const [opcoes, setOpcoes] = useState<OpcoesRelatorio | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [aplicados, setAplicados] = useState<FiltrosRelatorio>(vazio);
  const ultimaConsulta = useRef(0);
  const [exportando,setExportando]=useState(false);
  const travaExcel=useRef(false);
  async function exportarExcel(){if(travaExcel.current||!dados)return;travaExcel.current=true;setExportando(true);setErro("");try{await baixarArquivo("/relatorios/operacionais/exportar/",`relatorio-${dados.secao}.xlsx`,{...aplicados});}catch(falha){setErro(await erroArquivo(falha,"Não foi possível exportar o relatório."));}finally{travaExcel.current=false;setExportando(false);}}
  const { selecionadas: colunasProducao, setSelecionadas: setColunasProducao } = useColunasImpressao(
    CHAVE_COLUNAS_PRODUCAO,
    COLUNAS_PRODUCAO,
  );
  async function carregar(proximos = filtros) {
    if (proximos.data_inicio && proximos.data_fim && proximos.data_inicio > proximos.data_fim) { setErro("A data final deve ser igual ou posterior à inicial."); return; }
    const consulta = ++ultimaConsulta.current;
    setCarregando(true); setErro("");
    try {
      const resultado = await obterRelatorioOperacional(proximos);
      if (consulta !== ultimaConsulta.current) return;
      setDados(resultado); setAplicados({ ...proximos });
    } catch { if (consulta === ultimaConsulta.current) setErro("Não foi possível carregar os relatórios operacionais."); }
    finally { if (consulta === ultimaConsulta.current) setCarregando(false); }
  }
  useEffect(() => { void obterOpcoesRelatorio().then(setOpcoes).catch(() => setErro("Não foi possível carregar as opções dos relatórios.")); if (!entradaPainel) void carregar(vazio); }, []);
  function alterar(campo: keyof FiltrosRelatorio, valor: string | number) { setFiltros((atual) => ({ ...atual, [campo]: valor || undefined, pagina: 1 })); }
  function trocarSecao(secao: SecaoRelatorio) { const proximos = { ...filtros, secao, pagina: 1, por_pagina: secao === "producao_propriedade" ? 100 : 25 }; setFiltros(proximos); void carregar(proximos); }
  function paginar(pagina: number) { const proximos = { ...filtros, pagina }; setFiltros(proximos); void carregar(proximos); }
  return <section className="modulo-relatorios-operacionais">
      <style>{`@media print { @page relatorio {size: A4 ${orientacao==="retrato"?"portrait":"landscape"};} ${densidade==="compacta"?".tabela-relatorio td, .tabela-relatorio th {padding: 3px !important; font-size: 9px !important;}":""} }`}</style>
      <div className="card favoritos-campos nao-imprimir"><label>Orientação da impressão<select value={orientacao} onChange={e=>setOrientacao(e.target.value as "retrato"|"paisagem")}><option value="paisagem">Paisagem</option><option value="retrato">Retrato</option></select></label><label>Espaçamento<select value={densidade} onChange={e=>setDensidade(e.target.value as "normal"|"compacta")}><option value="normal">Normal</option><option value="compacta">Compacto</option></select></label><small>Salve um favorito para reutilizar filtros, colunas de produção e impressão.</small></div>
      <FiltrosFavoritos contexto="relatorios" configuracao={{colunas:colunasProducao,orientacao,densidade}} aplicarConfiguracao={config=>{setColunasProducao(config.colunas?.filter((c):c is ColunaProducao=>COLUNAS_PADRAO.includes(c as ColunaProducao))||COLUNAS_PADRAO);setOrientacao(config.orientacao==="paisagem"?"paisagem":"retrato");setDensidade(config.densidade==="compacta"?"compacta":"normal");}} filtros={filtros} aplicar={valores => {const proximos = {...vazio, ...valores}; setFiltros(proximos); void carregar(proximos);}} />
    <div className="card cabecalho-relatorio"><div><span className="kicker">Central oficial somente leitura</span><h2>Todos os relatórios</h2><p>Gestão rural, produção, comercial, financeiro, estoque, operações, máquinas, clima, mercado e auditoria em uma única aba.</p></div><div><span className="selo-leitura">Somente leitura</span><BotaoAcao acao="imprimir" type="button" disabled={carregando||exportando||!dados} onClick={()=>void exportarExcel()}>{exportando?"Gerando Excel…":"Exportar resultados em Excel"}</BotaoAcao><small>Todos os resultados dos filtros aplicados, incluindo outras páginas.</small></div></div>
    <form className="card filtros-operacionais" onSubmit={(e: FormEvent) => { e.preventDefault(); void carregar({ ...filtros, pagina: 1 }); }}>
      <label>Proprietário<select value={filtros.proprietario ?? ""} onChange={(e) => alterar("proprietario", e.target.value)}><option value="">Todos</option>{opcoes?.proprietarios.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>CAD/PRO<select value={filtros.cad_pro ?? ""} onChange={(e) => alterar("cad_pro", e.target.value)}><option value="">Todos</option>{opcoes?.cadpros.map((item) => <option key={item.id} value={item.id}>{item.codigo} — {item.descricao}</option>)}</select></label>
      <label>Propriedade<select value={filtros.propriedade ?? ""} onChange={(e) => alterar("propriedade", e.target.value)}><option value="">Todas</option>{propriedades.map((item) => <option key={item.id} value={item.id}>{rotuloPropriedade(item)}</option>)}</select></label>
      <label>Cultura<select value={filtros.cultura ?? ""} onChange={(e) => alterar("cultura", e.target.value)}><option value="">Todas</option>{opcoes?.culturas.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>Safra<select value={filtros.safra ?? ""} onChange={(e) => alterar("safra", e.target.value)}><option value="">Todas</option>{opcoes?.safras.map((item) => <option key={item}>{item}</option>)}</select></label>
      <details className="filtros-avancados"><summary>Mais filtros: armazenagem, transporte e comercial</summary><div className="filtros-avancados-campos">
      <label>Classificação<select value={filtros.classificacao_codigo ?? ""} onChange={(e) => alterar("classificacao_codigo", e.target.value)}><option value="">Todas</option>{opcoes?.classificacoes.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>Armazenagem<select value={filtros.armazem ?? ""} onChange={(e) => alterar("armazem", e.target.value)}><option value="">Todas</option>{opcoes?.armazens.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
      <label>Destinação<select value={filtros.destinado_semente ?? ""} onChange={(e) => alterar("destinado_semente", e.target.value)}><option value="">Todas</option><option value="true">Semente</option><option value="false">Grão comercial</option></select></label>
      <label>Motorista<select value={filtros.motorista ?? ""} onChange={(e) => alterar("motorista", e.target.value)}><option value="">Todos</option>{opcoes?.motoristas.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>Placa<select value={filtros.placa ?? ""} onChange={(e) => alterar("placa", e.target.value)}><option value="">Todas</option>{opcoes?.placas.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>Contrato<select value={filtros.numero_contrato ?? ""} onChange={(e) => alterar("numero_contrato", e.target.value)}><option value="">Todos</option>{opcoes?.contratos.filter(Boolean).map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>Comprador<select value={filtros.comprador ?? ""} onChange={(e) => alterar("comprador", e.target.value)}><option value="">Todos</option>{opcoes?.compradores.map((item) => <option key={item}>{item}</option>)}</select></label>
      </div></details>
      <label>De<input type="date" value={filtros.data_inicio ?? ""} onChange={(e) => alterar("data_inicio", e.target.value)} /></label><label>Até<input type="date" value={filtros.data_fim ?? ""} onChange={(e) => alterar("data_fim", e.target.value)} /></label>
      <div className="acoes-filtros"><button disabled={carregando}>{carregando ? "Atualizando..." : "Aplicar filtros"}</button><button disabled={carregando} type="button" className="secundario" onClick={() => { setFiltros(vazio); void carregar(vazio); }}>Limpar</button></div>
    </form>
    {erro && <p className="erro card" role="alert">{erro}</p>}
    {carregando && <div className="card vazio" role="status">Carregando relatórios operacionais...</div>}
    {dados && <div className="resumo-consulta" aria-label="Resumo dos filtros aplicados"><strong>{SECOES.find(item => item.id === dados.secao)?.nome} · {dados.dados.total} registros</strong>
      <span>Período: {aplicados.data_inicio ? formatarData(aplicados.data_inicio) : "sem início"} a {aplicados.data_fim ? formatarData(aplicados.data_fim) : "sem fim"}</span>
      <span>{[
        aplicados.proprietario && `Proprietário: ${aplicados.proprietario}`,
        aplicados.propriedade && `Propriedade: ${propriedades.find(item => item.id === Number(aplicados.propriedade))?.nome ?? aplicados.propriedade}`,
        aplicados.cad_pro && `CAD/PRO: ${opcoes?.cadpros.find(item => item.id === aplicados.cad_pro)?.codigo ?? aplicados.cad_pro}`,
        aplicados.cultura && `Cultura: ${aplicados.cultura}`, aplicados.safra && `Safra: ${aplicados.safra}`,
        aplicados.classificacao_codigo && `Classificação: ${aplicados.classificacao_codigo}`,
        aplicados.armazem && `Armazenagem: ${opcoes?.armazens.find(item => item.id === Number(aplicados.armazem))?.nome ?? aplicados.armazem}`,
        aplicados.destinado_semente && `Destinação: ${aplicados.destinado_semente === "true" ? "Semente" : "Grão comercial"}`,
        aplicados.motorista && `Motorista: ${aplicados.motorista}`, aplicados.placa && `Placa: ${aplicados.placa}`,
        aplicados.numero_contrato && `Contrato: ${aplicados.numero_contrato}`, aplicados.comprador && `Comprador: ${aplicados.comprador}`,
      ].filter(Boolean).join(" · ") || "Todos os registros da seção"}</span>
    </div>}
    {dados ? <>{SECOES_GRAOS.has(dados.secao) && <section className="resumos-operacionais">
      <article className="card"><span>Saldo físico</span><strong>{kg(dados.totais.saldo_fisico_kg)}</strong></article><article className="card"><span>Comprometido</span><strong>{kg(dados.totais.saldo_comprometido_kg)}</strong></article><article className="card"><span>Disponível</span><strong>{kg(dados.totais.saldo_disponivel_kg)}</strong></article><article className="card"><span>Produção rateada</span><strong>{kg(dados.totais.producao_rateada_kg)}</strong></article><article className="card"><span>Destinada a semente</span><strong>{kg(dados.totais.semente_kg)}</strong></article><article className="card"><span>Entregas no período</span><strong>{kg(dados.totais.entregas_kg)}</strong></article>
    </section>}{dados.secao === "saldos" && dados.por_cad_pro.length ? <section className="resumos-operacionais saldos-por-cadpro">{dados.por_cad_pro.map((item) => <article className="card" key={String(item.cad_pro)}><span>Saldo CAD/PRO {texto(item.cad_pro_nome)}</span><strong>{kg(item.saldo_disponivel_kg)}</strong><small>Físico {kg(item.saldo_fisico_kg)} · comprometido {kg(item.saldo_comprometido_kg)}</small></article>)}</section> : null}<nav className="catalogo-relatorios" aria-label="Todos os relatórios disponíveis">{GRUPOS_RELATORIOS.map((grupo) => <section key={grupo.nome}><h3>{grupo.nome}</h3><div className="abas-relatorios">{grupo.secoes.map((secao) => { const item = SECOES.find((opcao) => opcao.id === secao)!; return <button key={item.id} className={filtros.secao === item.id ? "" : "secundario"} onClick={() => trocarSecao(item.id)}>{item.nome}</button>; })}</div></section>)}</nav>{dados.secao === "producao_propriedade" && <SeletorColunasImpressao definicoes={COLUNAS_PRODUCAO} selecionadas={colunasProducao} alterar={setColunasProducao} descricao="Marque as colunas da tabela. A mesma seleção será usada na impressão e os totais gerais filtrados permanecerão no rodapé." />}<h2 className="somente-impressao">{SECOES.find(item => item.id === dados.secao)?.nome}</h2><div className={carregando ? "conteudo-atualizando" : ""}><TabelaRelatorio secao={dados.secao} itens={dados.dados.resultados} totaisProducao={dados.totais_producao_propriedade} colunasProducao={colunasProducao} /></div><div className="paginacao"><button className="secundario" disabled={carregando || dados.dados.pagina <= 1} onClick={() => paginar(dados.dados.pagina - 1)}>Anterior</button><span>Página {dados.dados.pagina} de {Math.max(1, dados.dados.total_paginas)} · {dados.dados.total} registros</span><button className="secundario" disabled={carregando || dados.dados.pagina >= dados.dados.total_paginas} onClick={() => paginar(dados.dados.pagina + 1)}>Próxima</button></div><p className="kicker">Relatório somente leitura · gerado em {new Date(dados.gerado_em).toLocaleString("pt-BR")}</p></> : null}
  </section>;
}
