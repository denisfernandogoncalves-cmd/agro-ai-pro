import axios from "axios";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { PosicaoSaldo } from "../../api/producaoSaldos";
import { Propriedade } from "../../api/propriedades";
import { ArmazemGraos, CADPro } from "../../api/cargasColhidas";
import { ContratoComercial } from "../../api/contratosComerciais";
import { quantidadeContrato } from "../CadastrosAgricolas/ContratosComerciais";
import EditorLancamentoVenda from "./EditorLancamentoVenda";
import CamposTransporteVenda from "./CamposTransporteVenda";
import { opcoesOrigemVenda, posicoesDaOrigemVenda } from "./origemVenda";
import {
  cancelarVenda,
  carregarVendas,
  confirmarVenda,
  criarVenda,
  registrarVendaComSaida,
  DadosEntrega,
  devolverVenda,
  entregarVenda,
  FiltrosVenda,
  NovaVenda,
  RegistroVenda,
  VendaGraos,
  AlvoEdicaoVenda,
} from "../../api/vendas";
import { criarControladorMutacaoVenda } from "./vendaMutationController";

const hoje = new Date().toISOString().slice(0, 10);
const vazio: NovaVenda = {
  numero_contrato: "",
  cliente_nome: "",
  posicao: 0,
  quantidade_kg: "",
  data_contrato: hoje,
  data_limite_entrega: null,
  observacoes: "",
};
const filtrosVazios: FiltrosVenda = { search: "", status: "", cultura: "", safra: "", classificacao_codigo: "" };
const entregaVazia: DadosEntrega = {
  quantidade_kg: "",
  data_movimento: hoje,
  destino: "",
  placa: "",
  motorista: "",
  nota_produtor: "",
  nota_empresa: "",
};

function kg(valor: string) {
  return `${Number(valor || 0).toLocaleString("pt-BR", { maximumFractionDigits: 3 })} kg`;
}

export function numeroPlanilhaVenda(valor: string | number, casas = 2) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  });
}

export function dataPlanilhaVenda(valor?: string) {
  const [ano, mes, dia] = (valor || "").slice(0, 10).split("-");
  return ano && mes && dia ? `${dia}/${mes}/${ano}` : "—";
}

export function identificacaoCadProVenda(
  venda: Pick<VendaGraos, "propriedade" | "propriedade_nome" | "cad_pro_codigo">,
  propriedades: Pick<Propriedade, "id" | "proprietario">[],
) {
  const proprietario = propriedades.find(item => item.id === venda.propriedade)?.proprietario?.trim();
  return [venda.propriedade_nome || "Produção histórica", venda.cad_pro_codigo, proprietario]
    .filter(Boolean)
    .join(" - ");
}

export function rotuloPosicaoVenda(posicao: PosicaoSaldo) {
  const propriedade = posicao.propriedade_nome || "Produção histórica sem propriedade";
  return `${propriedade} · ${posicao.cad_pro_codigo} · ${posicao.cultura} ${posicao.safra} · ${posicao.classificacao_codigo} · ${posicao.armazem_nome} · ${kg(posicao.saldo_disponivel_kg)} disponíveis`;
}

function mensagemErro(falha: unknown) {
  if (axios.isAxiosError(falha)) {
    const detalhe = falha.response?.data?.detail ?? falha.response?.data;
    if (typeof detalhe === "string") return detalhe;
    if (detalhe) return Object.values(detalhe).flat(2).join(" ");
  }
  return falha instanceof Error ? falha.message : "Não foi possível concluir a operação de venda.";
}

export function BotaoMutacaoVenda({ processando, children }: { processando: boolean; children: string }) {
  return <button disabled={processando} type="submit">{children}</button>;
}

export function AcoesLancamentoVenda({ desabilitado, editar, excluir }: { desabilitado: boolean; editar: () => void; excluir: () => void }) {
  return <div className="acoes"><button type="button" className="secundario" disabled={desabilitado} onClick={e => { e.stopPropagation(); editar(); }}>Editar</button><button type="button" className="perigo" disabled={desabilitado} onClick={e => { e.stopPropagation(); excluir(); }}>Excluir</button></div>;
}

