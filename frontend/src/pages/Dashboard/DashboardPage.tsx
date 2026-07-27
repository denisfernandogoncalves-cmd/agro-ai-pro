import { useCallback, useEffect, useMemo, useState } from "react";

import { listarPrevisoes, obterStatusClima, type PrevisaoClima, type StatusClima } from "../../api/clima";
import { obterInsights } from "../../api/insights";
import { carregarPainelMercado, carregarPainelMercadoEnterprise } from "../../api/mercado";
import type { Propriedade } from "../../api/propriedades";
import { obterDashboard, type Dashboard } from "../../api/relatorios";
import {
  AlertCard,
  Badge,
  ErrorState,
  PageHeader,
  ResponsiveGrid,
  SectionCard,
  Skeleton,
  StatCard,
} from "../../components/shared/ui";


type MarketPanel = Awaited<ReturnType<typeof carregarPainelMercado>>;
type MarketEnterprisePanel = Awaited<ReturnType<typeof carregarPainelMercadoEnterprise>>;
type InsightPanel = Awaited<ReturnType<typeof obterInsights>>;

const currency = (value: string | number) => Number(value).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const hectares = (value: number) => `${value.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} ha`;
const dataHora = (value: string | null | undefined) => value
  ? new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }).format(new Date(value))
  : "Não disponível";

