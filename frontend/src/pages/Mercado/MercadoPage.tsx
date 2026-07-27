import axios from "axios";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  atualizarCornBelt,
  atualizarMercadoEnterprise,
  carregarPainelMercado,
  carregarPainelMercadoEnterprise,
  carregarSerieMercado,
  type AtivoMercado,
  type ClimaCornBelt,
  type JanelaMercado,
  type NoticiaMercado,
  type PainelMercadoEnterprise,
  type PontoMercadoEnterprise,
} from "../../api/mercado";
import type { Propriedade } from "../../api/propriedades";
import {
  AlertCard,
  Badge,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  ResponsiveGrid,
  SectionCard,
  StatCard,
} from "../../components/shared/ui";
import GraficoMercado from "./GraficoMercado";

import "./mercado.css";


const ATIVOS: Array<{ id: AtivoMercado; nome: string }> = [
  { id: "soja_cbot", nome: "Soja CBOT" },
  { id: "milho_cbot", nome: "Milho CBOT" },
  { id: "trigo_cbot", nome: "Trigo CBOT" },
  { id: "farelo_soja", nome: "Farelo de soja" },
  { id: "oleo_soja", nome: "Óleo de soja" },
  { id: "brent", nome: "Petróleo Brent" },
  { id: "dolar", nome: "Dólar PTAX" },
];

const numero = (valor: string | number | null | undefined, casas = 2) => Number(valor || 0).toLocaleString("pt-BR", { maximumFractionDigits: casas });
const dataHora = (valor: string | null | undefined) => valor ? new Date(valor).toLocaleString("pt-BR") : "Não disponível";

function mensagemErro(falha: unknown) {
  if (axios.isAxiosError(falha) && typeof falha.response?.data?.detail === "string") {
    return falha.response.data.detail;
  }
  return "Não foi possível carregar o painel automático de mercado.";
}

