import AbasModulo from "../../components/AbasModulo";
import { abaDosFiltros, filtrosDaAba } from "./abasFinanceiro";
import AnexosLancamento from "../../components/AnexosLancamento";
import { useConferirDuplicidades } from "../../components/ConferirDuplicidades";
import { useEntradaPainel } from "../../components/AcoesContext";
import FiltrosFavoritos from "../../components/FiltrosFavoritos";
import { BotaoAcao } from "../../components/AcoesContext";
import { FormEvent, useEffect, useRef, useState } from "react";
import PainelFormulario from "../../components/PainelFormulario";
import { formatarData } from "../../utils/datas";
import axios from "axios";

import {
  cancelarLancamento,
  excluirLancamento,
  carregarFinanceiro,
  registrarBoleto,
  LancamentoFinanceiro,
  LancamentoInput,
  LeituraCodigoFinanceiro,
  liquidarLancamento,
  ParceiroFinanceiro,
  ResumoFinanceiro,
} from "../../api/financeiro";
import { Propriedade } from "../../api/propriedades";
import LeitorCodigoFinanceiro, { aplicarLeituraFinanceira, ResumoCodigoFinanceiro } from "./LeitorCodigoFinanceiro";
import EditorLancamento from "./EditorLancamento";
import FinanceiroImpressao from "./FinanceiroImpressao";


const hoje = new Date().toISOString().slice(0, 10);
const vazio: LancamentoInput = {
  tipo: "pagar",
  descricao: "",
  valor: "",
  categoria: "",
  parceiro: "",
  centro_custo: "",
  propriedade: "",
  safra: "",
  data_emissao: hoje,
  data_vencimento: hoje,
  observacoes: "",
  codigo_barras: "",
};

function mensagemErro(falha: unknown) {
  if (axios.isAxiosError(falha)) {
    const dados = falha.response?.data;
    if (typeof dados?.detail === "string") return dados.detail;
    if (dados && typeof dados === "object") return Object.values(dados).flat().join(" ");
  }
  return "Não foi possível concluir a operação financeira.";
}

