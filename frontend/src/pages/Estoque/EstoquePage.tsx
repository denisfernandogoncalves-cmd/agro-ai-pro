import { prioridadeValidade } from "../../utils/conferenciaConsultas";
import AbasModulo, { PainelAba } from "../../components/AbasModulo";
import { useEntradaPainel } from "../../components/AcoesContext";
import { BotaoAcao, useDestinoConsulta } from "../../components/AcoesContext";
import { formatarData } from "../../utils/datas";
import { FormEvent, useEffect, useRef, useState } from "react";
import axios from "axios";
import CorrecaoHistorico from "../../components/CorrecaoHistorico";
import { useAlteracoesNaoSalvas } from "../../components/AlteracoesNaoSalvas";

import {
  editarLote, excluirLote, excluirMovimentoEstoque,
  carregarEstoque,
  criarLote,
  LoteEstoque,
  MovimentacaoEstoque,
  PosicaoEstoque,
  ProdutoEstoque,
  registrarMovimento,
} from "../../api/estoque";
import { listarFornecedores, ParceiroFinanceiro } from "../../api/financeiro";
import { Propriedade, rotuloPropriedade } from "../../api/propriedades";
import ComprasEstoque from "./ComprasEstoque";
import ConsultaDisponibilidade from "./DisponibilidadeEstoque";


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
  const [aba, setAba] = useState("disponibilidade");
  const entradaPainel = useEntradaPainel("estoque");
  const [revisaoEstoque, setRevisaoEstoque] = useState(0);
  const [produtos, setProdutos] = useState<ProdutoEstoque[]>([]);
  const [fornecedores, setFornecedores] = useState<ParceiroFinanceiro[]>([]);
  const [lotes, setLotes] = useState<LoteEstoque[]>([]);
  const [posicoes, setPosicoes] = useState<PosicaoEstoque[]>([]);
  const [movimentos, setMovimentos] = useState<MovimentacaoEstoque[]>([]);
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
  const [edicaoLote, setEdicaoLote] = useState<number | null>(null);
  const protecaoLote = useAlteracoesNaoSalvas(auxiliar, "lote", edicaoLote);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [salvandoLote, setSalvandoLote] = useState(false);
  const cadastroLotes = useRef<HTMLDetailsElement>(null);
  const seletorLote = useRef<HTMLSelectElement>(null);

  useDestinoConsulta("estoque", valores => {setAba("movimentos"); const proximos = {search:String(valores.search || ""), tipo:"", produto:""}; setFiltros(proximos); void carregar(proximos);});

  function abrirCadastroLote() {
    setAba("lotes");
    void carregar();
    if (!cadastroLotes.current) return;
    cadastroLotes.current.open = true;
    cadastroLotes.current.scrollIntoView({ behavior: "smooth", block: "center" });
    cadastroLotes.current.querySelector("select")?.focus({ preventScroll: true });
  }

  async function carregar(selecao = filtros) {
    setCarregando(true);
    setErro("");
    try {
      const [dados, fornecedoresAtuais] = await Promise.all([carregarEstoque(selecao), listarFornecedores()]);
      setProdutos(dados.produtos);
      setFornecedores(fornecedoresAtuais);
      setLotes(dados.lotes);
      setPosicoes(dados.posicoes);
      setMovimentos(dados.movimentos);
      setRevisaoEstoque((valor) => valor + 1);
    } catch (falha) {
      setErro(mensagemErro(falha));
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    if (!entradaPainel) void carregar();
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
      const dadosLote = {
        produto: auxiliar.loteProduto,
        fornecedor: auxiliar.loteFornecedor,
        codigo: auxiliar.loteCodigo,
        data_validade: auxiliar.loteValidade,
      };
      const novoLote = edicaoLote ? await editarLote(edicaoLote, dadosLote) : await criarLote(dadosLote);
      setEdicaoLote(null);
      setAuxiliar({
        loteProduto: "",
        loteFornecedor: "",
        loteCodigo: "",
        loteValidade: "",
      });
      protecaoLote.marcarSalvo({loteProduto:"",loteFornecedor:"",loteCodigo:"",loteValidade:""});
      setLotes((atuais) => [...atuais, novoLote]);
      setMovimento((atual) => ({ ...atual, lote: String(novoLote.id) }));
      setSucesso(edicaoLote ? "Lote atualizado." : "Lote cadastrado e selecionado. Complete os dados para registrar a movimentação.");
      await carregar();
      if (!edicaoLote) setAba("movimentos");
    } catch (falha) {
      setErro(mensagemErro(falha));
    } finally {
      setSalvandoLote(false);
    }
  }

  async function excluirRegistro(nome: string, acao: () => Promise<unknown>) {
    if (salvandoLote || !(await protecaoLote.confirmarDescarte()) || !window.confirm(`Excluir ${nome}? O estoque será conferido e vínculos poderão bloquear a exclusão.`)) return;
    setSalvandoLote(true); setErro("");
    try { await acao(); setEdicaoLote(null); setSucesso("Registro excluído."); await carregar(); } catch (e) { setErro(mensagemErro(e)); } finally { setSalvandoLote(false); }
  }
  return (
    <section className="modulo-estoque">
      {erro && <p className="erro card" role="alert">{erro}</p>}
      {sucesso && <p className="sucesso card" role="status">{sucesso}</p>}

<AbasModulo modulo="estoque" ativa={aba} alterar={setAba} abas={[{id:"disponibilidade",titulo:"Disponibilidade"},{id:"compras",titulo:"Compras"},{id:"movimentos",titulo:"Movimentações"},{id:"lotes",titulo:"Lotes"}]} /><PainelAba modulo="estoque" aba="disponibilidade" ativa={aba}>
      <ConsultaDisponibilidade produtos={produtos} fornecedores={fornecedores} revisao={revisaoEstoque} />

</PainelAba><PainelAba modulo="estoque" aba="compras" ativa={aba}>
      <ComprasEstoque produtos={produtos} fornecedores={fornecedores} atualizarEstoque={carregar} />

</PainelAba><PainelAba modulo="estoque" aba="movimentos" ativa={aba}>
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
              {prioridadeValidade(lotes.filter((item) => item.ativo)).map((item) => <option key={item.id} value={item.id}>{item.produto_nome} · {item.codigo} · validade {item.data_validade?formatarData(item.data_validade):"não informada"} · saldo {item.saldo} {item.vencido?"· VENCIDO":""} · {item.fornecedor_nome || item.local_nome || "Fornecedor não informado"}</option>)}
            </select>
          </label>
          <p>Lotes ordenados pela validade: para saídas, prefira o que vence antes entre os lotes válidos do mesmo produto e local. Lotes vencidos exigem conferência; a seleção é manual.</p><BotaoAcao acao="cadastrar" type="button" onClick={abrirCadastroLote}>Novo lote</BotaoAcao>
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
          <BotaoAcao acao="cadastrar" disabled={carregando} type="submit">Registrar sem permitir alteração</BotaoAcao>
        </form>

        <section className="conteudo">
          <form className="painel-filtros" onSubmit={(e) => { e.preventDefault(); void carregar(); }}>
            <input aria-label="Buscar movimentos" placeholder="Produto, lote ou documento" value={filtros.search} onChange={(e) => setFiltros({ ...filtros, search: e.target.value })} />
            <select aria-label="Filtrar por tipo" value={filtros.tipo} onChange={(e) => setFiltros({ ...filtros, tipo: e.target.value })}><option value="">Entradas e saídas</option><option value="entrada">Entradas</option><option value="saida">Saídas</option></select>
            <select aria-label="Filtrar por produto" value={filtros.produto} onChange={(e) => setFiltros({ ...filtros, produto: e.target.value })}><option value="">Todos os produtos</option>{produtos.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select>
            <button type="submit">Filtrar</button>
          </form>

          <section className="card">
            <h2>Rastreabilidade</h2>
            <div className="lista">
              {movimentos.map((item) => (
                <article className="item movimento-estoque" key={item.id}>
                  <div><h3>{item.tipo === "entrada" ? "Entrada" : "Saída"} · {item.produto_nome}</h3><p>{formatarData(item.data_movimento)} · lote {item.lote_codigo} · {item.fornecedor_nome || item.local_nome || "Fornecedor não informado"}</p><small>{item.documento_fiscal || "Sem documento fiscal"} · por {item.criado_por_nome}</small></div>
                  <strong>{item.tipo === "entrada" ? "+" : "−"}{item.quantidade} {item.unidade}</strong><CorrecaoHistorico base="/estoque/movimentacoes/" dados={item} campos={[{nome:"quantidade",rotulo:"Quantidade",tipo:"number"},{nome:"custo_unitario",rotulo:"Custo unitário",tipo:"number",nullable:true},{nome:"data_movimento",rotulo:"Data",tipo:"date"},{nome:"documento_fiscal",rotulo:"Documento",opcional:true},{nome:"safra",rotulo:"Safra",opcional:true},{nome:"observacoes",rotulo:"Observações",opcional:true}]} atualizar={() => void carregar()} />
                </article>
              ))}
            </div>
          </section>
        </section>
      </section>


</PainelAba><PainelAba modulo="estoque" aba="lotes" ativa={aba}>
          <section className="card">
            <h2>Posição por lote</h2>
            <div className="lista">
              {posicoes.length === 0 ? <p className="vazio">Nenhum lote cadastrado.</p> : prioridadeValidade(posicoes).map((item) => (
                <article className={`item posicao ${item.vencido || item.vence_em_30_dias || item.abaixo_minimo ? "alerta-estoque" : ""}`} key={item.lote_id}>
                  <div><h3>{item.produto}</h3><p>Lote {item.codigo_lote} · {item.fornecedor || item.local || "Fornecedor não informado"}</p><small>{item.data_validade ? `Validade ${formatarData(item.data_validade)}` : "Sem validade informada"}</small>{Number(item.saldo)>0&&(item.vencido||item.vence_em_30_dias)&&<p><strong>{item.vencido?"Vencido — conferir destinação":"Vence em até 30 dias — priorizar uso"}</strong></p>}</div>
                  <strong>{item.saldo} {item.unidade}</strong><div className="acoes"><BotaoAcao acao="editar" disabled={salvandoLote} onClick={async () => { if (!(await protecaoLote.confirmarDescarte())) return; const lote=lotes.find(l => l.id===item.lote_id); if (!lote) return; const dados={loteProduto:String(lote.produto), loteFornecedor:String(lote.fornecedor ?? ""), loteCodigo:lote.codigo, loteValidade:lote.data_validade ?? ""}; setEdicaoLote(lote.id); setAuxiliar(dados); protecaoLote.marcarSalvo(dados); cadastroLotes.current?.scrollIntoView({block:"center"}); }}>Editar lote</BotaoAcao><BotaoAcao acao="excluir" className="perigo" disabled={salvandoLote} onClick={() => void excluirRegistro(`lote ${item.codigo_lote}`, () => excluirLote(item.lote_id))}>Excluir lote</BotaoAcao></div>
                </article>
              ))}
            </div>
          </section>

      <details open ref={cadastroLotes} className="card cadastros-auxiliares">
        <summary>Cadastro de lotes</summary>
        <div className="auxiliares-grade">
          <section>
            <h3>{edicaoLote ? "Editar lote" : "Novo lote"}</h3>
            <button type="button" disabled={carregando} onClick={() => void carregar()}>Atualizar cadastros</button>
            <label>Produto agrícola<select value={auxiliar.loteProduto} onChange={(e) => setAuxiliar({ ...auxiliar, loteProduto: e.target.value })}><option value="">Selecione</option>{produtos.filter((item) => item.ativo || String(item.id) === auxiliar.loteProduto).map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
            <label>Fornecedor<select value={auxiliar.loteFornecedor} onChange={(e) => setAuxiliar({ ...auxiliar, loteFornecedor: e.target.value })}><option value="">Selecione</option>{fornecedores.filter((item) => item.ativo || String(item.id) === auxiliar.loteFornecedor).map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
            <label>Código<input placeholder="Código do lote" value={auxiliar.loteCodigo} onChange={(e) => setAuxiliar({ ...auxiliar, loteCodigo: e.target.value })} /></label>
            <label>Validade<input type="date" value={auxiliar.loteValidade} onChange={(e) => setAuxiliar({ ...auxiliar, loteValidade: e.target.value })} /></label>
            <p>Escolha o produto agrícola e o fornecedor cadastrados na aba Cadastros agrícolas. Use Atualizar cadastros após incluir novos registros.</p>
            <BotaoAcao acao={edicaoLote ? "editar" : "cadastrar"} disabled={salvandoLote || !auxiliar.loteProduto || (!auxiliar.loteFornecedor && !lotes.find(l => l.id === edicaoLote)?.local) || !auxiliar.loteCodigo.trim()} type="button" onClick={() => void cadastrarLote()}>{salvandoLote ? "Salvando…" : edicaoLote ? "Salvar alterações" : "Cadastrar lote"}</BotaoAcao>{edicaoLote && <button type="button" disabled={salvandoLote} onClick={async () => { if (!(await protecaoLote.confirmarDescarte())) return; const dados={loteProduto:"",loteFornecedor:"",loteCodigo:"",loteValidade:""}; setEdicaoLote(null); setAuxiliar(dados); protecaoLote.marcarSalvo(dados); }}>Cancelar edição</button>}
          </section>
        </div>
      </details>
</PainelAba>

    </section>
  );
}