export default function MercadoPage({ selectedProperty = null }: { selectedProperty?: Propriedade | null }) {
  const [painel, setPainel] = useState<PainelMercadoEnterprise | null>(null);
  const [serie, setSerie] = useState<PontoMercadoEnterprise[]>([]);
  const [clima, setClima] = useState<ClimaCornBelt[]>([]);
  const [noticias, setNoticias] = useState<NoticiaMercado[]>([]);
  const [ativo, setAtivo] = useState<AtivoMercado>("soja_cbot");
  const [janela, setJanela] = useState<JanelaMercado>("30d");
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const carregar = useCallback(async () => {
    setLoading(true);
    setError("");
    const [resultadoPainel, resultadoLegado, resultadoSerie] = await Promise.allSettled([
      carregarPainelMercadoEnterprise(selectedProperty?.id),
      carregarPainelMercado(),
      carregarSerieMercado(ativo, janela),
    ]);
    const erros: string[] = [];
    if (resultadoPainel.status === "fulfilled") setPainel(resultadoPainel.value);
    else { setPainel(null); erros.push(mensagemErro(resultadoPainel.reason)); }
    if (resultadoLegado.status === "fulfilled") {
      setClima(resultadoLegado.value.clima);
      setNoticias(resultadoLegado.value.noticias);
    } else {
      setClima([]);
      setNoticias([]);
      erros.push("Clima do Corn Belt e notícias estão temporariamente indisponíveis.");
    }
    if (resultadoSerie.status === "fulfilled") setSerie(resultadoSerie.value);
    else { setSerie([]); erros.push("A série histórica selecionada está indisponível."); }
    setError(erros.join(" "));
    setLoading(false);
  }, [ativo, janela, selectedProperty?.id]);

  useEffect(() => { void carregar(); }, [carregar]);

  async function atualizarMercado(ativoSelecionado?: AtivoMercado) {
    setUpdating(true);
    setError("");
    setSuccess("");
    try {
      await atualizarMercadoEnterprise(ativoSelecionado);
      setSuccess(ativoSelecionado ? "Ativo atualizado." : "Atualização de todos os ativos concluída.");
      await carregar();
    } catch (falha) {
      setError(mensagemErro(falha));
    } finally {
      setUpdating(false);
    }
  }

  async function atualizarClima() {
    setUpdating(true);
    setError("");
    try {
      await atualizarCornBelt();
      setSuccess("Clima do Corn Belt atualizado.");
      await carregar();
    } catch (falha) {
      setError(mensagemErro(falha));
    } finally {
      setUpdating(false);
    }
  }

  const resumoSelecionado = painel?.ativos.find((item) => item.ativo === ativo);
  const climaPorRegiao = useMemo(() => {
    const grupos = new Map<string, ClimaCornBelt[]>();
    clima.forEach((item) => grupos.set(item.regiao, [...(grupos.get(item.regiao) ?? []), item]));
    return [...grupos.values()];
  }, [clima]);

  if (loading && !painel) return <LoadingState label="Carregando mercado e fatores integrados..." />;
  if (!painel && error) return <ErrorState description={error} onRetry={() => void carregar()} />;

  return (
    <section className="market-enterprise-page">
      <PageHeader
        eyebrow="Mercado e comercialização"
        title="Painel de mercado"
        description={`Cotações automáticas, Corn Belt e análise operacional${selectedProperty ? ` · ${selectedProperty.nome}` : " · contexto autorizado consolidado"}.`}
        actions={<div className="market-actions"><button type="button" disabled={updating} onClick={() => void atualizarMercado()}>{updating ? "Atualizando..." : "Atualizar ativos"}</button><button className="secundario" type="button" disabled={updating} onClick={() => void atualizarClima()}>Atualizar Corn Belt</button></div>}
      />

      {error && <AlertCard title="Carregamento parcial" tone="warning"><p>{error}</p></AlertCard>}
      {success && <AlertCard title="Atualização concluída" tone="success"><p>{success}</p></AlertCard>}

      <ResponsiveGrid className="market-asset-grid">
        {painel?.ativos.map((item) => (
          <button type="button" className={`market-asset-card ${ativo === item.ativo ? "is-active" : ""}`} key={item.ativo} onClick={() => setAtivo(item.ativo)}>
            <span>{item.ativo_nome}</span>
            {item.disponivel ? <>
              <strong>{numero(item.cotacao_atual, 4)}</strong>
              <small>{item.unidade} · {item.fonte}</small>
              <Badge tone={Number(item.variacao_diaria || 0) >= 0 ? "success" : "danger"}>{item.variacao_diaria ?? "—"}%</Badge>
              {item.desatualizado && <Badge tone="warning">Desatualizado</Badge>}
            </> : <><strong>—</strong><small>{item.mensagem || "Aguardando atualização"}</small><Badge tone="warning">{item.status}</Badge></>}
          </button>
        ))}
      </ResponsiveGrid>

      {resumoSelecionado?.disponivel && (
        <ResponsiveGrid className="stat-grid market-detail-grid">
          <StatCard label="Cotação atual" value={numero(resumoSelecionado.cotacao_atual, 4)} detail={resumoSelecionado.unidade} tone="info" />
          <StatCard label="Máxima" value={numero(resumoSelecionado.maxima, 4)} />
          <StatCard label="Mínima" value={numero(resumoSelecionado.minima, 4)} />
          <StatCard label="Variação diária" value={`${resumoSelecionado.variacao_diaria ?? "—"}%`} tone={Number(resumoSelecionado.variacao_diaria || 0) >= 0 ? "success" : "danger"} />
          <StatCard label="Horário do dado" value={dataHora(resumoSelecionado.data_hora)} detail={resumoSelecionado.fonte} />
          <StatCard label="Próxima atualização" value={dataHora(resumoSelecionado.proxima_atualizacao)} detail={resumoSelecionado.status} />
        </ResponsiveGrid>
      )}

      <SectionCard title={resumoSelecionado?.ativo_nome || "Histórico"} description="Série persistida pelo backend; indisponibilidade da fonte não apaga o último dado válido." actions={<div className="market-window-tabs">{(["intraday", "5d", "30d"] as JanelaMercado[]).map((item) => <button type="button" className={janela === item ? "is-active" : "secundario"} key={item} onClick={() => setJanela(item)}>{item === "intraday" ? "Intradiário" : item === "5d" ? "5 dias" : "30 dias"}</button>)}<button type="button" disabled={updating} onClick={() => void atualizarMercado(ativo)}>Atualizar este ativo</button></div>}>
        <GraficoMercado pontos={serie} titulo={resumoSelecionado?.ativo_nome || ativo} />
      </SectionCard>

      {painel?.analise && (
        <div className="market-analysis-columns">
          <SectionCard title="Análise automática integrada" description={`Tendência de curto prazo: ${painel.analise.tendencia_curto_prazo}.`}>
            <AlertCard title="Recomendação operacional" tone="info"><p>{painel.analise.recomendacao_operacional}</p><small>{painel.analise.aviso}</small></AlertCard>
            <div className="market-impact-list">{painel.analise.impactos.map((item, index) => <article key={`${item.fator}-${index}`}><Badge tone={item.direcao === "alta" ? "success" : "danger"}>{item.direcao}</Badge><div><strong>{item.fator}</strong><p>{item.descricao}</p></div></article>)}</div>
          </SectionCard>
          <SectionCard title="Fatores de alta e baixa">
            <div className="market-factor-columns"><div><h3>Fatores de alta</h3>{painel.analise.fatores_alta.length ? <ul>{painel.analise.fatores_alta.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="muted">Nenhum fator de alta identificado.</p>}</div><div><h3>Fatores de baixa</h3>{painel.analise.fatores_baixa.length ? <ul>{painel.analise.fatores_baixa.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="muted">Nenhum fator de baixa identificado.</p>}</div></div>
          </SectionCard>
        </div>
      )}

      <SectionCard title="Clima no Corn Belt" description="Previsão de sete dias das regiões monitoradas e seus riscos para oferta agrícola.">
        {climaPorRegiao.length === 0 ? <EmptyState title="Corn Belt sem dados" description="Execute a atualização manual ou aguarde o próximo ciclo." /> : <ResponsiveGrid className="market-corn-grid">{climaPorRegiao.map((previsoes) => { const proxima = previsoes[0]; const chuva = previsoes.reduce((total, item) => total + Number(item.precipitacao_mm), 0); const alerta = previsoes.find((item) => item.alerta); return <article className="market-corn-card" key={proxima.regiao}><span>{proxima.regiao_nome}</span><strong>{numero(chuva, 1)} mm</strong><small>{proxima.temperatura_min} °C a {proxima.temperatura_max} °C</small>{alerta && <Badge tone="warning">{alerta.alerta}</Badge>}</article>; })}</ResponsiveGrid>}
      </SectionCard>

      <SectionCard title="Fontes cadastradas" description="Notícias permanecem manuais para garantir origem verificável e evitar coleta externa não autorizada.">
        {noticias.length === 0 ? <EmptyState title="Nenhuma notícia ativa" /> : <div className="market-news-grid">{noticias.slice(0, 6).map((noticia) => <article key={noticia.id}><span>{noticia.fonte}</span><strong>{noticia.titulo}</strong><p>{noticia.resumo}</p><a href={noticia.url} rel="noreferrer" target="_blank">Abrir fonte</a></article>)}</div>}
      </SectionCard>
    </section>
  );
}
