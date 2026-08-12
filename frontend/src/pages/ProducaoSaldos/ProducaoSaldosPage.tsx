import axios from "axios";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { Propriedade } from "../../api/propriedades";
import {
  carregarOpcoesProducaoSaldo,
  consultarPainelSaldos,
  creditarProducao,
  FiltrosSaldo,
  listarMovimentacoesSaldo,
  LoteGraos,
  MovimentacaoSaldo,
  PainelSaldos,
} from "../../api/producaoSaldos";
import { ArmazemGraos, CADPro } from "../../api/cargasColhidas";
import { criarControladorCreditoProducao } from "./creditoProducaoSubmission";

const filtrosVazios: FiltrosSaldo = {
  propriedade: "",
  cad_pro: "",
  cultura: "",
  safra: "",
  classificacao_codigo: "",
  armazem: "",
};

const creditoVazio = {
  lote: 0,
  quantidade_kg: "",
  data_movimento: new Date().toISOString().slice(0, 10),
  referencia_externa: "",
  observacoes: "",
};

function numero(valor: string) {
  return Number(valor || 0);
}

function kg(valor: string) {
  return `${numero(valor).toLocaleString("pt-BR", { maximumFractionDigits: 3 })} kg`;
}

function mensagemErro(falha: unknown) {
  if (axios.isAxiosError(falha)) {
    const dados = falha.response?.data;
    if (typeof dados?.mensagem === "string") return dados.mensagem;
    if (typeof dados?.detail === "string") return dados.detail;
    if (dados && typeof dados === "object") return Object.values(dados).flat(2).join(" ");
  }
  return "Não foi possível atualizar a produção e os saldos.";
}

type Props = { propriedades: Propriedade[] };

export function BotaoCreditarProducao({ desabilitado }: { desabilitado: boolean }) {
  return <button disabled={desabilitado} type="submit">Creditar produção</button>;
}

