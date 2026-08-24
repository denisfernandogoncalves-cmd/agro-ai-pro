import { FormEvent, useEffect, useState } from "react";
import axios from "axios";

import {
  carregarEstoque,
  criarLote,
  LocalEstoque,
  LoteEstoque,
  MovimentacaoEstoque,
  PosicaoEstoque,
  ProdutoEstoque,
  registrarMovimento,
  ResumoEstoque,
} from "../../api/estoque";
import { Propriedade } from "../../api/propriedades";


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
  const [locais, setLocais] = useState<LocalEstoque[]>([]);
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
    loteLocal: "",
    loteCodigo: "",
    loteValidade: "",
  });
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function carregar() {
    setCarregando(true);
    setErro("");
    try {
      const dados = await carregarEstoque(filtros);
      setProdutos(dados.produtos);
      setLocais(dados.locais);
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
    setErro("");
    setSucesso("");
    try {
      await criarLote({
        produto: auxiliar.loteProduto,
        local: auxiliar.loteLocal,
        codigo: auxiliar.loteCodigo,
        data_validade: auxiliar.loteValidade,
      });
      setAuxiliar({
        loteProduto: "",
        loteLocal: "",
        loteCodigo: "",
        loteValidade: "",
      });
      setSucesso("Lote cadastrado.");
      await carregar();
    } catch (falha) {
      setErro(mensagemErro(falha));
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
            <select required value={movimento.lote} onChange={(e) => setMovimento({ ...movimento, lote: e.target.value })}>
              <option value="">Selecione</option>
              {lotes.filter((item) => item.ativo).map((item) => <option key={item.id} value={item.id}>{item.produto_nome} · {item.codigo} · {item.local_nome}</option>)}
            </select>
          </label>
          <div className="linha">
            <label>Quantidade<input required min="0.001" step="0.001" type="number" value={movimento.quantidade} onChange={(e) => setMovimento({ ...movimento, quantidade: e.target.value })} /></label>
            <label>Custo unitário<input required={movimento.tipo === "entrada"} min="0" step="0.0001" type="number" value={movimento.custo_unitario} onChange={(e) => setMovimento({ ...movimento, custo_unitario: e.target.value })} /></label>
          </div>
          <label>Data<input required type="date" value={movimento.data_movimento} onChange={(e) => setMovimento({ ...movimento, data_movimento: e.target.value })} /></label>
          <label>Documento fiscal (opcional)<input value={movimento.documento_fiscal} onChange={(e) => setMovimento({ ...movimento, documento_fiscal: e.target.value })} /></label>
          <label>Propriedade
            <select value={movimento.propriedade} onChange={(e) => setMovimento({ ...movimento, propriedade: e.target.value })}>
              <option value="">Não vinculada</option>
              {propriedades.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}
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
                  <div><h3>{item.produto}</h3><p>Lote {item.codigo_lote} · {item.local}</p><small>{item.data_validade ? `Validade ${item.data_validade}` : "Sem validade informada"}</small></div>
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
                  <div><h3>{item.tipo === "entrada" ? "Entrada" : "Saída"} · {item.produto_nome}</h3><p>{item.data_movimento} · lote {item.lote_codigo} · {item.local_nome}</p><small>{item.documento_fiscal || "Sem documento fiscal"} · por {item.criado_por_nome}</small></div>
                  <strong>{item.tipo === "entrada" ? "+" : "−"}{item.quantidade} {item.unidade}</strong>
                </article>
              ))}
            </div>
          </section>
        </section>
      </section>

      <details className="card cadastros-auxiliares">
        <summary>Cadastro de lotes</summary>
        <div className="auxiliares-grade">
          <section>
            <h3>Novo lote</h3>
            <label>Produto<select value={auxiliar.loteProduto} onChange={(e) => setAuxiliar({ ...auxiliar, loteProduto: e.target.value })}><option value="">Selecione</option>{produtos.filter((item) => item.ativo).map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
            <label>Depósito<select value={auxiliar.loteLocal} onChange={(e) => setAuxiliar({ ...auxiliar, loteLocal: e.target.value })}><option value="">Selecione</option>{locais.filter((item) => item.ativo).map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
            <label>Código<input placeholder="Código do lote" value={auxiliar.loteCodigo} onChange={(e) => setAuxiliar({ ...auxiliar, loteCodigo: e.target.value })} /></label>
            <label>Validade<input type="date" value={auxiliar.loteValidade} onChange={(e) => setAuxiliar({ ...auxiliar, loteValidade: e.target.value })} /></label>
            <button disabled={!auxiliar.loteProduto || !auxiliar.loteLocal || !auxiliar.loteCodigo} type="button" onClick={() => void cadastrarLote()}>Cadastrar lote</button>
          </section>
        </div>
      </details>
    </section>
  );
}
