import { FormEvent, useEffect, useState } from "react";
import axios from "axios";

import { LoteEstoque } from "../../api/estoque";
import {
  adicionarInsumo,
  cancelarOperacao,
  carregarOperacoes,
  concluirOperacao,
  criarOperacao,
  iniciarOperacao,
  OperacaoAgricola,
} from "../../api/operacoes";
import { Talhao } from "../../api/talhoes";


const hoje = new Date().toISOString().slice(0, 10);
const vazio = {
  talhao: "",
  tipo: "plantio",
  descricao: "",
  data_planejada: hoje,
  area_hectares: "",
  responsavel: "",
  custo_estimado: "0",
  observacoes: "",
};

function mensagemErro(falha: unknown) {
  if (axios.isAxiosError(falha)) {
    const dados = falha.response?.data;
    if (typeof dados?.detail === "string") return dados.detail;
    if (dados && typeof dados === "object") return Object.values(dados).flat().join(" ");
  }
  return "Não foi possível concluir a operação agrícola.";
}

export default function OperacoesPage() {
  const [operacoes, setOperacoes] = useState<OperacaoAgricola[]>([]);
  const [talhoes, setTalhoes] = useState<Talhao[]>([]);
  const [lotes, setLotes] = useState<LoteEstoque[]>([]);
  const [formulario, setFormulario] = useState(vazio);
  const [filtros, setFiltros] = useState({ search: "", status: "", tipo: "" });
  const [selecionada, setSelecionada] = useState<OperacaoAgricola | null>(null);
  const [insumo, setInsumo] = useState({ lote: "", planejada: "", utilizada: "" });
  const [encerramento, setEncerramento] = useState({ data: hoje, custo: "" });
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function carregar() {
    setCarregando(true);
    setErro("");
    try {
      const dados = await carregarOperacoes(filtros);
      setOperacoes(dados.operacoes);
      setTalhoes(dados.talhoes);
      setLotes(dados.lotes);
      setSelecionada((atual) =>
        dados.operacoes.find((item) => item.id === atual?.id) ?? dados.operacoes[0] ?? null
      );
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
    setErro("");
    try {
      await criarOperacao(formulario);
      setFormulario(vazio);
      setSucesso("Operação planejada.");
      await carregar();
    } catch (falha) {
      setErro(mensagemErro(falha));
    }
  }

  async function incluirInsumo() {
    if (!selecionada) return;
    setErro("");
    try {
      await adicionarInsumo({
        operacao: selecionada.id,
        lote: insumo.lote,
        quantidade_planejada: insumo.planejada,
        quantidade_utilizada: insumo.utilizada,
      });
      setInsumo({ lote: "", planejada: "", utilizada: "" });
      setSucesso("Insumo vinculado ao planejamento.");
      await carregar();
    } catch (falha) {
      setErro(mensagemErro(falha));
    }
  }

  async function transicionar(acao: "iniciar" | "concluir" | "cancelar") {
    if (!selecionada) return;
    setErro("");
    try {
      if (acao === "iniciar") {
        await iniciarOperacao(selecionada.id, encerramento.data);
      } else if (acao === "concluir") {
        await concluirOperacao(selecionada.id, encerramento.data, encerramento.custo);
      } else {
        await cancelarOperacao(selecionada.id);
      }
      setSucesso(`Operação ${acao === "iniciar" ? "iniciada" : acao === "concluir" ? "concluída" : "cancelada"}.`);
      await carregar();
    } catch (falha) {
      setErro(mensagemErro(falha));
    }
  }

  const talhaoSelecionado = talhoes.find((item) => String(item.id) === formulario.talhao);

  return (
    <section className="modulo-operacoes">
      {erro && <p className="erro card">{erro}</p>}
      {sucesso && <p className="sucesso card">{sucesso}</p>}
      <section className="grade operacoes-grade">
        <form className="card formulario" onSubmit={salvar}>
          <h2>Planejar operação</h2>
          <label>Talhão<select required value={formulario.talhao} onChange={(e) => {
            const talhao = talhoes.find((item) => String(item.id) === e.target.value);
            setFormulario({ ...formulario, talhao: e.target.value, area_hectares: talhao?.area_hectares ?? "" });
          }}><option value="">Selecione</option>{talhoes.map((item) => <option key={item.id} value={item.id}>{item.nome} · {item.propriedade_nome}</option>)}</select></label>
          <label>Tipo<select value={formulario.tipo} onChange={(e) => setFormulario({ ...formulario, tipo: e.target.value })}><option value="preparo">Preparo do solo</option><option value="plantio">Plantio</option><option value="adubacao">Adubação</option><option value="pulverizacao">Pulverização</option><option value="irrigacao">Irrigação</option><option value="colheita">Colheita</option><option value="outra">Outra</option></select></label>
          <label>Descrição<input required value={formulario.descricao} onChange={(e) => setFormulario({ ...formulario, descricao: e.target.value })} /></label>
          <div className="linha">
            <label>Data planejada<input required type="date" value={formulario.data_planejada} onChange={(e) => setFormulario({ ...formulario, data_planejada: e.target.value })} /></label>
            <label>Área (ha)<input required max={talhaoSelecionado?.area_hectares} min="0.01" step="0.01" type="number" value={formulario.area_hectares} onChange={(e) => setFormulario({ ...formulario, area_hectares: e.target.value })} /></label>
          </div>
          <label>Responsável<input value={formulario.responsavel} onChange={(e) => setFormulario({ ...formulario, responsavel: e.target.value })} /></label>
          <label>Custo estimado<input min="0" step="0.01" type="number" value={formulario.custo_estimado} onChange={(e) => setFormulario({ ...formulario, custo_estimado: e.target.value })} /></label>
          <label>Observações<textarea value={formulario.observacoes} onChange={(e) => setFormulario({ ...formulario, observacoes: e.target.value })} /></label>
          <button disabled={carregando} type="submit">Salvar planejamento</button>
        </form>

        <section className="conteudo">
          <form className="painel-filtros" onSubmit={(e) => { e.preventDefault(); void carregar(); }}>
            <input aria-label="Buscar operações" placeholder="Descrição, responsável ou talhão" value={filtros.search} onChange={(e) => setFiltros({ ...filtros, search: e.target.value })} />
            <select aria-label="Filtrar status" value={filtros.status} onChange={(e) => setFiltros({ ...filtros, status: e.target.value })}><option value="">Todos os estados</option><option value="planejada">Planejadas</option><option value="em_execucao">Em execução</option><option value="concluida">Concluídas</option><option value="cancelada">Canceladas</option></select>
            <select aria-label="Filtrar tipo" value={filtros.tipo} onChange={(e) => setFiltros({ ...filtros, tipo: e.target.value })}><option value="">Todos os tipos</option><option value="plantio">Plantio</option><option value="pulverizacao">Pulverização</option><option value="colheita">Colheita</option></select>
            <button type="submit">Filtrar</button>
          </form>
          <div className="lista">
            {operacoes.length === 0 ? <div className="card vazio">Nenhuma operação planejada.</div> : operacoes.map((item) => (
              <article className={`card item ${selecionada?.id === item.id ? "ativo" : ""}`} key={item.id} onClick={() => setSelecionada(item)}>
                <div><h3>{item.descricao}</h3><p>{item.talhao_nome} · {item.data_planejada} · {item.status.replace("_", " ")}</p><small>{item.area_hectares} ha · {item.responsavel || "Sem responsável"}</small></div>
                <strong>{Number(item.custo_estimado).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</strong>
              </article>
            ))}
          </div>
        </section>
      </section>

      {selecionada && (
        <section className="card detalhe-operacao">
          <div><h2>{selecionada.descricao}</h2><p>{selecionada.propriedade_nome} · {selecionada.talhao_nome} · criado por {selecionada.criado_por_nome}</p></div>
          <section className="insumos-operacao">
            <h3>Insumos planejados</h3>
            {selecionada.insumos.map((item) => <p key={item.id}>{item.produto_nome} · lote {item.lote_codigo}: {item.quantidade_utilizada ?? item.quantidade_planejada} {item.unidade}{item.movimentacao_estoque ? " · baixado no estoque" : ""}</p>)}
            {["planejada", "em_execucao"].includes(selecionada.status) && (
              <div className="linha-insumo">
                <select value={insumo.lote} onChange={(e) => setInsumo({ ...insumo, lote: e.target.value })}><option value="">Selecione o lote</option>{lotes.filter((item) => item.ativo).map((item) => <option key={item.id} value={item.id}>{item.produto_nome} · {item.codigo} · saldo {item.saldo}</option>)}</select>
                <input min="0.001" placeholder="Quantidade planejada" step="0.001" type="number" value={insumo.planejada} onChange={(e) => setInsumo({ ...insumo, planejada: e.target.value })} />
                <input min="0.001" placeholder="Quantidade utilizada" step="0.001" type="number" value={insumo.utilizada} onChange={(e) => setInsumo({ ...insumo, utilizada: e.target.value })} />
                <button disabled={!insumo.lote || !insumo.planejada} type="button" onClick={() => void incluirInsumo()}>Adicionar</button>
              </div>
            )}
          </section>
          <div className="linha-transicao">
            <label>Data<input type="date" value={encerramento.data} onChange={(e) => setEncerramento({ ...encerramento, data: e.target.value })} /></label>
            <label>Custo realizado<input min="0" step="0.01" type="number" value={encerramento.custo} onChange={(e) => setEncerramento({ ...encerramento, custo: e.target.value })} /></label>
            {selecionada.status === "planejada" && <button type="button" onClick={() => void transicionar("iniciar")}>Iniciar</button>}
            {selecionada.status === "em_execucao" && <button type="button" onClick={() => void transicionar("concluir")}>Concluir e baixar insumos</button>}
            {["planejada", "em_execucao"].includes(selecionada.status) && <button className="perigo" type="button" onClick={() => void transicionar("cancelar")}>Cancelar operação</button>}
          </div>
        </section>
      )}
    </section>
  );
}
