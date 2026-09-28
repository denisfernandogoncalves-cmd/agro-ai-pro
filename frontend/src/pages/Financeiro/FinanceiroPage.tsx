import { FormEvent, useEffect, useState } from "react";
import axios from "axios";

import {
  cancelarLancamento,
  carregarFinanceiro,
  CategoriaFinanceira,
  CentroCusto,
  criarCategoria,
  criarCentroCusto,
  criarLancamento,
  criarParceiro,
  LancamentoFinanceiro,
  LancamentoInput,
  liquidarLancamento,
  ParceiroFinanceiro,
  ResumoFinanceiro,
} from "../../api/financeiro";
import { Propriedade } from "../../api/propriedades";


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

const filtrosVazios = { tipo: "", status: "", search: "", parceiro: "", dataReferencia: "vencimento", inicio: "", fim: "" };

type Props = { propriedades: Propriedade[] };

export default function FinanceiroPage({ propriedades }: Props) {
  const [categorias, setCategorias] = useState<CategoriaFinanceira[]>([]);
  const [parceiros, setParceiros] = useState<ParceiroFinanceiro[]>([]);
  const [centros, setCentros] = useState<CentroCusto[]>([]);
  const [lancamentos, setLancamentos] = useState<LancamentoFinanceiro[]>([]);
  const [resumo, setResumo] = useState<ResumoFinanceiro | null>(null);
  const [formulario, setFormulario] = useState<LancamentoInput>(vazio);
  const [filtros, setFiltros] = useState(filtrosVazios);
  const [auxiliar, setAuxiliar] = useState({
    categoria: "",
    aplicacao: "despesa",
    parceiro: "",
    tipoParceiro: "fornecedor",
    centro: "",
    propriedade: "",
    safra: "",
  });
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function carregar(selecao = filtros) {
    if (selecao.inicio && selecao.fim && selecao.inicio > selecao.fim) {
      setErro("A data final deve ser igual ou posterior à inicial.");
      return;
    }
    setCarregando(true);
    setErro("");
    try {
      const dados = await carregarFinanceiro({
        tipo: selecao.tipo, status: selecao.status, search: selecao.search, parceiro: selecao.parceiro,
        [`${selecao.dataReferencia}_inicio`]: selecao.inicio,
        [`${selecao.dataReferencia}_fim`]: selecao.fim,
      });
      setCategorias(dados.categorias);
      setParceiros(dados.parceiros);
      setCentros(dados.centros);
      setLancamentos(dados.lancamentos);
      setResumo(dados.resumo);
    } catch (falha) {
      setErro(mensagemErro(falha));
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    void carregar();
  }, []);

  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    setCarregando(true);
    try {
      await criarLancamento(formulario);
      setFormulario(vazio);
      await carregar();
    } catch (falha) {
      setErro(mensagemErro(falha));
      setCarregando(false);
    }
  }

  async function cadastrarAuxiliar(tipo: "categoria" | "parceiro" | "centro") {
    setErro("");
    try {
      if (tipo === "categoria") {
        await criarCategoria(auxiliar.categoria, auxiliar.aplicacao);
      } else if (tipo === "parceiro") {
        await criarParceiro(auxiliar.parceiro, auxiliar.tipoParceiro);
      } else {
        await criarCentroCusto(
          auxiliar.centro,
          auxiliar.propriedade,
          auxiliar.safra,
        );
      }
      await carregar();
    } catch (falha) {
      setErro(mensagemErro(falha));
    }
  }

  async function liquidar(item: LancamentoFinanceiro) {
    const data = window.prompt("Data da liquidação (AAAA-MM-DD):", hoje);
    if (!data) return;
    const valor = window.prompt("Valor liquidado:", item.valor);
    if (!valor) return;
    try {
      await liquidarLancamento(item.id, data, valor);
      await carregar();
    } catch (falha) {
      setErro(mensagemErro(falha));
    }
  }

  async function cancelar(item: LancamentoFinanceiro) {
    if (!window.confirm(`Cancelar "${item.descricao}"?`)) return;
    try {
      await cancelarLancamento(item.id);
      await carregar();
    } catch (falha) {
      setErro(mensagemErro(falha));
    }
  }

  return (
    <section className="modulo-financeiro">
      {erro && <p className="erro card">{erro}</p>}
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

      <section className="grade financeiro-grade">
        <form className="card formulario" onSubmit={salvar}>
          <h2>Novo lançamento</h2>
          <div className="linha">
            <label>Tipo<select value={formulario.tipo} onChange={(e) => setFormulario({ ...formulario, tipo: e.target.value as "pagar" | "receber" })}><option value="pagar">Conta a pagar</option><option value="receber">Conta a receber</option></select></label>
            <label>Valor<input min="0.01" required step="0.01" type="number" value={formulario.valor} onChange={(e) => setFormulario({ ...formulario, valor: e.target.value })} /></label>
          </div>
          <label>Descrição<input required value={formulario.descricao} onChange={(e) => setFormulario({ ...formulario, descricao: e.target.value })} /></label>
          <label>Categoria<select required value={formulario.categoria} onChange={(e) => setFormulario({ ...formulario, categoria: e.target.value })}><option value="">Selecione</option>{categorias.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
          <label>Parceiro<select value={formulario.parceiro} onChange={(e) => setFormulario({ ...formulario, parceiro: e.target.value })}><option value="">Sem parceiro</option>{parceiros.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
          <label>Centro de custo<select value={formulario.centro_custo} onChange={(e) => setFormulario({ ...formulario, centro_custo: e.target.value })}><option value="">Sem centro</option>{centros.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
          <div className="linha">
            <label>Propriedade<select value={formulario.propriedade} onChange={(e) => setFormulario({ ...formulario, propriedade: e.target.value })}><option value="">Geral</option>{propriedades.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
            <label>Safra<input value={formulario.safra} onChange={(e) => setFormulario({ ...formulario, safra: e.target.value })} /></label>
          </div>
          <div className="linha">
            <label>Emissão<input required type="date" value={formulario.data_emissao} onChange={(e) => setFormulario({ ...formulario, data_emissao: e.target.value })} /></label>
            <label>Vencimento<input required type="date" value={formulario.data_vencimento} onChange={(e) => setFormulario({ ...formulario, data_vencimento: e.target.value })} /></label>
          </div>
          <label>Observações<textarea value={formulario.observacoes} onChange={(e) => setFormulario({ ...formulario, observacoes: e.target.value })} /></label>
          <button disabled={carregando} type="submit">Salvar lançamento</button>
        </form>

        <section className="conteudo">
          <form className="card filtros-financeiro" onSubmit={(e) => { e.preventDefault(); void carregar(); }}>
            <h2>Filtros financeiros</h2>
            <p>Os totais e a lista consideram os filtros aplicados.</p>
            <label>Buscar lançamentos<input placeholder="Descrição, parceiro ou safra" value={filtros.search} onChange={(e) => setFiltros({ ...filtros, search: e.target.value })} /></label>
            <div className="linha">
              <label>Tipo<select value={filtros.tipo} onChange={(e) => setFiltros({ ...filtros, tipo: e.target.value })}><option value="">Todos os tipos</option><option value="pagar">Contas a pagar / pagas</option><option value="receber">Contas a receber / recebidas</option></select></label>
              <label>Situação<select value={filtros.status} onChange={(e) => setFiltros({ ...filtros, status: e.target.value })}><option value="">Todas as situações</option><option value="pendente">A pagar / a receber</option><option value="liquidado">Pagos / recebidos</option><option value="cancelado">Cancelados</option></select></label>
            </div>
            <label>Quem recebe / parceiro<select value={filtros.parceiro} onChange={(e) => setFiltros({ ...filtros, parceiro: e.target.value })}><option value="">Todos os parceiros</option>{parceiros.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
            <label>Filtrar por data de<select value={filtros.dataReferencia} onChange={(e) => setFiltros({ ...filtros, dataReferencia: e.target.value })}><option value="vencimento">Vencimento</option><option value="liquidacao">Pagamento / recebimento</option></select></label>
            <div className="linha">
              <label>Data inicial<input type="date" value={filtros.inicio} onChange={(e) => setFiltros({ ...filtros, inicio: e.target.value })} /></label>
              <label>Data final<input type="date" min={filtros.inicio || undefined} value={filtros.fim} onChange={(e) => setFiltros({ ...filtros, fim: e.target.value })} /></label>
            </div>
            <div className="acoes">
              <button disabled={carregando} type="submit">Aplicar filtros</button>
              <button disabled={carregando} type="button" className="secundario" onClick={() => { setFiltros(filtrosVazios); void carregar(filtrosVazios); }}>Limpar filtros</button>
            </div>
          </form>
          <div className="lista">
            {lancamentos.map((item) => (
              <article className={`card item lancamento ${item.atrasado ? "atrasado" : ""}`} key={item.id}>
                <div>
                  <span className="kicker">{item.status === "liquidado" ? (item.tipo === "pagar" ? "Pago" : "Recebido") : (item.tipo === "pagar" ? "A pagar" : "A receber")} · {item.status}</span>
                  <h3>{item.descricao}</h3>
                  <p>{item.categoria_nome} · vence {item.data_vencimento}</p>
                  <p>{item.tipo === "pagar" ? "Quem recebe" : "Parceiro"}: {item.parceiro_nome || "Não informado"}</p>
                  {item.data_liquidacao && <p>{item.tipo === "pagar" ? "Pago" : "Recebido"} em {item.data_liquidacao}</p>}
                </div>
                <div>
                  <strong>{moeda(item.status === "liquidado" ? item.valor_liquidado ?? item.valor : item.valor)}</strong>
                  {item.status === "pendente" && <div className="acoes"><button onClick={() => void liquidar(item)}>Liquidar</button><button className="perigo" onClick={() => void cancelar(item)}>Cancelar</button></div>}
                </div>
              </article>
            ))}
            {!carregando && lancamentos.length === 0 && <div className="card vazio">Nenhum lançamento encontrado.</div>}
          </div>
        </section>
      </section>

      <details className="card cadastros-auxiliares">
        <summary>Cadastros auxiliares</summary>
        <div className="auxiliares-grade">
          <section><h3>Categoria</h3><input placeholder="Nome" value={auxiliar.categoria} onChange={(e) => setAuxiliar({ ...auxiliar, categoria: e.target.value })} /><select value={auxiliar.aplicacao} onChange={(e) => setAuxiliar({ ...auxiliar, aplicacao: e.target.value })}><option value="despesa">Despesa</option><option value="receita">Receita</option><option value="ambos">Ambos</option></select><button disabled={!auxiliar.categoria} onClick={() => void cadastrarAuxiliar("categoria")}>Adicionar</button></section>
          <section><h3>Parceiro</h3><input placeholder="Nome" value={auxiliar.parceiro} onChange={(e) => setAuxiliar({ ...auxiliar, parceiro: e.target.value })} /><select value={auxiliar.tipoParceiro} onChange={(e) => setAuxiliar({ ...auxiliar, tipoParceiro: e.target.value })}><option value="fornecedor">Fornecedor</option><option value="cliente">Cliente</option><option value="ambos">Ambos</option></select><button disabled={!auxiliar.parceiro} onClick={() => void cadastrarAuxiliar("parceiro")}>Adicionar</button></section>
          <section><h3>Centro de custo</h3><input placeholder="Nome" value={auxiliar.centro} onChange={(e) => setAuxiliar({ ...auxiliar, centro: e.target.value })} /><input placeholder="Safra" value={auxiliar.safra} onChange={(e) => setAuxiliar({ ...auxiliar, safra: e.target.value })} /><button disabled={!auxiliar.centro} onClick={() => void cadastrarAuxiliar("centro")}>Adicionar</button></section>
        </div>
      </details>
    </section>
  );
}
