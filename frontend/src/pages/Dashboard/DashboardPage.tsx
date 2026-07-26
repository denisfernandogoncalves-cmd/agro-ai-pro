import { useCallback, useEffect, useMemo, useState } from "react";

import { listarPrevisoes, type PrevisaoClima } from "../../api/clima";
import { obterInsights } from "../../api/insights";
import { carregarPainelMercado } from "../../api/mercado";
import type { Propriedade } from "../../api/propriedades";
import { obterDashboard, type Dashboard } from "../../api/relatorios";
import {
  AlertCard,
  Badge,
  EmptyState,
  ErrorState,
  PageHeader,
  ResponsiveGrid,
  SectionCard,
  Skeleton,
  StatCard,
} from "../../components/shared/ui";

type MarketPanel = Awaited<ReturnType<typeof carregarPainelMercado>>;
type InsightPanel = Awaited<ReturnType<typeof obterInsights>>;

const currency = (value: string | number) => Number(value).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const hectares = (value: number) => `${value.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} ha`;

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
  const [insights, setInsights] = useState<InsightPanel | null>(null);
  const [weather, setWeather] = useState<PrevisaoClima[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setErrors([]);
    const propertyId = selectedProperty ? String(selectedProperty.id) : "";
    const [dashboardResult, marketResult, insightsResult, weatherResult] = await Promise.allSettled([
      obterDashboard(propertyId, safra),
      carregarPainelMercado(),
      obterInsights(propertyId),
      selectedProperty ? listarPrevisoes(selectedProperty.id) : Promise.resolve([] as PrevisaoClima[]),
    ] as const);
    const nextErrors: string[] = [];
    if (dashboardResult.status === "fulfilled") setDashboard(dashboardResult.value); else { setDashboard(null); nextErrors.push("Indicadores gerenciais indisponíveis."); }
    if (marketResult.status === "fulfilled") setMarket(marketResult.value); else { setMarket(null); nextErrors.push("Resumo de mercado indisponível."); }
    if (insightsResult.status === "fulfilled") setInsights(insightsResult.value); else { setInsights(null); nextErrors.push("Insights do assistente indisponíveis."); }
    if (weatherResult.status === "fulfilled") setWeather(weatherResult.value); else { setWeather([]); nextErrors.push("Alertas climáticos indisponíveis."); }
    setErrors(nextErrors);
    setLoading(false);
  }, [safra, selectedProperty]);

  useEffect(() => { void load(); }, [load]);

  const scopedProperties = useMemo(
    () => selectedProperty ? [selectedProperty] : properties,
    [properties, selectedProperty],
  );
  const declaredArea = useMemo(
    () => scopedProperties.reduce((sum, property) => sum + Number(property.area_hectares || 0), 0),
    [scopedProperties],
  );
  const calculatedArea = useMemo(
    () => scopedProperties.reduce((sum, property) => sum + Number(property.area_calculada_hectares || 0), 0),
    [scopedProperties],
  );
  const weatherAlerts = weather.filter((item) => item.alerta_agricola.trim());

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
            {dashboard && dashboard.estoque.itens_abaixo_minimo === 0 && dashboard.estoque.lotes_vencidos === 0 && dashboard.maquinas.manutencoes_pendentes === 0 && weatherAlerts.length === 0 && <p className="muted">Nenhum alerta disponível no filtro atual.</p>}
          </div>
        </SectionCard>

        <SectionCard title="Mercado" description="Resumo global cadastrado no módulo Mercado.">
          <div className="market-summary-list">
            {market?.resumos.length ? market.resumos.map((item) => (
              <article key={item.produto}>
                <span>{item.produto_nome}</span>
                <strong>{Number(item.valor).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}</strong>
                <small>{item.unidade}</small>
                {item.variacao_percentual !== null && <Badge tone={Number(item.variacao_percentual) >= 0 ? "success" : "danger"}>{Number(item.variacao_percentual).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%</Badge>}
              </article>
            )) : <p className="muted">Nenhum resumo de mercado disponível.</p>}
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Gestão da Produção" description="Novo domínio oficial para recebimento, qualidade, grãos, CAD/PRO, contratos e embarques.">
        <EmptyState
          title="Indicadores de produção ainda não disponíveis"
          description="A API operacional será criada em uma etapa própria. Até lá, o Dashboard não apresenta números simulados nem reutiliza indevidamente o estoque de insumos."
        />
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