export default function ProducaoSaldosPage({ propriedades }: Props) {
  const [painel, setPainel] = useState<PainelSaldos | null>(null);
  const [movimentos, setMovimentos] = useState<MovimentacaoSaldo[]>([]);
  const [cadpros, setCadpros] = useState<CADPro[]>([]);
  const [armazens, setArmazens] = useState<ArmazemGraos[]>([]);
  const [lotes, setLotes] = useState<LoteGraos[]>([]);
  const [filtros, setFiltros] = useState<FiltrosSaldo>(filtrosVazios);
  const [credito, setCredito] = useState(creditoVazio);
  const [carregando, setCarregando] = useState(false);
  const [creditando, setCreditando] = useState(false);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const controladorCredito = useRef(criarControladorCreditoProducao());

  async function carregar(filtrosAtuais = filtros) {
    setCarregando(true);
    setErro("");
    try {
      const [dadosPainel, dadosMovimentos, opcoes] = await Promise.all([
        consultarPainelSaldos(filtrosAtuais),
        listarMovimentacoesSaldo(filtrosAtuais),
        carregarOpcoesProducaoSaldo(),
      ]);
      setPainel(dadosPainel);
      setMovimentos(dadosMovimentos.slice(0, 30));
      setCadpros(opcoes.cadpros);
      setArmazens(opcoes.armazens);
      setLotes(opcoes.lotes);
    } catch (falha) {
      setErro(mensagemErro(falha));
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => { void carregar(filtrosVazios); }, []);

  const armazensFiltrados = useMemo(
    () => armazens.filter(
      (item) => !filtros.propriedade || String(item.propriedade) === filtros.propriedade,
    ),
    [armazens, filtros.propriedade],
  );

  const lotesAtivos = useMemo(
    () => lotes.filter((item) => item.ativo && item.cad_pro),
    [lotes],
  );

  async function registrarProducao(evento: FormEvent) {
    evento.preventDefault();
    if (controladorCredito.current.emAndamento()) return;
    setErro("");
    setSucesso("");
    setCreditando(true);
    try {
      const resultado = await controladorCredito.current.enviar(
        credito,
        creditarProducao,
      );
      setSucesso(
        resultado.idempotente
          ? "Produção já registrada anteriormente."
          : "Produção registrada no ledger oficial.",
      );
      setCredito(creditoVazio);
      await carregar();
    } catch (falha) {
      setErro(mensagemErro(falha));
    } finally {
      setCreditando(false);
    }
  }

  return (
    <section className="modulo-producao-saldos">
      <div>
        <span className="kicker">Ledger oficial por CAD/PRO</span>
        <h2>Produção e saldos</h2>
        <p>Consulte físico, comprometido e disponível por cultura, safra, classificação e armazenagem.</p>
      </div>
      {erro && <p className="erro card" role="alert">{erro}</p>}
      {sucesso && <p className="sucesso card">{sucesso}</p>}

      <form className="card filtros-saldos" onSubmit={(evento) => { evento.preventDefault(); void carregar(); }}>
        <select aria-label="Filtrar saldo por propriedade" value={filtros.propriedade} onChange={(e) => setFiltros({ ...filtros, propriedade: e.target.value, armazem: "" })}><option value="">Todas as propriedades</option>{propriedades.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select>
        <select aria-label="Filtrar saldo por CAD/PRO" value={filtros.cad_pro} onChange={(e) => setFiltros({ ...filtros, cad_pro: e.target.value })}><option value="">Todos os CAD/PROs</option>{cadpros.map((item) => <option key={item.id} value={item.id}>{item.codigo}</option>)}</select>
        <input aria-label="Filtrar saldo por cultura" placeholder="Cultura" value={filtros.cultura} onChange={(e) => setFiltros({ ...filtros, cultura: e.target.value })} />
        <input aria-label="Filtrar saldo por safra" placeholder="Safra" value={filtros.safra} onChange={(e) => setFiltros({ ...filtros, safra: e.target.value })} />
        <input aria-label="Filtrar saldo por classificação" placeholder="Classificação" value={filtros.classificacao_codigo} onChange={(e) => setFiltros({ ...filtros, classificacao_codigo: e.target.value })} />
        <select aria-label="Filtrar saldo por armazenagem" value={filtros.armazem} onChange={(e) => setFiltros({ ...filtros, armazem: e.target.value })}><option value="">Todas as armazenagens</option>{armazensFiltrados.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select>
        <button disabled={carregando} type="submit">Aplicar filtros</button>
        <button className="secundario" type="button" onClick={() => { setFiltros(filtrosVazios); void carregar(filtrosVazios); }}>Limpar</button>
      </form>

      <section className="resumo-saldos">
        <article className="card"><span>Saldo físico</span><strong>{kg(painel?.resumo.saldo_fisico_kg ?? "0")}</strong></article>
        <article className="card"><span>Comprometido</span><strong>{kg(painel?.resumo.saldo_comprometido_kg ?? "0")}</strong></article>
        <article className="card destaque-disponivel"><span>Disponível</span><strong>{kg(painel?.resumo.saldo_disponivel_kg ?? "0")}</strong></article>
        <article className="card"><span>CAD/PROs · posições</span><strong>{painel?.resumo.cadpros ?? 0} · {painel?.resumo.posicoes ?? 0}</strong></article>
      </section>

      <section className="grade producao-saldos-grade">
        <form className="card formulario" onSubmit={registrarProducao}>
          <h3>Registrar produção</h3>
          <p>O crédito usa o lote e os bloqueios canônicos já validados pelo núcleo de Grãos.</p>
          <label>Lote<select required value={credito.lote || ""} onChange={(e) => setCredito({ ...credito, lote: Number(e.target.value) })}><option value="">Selecione</option>{lotesAtivos.map((item) => <option key={item.id} value={item.id}>{item.codigo} · {item.cad_pro_codigo} · {item.cultura} {item.safra} · {item.classificacao_codigo} · {item.armazem_nome}</option>)}</select></label>
          <label>Quantidade líquida (kg)<input required min="0.001" step="0.001" type="number" value={credito.quantidade_kg} onChange={(e) => setCredito({ ...credito, quantidade_kg: e.target.value })} /></label>
          <label>Data do movimento<input required type="date" value={credito.data_movimento} onChange={(e) => setCredito({ ...credito, data_movimento: e.target.value })} /></label>
          <label>Referência externa<input maxLength={160} placeholder="Romaneio, ticket ou documento" value={credito.referencia_externa} onChange={(e) => setCredito({ ...credito, referencia_externa: e.target.value })} /></label>
          <label>Observações<textarea value={credito.observacoes} onChange={(e) => setCredito({ ...credito, observacoes: e.target.value })} /></label>
          <BotaoCreditarProducao desabilitado={carregando || creditando} />
        </form>

        <section className="conteudo saldo-consolidado">
          <h3>Consolidado por CAD/PRO</h3>
          <div className="lista">{painel?.consolidado_cadpro.length ? painel.consolidado_cadpro.map((item) => <article className="card item saldo-cadpro" key={item.cad_pro}><div><span className="kicker">{item.cad_pro_codigo}</span><h3>{item.cad_pro_descricao}</h3><p>{item.posicoes} posição(ões) nas dimensões filtradas</p></div><div className="metricas-saldo"><span>Físico <strong>{kg(item.saldo_fisico_kg)}</strong></span><span>Comprometido <strong>{kg(item.saldo_comprometido_kg)}</strong></span><span>Disponível <strong>{kg(item.saldo_disponivel_kg)}</strong></span></div></article>) : <div className="card vazio">Nenhum saldo encontrado.</div>}</div>
        </section>
      </section>

      <section className="card tabela-saldos">
        <h3>Posições por cultura · safra · classificação · armazenagem</h3>
        <div className="tabela-scroll"><table><thead><tr><th>CAD/PRO</th><th>Cultura</th><th>Safra</th><th>Classificação</th><th>Armazenagem</th><th>Físico</th><th>Comprometido</th><th>Disponível</th><th>Versão</th></tr></thead><tbody>{painel?.posicoes.map((item) => <tr key={item.id}><td>{item.cad_pro_codigo}</td><td>{item.cultura}</td><td>{item.safra}</td><td>{item.classificacao_codigo}</td><td>{item.armazem_nome}</td><td>{kg(item.saldo_fisico_kg)}</td><td>{kg(item.saldo_comprometido_kg)}</td><td><strong>{kg(item.saldo_disponivel_kg)}</strong></td><td>{item.versao}</td></tr>)}</tbody></table></div>
      </section>

      <section className="card rastreabilidade-saldos">
        <h3>Rastreabilidade recente</h3>
        <div className="lista">{movimentos.length ? movimentos.map((item) => <article className="movimento-saldo" key={item.id}><div><span className="kicker">{item.data_movimento} · {item.operacao.split("_").join(" ")}</span><strong>{item.cad_pro_codigo} · {item.lote_codigo}</strong><small>{item.cultura} {item.safra} · {item.classificacao_codigo} · {item.armazem_nome}</small></div><div><strong>{numero(item.delta_fisico_kg) >= 0 ? "+" : ""}{kg(item.delta_fisico_kg)}</strong><small>{item.referencia_externa || item.origem_chave_idempotencia}</small></div></article>) : <p>Nenhuma movimentação encontrada.</p>}</div>
      </section>
    </section>
  );
}