export function RastreabilidadeVenda({
  venda,
}: {
  venda: Pick<VendaGraos, "posicao" | "lote_operacional_codigo">;
}) {
  return <div className="origens-venda"><h4>Rastreabilidade comprovável</h4><p>A posição oficial #{venda.posicao} é a dimensão autoritativa desta venda.</p><p><small>O lote {venda.lote_operacional_codigo} é usado somente como adaptador operacional do ledger. Nenhum lote ou carga representa origem física alocada à venda.</small></p></div>;
}

export default function VendasPage() {
  const [vendas, setVendas] = useState<VendaGraos[]>([]);
  const [posicoes, setPosicoes] = useState<PosicaoSaldo[]>([]);
  const [propriedades, setPropriedades] = useState<Propriedade[]>([]);
  const [cadpros, setCadpros] = useState<CADPro[]>([]);
  const [armazens, setArmazens] = useState<ArmazemGraos[]>([]);
  const [novaPosicao, setNovaPosicao] = useState({ cultura: "Soja", safra: "", classificacao_codigo: "PADRAO", armazem: 0 });
  const [contratos, setContratos] = useState<ContratoComercial[]>([]);
  const [editor, setEditor] = useState<AlvoEdicaoVenda | null>(null);
  const [selecionada, setSelecionada] = useState<VendaGraos | null>(null);
  const [formulario, setFormulario] = useState<NovaVenda>(vazio);
  const [tipoLancamento, setTipoLancamento] = useState<"saida" | "rascunho">("saida");
  const [novaSaida, setNovaSaida] = useState<DadosEntrega>(entregaVazia);
  const [origemSelecionada, setOrigemSelecionada] = useState("");
  const [filtros, setFiltros] = useState<FiltrosVenda>(filtrosVazios);
  const [quantidadeMovimento, setQuantidadeMovimento] = useState("");
  const [dadosEntrega, setDadosEntrega] = useState<DadosEntrega>(entregaVazia);
  const [processando, setProcessando] = useState(false);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const controlador = useRef(criarControladorMutacaoVenda());

  async function carregar(atuais = filtros) {
    const dados = await carregarVendas(atuais);
    setVendas(dados.vendas);
    setPosicoes(dados.posicoes);
    setPropriedades(dados.propriedades);
    setCadpros(dados.cadpros);
    setArmazens(dados.armazens);
    setContratos(dados.contratos);
    setSelecionada((atual) => dados.vendas.find((item) => item.id === atual?.id) ?? dados.vendas[0] ?? null);
  }

  useEffect(() => { void carregar(filtrosVazios).catch((falha) => setErro(mensagemErro(falha))); }, []);

  const origensDisponiveis = useMemo(
    () => opcoesOrigemVenda(posicoes, propriedades, cadpros),
    [posicoes, propriedades, cadpros],
  );
  const origemVenda = origensDisponiveis.find(o => o.chave === origemSelecionada);
  const iniciarPosicao = formulario.posicao === -1;
  const posicoesDisponiveis = useMemo(
    () => posicoesDaOrigemVenda(posicoes, origemSelecionada),
    [posicoes, origemSelecionada],
  );

  async function executar(assinatura: string, acao: (chave: string) => Promise<unknown>, mensagem: string) {
    if (controlador.current.emAndamento()) return false;
    setErro(""); setSucesso(""); setProcessando(true);
    try {
      await controlador.current.executar(assinatura, acao);
      setSucesso(mensagem);
      await carregar();
      return true;
    } catch (falha) {
      setErro(mensagemErro(falha));
      return false;
    } finally {
      setProcessando(false);
    }
  }

  async function criar(evento: FormEvent) {
    evento.preventDefault();
    if (!origemVenda || (iniciarPosicao ? !origemVenda.propriedade || !novaPosicao.armazem : !posicoesDisponiveis.some(p => p.id === formulario.posicao))) {
      setErro("Selecione a origem e a posição, ou informe os dados para iniciar o estoque.");
      return;
    }
    const criada = await executar(JSON.stringify(["criar", tipoLancamento, formulario, novaSaida, origemSelecionada, novaPosicao]), (chave) => {
      const dados: RegistroVenda = { ...formulario, cliente_nome: formulario.contrato || tipoLancamento === "rascunho" ? formulario.cliente_nome : novaSaida.destino.trim(), data_limite_entrega: tipoLancamento === "saida" ? null : formulario.data_limite_entrega, quantidade_kg: quantidadeContrato(formulario.quantidade_kg) };
      if (iniciarPosicao) {
        delete dados.posicao;
        dados.nova_posicao = { ...novaPosicao, propriedade: origemVenda.propriedade!, cad_pro: origemVenda.cad_pro };
      }
      return tipoLancamento === "saida"
        ? registrarVendaComSaida({ ...novaSaida, ...dados, data_movimento: formulario.data_contrato }, chave)
        : criarVenda(dados, chave);
    }, tipoLancamento === "saida" ? "Venda e saída registradas; peso líquido baixado do estoque." : "Venda criada em rascunho, sem alterar o saldo.");
    if (criada) { setFormulario(vazio); setNovaSaida(entregaVazia); setOrigemSelecionada(""); }
  }

  const aberto = selecionada && !selecionada.excluida_em && ["confirmada", "parcial"].includes(selecionada.status);
  const devolvivel = selecionada ? Number(selecionada.quantidade_entregue_kg) - Number(selecionada.quantidade_devolvida_kg) : 0;
  const saldoSelecionado = selecionada
    ? posicoes.find((item) => item.id === selecionada.posicao)
    : null;
  const saidas = vendas.filter(v => !v.excluida_em).flatMap((venda) => venda.entregas.filter(e => !e.cancelado_em).map((entrega) => ({ venda, entrega })));
  const totalEntregue = saidas.reduce((total, item) => total + Number(item.entrega.quantidade_kg), 0);
  const totalDevolvido = vendas.filter(v => !v.excluida_em).reduce((total, item) => total + Number(item.quantidade_devolvida_kg), 0);
  const propriedadesSaida = Array.from(new Set(vendas.map(
    (item) => item.propriedade_nome || "Produção histórica sem propriedade",
  )));
  const cadprosSaida = Array.from(new Set(vendas.map((item) => item.cad_pro_codigo)));
  const culturasSaida = Array.from(new Set(vendas.map((item) => item.cultura)));
  const safrasSaida = Array.from(new Set(vendas.map((item) => item.safra)));

  return (
    <section className="modulo-vendas">
      <div><span className="kicker">Comercial integrado ao ledger oficial</span><h2>Vendas de grãos</h2><p>Contratos, reservas, entregas e devoluções rastreados por CAD/PRO e posição oficial.</p></div>
      {erro && <p className="erro card" role="alert">{erro}</p>}
      {sucesso && <p className="sucesso card">{sucesso}</p>}

      <form className="card filtros-vendas" onSubmit={(e) => { e.preventDefault(); void carregar().catch(falha => setErro(mensagemErro(falha))); }}>
        <input aria-label="Buscar vendas" placeholder="Contrato ou cliente" value={filtros.search} onChange={(e) => setFiltros({ ...filtros, search: e.target.value })} />
        <select aria-label="Filtrar venda por status" value={filtros.status} onChange={(e) => setFiltros({ ...filtros, status: e.target.value })}><option value="">Todos os status</option><option value="rascunho">Rascunho</option><option value="confirmada">Confirmada</option><option value="parcial">Entrega parcial</option><option value="entregue">Entregue</option><option value="cancelada">Cancelada</option></select>
        <input aria-label="Filtrar venda por cultura" placeholder="Cultura" value={filtros.cultura} onChange={(e) => setFiltros({ ...filtros, cultura: e.target.value })} />
        <input aria-label="Filtrar venda por safra" placeholder="Safra" value={filtros.safra} onChange={(e) => setFiltros({ ...filtros, safra: e.target.value })} />
        <input aria-label="Filtrar venda por classificação" placeholder="Classificação" value={filtros.classificacao_codigo} onChange={(e) => setFiltros({ ...filtros, classificacao_codigo: e.target.value })} />
        <button disabled={processando} type="submit">Filtrar</button>
        <label><input type="checkbox" checked={filtros.mostrar_excluidas === "true"} onChange={e => { const novos = { ...filtros, mostrar_excluidas: String(e.target.checked) }; setFiltros(novos); void carregar(novos).catch(falha => setErro(mensagemErro(falha))); }} /> Mostrar histórico de exclusões</label>
      </form>

      <section className="grade vendas-grade">
        <form className="card formulario formulario-venda-horizontal" onSubmit={criar}>
          <h3>Nova venda</h3>
          <label>Tipo de lançamento<select value={tipoLancamento} disabled={processando} onChange={e => setTipoLancamento(e.target.value as "saida" | "rascunho")}><option value="saida">Venda com saída de grãos</option><option value="rascunho">Apenas rascunho (sem saída)</option></select></label>
          <p>{tipoLancamento === "saida" ? "O peso líquido será baixado mesmo sem saldo. O estoque poderá ficar negativo e será compensado pelas próximas entradas na mesma propriedade, CAD/PRO, cultura, safra, classificação e armazenagem." : "O rascunho não reserva nem movimenta grãos."}</p>
          <label>{tipoLancamento === "saida" ? "Data" : "Data do contrato"}<input required type="date" value={formulario.data_contrato} onChange={e => setFormulario({ ...formulario, data_contrato: e.target.value })} /></label>
          {tipoLancamento === "saida" && <CamposTransporteVenda dados={novaSaida} alterar={setNovaSaida} destinoPadrao={formulario.cliente_nome} destinoObrigatorio={!formulario.contrato} />}
          <label>Propriedade / CAD/PRO / Proprietário<select required disabled={processando} value={origemSelecionada} onChange={e => { setOrigemSelecionada(e.target.value); setFormulario({ ...formulario, posicao: 0 }); }}><option value="">Selecione a propriedade / CAD/PRO / proprietário</option>{origensDisponiveis.map(origem => <option key={origem.chave} value={origem.chave}>{origem.rotulo}</option>)}</select></label>
          <label>Contrato / empresa (Nº do contrato, opcional)<select value={formulario.contrato || ""} onChange={e => { const contrato = contratos.find(c => c.id === Number(e.target.value)); setFormulario({ ...formulario, contrato: contrato?.id, numero_contrato: contrato?.numero || "", cliente_nome: contrato?.empresa || formulario.cliente_nome, quantidade_kg: contrato?.quantidade_kg ? Number(contrato.quantidade_kg).toLocaleString("pt-BR", { maximumFractionDigits: 3 }) : formulario.quantidade_kg }); }}><option value="">Sem contrato</option>{contratos.filter(c => c.ativo).map(c => <option key={c.id} value={c.id}>{c.numero} · {c.empresa} · {c.produto}</option>)}</select></label>
          <p><small>O contrato é opcional. Para vender sem contrato, informe o destino/comprador e o peso líquido. Se selecionar um contrato, a quantidade sugerida pode ser ajustada.</small></p>
          {tipoLancamento === "rascunho" && !formulario.contrato && <label>Comprador / empresa<input required maxLength={160} value={formulario.cliente_nome} onChange={e => setFormulario({ ...formulario, cliente_nome: e.target.value })} /></label>}
          <label>Posição oficial<select required disabled={processando} value={formulario.posicao || ""} onChange={(e) => setFormulario({ ...formulario, posicao: Number(e.target.value) })}><option value="">Selecione</option>{posicoesDisponiveis.map((item) => <option key={item.id} value={item.id}>{rotuloPosicaoVenda(item)}</option>)}{origemVenda?.propriedade && <option value={-1}>Iniciar estoque sem entrada anterior</option>}</select></label>
          {iniciarPosicao && <fieldset><legend>Origem do saldo a iniciar</legend><label>Produto<select value={novaPosicao.cultura} onChange={e => setNovaPosicao({ ...novaPosicao, cultura: e.target.value })}><option>Soja</option><option>Milho</option><option>Trigo</option></select></label><label>Safra<input required maxLength={20} value={novaPosicao.safra} onChange={e => setNovaPosicao({ ...novaPosicao, safra: e.target.value })} /></label><label>Classificação<input required maxLength={50} value={novaPosicao.classificacao_codigo} onChange={e => setNovaPosicao({ ...novaPosicao, classificacao_codigo: e.target.value })} /></label><label>Armazenagem<select required value={novaPosicao.armazem || ""} onChange={e => setNovaPosicao({ ...novaPosicao, armazem: Number(e.target.value) })}><option value="">Selecione</option>{armazens.map(a => <option key={a.id} value={a.id}>{a.nome}</option>)}</select></label></fieldset>}
          <label>{tipoLancamento === "saida" ? "Peso líquido (kg)" : "Quantidade contratada (kg)"}<input required inputMode="decimal" placeholder="Ex.: 35.000,500" value={formulario.quantidade_kg} onChange={(e) => setFormulario({ ...formulario, quantidade_kg: e.target.value })} /></label>
          {tipoLancamento === "rascunho" && <label>Limite de entrega<input type="date" value={formulario.data_limite_entrega ?? ""} onChange={e => setFormulario({ ...formulario, data_limite_entrega: e.target.value || null })} /></label>}
          <label>Observações<textarea value={formulario.observacoes} onChange={(e) => setFormulario({ ...formulario, observacoes: e.target.value })} /></label>
          <BotaoMutacaoVenda processando={processando}>{tipoLancamento === "saida" ? "Registrar venda e saída" : "Criar rascunho"}</BotaoMutacaoVenda>
        </form>

        <section className="card controle-planilha controle-planilha-vendas somente-impressao">
          <h2 className="somente-impressao titulo-impressao-vendas">Vendas</h2>
          <div className="controle-planilha-titulo"><div><span className="kicker">Controle de saída de grãos</span><h3>{propriedadesSaida.join(" · ") || "Todas as propriedades"}</h3><p>CAD/PRO {cadprosSaida.join(", ") || "—"} · {culturasSaida.join(", ") || "todas as culturas"} · safra {safrasSaida.join(", ") || "todas"}</p></div><div className="controle-planilha-total"><span>Saída líquida</span><strong>{kg(String(totalEntregue - totalDevolvido))}</strong><small>{((totalEntregue - totalDevolvido) / 60).toLocaleString("pt-BR", { maximumFractionDigits: 3 })} sacas de 60 kg</small></div></div>
          <div className="tabela-responsiva"><table className="tabela-relatorio tabela-controle vendas-planilha"><thead><tr><th>Data</th><th>Destino</th><th><span className="nao-imprimir">Placa / Motorista</span><span className="somente-impressao">Placa</span></th><th>CAD/PRO</th><th>Contrato</th><th>Nº da nota de produtor</th><th>Nº nota empresa</th><th>Peso líquido (kg)</th><th>Quantidade (sacas de 60 kg)</th><th>Ações</th></tr></thead><tbody>{saidas.length ? saidas.map(({ venda, entrega }) => <tr key={`saida-${entrega.id}`}><td>{dataPlanilhaVenda(entrega.data_entrega)}</td><td>{entrega.destino || venda.cliente_nome}</td><td>{entrega.placa || "—"}<small className="nao-imprimir">{entrega.motorista || "—"}</small></td><td><span className="nao-imprimir">{venda.cad_pro_codigo}</span><span className="somente-impressao cadpro-impressao">{identificacaoCadProVenda(venda, propriedades)}</span></td><td>{venda.numero_contrato || "Sem contrato"}</td><td>{entrega.nota_produtor || "—"}</td><td>{entrega.nota_empresa || "—"}</td><td>{numeroPlanilhaVenda(entrega.quantidade_kg, 3)}</td><td>{numeroPlanilhaVenda(Number(entrega.quantidade_kg) / 60)}</td><td><AcoesLancamentoVenda desabilitado={processando} editar={() => setEditor({ venda, natureza: "entrega", movimento: entrega, excluir: false })} excluir={() => setEditor({ venda, natureza: "entrega", movimento: entrega, excluir: true })} /></td></tr>) : <tr><td colSpan={10}>Nenhuma saída registrada para os filtros informados.</td></tr>}</tbody></table></div>
        </section>

        <section className="conteudo">
          <h3>Vendas registradas</h3>
          <div className="lista">{vendas.length ? vendas.map((item) => <article className={`card item venda-item ${selecionada?.id === item.id ? "ativo" : ""}`} key={item.id} onClick={() => setSelecionada(item)}><div><span className="kicker">{item.excluida_em ? "Excluída — histórico" : item.status}</span><h3>{item.numero_contrato || "Sem contrato"} · {item.cliente_nome}</h3><p>{item.cad_pro_codigo} · {item.cultura} {item.safra} · {item.classificacao_codigo} · {item.armazem_nome}</p></div><div className="metricas-venda"><span>Contratado <strong>{kg(item.quantidade_kg)}</strong></span><span>Reservado <strong>{kg(item.quantidade_reservada_kg)}</strong></span><span>Entregue <strong>{kg(item.quantidade_entregue_kg)}</strong></span><span>Cancelado <strong>{kg(item.quantidade_cancelada_kg)}</strong></span>{!item.excluida_em && <AcoesLancamentoVenda desabilitado={processando} editar={() => setEditor({ venda: item, natureza: "venda", excluir: false })} excluir={() => setEditor({ venda: item, natureza: "venda", excluir: true })} />}</div></article>) : <div className="card vazio">Nenhuma venda encontrada.</div>}</div>
        </section>
      </section>

      {selecionada && <section className="card detalhe-venda"><div className="detalhe-venda-topo"><div><span className="kicker">Detalhe e rastreabilidade</span><h3>{selecionada.numero_contrato || "Sem contrato"}</h3><p>{selecionada.propriedade_nome} · posição oficial #{selecionada.posicao}</p></div><div className="acoes">{!selecionada.excluida_em && selecionada.status === "rascunho" && <button disabled={processando} onClick={() => { void executar(`confirmar:${selecionada.id}`, (chave) => confirmarVenda(selecionada.id, chave), "Venda confirmada e saldo reservado."); }}>Confirmar e reservar</button>}{!selecionada.excluida_em && selecionada.status !== "entregue" && selecionada.status !== "cancelada" && <button className="perigo" disabled={processando} onClick={() => { void executar(`cancelar:${selecionada.id}`, (chave) => cancelarVenda(selecionada.id, "Cancelamento pelo painel", chave), "Venda cancelada; somente a reserva aberta foi liberada."); }}>Cancelar</button>}</div></div>
        <div className="resumo-venda"><span>Físico da posição <strong>{kg(saldoSelecionado?.saldo_fisico_kg ?? "0")}</strong></span><span>Comprometido da posição <strong>{kg(saldoSelecionado?.saldo_comprometido_kg ?? "0")}</strong></span><span>Disponível da posição <strong>{kg(saldoSelecionado?.saldo_disponivel_kg ?? "0")}</strong></span><span>Reservado nesta venda <strong>{kg(selecionada.quantidade_reservada_kg)}</strong></span><span>Entregue <strong>{kg(selecionada.quantidade_entregue_kg)}</strong></span><span>Devolvido <strong>{kg(selecionada.quantidade_devolvida_kg)}</strong></span><span>Cancelado <strong>{kg(selecionada.quantidade_cancelada_kg)}</strong></span></div>
        {aberto && <form className="movimentos-venda formulario-saida" onSubmit={e => { e.preventDefault(); const assinatura = JSON.stringify(["entregar", selecionada.id, dadosEntrega]); void executar(assinatura, (chave) => entregarVenda(selecionada.id, { ...dadosEntrega, quantidade_kg: quantidadeContrato(dadosEntrega.quantidade_kg) }, chave), "Entrega registrada; físico e comprometido foram reduzidos uma única vez.").then(ok => { if (ok) setDadosEntrega(entregaVazia); }); }}>
          <label>Data<input required type="date" value={dadosEntrega.data_movimento} onChange={e => setDadosEntrega({ ...dadosEntrega, data_movimento: e.target.value })} /></label>
          <CamposTransporteVenda dados={dadosEntrega} alterar={setDadosEntrega} destinoPadrao={selecionada.cliente_nome} />
          <label>CAD/PRO<input readOnly value={selecionada.cad_pro_codigo} /></label><label>Nº do contrato<input readOnly value={selecionada.numero_contrato} /></label>
          <label>Peso líquido (kg)<input required inputMode="decimal" placeholder="Ex.: 35.000,500" value={dadosEntrega.quantidade_kg} onChange={e => setDadosEntrega({ ...dadosEntrega, quantidade_kg: e.target.value })} /></label>
          <button type="submit" disabled={processando}>Registrar entrega</button>
        </form>}
        {!selecionada.excluida_em && devolvivel > 0 && <div className="movimentos-venda"><label>Quantidade da devolução (kg)<input min="0.001" step="0.001" type="number" value={quantidadeMovimento} onChange={(e) => setQuantidadeMovimento(e.target.value)} /></label><button className="secundario" disabled={processando || !quantidadeMovimento} onClick={() => { void executar(`devolver:${selecionada.id}:${quantidadeMovimento}`, (chave) => devolverVenda(selecionada.id, quantidadeMovimento, hoje, chave), "Devolução registrada no físico sem reabrir a reserva."); }}>Registrar devolução</button></div>}
        <RastreabilidadeVenda venda={selecionada} />
        <h4>Entregas e devoluções</h4>
        {(["entrega", "devolucao"] as const).map(natureza => <div key={natureza}>{(natureza === "entrega" ? selecionada.entregas : selecionada.devolucoes).filter(m => !m.cancelado_em || filtros.mostrar_excluidas === "true").map(m => <article className="item" key={m.id}><div><strong>{natureza === "entrega" ? "Entrega" : "Devolução"} #{m.id} · {kg(m.quantidade_kg)}</strong><p>{m.data_entrega || m.data_devolucao} · {m.cancelado_em ? "Excluído/substituído" : "Ativo"}</p>{!m.cancelado_em && !selecionada.excluida_em && <AcoesLancamentoVenda desabilitado={processando} editar={() => setEditor({ venda: selecionada, natureza, movimento: m, excluir: false })} excluir={() => setEditor({ venda: selecionada, natureza, movimento: m, excluir: true })} />}</div></article>)}</div>)}
        {!!selecionada.alteracoes?.length && <details><summary>Histórico de correções e exclusões</summary>{selecionada.alteracoes.map(a => <p key={a.id}>{new Date(a.criado_em).toLocaleString("pt-BR")} · {a.usuario} · {a.tipo.replace(/_/g, " ")} · {a.motivo}</p>)}</details>}
      </section>}
      {editor && <EditorLancamentoVenda alvo={editor} contratos={contratos} posicoes={posicoes} processando={processando} erroOperacao={erro} executar={executar} fechar={() => setEditor(null)} />}
    </section>
  );
}
