import { Component, lazy, Suspense, type ReactNode } from "react";

import type { Propriedade } from "../api/propriedades";
import { ErrorState, LoadingState } from "../components/shared/ui";
import type { ModuleId } from "./navigation";

const DashboardPage = lazy(() => import("../pages/Dashboard/DashboardPage"));
const TalhoesPage = lazy(() => import("../pages/Talhoes/TalhoesPage"));
const GeoprocessamentoPage = lazy(() => import("../pages/Geoprocessamento/GeoprocessamentoPage"));
const ClimaPage = lazy(() => import("../pages/Clima/ClimaPage"));
const MercadoPage = lazy(() => import("../pages/Mercado/MercadoPage"));
const FinanceiroPage = lazy(() => import("../pages/Financeiro/FinanceiroPage"));
const EstoquePage = lazy(() => import("../pages/Estoque/EstoquePage"));
const OperacoesPage = lazy(() => import("../pages/Operacoes/OperacoesPage"));
const ProducaoPage = lazy(() => import("../pages/Producao/ProducaoPage"));
const MaquinasPage = lazy(() => import("../pages/Maquinas/MaquinasPage"));
const RelatoriosPage = lazy(() => import("../pages/Relatorios/RelatoriosPage"));
const InsightsPage = lazy(() => import("../pages/Insights/InsightsPage"));

class ModuleErrorBoundary extends Component<{ children: ReactNode; resetKey: string }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidUpdate(previous: { resetKey: string }) {
    if (previous.resetKey !== this.props.resetKey && this.state.failed) this.setState({ failed: false });
  }
  render() {
    if (this.state.failed) return <ErrorState title="Falha ao carregar o módulo" description="Atualize a página ou tente acessar o módulo novamente." onRetry={() => window.location.reload()} />;
    return this.props.children;
  }
}

export default function ModuleRenderer({
  module,
  properties,
  selectedProperty,
  safra,
  propertiesContent,
}: {
  module: ModuleId;
  properties: Propriedade[];
  selectedProperty: Propriedade | null;
  safra: string;
  propertiesContent: ReactNode;
}) {
  let content: ReactNode;
  switch (module) {
    case "dashboard": content = <DashboardPage properties={properties} selectedProperty={selectedProperty} safra={safra} />; break;
    case "propriedades": content = propertiesContent; break;
    case "talhoes": content = <TalhoesPage />; break;
    case "geoprocessamento": content = <GeoprocessamentoPage properties={properties} selectedProperty={selectedProperty} safra={safra} />; break;
    case "clima": content = <ClimaPage propriedades={properties} />; break;
    case "mercado": content = <MercadoPage />; break;
    case "financeiro": content = <FinanceiroPage propriedades={properties} />; break;
    case "estoque": content = <EstoquePage propriedades={properties} />; break;
    case "operacoes": content = <OperacoesPage />; break;
    case "producao": content = <ProducaoPage properties={properties} selectedProperty={selectedProperty} safra={safra} />; break;
    case "maquinas": content = <MaquinasPage propriedades={properties} />; break;
    case "relatorios": content = <RelatoriosPage propriedades={properties} />; break;
    case "insights": content = <InsightsPage propriedades={properties} />; break;
  }
  return (
    <ModuleErrorBoundary resetKey={module}>
      <Suspense fallback={<LoadingState label="Carregando módulo sob demanda..." />}>{content}</Suspense>
    </ModuleErrorBoundary>
  );
}
