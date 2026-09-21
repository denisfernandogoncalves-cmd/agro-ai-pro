import { FormEvent, useEffect, useRef, useState } from "react";
import axios from "axios";

import {
  cancelarLancamento,
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

type Props = { propriedades: Propriedade[] };

export default function FinanceiroPage(_props: Props) {
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
  const [filtros, setFiltros] = useState({ tipo: "", status: "", search: "" });
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function carregar() {
    setCarregando(true);
    setErro("");
    try {
      const dados = await carregarFinanceiro(filtros);
      setParceiros(dados.parceiros);
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
    if (carregando) return;
    if (!Number.isInteger(Number(numeroBoleto)) || !Number.isInteger(Number(quantidade)) || Number(numeroBoleto) < 1 || Number(quantidade) > 9999 || Number(numeroBoleto) > Number(quantidade)) {
      setErro("Informe o número deste boleto e o total de boletos da compra. Exemplo: 1 de 4.");
      return;
    }
    setCarregando(true);
    setErro(""); setSucesso("");
    try {
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
      {sucesso && <p className="card" role="status">{sucesso}</p>}
      {resumo && (
        <section className="resumos-financeiros">
          <article className="card"><span>A pagar</span><strong>{moeda(resumo.a_pagar)}</strong></article>
          <article className="card"><span>A receber</span><strong>{moeda(resumo.a_receber)}</strong></article>
          <article className="card"><span>Saldo previsto</span><strong>{moeda(resumo.saldo_previsto)}</strong></article>
          <article className="card"><span>Saldo realizado</span><strong>{moeda(resumo.saldo_realizado)}</strong></article>
          <article className="card alerta-financeiro"><span>Em atraso</span><strong>{moeda(resumo.valor_atrasado)}</strong></article>
        </section>
      )}

      <LeitorCodigoFinanceiro desabilitado={carregando} aplicar={(leitura, vencimento) => {
        setFormulario(atual => aplicarLeituraFinanceira(atual, leitura, vencimento));
        setLeituraAplicada(leitura);
      }} />
      <section className="grade financeiro-grade">
        <form className="card formulario" onSubmit={salvar}>
          <fieldset disabled={carregando} style={{ border: 0, padding: 0, margin: 0, minWidth: 0, display: "grid", gap: 14 }}>
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
          <button disabled={carregando} type="submit">{carregando ? "Salvando..." : "Salvar boleto"}</button>
          </fieldset>
        </form>

        <section className="conteudo">
          <form className="card painel-filtros" onSubmit={(e) => { e.preventDefault(); void carregar(); }}>
            <input aria-label="Buscar lançamentos" placeholder="Buscar descrição ou recebedor" value={filtros.search} onChange={(e) => setFiltros({ ...filtros, search: e.target.value })} />
            <select value={filtros.tipo} onChange={(e) => setFiltros({ ...filtros, tipo: e.target.value })}><option value="">Todos os tipos</option><option value="pagar">A pagar</option><option value="receber">A receber</option></select>
            <select value={filtros.status} onChange={(e) => setFiltros({ ...filtros, status: e.target.value })}><option value="">Todos os status</option><option value="pendente">Pendente</option><option value="liquidado">Liquidado</option><option value="cancelado">Cancelado</option></select>
            <button type="submit">Aplicar filtros</button>
          </form>
          <div className="lista">
            {lancamentos.map((item) => (
              <article className={`card item lancamento ${item.atrasado ? "atrasado" : ""}`} key={item.id}>
                <div>
                  <span className="kicker">{item.tipo === "pagar" ? "A pagar" : "A receber"} · {item.status}</span>
                  <h3>{item.descricao}</h3>
                  <p>{item.recebedor_nome || item.parceiro_nome || "Recebedor não informado"}{item.total_boletos ? ` · boleto ${item.parcela_numero} de ${item.total_boletos}` : item.parcela_numero ? ` · parcela ${item.parcela_numero}` : ""} · vence {item.data_vencimento}</p>
                  {item.codigo_barras && <details><summary>Código de barras</summary><code style={{ overflowWrap: "anywhere" }}>{item.codigo_barras}</code></details>}
                </div>
                <div>
                  <strong>{moeda(item.valor)}</strong>
                  {item.status === "pendente" && <div className="acoes"><button onClick={() => void liquidar(item)}>Liquidar</button><button className="perigo" onClick={() => void cancelar(item)}>Cancelar</button></div>}
                </div>
              </article>
            ))}
            {!carregando && lancamentos.length === 0 && <div className="card vazio">Nenhum lançamento encontrado.</div>}
          </div>
        </section>
      </section>

    </section>
  );
}