function moeda(valor: string | number) {
  return Number(valor).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

const filtrosVazios = { tipo: "", status: "", search: "", parceiro: "", recebedor: "", dataReferencia: "vencimento", inicio: "", fim: "" };

type Props = { propriedades: Propriedade[] };

export default function FinanceiroPage(_props: Props) {
  const [aba, setAba] = useState("todos");
  const sequenciaConsulta = useRef(0);
  const entradaPainel = useEntradaPainel("financeiro");
  const [parceiros, setParceiros] = useState<ParceiroFinanceiro[]>([]);
  const [lancamentos, setLancamentos] = useState<LancamentoFinanceiro[]>([]);
  const [resumo, setResumo] = useState<ResumoFinanceiro | null>(null);
  const [formulario, setFormulario] = useState<LancamentoInput>(vazio);
  const [leituraAplicada, setLeituraAplicada] = useState<LeituraCodigoFinanceiro | null>(null);
  const [quantidade, setQuantidade] = useState("1");
  const [numeroBoleto, setNumeroBoleto] = useState("1");
  const [recebedor, setRecebedor] = useState("");
  const [sucesso, setSucesso] = useState("");
  const chave = useRef<string | null>(null);
  const [filtros, setFiltros] = useState(filtrosVazios);
  const [filtrosImpressao, setFiltrosImpressao] = useState("Todos os lançamentos");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [editando, setEditando] = useState<LancamentoFinanceiro | null>(null);
  const [excluindo, setExcluindo] = useState(false);
  const travaExclusao = useRef(false);
  const travaMutacao = useRef(false);
  const [salvando, setSalvando] = useState(false);

  async function excluir(item: LancamentoFinanceiro) {
    if (travaExclusao.current || travaMutacao.current) return;
    if (!window.confirm(`Excluir definitivamente "${item.descricao}" (${moeda(item.valor)})? O lançamento será removido dos totais financeiros. Esta ação não pode ser desfeita.`)) return;
    travaExclusao.current = true; travaMutacao.current = true; setExcluindo(true); setErro(""); setSucesso("");
    try {
      await excluirLancamento(item.id);
      setSucesso("Lançamento excluído.");
      await carregar();
    } catch (falha) { setErro(mensagemErro(falha)); }
    finally { travaMutacao.current = false; travaExclusao.current = false; setExcluindo(false); }
  }

  async function carregar(selecao = filtros) {
    if (selecao.inicio && selecao.fim && selecao.inicio > selecao.fim) {
      setErro("A data final deve ser igual ou posterior à inicial.");
      return;
    }
    const requisicao = ++sequenciaConsulta.current;
    setCarregando(true);
    setErro("");
    try {
      const dados = await carregarFinanceiro({
        tipo: selecao.tipo, status: selecao.status, search: selecao.search, parceiro: selecao.parceiro, recebedor: selecao.recebedor,
        [`${selecao.dataReferencia}_inicio`]: selecao.inicio,
        [`${selecao.dataReferencia}_fim`]: selecao.fim,
      });
      if (requisicao !== sequenciaConsulta.current) return;
      setAba(abaDosFiltros(selecao));
      setParceiros(dados.parceiros);
      setLancamentos(dados.lancamentos);
      setResumo(dados.resumo);
      setFiltrosImpressao([
        selecao.tipo && (selecao.tipo === "pagar" ? "Contas a pagar / pagas" : "Contas a receber / recebidas"),
        selecao.status && `Situação: ${selecao.status}`,
        selecao.search && `Busca: ${selecao.search}`,
        selecao.recebedor && `Favorecido: ${selecao.recebedor}`,
        selecao.parceiro && `Parceiro: ${dados.parceiros.find(p => String(p.id) === selecao.parceiro)?.nome || selecao.parceiro}`,
        (selecao.inicio || selecao.fim) && `${selecao.dataReferencia === "vencimento" ? "Vencimento" : "Liquidação"}: ${selecao.inicio ? selecao.inicio.split("-").reverse().join("/") : "sem início"} a ${selecao.fim ? selecao.fim.split("-").reverse().join("/") : "sem fim"}`,
      ].filter(Boolean).join(" · ") || "Todos os lançamentos");
    } catch (falha) {
      if (requisicao === sequenciaConsulta.current) setErro(mensagemErro(falha));
    } finally {
      if (requisicao === sequenciaConsulta.current) setCarregando(false);
    }
  }

  useEffect(() => {
    if (!entradaPainel) void carregar();
  }, []);

  const conferirDuplicidades=useConferirDuplicidades();
  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    if (carregando || travaMutacao.current) return;
    if (!Number.isInteger(Number(numeroBoleto)) || !Number.isInteger(Number(quantidade)) || Number(numeroBoleto) < 1 || Number(quantidade) > 9999 || Number(numeroBoleto) > Number(quantidade)) {
      setErro("Informe o número deste boleto e o total de boletos da compra. Exemplo: 1 de 4.");
      return;
    }
    travaMutacao.current = true; setSalvando(true);
    setCarregando(true);
    setErro(""); setSucesso("");
    try {
      if (!(await conferirDuplicidades("financeiro",{data:formulario.data_vencimento,quantidade:Number(formulario.valor.replace(",",".")),descricao:formulario.descricao,recebedor:recebedor.trim()}))) {setCarregando(false);return;}
      chave.current ??= crypto.randomUUID();
      const resultado = await registrarBoleto({
        idempotency_key: chave.current, tipo: formulario.tipo, descricao: formulario.descricao,
        recebedor_nome: recebedor.trim(), parcela_numero: Number(numeroBoleto), total_boletos: Number(quantidade), valor: formulario.valor,
        data_emissao: formulario.data_emissao, data_vencimento: formulario.data_vencimento,
        observacoes: formulario.observacoes, codigo_barras: formulario.codigo_barras || "",
      });
      chave.current = null;
      setFormulario(vazio);
      setLeituraAplicada(null);
      setQuantidade("1"); setNumeroBoleto("1"); setRecebedor("");
      setSucesso(`Boleto ${resultado.boleto.parcela_numero} de ${resultado.boleto.total_boletos} cadastrado.`);
      await carregar();
    } catch (falha) {
      setErro(mensagemErro(falha));
      setCarregando(false);
    } finally { travaMutacao.current = false; setSalvando(false); }
  }

  async function liquidar(item: LancamentoFinanceiro) {
    if (travaMutacao.current) return;
    const data = window.prompt("Data da liquidação (AAAA-MM-DD):", hoje);
    if (!data) return;
    const valor = window.prompt("Valor liquidado:", item.valor);
    if (!valor) return;
    travaMutacao.current = true; setSalvando(true); setErro(""); setSucesso("");
    try {
      await liquidarLancamento(item.id, data, valor);
      await carregar();
    } catch (falha) {
      setErro(mensagemErro(falha));
    } finally { travaMutacao.current = false; setSalvando(false); }
  }

  async function cancelar(item: LancamentoFinanceiro) {
    if (travaMutacao.current) return;
    if (!window.confirm(`Cancelar "${item.descricao}"?`)) return;
    travaMutacao.current = true; setSalvando(true); setErro(""); setSucesso("");
    try {
      await cancelarLancamento(item.id);
      await carregar();
    } catch (falha) {
      setErro(mensagemErro(falha));
    } finally { travaMutacao.current = false; setSalvando(false); }
  }

  return (
    <section className="modulo-financeiro">
      <FiltrosFavoritos contexto="financeiro" filtros={filtros} aplicar={valores => {const proximos = {...filtrosVazios, ...valores}; setFiltros(proximos); void carregar(proximos);}} />
      <FinanceiroImpressao lancamentos={lancamentos} resumo={resumo} filtros={filtrosImpressao} carregando={carregando} />
      {editando && <EditorLancamento key={editando.id} item={editando} onFechar={() => setEditando(null)} onSalvo={() => { setEditando(null); setSucesso("Lançamento atualizado."); void carregar(); }} />}
      {erro && <p className="erro card" role="alert">{erro}</p>}
      {sucesso && <p className="card" role="status">{sucesso}</p>}
      {resumo && (
        <section className="resumos-financeiros" aria-label="Totais dos filtros aplicados">
          <article className="card"><span>A pagar</span><strong>{moeda(resumo.a_pagar)}</strong></article>
          <article className="card"><span>Pagos</span><strong>{moeda(resumo.saidas_realizadas)}</strong></article>
          <article className="card"><span>A receber</span><strong>{moeda(resumo.a_receber)}</strong></article>
          <article className="card"><span>Saldo previsto</span><strong>{moeda(resumo.saldo_previsto)}</strong></article>
          <article className="card"><span>Saldo realizado</span><strong>{moeda(resumo.saldo_realizado)}</strong></article>
          <article className="card alerta-financeiro"><span>Em atraso</span><strong>{moeda(resumo.valor_atrasado)}</strong></article>
        </section>
      )}

      <AbasModulo modulo="financeiro" ativa={aba} desabilitado={carregando || salvando || excluindo} alterar={id => {const proximos=filtrosDaAba(id,filtros);setFiltros(proximos);void carregar(proximos);}} abas={[{id:"todos",titulo:"Todos"},{id:"pagar",titulo:"A pagar"},{id:"receber",titulo:"A receber"},{id:"liquidados",titulo:"Liquidados"}]} />
      {["todos","pagar","receber","liquidados"].filter(id=>id!==aba).map(id=><section key={id} role="tabpanel" id={`financeiro-painel-${id}`} aria-labelledby={`financeiro-aba-${id}`} hidden className="aba-modulo-painel"/>)}
      <section role="tabpanel" id={`financeiro-painel-${aba}`} aria-labelledby={`financeiro-aba-${aba}`} tabIndex={0} className="aba-modulo-painel">
      <section className="grade financeiro-grade">
      <PainelFormulario titulo="Novo lançamento financeiro">
      <LeitorCodigoFinanceiro desabilitado={carregando || excluindo || salvando} aplicar={(leitura, vencimento) => {
        setFormulario(atual => aplicarLeituraFinanceira(atual, leitura, vencimento));
        setLeituraAplicada(leitura);
      }} />
        <form className="card formulario" onSubmit={salvar}>
          <fieldset disabled={carregando || excluindo || salvando} style={{ border: 0, padding: 0, margin: 0, minWidth: 0, display: "grid", gap: 14 }}>
          <h2>Novo lançamento</h2>
          <label>Quem vai receber<input required maxLength={160} list="recebedores-financeiros" placeholder="Digite o nome ou escolha um cadastrado" value={recebedor} onChange={e => setRecebedor(e.target.value)} /></label>
          <datalist id="recebedores-financeiros">{parceiros.filter(p => p.ativo).map(p => <option key={p.id} value={p.nome} />)}</datalist>
          <div className="linha">
            <label>Número deste boleto<input required type="number" min="1" max={quantidade || "9999"} step="1" value={numeroBoleto} onChange={e => setNumeroBoleto(e.target.value)} /></label>
            <label>Total de boletos da compra<input required type="number" min="1" max="9999" step="1" value={quantidade} onChange={e => setQuantidade(e.target.value)} /></label>
          </div>
          <p>Boleto <strong>{numeroBoleto || "—"} de {quantidade || "—"}</strong>. O valor e o vencimento abaixo pertencem somente a este boleto.</p>
          {formulario.codigo_barras && <div><p>Código associado: <code style={{ overflowWrap: "anywhere" }}>{formulario.codigo_barras}</code></p><button type="button" onClick={() => { setFormulario({ ...formulario, codigo_barras: "" }); setLeituraAplicada(null); }}>Desvincular código</button></div>}
          {leituraAplicada && formulario.codigo_barras === leituraAplicada.codigo_barras && <ResumoCodigoFinanceiro leitura={leituraAplicada} />}
          <div className="linha">
            <label>Tipo<select value={formulario.tipo} onChange={(e) => setFormulario({ ...formulario, tipo: e.target.value as "pagar" | "receber" })}><option value="pagar">Conta a pagar</option><option value="receber">Conta a receber</option></select></label>
            <label>Valor deste boleto<input min="0.01" max="999999999999.99" required step="0.01" type="number" value={formulario.valor} onChange={(e) => setFormulario({ ...formulario, valor: e.target.value })} /></label>
          </div>
          <label>Descrição<input required value={formulario.descricao} onChange={(e) => setFormulario({ ...formulario, descricao: e.target.value })} /></label>
          <div className="linha">
            <label>Emissão<input required type="date" value={formulario.data_emissao} onChange={(e) => setFormulario({ ...formulario, data_emissao: e.target.value })} /></label>
            <label>Vencimento deste boleto<input required type="date" value={formulario.data_vencimento} onChange={(e) => setFormulario({ ...formulario, data_vencimento: e.target.value })} /></label>
          </div>
          <label>Observações<textarea value={formulario.observacoes} onChange={(e) => setFormulario({ ...formulario, observacoes: e.target.value })} /></label>
          <button disabled={carregando || excluindo || salvando} type="submit">{salvando ? "Salvando..." : "Salvar boleto"}</button>
          </fieldset>
        </form>
      </PainelFormulario>

        <section className="conteudo">
          <form className="card filtros-financeiro" onSubmit={(e) => { e.preventDefault(); void carregar(); }}>
            <h2>Filtros financeiros</h2>
            <p>Os totais e a lista consideram os filtros aplicados.</p>
            <label>Buscar lançamentos<input placeholder="Descrição, parceiro ou safra" value={filtros.search} onChange={(e) => setFiltros({ ...filtros, search: e.target.value })} /></label>
            <div className="linha">
              <label>Tipo<select value={filtros.tipo} onChange={(e) => setFiltros({ ...filtros, tipo: e.target.value })}><option value="">Todos os tipos</option><option value="pagar">Contas a pagar / pagas</option><option value="receber">Contas a receber / recebidas</option></select></label>
              <label>Situação<select value={filtros.status} onChange={(e) => setFiltros({ ...filtros, status: e.target.value })}><option value="">Todas as situações</option><option value="pendente">A pagar / a receber</option><option value="liquidado">Pagos / recebidos</option><option value="cancelado">Cancelados</option></select></label>
            </div>
            <details className="filtros-avancados"><summary>Filtros por recebedor e parceiro</summary>
            <label>Quem recebe<input placeholder="Nome completo ou parte do nome" value={filtros.recebedor} onChange={(e) => setFiltros({ ...filtros, recebedor: e.target.value })} /></label>
            <label>Parceiro cadastrado<select value={filtros.parceiro} onChange={(e) => setFiltros({ ...filtros, parceiro: e.target.value })}><option value="">Todos os parceiros</option>{parceiros.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
            </details>
            <label>Filtrar por data de<select value={filtros.dataReferencia} onChange={(e) => setFiltros({ ...filtros, dataReferencia: e.target.value })}><option value="vencimento">Vencimento</option><option value="liquidacao">Pagamento / recebimento</option></select></label>
            <div className="linha">
              <label>Data inicial<input type="date" value={filtros.inicio} onChange={(e) => setFiltros({ ...filtros, inicio: e.target.value })} /></label>
              <label>Data final<input type="date" min={filtros.inicio || undefined} value={filtros.fim} onChange={(e) => setFiltros({ ...filtros, fim: e.target.value })} /></label>
            </div>
            <div className="acoes">
              <button disabled={carregando || excluindo || salvando} type="submit">Aplicar filtros</button>
              <button disabled={carregando || excluindo || salvando} type="button" className="secundario" onClick={() => { setFiltros(filtrosVazios); void carregar(filtrosVazios); }}>Limpar filtros</button>
            </div>
          </form>
          <div className="resumo-consulta" role="status"><strong>Resultado da consulta</strong><span>{salvando || excluindo ? "Processando lançamento..." : carregando ? "Atualizando lançamentos..." : `${lancamentos.length} lançamento(s) · ${filtrosImpressao}`}</span></div>
          <div className="lista">
            {lancamentos.map((item) => (
              <article className={`card item lancamento ${item.atrasado ? "atrasado" : ""}`} key={item.id}>
                <div>
                  <span className="kicker">{item.status === "liquidado" ? (item.tipo === "pagar" ? "Pago" : "Recebido") : (item.tipo === "pagar" ? "A pagar" : "A receber")} · {item.status}</span>
                  <h3>{item.descricao}</h3>
                  <p>{item.recebedor_nome || item.parceiro_nome || "Recebedor não informado"}{item.total_boletos ? ` · boleto ${item.parcela_numero} de ${item.total_boletos}` : item.parcela_numero ? ` · parcela ${item.parcela_numero}` : ""} · vence {formatarData(item.data_vencimento)}</p>
                  {item.data_liquidacao && <p>{item.tipo === "pagar" ? "Pago" : "Recebido"} em {formatarData(item.data_liquidacao)}</p>}
                  <AnexosLancamento entidade="financeiro" registro={item.id} />
                  {item.codigo_barras && <details><summary>Código de barras</summary><code style={{ overflowWrap: "anywhere" }}>{item.codigo_barras}</code></details>}
                </div>
                <div>
                  <strong>{moeda(item.status === "liquidado" ? item.valor_liquidado ?? item.valor : item.valor)}</strong>
                  <div className="acoes acoes-lancamento">
                    <BotaoAcao acao="editar" type="button" className="secundario" disabled={carregando || excluindo || salvando} onClick={() => setEditando(item)}>Editar</BotaoAcao>
                    <BotaoAcao acao="excluir" type="button" className="perigo" disabled={carregando || excluindo || salvando} onClick={() => void excluir(item)}>Excluir</BotaoAcao>
                    {item.status === "pendente" && <><BotaoAcao acao="editar" disabled={carregando || excluindo || salvando} onClick={() => void liquidar(item)}>Liquidar</BotaoAcao><BotaoAcao acao="excluir" className="secundario" disabled={carregando || excluindo || salvando} onClick={() => void cancelar(item)}>Cancelar lançamento</BotaoAcao></>}
                  </div>
                </div>
              </article>
            ))}
            {!carregando && lancamentos.length === 0 && <div className="card vazio">Nenhum lançamento encontrado.</div>}
          </div>
        </section>
      </section>

      </section>
    </section>
  );
}
