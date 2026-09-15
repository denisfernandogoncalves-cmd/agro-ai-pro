import { FormEvent, useEffect, useRef, useState } from "react";
import axios from "axios";

import {
  carregarEstoque,
  criarLote,
  LoteEstoque,
  MovimentacaoEstoque,
  PosicaoEstoque,
  ProdutoEstoque,
  registrarMovimento,
  ResumoEstoque,
} from "../../api/estoque";
import { listarFornecedores, ParceiroFinanceiro } from "../../api/financeiro";
import { Propriedade, rotuloPropriedade } from "../../api/propriedades";
import ComprasEstoque from "./ComprasEstoque";


const hoje = new Date().toISOString().slice(0, 10);

function mensagemErro(falha: unknown) {
  if (axios.isAxiosError(falha)) {
    const dados = falha.response?.data;
    if (typeof dados?.detail === "string") return dados.detail;
    if (dados && typeof dados === "object") return Object.values(dados).flat().join(" ");
  }
  return "Não foi possível concluir a operação de estoque.";
}

type Props = { propriedades: Propriedade[] };

export default function EstoquePage({ propriedades }: Props) {
  const [produtos, setProdutos] = useState<ProdutoEstoque[]>([]);
  const [fornecedores, setFornecedores] = useState<ParceiroFinanceiro[]>([]);
  const [lotes, setLotes] = useState<LoteEstoque[]>([]);
  const [posicoes, setPosicoes] = useState<PosicaoEstoque[]>([]);
  const [movimentos, setMovimentos] = useState<MovimentacaoEstoque[]>([]);
  const [resumo, setResumo] = useState<ResumoEstoque | null>(null);
  const [filtros, setFiltros] = useState({ search: "", tipo: "", produto: "" });
  const [movimento, setMovimento] = useState({
    tipo: "entrada" as "entrada" | "saida",
    lote: "",
    quantidade: "",
    custo_unitario: "",
    data_movimento: hoje,
    documento_fiscal: "",
    propriedade: "",
    safra: "",
    observacoes: "",
  });
  const [auxiliar, setAuxiliar] = useState({
    loteProduto: "",
    loteFornecedor: "",
    loteCodigo: "",
    loteValidade: "",
  });
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [salvandoLote, setSalvandoLote] = useState(false);
  const cadastroLotes = useRef<HTMLDetailsElement>(null);
  const seletorLote = useRef<HTMLSelectElement>(null);

  function abrirCadastroLote() {
    if (!cadastroLotes.current) return;
    void carregar();
    cadastroLotes.current.open = true;
    cadastroLotes.current.scrollIntoView({ behavior: "smooth", block: "center" });
    cadastroLotes.current.querySelector("select")?.focus({ preventScroll: true });
  }

  async function carregar() {
    setCarregando(true);
    setErro("");
    try {
      const [dados, fornecedoresAtuais] = await Promise.all([carregarEstoque(filtros), listarFornecedores()]);
      setProdutos(dados.produtos);
      setFornecedores(fornecedoresAtuais);
      setLotes(dados.lotes);
      setPosicoes(dados.posicoes);
      setMovimentos(dados.movimentos);
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

  async function salvarMovimento(evento: FormEvent) {
    evento.preventDefault();
    setCarregando(true);
    setErro("");
    setSucesso("");
    try {
      await registrarMovimento(movimento);
      setMovimento({
        ...movimento,
        lote: "",
        quantidade: "",
        custo_unitario: "",
        documento_fiscal: "",
        observacoes: "",
      });
      setSucesso(`${movimento.tipo === "entrada" ? "Entrada" : "Saída"} registrada com rastreabilidade.`);
      await carregar();
    } catch (falha) {
      setErro(mensagemErro(falha));
      setCarregando(false);
    }
  }

  async function cadastrarLote() {
    if (salvandoLote) return;
    setSalvandoLote(true);
    setErro("");
    setSucesso("");
    try {
      const novoLote = await criarLote({
        produto: auxiliar.loteProduto,
        fornecedor: auxiliar.loteFornecedor,
        codigo: auxiliar.loteCodigo,
        data_validade: auxiliar.loteValidade,
      });
      setAuxiliar({
        loteProduto: "",
        loteFornecedor: "",
        loteCodigo: "",
        loteValidade: "",
      });
      setLotes((atuais) => [...atuais, novoLote]);
      setMovimento((atual) => ({ ...atual, lote: String(novoLote.id) }));
      setSucesso("Lote cadastrado e selecionado. Complete os dados para registrar a movimentação.");
      await carregar();
      seletorLote.current?.focus();
    } catch (falha) {
      setErro(mensagemErro(falha));
    } finally {
      setSalvandoLote(false);
    }
  }

  return (
    <section className="modulo-estoque">
      {erro && <p className="erro card">{erro}</p>}
      {sucesso && <p className="sucesso card">{sucesso}</p>}

      {resumo && (
        <section className="resumos-estoque" aria-label="Resumo do estoque">
          <article className="card"><span>Produtos ativos</span><strong>{resumo.produtos_ativos}</strong></article>
          <article className="card"><span>Lotes com saldo</span><strong>{resumo.lotes_com_saldo}</strong></article>
          <article className="card alerta-estoque"><span>Vencidos</span><strong>{resumo.lotes_vencidos}</strong></article>
          <article className="card"><span>Vencem em 30 dias</span><strong>{resumo.lotes_vencendo}</strong></article>
          <article className="card alerta-estoque"><span>Abaixo do mínimo</span><strong>{resumo.itens_abaixo_minimo}</strong></article>
        </section>
      )}

      <ComprasEstoque produtos={produtos} fornecedores={fornecedores} atualizarEstoque={carregar} />
      <details className="card estoque-movimentos">
      <summary>Outras movimentações, saldos e rastreabilidade</summary>
      <section className="grade estoque-grade">
        <form className="card formulario" onSubmit={salvarMovimento}>
          <h2>Nova movimentação</h2>
          <label>Tipo
            <select value={movimento.tipo} onChange={(e) => setMovimento({ ...movimento, tipo: e.target.value as "entrada" | "saida" })}>
              <option value="entrada">Entrada</option>
              <option value="saida">Saída</option>
            </select>
          </label>
          <label>Lote
            <select ref={seletorLote} required value={movimento.lote} onChange={(e) => setMovimento({ ...movimento, lote: e.target.value })}>
              <option value="">Selecione</option>
              {lotes.filter((item) => item.ativo).map((item) => <option key={item.id} value={item.id}>{item.produto_nome} · {item.codigo} · {item.fornecedor_nome || item.local_nome || "Fornecedor não informado"}</option>)}
            </select>
          </label>
          <button type="button" onClick={abrirCadastroLote}>Novo lote</button>
          {lotes.every((item) => !item.ativo) && <p>Nenhum lote ativo. Use Novo lote para cadastrar antes de movimentar.</p>}
          <div className="linha">
            <label>Quantidade<input required min="0.001" step="0.001" type="number" value={movimento.quantidade} onChange={(e) => setMovimento({ ...movimento, quantidade: e.target.value })} /></label>
            <label>Custo unitário<input required={movimento.tipo === "entrada"} min="0" step="0.0001" type="number" value={movimento.custo_unitario} onChange={(e) => setMovimento({ ...movimento, custo_unitario: e.target.value })} /></label>
          </div>
          <label>Data<input required type="date" value={movimento.data_movimento} onChange={(e) => setMovimento({ ...movimento, data_movimento: e.target.value })} /></label>
          <label>Documento fiscal (opcional)<input value={movimento.documento_fiscal} onChange={(e) => setMovimento({ ...movimento, documento_fiscal: e.target.value })} /></label>
          <label>Propriedade
            <select value={movimento.propriedade} onChange={(e) => setMovimento({ ...movimento, propriedade: e.target.value })}>
              <option value="">Não vinculada</option>
              {propriedades.map((item) => <option key={item.id} value={item.id}>{rotuloPropriedade(item)}</option>)}
            </select>
          </label>
          <label>Safra<input placeholder="2026/2027" value={movimento.safra} onChange={(e) => setMovimento({ ...movimento, safra: e.target.value })} /></label>
          <label>Observações<textarea value={movimento.observacoes} onChange={(e) => setMovimento({ ...movimento, observacoes: e.target.value })} /></label>
          <button disabled={carregando} type="submit">Registrar sem permitir alteração</button>
        </form>

        <section className="conteudo">
          <form className="painel-filtros" onSubmit={(e) => { e.preventDefault(); void carregar(); }}>
            <input aria-label="Buscar movimentos" placeholder="Produto, lote ou documento" value={filtros.search} onChange={(e) => setFiltros({ ...filtros, search: e.target.value })} />
            <select aria-label="Filtrar por tipo" value={filtros.tipo} onChange={(e) => setFiltros({ ...filtros, tipo: e.target.value })}><option value="">Entradas e saídas</option><option value="entrada">Entradas</option><option value="saida">Saídas</option></select>
            <select aria-label="Filtrar por produto" value={filtros.produto} onChange={(e) => setFiltros({ ...filtros, produto: e.target.value })}><option value="">Todos os produtos</option>{produtos.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select>
            <button type="submit">Filtrar</button>
          </form>

          <section className="card">
            <h2>Posição por lote</h2>
            <div className="lista">
              {posicoes.length === 0 ? <p className="vazio">Nenhum lote cadastrado.</p> : posicoes.map((item) => (
                <article className={`item posicao ${item.vencido || item.abaixo_minimo ? "alerta-estoque" : ""}`} key={item.lote_id}>
                  <div><h3>{item.produto}</h3><p>Lote {item.codigo_lote} · {item.fornecedor || item.local || "Fornecedor não informado"}</p><small>{item.data_validade ? `Validade ${item.data_validade}` : "Sem validade informada"}</small></div>
                  <strong>{item.saldo} {item.unidade}</strong>
                </article>
              ))}
            </div>
          </section>

          <section className="card">
            <h2>Rastreabilidade</h2>
            <div className="lista">
              {movimentos.map((item) => (
                <article className="item movimento-estoque" key={item.id}>
                  <div><h3>{item.tipo === "entrada" ? "Entrada" : "Saída"} · {item.produto_nome}</h3><p>{item.data_movimento} · lote {item.lote_codigo} · {item.fornecedor_nome || item.local_nome || "Fornecedor não informado"}</p><small>{item.documento_fiscal || "Sem documento fiscal"} · por {item.criado_por_nome}</small></div>
                  <strong>{item.tipo === "entrada" ? "+" : "−"}{item.quantidade} {item.unidade}</strong>
                </article>
              ))}
            </div>
          </section>
        </section>
      </section>

      <details ref={cadastroLotes} className="card cadastros-auxiliares">
        <summary>Cadastro de lotes</summary>
        <div className="auxiliares-grade">
          <section>
            <h3>Novo lote</h3>
            <button type="button" disabled={carregando} onClick={() => void carregar()}>Atualizar cadastros</button>
            <label>Produto agrícola<select value={auxiliar.loteProduto} onChange={(e) => setAuxiliar({ ...auxiliar, loteProduto: e.target.value })}><option value="">Selecione</option>{produtos.filter((item) => item.ativo).map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
            <label>Fornecedor<select value={auxiliar.loteFornecedor} onChange={(e) => setAuxiliar({ ...auxiliar, loteFornecedor: e.target.value })}><option value="">Selecione</option>{fornecedores.filter((item) => item.ativo).map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
            <label>Código<input placeholder="Código do lote" value={auxiliar.loteCodigo} onChange={(e) => setAuxiliar({ ...auxiliar, loteCodigo: e.target.value })} /></label>
            <label>Validade<input type="date" value={auxiliar.loteValidade} onChange={(e) => setAuxiliar({ ...auxiliar, loteValidade: e.target.value })} /></label>
            <p>Escolha o produto agrícola e o fornecedor cadastrados na aba Cadastros agrícolas. Use Atualizar cadastros após incluir novos registros.</p>
            <button disabled={salvandoLote || !auxiliar.loteProduto || !auxiliar.loteFornecedor || !auxiliar.loteCodigo.trim()} type="button" onClick={() => void cadastrarLote()}>{salvandoLote ? "Cadastrando…" : "Cadastrar lote"}</button>
          </section>
        </div>
      </details>
      </details>
    </section>
  );
}
