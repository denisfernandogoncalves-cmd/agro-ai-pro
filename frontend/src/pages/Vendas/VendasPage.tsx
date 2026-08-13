import axios from "axios";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { PosicaoSaldo } from "../../api/producaoSaldos";
import {
  cancelarVenda,
  carregarVendas,
  confirmarVenda,
  criarVenda,
  devolverVenda,
  entregarVenda,
  FiltrosVenda,
  NovaVenda,
  VendaGraos,
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

function kg(valor: string) {
  return `${Number(valor || 0).toLocaleString("pt-BR", { maximumFractionDigits: 3 })} kg`;
}

function mensagemErro(falha: unknown) {
  if (axios.isAxiosError(falha)) {
    const detalhe = falha.response?.data?.detail;
    if (typeof detalhe === "string") return detalhe;
    if (detalhe) return Object.values(detalhe).flat(2).join(" ");
  }
  return "Não foi possível concluir a operação de venda.";
}

export function BotaoMutacaoVenda({ processando, children }: { processando: boolean; children: string }) {
  return <button disabled={processando} type="submit">{children}</button>;
}

export default function VendasPage() {
  const [vendas, setVendas] = useState<VendaGraos[]>([]);
  const [posicoes, setPosicoes] = useState<PosicaoSaldo[]>([]);
  const [selecionada, setSelecionada] = useState<VendaGraos | null>(null);
  const [formulario, setFormulario] = useState<NovaVenda>(vazio);
  const [filtros, setFiltros] = useState<FiltrosVenda>(filtrosVazios);
  const [quantidadeMovimento, setQuantidadeMovimento] = useState("");
  const [processando, setProcessando] = useState(false);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const controlador = useRef(criarControladorMutacaoVenda());

  async function carregar(atuais = filtros) {
    const dados = await carregarVendas(atuais);
    setVendas(dados.vendas);
    setPosicoes(dados.posicoes);
    setSelecionada((atual) => dados.vendas.find((item) => item.id === atual?.id) ?? dados.vendas[0] ?? null);
  }

  useEffect(() => { void carregar(filtrosVazios).catch((falha) => setErro(mensagemErro(falha))); }, []);

  const posicoesDisponiveis = useMemo(
    () => posicoes.filter((item) => Number(item.saldo_disponivel_kg) > 0),
    [posicoes],
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
    const criada = await executar(JSON.stringify(["criar", formulario]), (chave) => criarVenda(formulario, chave), "Venda criada em rascunho, sem alterar o saldo.");
    if (criada) setFormulario(vazio);
  }

  const aberto = selecionada && ["confirmada", "parcial"].includes(selecionada.status);
  const devolvivel = selecionada ? Number(selecionada.quantidade_entregue_kg) - Number(selecionada.quantidade_devolvida_kg) : 0;
  const saldoSelecionado = selecionada
    ? posicoes.find((item) => item.id === selecionada.posicao)
    : null;

  return (
    <section className="modulo-vendas">
      <div><span className="kicker">Comercial integrado ao ledger oficial</span><h2>Vendas com bloqueio por saldo</h2><p>Contratos, reservas, entregas e devoluções rastreados por CAD/PRO e posição oficial.</p></div>
      {erro && <p className="erro card" role="alert">{erro}</p>}
      {sucesso && <p className="sucesso card">{sucesso}</p>}

      <form className="card filtros-vendas" onSubmit={(e) => { e.preventDefault(); void carregar(); }}>
        <input aria-label="Buscar vendas" placeholder="Contrato ou cliente" value={filtros.search} onChange={(e) => setFiltros({ ...filtros, search: e.target.value })} />
        <select aria-label="Filtrar venda por status" value={filtros.status} onChange={(e) => setFiltros({ ...filtros, status: e.target.value })}><option value="">Todos os status</option><option value="rascunho">Rascunho</option><option value="confirmada">Confirmada</option><option value="parcial">Entrega parcial</option><option value="entregue">Entregue</option><option value="cancelada">Cancelada</option></select>
        <input aria-label="Filtrar venda por cultura" placeholder="Cultura" value={filtros.cultura} onChange={(e) => setFiltros({ ...filtros, cultura: e.target.value })} />
        <input aria-label="Filtrar venda por safra" placeholder="Safra" value={filtros.safra} onChange={(e) => setFiltros({ ...filtros, safra: e.target.value })} />
        <input aria-label="Filtrar venda por classificação" placeholder="Classificação" value={filtros.classificacao_codigo} onChange={(e) => setFiltros({ ...filtros, classificacao_codigo: e.target.value })} />
        <button disabled={processando} type="submit">Filtrar</button>
      </form>

      <section className="grade vendas-grade">
        <form className="card formulario" onSubmit={criar}>
          <h3>Novo contrato</h3>
          <p>O rascunho não reserva nem movimenta grãos.</p>
          <label>Número do contrato<input required maxLength={80} value={formulario.numero_contrato} onChange={(e) => setFormulario({ ...formulario, numero_contrato: e.target.value })} /></label>
          <label>Cliente<input required maxLength={160} value={formulario.cliente_nome} onChange={(e) => setFormulario({ ...formulario, cliente_nome: e.target.value })} /></label>
          <label>Posição oficial<select required value={formulario.posicao || ""} onChange={(e) => setFormulario({ ...formulario, posicao: Number(e.target.value) })}><option value="">Selecione</option>{posicoesDisponiveis.map((item) => <option key={item.id} value={item.id}>{item.cad_pro_codigo} · {item.cultura} {item.safra} · {item.classificacao_codigo} · {item.armazem_nome} · {kg(item.saldo_disponivel_kg)} disponíveis</option>)}</select></label>
          <label>Quantidade contratada (kg)<input required min="0.001" step="0.001" type="number" value={formulario.quantidade_kg} onChange={(e) => setFormulario({ ...formulario, quantidade_kg: e.target.value })} /></label>
          <div className="linha"><label>Data do contrato<input required type="date" value={formulario.data_contrato} onChange={(e) => setFormulario({ ...formulario, data_contrato: e.target.value })} /></label><label>Limite de entrega<input type="date" value={formulario.data_limite_entrega ?? ""} onChange={(e) => setFormulario({ ...formulario, data_limite_entrega: e.target.value || null })} /></label></div>
          <label>Observações<textarea value={formulario.observacoes} onChange={(e) => setFormulario({ ...formulario, observacoes: e.target.value })} /></label>
          <BotaoMutacaoVenda processando={processando}>Criar rascunho</BotaoMutacaoVenda>
        </form>

        <section className="conteudo">
          <h3>Contratos</h3>
          <div className="lista">{vendas.length ? vendas.map((item) => <article className={`card item venda-item ${selecionada?.id === item.id ? "ativo" : ""}`} key={item.id} onClick={() => setSelecionada(item)}><div><span className="kicker">{item.status}</span><h3>{item.numero_contrato} · {item.cliente_nome}</h3><p>{item.cad_pro_codigo} · {item.cultura} {item.safra} · {item.classificacao_codigo} · {item.armazem_nome}</p></div><div className="metricas-venda"><span>Contratado <strong>{kg(item.quantidade_kg)}</strong></span><span>Reservado <strong>{kg(item.quantidade_reservada_kg)}</strong></span><span>Entregue <strong>{kg(item.quantidade_entregue_kg)}</strong></span><span>Cancelado <strong>{kg(item.quantidade_cancelada_kg)}</strong></span></div></article>) : <div className="card vazio">Nenhuma venda encontrada.</div>}</div>
        </section>
      </section>

      {selecionada && <section className="card detalhe-venda"><div className="detalhe-venda-topo"><div><span className="kicker">Detalhe e rastreabilidade</span><h3>{selecionada.numero_contrato}</h3><p>{selecionada.propriedade_nome} · lote {selecionada.lote_codigo}</p></div><div className="acoes">{selecionada.status === "rascunho" && <button disabled={processando} onClick={() => { void executar(`confirmar:${selecionada.id}`, (chave) => confirmarVenda(selecionada.id, chave), "Venda confirmada e saldo reservado."); }}>Confirmar e reservar</button>}{selecionada.status !== "entregue" && selecionada.status !== "cancelada" && <button className="perigo" disabled={processando} onClick={() => { void executar(`cancelar:${selecionada.id}`, (chave) => cancelarVenda(selecionada.id, "Cancelamento pelo painel", chave), "Venda cancelada; somente a reserva aberta foi liberada."); }}>Cancelar</button>}</div></div>
        <div className="resumo-venda"><span>Físico da posição <strong>{kg(saldoSelecionado?.saldo_fisico_kg ?? "0")}</strong></span><span>Comprometido da posição <strong>{kg(saldoSelecionado?.saldo_comprometido_kg ?? "0")}</strong></span><span>Disponível da posição <strong>{kg(saldoSelecionado?.saldo_disponivel_kg ?? "0")}</strong></span><span>Reservado nesta venda <strong>{kg(selecionada.quantidade_reservada_kg)}</strong></span><span>Entregue <strong>{kg(selecionada.quantidade_entregue_kg)}</strong></span><span>Devolvido <strong>{kg(selecionada.quantidade_devolvida_kg)}</strong></span><span>Cancelado <strong>{kg(selecionada.quantidade_cancelada_kg)}</strong></span></div>
        {(aberto || devolvivel > 0) && <div className="movimentos-venda"><label>Quantidade (kg)<input min="0.001" step="0.001" type="number" value={quantidadeMovimento} onChange={(e) => setQuantidadeMovimento(e.target.value)} /></label>{aberto && <button disabled={processando || !quantidadeMovimento} onClick={() => { void executar(`entregar:${selecionada.id}:${quantidadeMovimento}`, (chave) => entregarVenda(selecionada.id, quantidadeMovimento, hoje, chave), "Entrega registrada; físico e comprometido foram reduzidos uma única vez."); }}>Registrar entrega</button>}{devolvivel > 0 && <button className="secundario" disabled={processando || !quantidadeMovimento} onClick={() => { void executar(`devolver:${selecionada.id}:${quantidadeMovimento}`, (chave) => devolverVenda(selecionada.id, quantidadeMovimento, hoje, chave), "Devolução registrada no físico sem reabrir a reserva."); }}>Registrar devolução</button>}</div>}
        <div className="origens-venda"><h4>Cargas e grupos de origem do lote</h4>{selecionada.origens_colheita.length ? selecionada.origens_colheita.map((origem) => <p key={origem.carga_id}>Carga #{origem.carga_id} · {origem.data_colheita} · {origem.placa} · {kg(origem.peso_liquido_kg)} · grupo {origem.grupo_nome}</p>) : <p>Posição originada por produção sem carga vinculada ao lote operacional.</p>}</div>
      </section>}
    </section>
  );
}
