import { useRascunhoAutomatico } from "../../components/RascunhoAutomatico";
import { useAlteracoesNaoSalvas } from "../../components/AlteracoesNaoSalvas";
import ConferenciaSaldo from "../../components/ConferenciaSaldo";
import { useEntradaPainel } from "../../components/AcoesContext";
import FiltrosFavoritos from "../../components/FiltrosFavoritos";
import { BotaoAcao } from "../../components/AcoesContext";
import axios from "axios";
import PainelFormulario from "../../components/PainelFormulario";
import { formatarData } from "../../utils/datas";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { Propriedade, rotuloPropriedade } from "../../api/propriedades";
import {
  carregarOpcoesProducaoSaldo,
  consultarPainelSaldos,
  creditarProducao,
  FiltrosSaldo,
  listarMovimentacoesSaldo,
  LoteGraos,
  MovimentacaoSaldo,
  PainelSaldos,
  PosicaoSaldo,
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

export function numeroPlanilhaSaldo(valor: string | number) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  });
}

export function identificacaoPosicaoSaldo(
  posicao: Pick<PosicaoSaldo, "propriedade_id" | "propriedade_nome" | "cad_pro_codigo">,
  propriedades: Pick<Propriedade, "id" | "proprietario">[],
) {
  const proprietario = propriedades.find(
    item => item.id === posicao.propriedade_id,
  )?.proprietario?.trim();
  return [
    posicao.propriedade_nome || "Produção histórica sem propriedade",
    posicao.cad_pro_codigo,
    proprietario,
  ].filter(Boolean).join(" - ");
}

