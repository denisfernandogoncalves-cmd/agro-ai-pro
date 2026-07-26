import type { Propriedade } from "../../api/propriedades";
import {
  Badge,
  EmptyState,
  PageHeader,
  ResponsiveGrid,
  SectionCard,
} from "../../components/shared/ui";

export default function ProducaoPage({
  selectedProperty,
  safra,
}: {
  selectedProperty: Propriedade | null;
  safra: string;
}) {
  const contexto = [selectedProperty?.nome, safra ? `safra ${safra}` : ""]
    .filter(Boolean)
    .join(" · ");

  return (
    <section className="production-page">
      <PageHeader
        eyebrow="Módulo oficial"
        title="Gestão da Produção Agrícola"
        description={`Controle físico, fiscal e comercial da produção${contexto ? ` para ${contexto}` : ""}.`}
        actions={<Badge tone="info">Escopo registrado</Badge>}
      />

      <ResponsiveGrid className="production-scope-grid">
        <SectionCard title="Recebimento e qualidade">
          <p className="muted">Cargas, motorista, placa, talhão, cultura, safra, pesos, umidade, impureza, defeitos e local de armazenagem.</p>
        </SectionCard>
        <SectionCard title="CAD/PRO e estoque de grãos">
          <p className="muted">Múltiplos CAD/PRO por propriedade, titularidade, saldos por cultura, safra e local, com transferências rastreáveis.</p>
        </SectionCard>
        <SectionCard title="Contratos e embarques">
          <p className="muted">Compradores, contratos, romaneios, notas fiscais, preço, valor, baixa de saldo e integração financeira.</p>
        </SectionCard>
        <SectionCard title="Auditoria e inteligência">
          <p className="muted">Histórico imutável, comparativos entre safras, produtividade, alertas de qualidade e apoio à comercialização.</p>
        </SectionCard>
      </ResponsiveGrid>

      <EmptyState
        title="Operação ainda não habilitada nesta entrega"
        description="As APIs e tabelas transacionais deste novo domínio serão implementadas em etapa própria. Nenhum dado foi inventado ou duplicado no frontend."
      />
    </section>
  );
}