export default function DashboardPage({
  properties,
  selectedProperty,
  safra,
}: {
  properties: Propriedade[];
  selectedProperty: Propriedade | null;
  safra: string;
}) {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [market, setMarket] = useState<MarketPanel | null>(null);
  const [marketEnterprise, setMarketEnterprise] = useState<MarketEnterprisePanel | null>(null);
  const [insights, setInsights] = useState<InsightPanel | null>(null);
  const [weather, setWeather] = useState<PrevisaoClima[]>([]);
  const [weatherStatus, setWeatherStatus] = useState<StatusClima | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setErrors([]);
    const propertyId = selectedProperty ? String(selectedProperty.id) : "";
    const dashboardPromise = obterDashboard(propertyId, safra);
    const marketPromise = carregarPainelMercado();
    const marketEnterprisePromise = carregarPainelMercadoEnterprise(selectedProperty?.id);
    const insightsPromise = obterInsights(propertyId);
    const weatherPromise: Promise<PrevisaoClima[]> = selectedProperty
      ? listarPrevisoes(selectedProperty.id)
      : Promise.resolve([]);
    const weatherStatusPromise: Promise<StatusClima | null> = selectedProperty
      ? obterStatusClima(selectedProperty.id)
      : Promise.resolve(null);
    const [dashboardResult, marketResult, marketEnterpriseResult, insightsResult, weatherResult, weatherStatusResult] = await Promise.allSettled([
      dashboardPromise,
      marketPromise,
      marketEnterprisePromise,
      insightsPromise,
      weatherPromise,
      weatherStatusPromise,
    ] as const);
    const nextErrors: string[] = [];
    if (dashboardResult.status === "fulfilled") setDashboard(dashboardResult.value); else { setDashboard(null); nextErrors.push("Indicadores gerenciais indisponíveis."); }
    if (marketResult.status === "fulfilled") setMarket(marketResult.value); else { setMarket(null); nextErrors.push("Resumo legado de mercado indisponível."); }
    if (marketEnterpriseResult.status === "fulfilled") setMarketEnterprise(marketEnterpriseResult.value); else { setMarketEnterprise(null); nextErrors.push("Cotações automáticas indisponíveis."); }
    if (insightsResult.status === "fulfilled") setInsights(insightsResult.value); else { setInsights(null); nextErrors.push("Insights do assistente indisponíveis."); }
    if (weatherResult.status === "fulfilled") setWeather(weatherResult.value); else { setWeather([]); nextErrors.push("Previsão diária indisponível."); }
    if (weatherStatusResult.status === "fulfilled") setWeatherStatus(weatherStatusResult.value); else { setWeatherStatus(null); nextErrors.push("Clima atual indisponível."); }
    setErrors(nextErrors);
    setLoading(false);
  }, [safra, selectedProperty]);

  useEffect(() => { void load(); }, [load]);

  const scopedProperties = selectedProperty ? [selectedProperty] : properties;
  const declaredArea = useMemo(
    () => scopedProperties.reduce((sum, property) => sum + Number(property.area_hectares || 0), 0),
    [scopedProperties],
  );
  const calculatedArea = useMemo(
    () => scopedProperties.reduce((sum, property) => sum + Number(property.area_calculada_hectares || 0), 0),
    [scopedProperties],
  );
  const weatherAlerts = weather.filter((item) => item.alerta_agricola.trim());
  const nextRain = weather.reduce((sum, item) => sum + Number(item.chuva_mm || 0), 0);
  const enterpriseAssets = marketEnterprise?.ativos.filter((item) => item.disponivel).slice(0, 7) ?? [];

  if (loading && !dashboard) {
    return (
      <section className="dashboard-page">
        <PageHeader eyebrow="Visão executiva" title="Dashboard" description="Consolidando dados autorizados do ERP." />
        <ResponsiveGrid className="stat-grid">{Array.from({ length: 8 }, (_, index) => <article className="stat-card" key={index}><Skeleton className="skeleton--label" /><Skeleton className="skeleton--value" /></article>)}</ResponsiveGrid>
      </section>
    );
  }

  if (!dashboard && errors.length > 0) {
    return <ErrorState description={errors.join(" ")} onRetry={() => void load()} />;
  }

  return (
    <section className="dashboard-page">
      <PageHeader
        eyebrow="Visão executiva"
        title="Dashboard"
        description={`Dados reais das APIs existentes${selectedProperty ? ` para ${selectedProperty.nome}` : ""}${safra ? ` · safra ${safra}` : ""}.`}
        actions={<button type="button" disabled={loading} onClick={() => void load()}>{loading ? "Atualizando..." : "Atualizar"}</button>}
      />

      {errors.length > 0 && <AlertCard title="Carregamento parcial" tone="warning"><p>{errors.join(" ")}</p></AlertCard>}

      <ResponsiveGrid className="stat-grid">
        {dashboard && <StatCard label="Propriedades" value={dashboard.estrutura.propriedades} detail="Autorizadas no filtro atual" />}
        {dashboard && <StatCard label="Talhões" value={dashboard.estrutura.talhoes} detail={`${dashboard.estrutura.area_talhoes} ha cadastrados`} />}
        <StatCard label="Área declarada" value={hectares(declaredArea)} />
        {calculatedArea > 0 && <StatCard label="Área calculada" value={hectares(calculatedArea)} detail="Geometrias processadas" tone="info" />}
        {dashboard && <StatCard label="Operações planejadas" value={dashboard.operacoes.planejadas} />}
        {dashboard && <StatCard label="Em andamento" value={dashboard.operacoes.em_execucao} tone={dashboard.operacoes.em_execucao > 0 ? "warning" : "neutral"} />}
        {dashboard && <StatCard label="Concluídas" value={dashboard.operacoes.concluidas} tone="success" />}
        {dashboard && <StatCard label="Máquinas em manutenção" value={dashboard.maquinas.em_manutencao} tone={dashboard.maquinas.em_manutencao > 0 ? "warning" : "neutral"} />}
        {weatherStatus && <StatCard label="Temperatura atual" value={`${weatherStatus.atual.temperatura ?? "—"} °C`} detail={String(weatherStatus.atual.condicao ?? "Clima atual")} tone="info" />}
        {selectedProperty && weather.length > 0 && <StatCard label="Chuva prevista · 7 dias" value={`${nextRain.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mm`} />}
      </ResponsiveGrid>

      {dashboard && (
        <ResponsiveGrid className="stat-grid stat-grid--finance">
          <StatCard label="Contas a pagar" value={currency(dashboard.financeiro.a_pagar)} />
          <StatCard label="Contas a receber" value={currency(dashboard.financeiro.a_receber)} />
          <StatCard label="Saldo previsto" value={currency(dashboard.financeiro.saldo_previsto)} tone={Number(dashboard.financeiro.saldo_previsto) >= 0 ? "success" : "danger"} />
          <StatCard label="Valor vencido" value={currency(dashboard.financeiro.valor_atrasado)} tone={Number(dashboard.financeiro.valor_atrasado) > 0 ? "danger" : "neutral"} />
        </ResponsiveGrid>
      )}

      <div className="dashboard-columns">
        <SectionCard title="Alertas operacionais" description="Indicadores disponíveis no backend atual.">
          <div className="alert-list">
            {dashboard && dashboard.estoque.itens_abaixo_minimo > 0 && <AlertCard title="Estoque abaixo do mínimo" tone="danger"><p>{dashboard.estoque.itens_abaixo_minimo} item(ns) exigem atenção.</p></AlertCard>}
            {dashboard && dashboard.estoque.lotes_vencidos > 0 && <AlertCard title="Lotes vencidos" tone="danger"><p>{dashboard.estoque.lotes_vencidos} lote(s) vencido(s).</p></AlertCard>}
            {dashboard && dashboard.maquinas.manutencoes_pendentes > 0 && <AlertCard title="Manutenções pendentes"><p>{dashboard.maquinas.manutencoes_pendentes} manutenção(ões) pendente(s).</p></AlertCard>}
            {weatherAlerts.map((item) => <AlertCard key={item.id} title={`Clima · ${item.propriedade_nome}`}><p>{item.alerta_agricola}</p></AlertCard>)}
            {weatherStatus && weatherStatus.alertas_ativos > 0 && <AlertCard title="Notificações climáticas" tone="warning"><p>{weatherStatus.alertas_ativos} alerta(s) ativo(s) na propriedade selecionada.</p></AlertCard>}
            {dashboard && dashboard.estoque.itens_abaixo_minimo === 0 && dashboard.estoque.lotes_vencidos === 0 && dashboard.maquinas.manutencoes_pendentes === 0 && weatherAlerts.length === 0 && !weatherStatus?.alertas_ativos && <p className="muted">Nenhum alerta disponível no filtro atual.</p>}
          </div>
        </SectionCard>

        <SectionCard title="Clima automático" description={selectedProperty ? `Condições atuais de ${selectedProperty.nome}.` : "Selecione uma propriedade para detalhar o clima."}>
          {weatherStatus ? (
            <div className="market-summary-list">
              <article><span>Condição</span><strong>{String(weatherStatus.atual.condicao ?? "—")}</strong><small>Atualização {dataHora(weatherStatus.configuracao.ultima_atualizacao)}</small></article>
              <article><span>Pulverização</span><strong>{weatherStatus.proxima_hora?.condicao_pulverizacao || "—"}</strong><small>Próxima hora</small></article>
              <article><span>Colheita</span><strong>{weatherStatus.proxima_hora?.condicao_colheita || "—"}</strong><small>Próxima hora</small></article>
              <article><span>Próxima atualização</span><strong>{dataHora(weatherStatus.configuracao.proxima_atualizacao)}</strong><small>{weatherStatus.configuracao.desatualizado ? "Dados desatualizados" : "Sincronizado"}</small></article>
            </div>
          ) : <p className="muted">Clima detalhado disponível após selecionar uma propriedade localizada.</p>}
        </SectionCard>
      </div>

      <SectionCard title="Mercado automático" description={marketEnterprise ? `Tendência integrada: ${marketEnterprise.analise.tendencia_curto_prazo}.` : "Fallback para os registros legados do módulo Mercado."}>
        <div className="market-summary-list">
          {enterpriseAssets.length ? enterpriseAssets.map((item) => (
            <article key={item.ativo}>
              <span>{item.ativo_nome}</span>
              <strong>{Number(item.cotacao_atual).toLocaleString("pt-BR", { maximumFractionDigits: 4 })}</strong>
              <small>{item.unidade} · {dataHora(item.ultima_atualizacao)}</small>
              {item.variacao_diaria !== null && item.variacao_diaria !== undefined && <Badge tone={Number(item.variacao_diaria) >= 0 ? "success" : "danger"}>{Number(item.variacao_diaria).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%</Badge>}
            </article>
          )) : market?.resumos.length ? market.resumos.map((item) => (
            <article key={item.produto}>
              <span>{item.produto_nome}</span>
              <strong>{Number(item.valor).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}</strong>
              <small>{item.unidade}</small>
              {item.variacao_percentual !== null && <Badge tone={Number(item.variacao_percentual) >= 0 ? "success" : "danger"}>{Number(item.variacao_percentual).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%</Badge>}
            </article>
          )) : <p className="muted">Nenhuma cotação disponível.</p>}
        </div>
        {marketEnterprise?.analise.recomendacao_operacional && <AlertCard title="Comercialização" tone="info"><p>{marketEnterprise.analise.recomendacao_operacional}</p></AlertCard>}
      </SectionCard>

      <SectionCard title="Insights do assistente" description="Sugestões explicáveis produzidas com dados internos.">
        <ResponsiveGrid className="insight-grid">
          {insights?.insights.length ? insights.insights.slice(0, 6).map((item) => (
            <AlertCard key={item.codigo} title={item.titulo} tone={item.nivel === "critico" ? "danger" : item.nivel === "atencao" ? "warning" : "info"}>
              <p>{item.evidencia}</p><small>{item.recomendacao}</small>
            </AlertCard>
          )) : <p className="muted">Nenhum insight disponível para o filtro atual.</p>}
        </ResponsiveGrid>
      </SectionCard>
    </section>
  );
}