export function TabelaImpressaoSaldos({
  posicoes,
  propriedades,
}: {
  posicoes: PosicaoSaldo[];
  propriedades: Pick<Propriedade, "id" | "proprietario">[];
}) {
  const totais = posicoes.reduce((acumulado, item) => ({
    fisico: acumulado.fisico + numero(item.saldo_fisico_kg),
    comprometido: acumulado.comprometido + numero(item.saldo_comprometido_kg),
    disponivel: acumulado.disponivel + numero(item.saldo_disponivel_kg),
  }), { fisico: 0, comprometido: 0, disponivel: 0 });
  return <div className="tabela-responsiva"><table className="tabela-relatorio tabela-controle producao-saldos-planilha">
    <caption>Posições de produção e totais dos filtros aplicados</caption>
    <thead><tr><th className="coluna-saldo-origem">Propriedade / CAD-PRO / proprietário</th><th>Cultura</th><th>Safra</th><th>Armazenagem</th><th>Físico (kg)</th><th>Comprometido (kg)</th><th>Disponível (kg)</th></tr></thead>
    <tbody>{posicoes.length ? posicoes.map(item => <tr key={`saldo-impressao-${item.id}`}><td>{identificacaoPosicaoSaldo(item, propriedades)}</td><td>{item.cultura}</td><td>{item.safra}</td><td>{item.armazem_nome}</td><td>{numeroPlanilhaSaldo(item.saldo_fisico_kg)}</td><td>{numeroPlanilhaSaldo(item.saldo_comprometido_kg)}</td><td><strong>{numeroPlanilhaSaldo(item.saldo_disponivel_kg)}</strong></td></tr>) : <tr><td colSpan={7}>Nenhuma posição encontrada para os filtros informados.</td></tr>}</tbody>
    {posicoes.length > 0 && <tfoot><tr><td><strong>TOTAL</strong><small>Total das posições impressas</small></td><td>—</td><td>—</td><td>—</td><td><strong>{numeroPlanilhaSaldo(totais.fisico)}</strong></td><td><strong>{numeroPlanilhaSaldo(totais.comprometido)}</strong></td><td><strong>{numeroPlanilhaSaldo(totais.disponivel)}</strong></td></tr></tfoot>}
  </table></div>;
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

export function filtrarLotesProducao(lotes: LoteGraos[], filtros: FiltrosSaldo = {}) {
  return lotes.filter((lote) =>
    lote.ativo
    && lote.cad_pro
    && (!filtros.propriedade || String(lote.propriedade_id) === filtros.propriedade)
    && (!filtros.cad_pro || lote.cad_pro === filtros.cad_pro)
    && (!filtros.cultura || lote.cultura.toLowerCase() === filtros.cultura.trim().toLowerCase())
    && (!filtros.safra || lote.safra === filtros.safra.trim())
    && (!filtros.classificacao_codigo || lote.classificacao_codigo === filtros.classificacao_codigo.trim().toUpperCase())
    && (!filtros.armazem || String(lote.armazem) === filtros.armazem)
  );
}

export function BotaoCreditarProducao({ desabilitado, motivoBloqueio }: { desabilitado: boolean; motivoBloqueio?: string }) {
  return <BotaoAcao acao="cadastrar" disabled={desabilitado} motivoBloqueio={motivoBloqueio} type="submit">Creditar produção</BotaoAcao>;
}

export function mesmosFiltrosSaldo(a: FiltrosSaldo, b: FiltrosSaldo) {
  return (Object.keys(filtrosVazios) as (keyof FiltrosSaldo)[]).every(chave => (a[chave] || "") === (b[chave] || ""));
}

export default function ProducaoSaldosPage({ propriedades }: Props) {
  const [conferencia, setConferencia] = useState<number | null>(null);
  const entradaPainel = useEntradaPainel("producao-saldos");
  const [painel, setPainel] = useState<PainelSaldos | null>(null);
  const [movimentos, setMovimentos] = useState<MovimentacaoSaldo[]>([]);
  const [cadpros, setCadpros] = useState<CADPro[]>([]);
  const [armazens, setArmazens] = useState<ArmazemGraos[]>([]);
  const [lotes, setLotes] = useState<LoteGraos[]>([]);
  const [filtros, setFiltros] = useState<FiltrosSaldo>(filtrosVazios);
  const [filtrosAplicados, setFiltrosAplicados] = useState<FiltrosSaldo>(filtrosVazios);
  const ultimaConsulta = useRef(0);
  const [credito, setCredito] = useState(creditoVazio);
  const protecao = useAlteracoesNaoSalvas(credito, "Crédito de produção");
  const [carregando, setCarregando] = useState(false);
  const [creditando, setCreditando] = useState(false);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const controladorCredito = useRef(criarControladorCreditoProducao());

  const rascunho = useRascunhoAutomatico("producao-saldos", {credito}, salvo => setCredito({...creditoVazio,...salvo.credito}));
  async function carregar(filtrosAtuais = filtros) {
    const consulta = ++ultimaConsulta.current;
    setCarregando(true);
    setErro("");
    try {
      const [dadosPainel, dadosMovimentos, opcoes] = await Promise.all([
        consultarPainelSaldos(filtrosAtuais),
        listarMovimentacoesSaldo(filtrosAtuais),
        carregarOpcoesProducaoSaldo(),
      ]);
      if (consulta !== ultimaConsulta.current) return;
      setPainel(dadosPainel);
      setFiltrosAplicados({ ...filtrosAtuais });
      setMovimentos(dadosMovimentos.slice(0, 30));
      setCadpros(opcoes.cadpros);
      setArmazens(opcoes.armazens);
      setLotes(opcoes.lotes);
    } catch (falha) {
      if (consulta === ultimaConsulta.current) setErro(mensagemErro(falha));
    } finally {
      if (consulta === ultimaConsulta.current) setCarregando(false);
    }
  }

  useEffect(() => { if (!entradaPainel) void carregar(filtrosVazios); }, []);

  const cadprosFiltrados = useMemo(
    () => cadpros.filter((item) =>
      !filtros.propriedade
      || item.propriedades.includes(Number(filtros.propriedade))
    ),
    [cadpros, filtros.propriedade],
  );

  const lotesAtivos = useMemo(
    () => filtrarLotesProducao(lotes, filtros),
    [lotes, filtros],
  );
  const loteCreditoValido = lotesAtivos.some((item) => item.id === credito.lote);
  const propriedadeSelecionada = propriedades.find(
    (item) => String(item.id) === filtrosAplicados.propriedade,
  );
  const filtrosPendentes = !mesmosFiltrosSaldo(filtros, filtrosAplicados);
  const posicoesImpressao = painel?.posicoes ?? [];
  const propriedadesImpressao = [...new Set(posicoesImpressao.map(
    item => item.propriedade_nome || "Produção histórica sem propriedade",
  ))];
  const cadprosImpressao = [...new Set(posicoesImpressao.map(item => item.cad_pro_codigo))];
  const culturasImpressao = [...new Set(posicoesImpressao.map(item => item.cultura))];
  const safrasImpressao = [...new Set(posicoesImpressao.map(item => item.safra))];

  async function registrarProducao(evento: FormEvent) {
    evento.preventDefault();
    if (controladorCredito.current.emAndamento()) return;
    if (!loteCreditoValido) {
      setErro("Selecione um lote compatível com os filtros antes de creditar a produção.");
      return;
    }
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
      rascunho.limpar({credito:creditoVazio});
      setCredito(creditoVazio);
      protecao.marcarSalvo(creditoVazio);
      await carregar();
    } catch (falha) {
      setErro(mensagemErro(falha));
    } finally {
      setCreditando(false);
    }
  }

  return (
    <section className="modulo-producao-saldos">
      <FiltrosFavoritos contexto="producao-saldos" filtros={filtros} aplicar={valores => {const proximos = {...filtrosVazios, ...valores}; setFiltros(proximos); void carregar(proximos);}} />
      <div>
        <span className="kicker">Ledger oficial por CAD/PRO</span>
        <h2>Produção e saldos</h2>
        <p>Consulte físico, comprometido e disponível por cultura, safra, classificação e armazenagem.</p>
      </div>
      {erro && <p className="erro card" role="alert">{erro}</p>}
      {sucesso && <p className="sucesso card" role="status">{sucesso}</p>}

      <section className="card controle-planilha controle-planilha-impressao controle-planilha-producao somente-impressao" hidden={carregando || filtrosPendentes}>
        <h2 className="somente-impressao titulo-impressao-planilha">Produção e saldos</h2>
        <div className="controle-planilha-titulo"><div><span className="kicker">Controle de produção e estoque</span><h3>{propriedadesImpressao.join(" · ") || "Todas as propriedades"}</h3><p>CAD/PRO {cadprosImpressao.join(", ") || "—"} · {culturasImpressao.join(", ") || "todas as culturas"} · safra {safrasImpressao.join(", ") || "todas"}</p></div><div className="controle-planilha-total"><span>Saldo disponível</span><strong>{kg(painel?.resumo.saldo_disponivel_kg ?? "0")}</strong><small>Físico {kg(painel?.resumo.saldo_fisico_kg ?? "0")} · comprometido {kg(painel?.resumo.saldo_comprometido_kg ?? "0")}</small></div></div>
        <TabelaImpressaoSaldos posicoes={posicoesImpressao} propriedades={propriedades} />
      </section>

      <form className="card filtros-saldos" onSubmit={(evento) => { evento.preventDefault(); void carregar(); }}>
        <select aria-label="Filtrar saldo por propriedade" value={filtros.propriedade} onChange={(e) => { const propriedade = e.target.value; const cadproAtualValido = cadpros.some((item) => item.id === filtros.cad_pro && (!propriedade || item.propriedades.includes(Number(propriedade)))); const novos = { ...filtros, propriedade, cad_pro: cadproAtualValido ? filtros.cad_pro : "" }; setFiltros(novos); setCredito(atual => ({ ...atual, lote: 0 })); void carregar(novos); }}><option value="">Todas as propriedades</option>{propriedades.map((item) => <option key={item.id} value={item.id}>{rotuloPropriedade(item)}</option>)}</select>
        <select aria-label="Filtrar saldo por CAD/PRO" value={filtros.cad_pro} onChange={(e) => setFiltros({ ...filtros, cad_pro: e.target.value })}><option value="">Todos os CAD/PROs da propriedade</option>{cadprosFiltrados.map((item) => <option key={item.id} value={item.id}>{item.codigo}</option>)}</select>
        <input aria-label="Filtrar saldo por cultura" placeholder="Cultura" value={filtros.cultura} onChange={(e) => setFiltros({ ...filtros, cultura: e.target.value })} />
        <input aria-label="Filtrar saldo por safra" placeholder="Safra" value={filtros.safra} onChange={(e) => setFiltros({ ...filtros, safra: e.target.value })} />
        <input aria-label="Filtrar saldo por classificação" placeholder="Classificação" value={filtros.classificacao_codigo} onChange={(e) => setFiltros({ ...filtros, classificacao_codigo: e.target.value })} />
        <select aria-label="Filtrar saldo por armazenagem" value={filtros.armazem} onChange={(e) => setFiltros({ ...filtros, armazem: e.target.value })}><option value="">Todas as armazenagens</option>{armazens.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select>
        <button disabled={carregando} type="submit">Aplicar filtros</button>
        <button className="secundario" type="button" onClick={() => { setFiltros(filtrosVazios); void carregar(filtrosVazios); }}>Limpar</button>
      </form>

      {carregando ? <p role="status">Atualizando saldos da consulta...</p> : filtrosPendentes && <p role="status">Filtros alterados. Clique em Aplicar filtros para consultar os saldos selecionados.</p>}
      <div hidden={carregando || filtrosPendentes}>
      <section className="resumo-saldos">
        <article className="card"><span>Saldo físico</span><strong>{kg(painel?.resumo.saldo_fisico_kg ?? "0")}</strong></article>
        <article className="card"><span>Comprometido</span><strong>{kg(painel?.resumo.saldo_comprometido_kg ?? "0")}</strong></article>
        <article className="card destaque-disponivel"><span>Disponível</span><strong>{kg(painel?.resumo.saldo_disponivel_kg ?? "0")}</strong></article>
        <article className="card"><span>Propriedades · CAD/PROs · posições</span><strong>{painel?.resumo.propriedades ?? 0} · {painel?.resumo.cadpros ?? 0} · {painel?.resumo.posicoes ?? 0}</strong><small>Na consulta atual</small></article>
      </section>

      <section className="grade producao-saldos-grade">
        <PainelFormulario titulo="Registrar produção">
        {rascunho.aviso}
        <form className="card formulario" onSubmit={registrarProducao}>
          <h3>Registrar produção</h3>
          <p>Selecione um lote compatível com os filtros da consulta para registrar a produção.</p>
          <label>Lote<select required value={credito.lote || ""} onChange={(e) => setCredito({ ...credito, lote: Number(e.target.value) })}><option value="">Selecione</option>{lotesAtivos.map((item) => <option key={item.id} value={item.id}>{item.codigo} · {item.cad_pro_codigo} · {item.cultura} {item.safra} · {item.classificacao_codigo} · {item.armazem_nome}</option>)}</select></label>
          <label>Quantidade líquida (kg)<input required min="0.001" step="0.001" type="number" value={credito.quantidade_kg} onChange={(e) => setCredito({ ...credito, quantidade_kg: e.target.value })} /></label>
          <label>Data do movimento<input required type="date" value={credito.data_movimento} onChange={(e) => setCredito({ ...credito, data_movimento: e.target.value })} /></label>
          <label>Referência externa<input maxLength={160} placeholder="Romaneio, ticket ou documento" value={credito.referencia_externa} onChange={(e) => setCredito({ ...credito, referencia_externa: e.target.value })} /></label>
          <label>Observações<textarea value={credito.observacoes} onChange={(e) => setCredito({ ...credito, observacoes: e.target.value })} /></label>
          <BotaoCreditarProducao desabilitado={carregando || creditando || !loteCreditoValido} motivoBloqueio={carregando ? "Aguarde o carregamento." : creditando ? "Aguarde o processamento." : "Selecione um lote compatível com os filtros."} />
        </form>

        </PainelFormulario>
        <section className="conteudo saldo-consolidado">
          <h3>{propriedadeSelecionada ? `Produção de ${propriedadeSelecionada.nome}` : "Consolidado por propriedade"}</h3>
          <div className="lista">{painel?.consolidado_propriedade?.length ? painel.consolidado_propriedade.map((item) => <article className="card item saldo-cadpro" key={item.propriedade ?? "historico"}><div><span className="kicker">CAD/PRO {item.cadpros.map(c => c.codigo).join(" · ")}</span><h3>{item.propriedade_nome}</h3><p>{item.posicoes} posição(ões) nas dimensões filtradas</p></div><div className="metricas-saldo"><span>Físico <strong>{kg(item.saldo_fisico_kg)}</strong></span><span>Comprometido <strong>{kg(item.saldo_comprometido_kg)}</strong></span><span>Disponível <strong>{kg(item.saldo_disponivel_kg)}</strong></span></div></article>) : <div className="card vazio">Nenhum saldo encontrado.</div>}</div>
        </section>
      </section>

      <section className="card tabela-saldos">
        <h3>Posições por cultura · safra · classificação · armazenagem</h3>
        <div className="tabela-scroll"><table><thead><tr><th>Propriedade produtora</th><th>CAD/PRO</th><th>Cultura</th><th>Safra</th><th>Classificação</th><th>Armazenagem</th><th>Físico</th><th>Comprometido</th><th>Disponível</th><th>Versão</th><th>Conferência</th></tr></thead><tbody>{painel?.posicoes.map((item) => <tr key={item.id}><td>{item.propriedade_nome || "Produção histórica sem propriedade"}</td><td>{item.cad_pro_codigo}</td><td>{item.cultura}</td><td>{item.safra}</td><td>{item.classificacao_codigo}</td><td>{item.armazem_nome}</td><td>{kg(item.saldo_fisico_kg)}</td><td>{kg(item.saldo_comprometido_kg)}</td><td><strong>{kg(item.saldo_disponivel_kg)}</strong></td><td>{item.versao}</td><td><button type="button" className="secundario" onClick={() => setConferencia(item.id)}>Conferir saldo</button></td></tr>)}</tbody></table></div>
      </section>

      {conferencia !== null && <><button type="button" className="secundario nao-imprimir" onClick={() => setConferencia(null)}>Fechar conferência</button><ConferenciaSaldo key={conferencia} posicao={conferencia} atualizar={() => void carregar()} /></>}
      <section className="card rastreabilidade-saldos">
        <h3>Rastreabilidade recente</h3>
        <div className="lista">{movimentos.length ? movimentos.map((item) => <article className="movimento-saldo" key={item.id}><div><span className="kicker">{formatarData(item.data_movimento)} · {item.operacao.split("_").join(" ")}</span><strong>{item.cad_pro_codigo} · {item.lote_codigo}</strong><small>{item.cultura} {item.safra} · {item.classificacao_codigo} · {item.armazem_nome}</small></div><div><strong>{numero(item.delta_fisico_kg) >= 0 ? "+" : ""}{kg(item.delta_fisico_kg)}</strong><small>{item.referencia_externa || item.origem_chave_idempotencia}</small></div></article>) : <p>Nenhuma movimentação encontrada.</p>}</div>
      </section>
      </div>
    </section>
  );
}
