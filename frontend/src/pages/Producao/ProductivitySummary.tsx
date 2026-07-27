import { useEffect, useState } from "react";

import { api } from "../../api/propriedades";
import type { DashboardProducao } from "../../api/producaoIntegrada";
import type { Propriedade } from "../../api/propriedades";
import { EmptyState, ErrorState, LoadingState, SectionCard } from "../../components/shared/ui";

export default function ProductivitySummary({
  selectedProperty,
  safra,
}: {
  selectedProperty: Propriedade | null;
  safra: string;
}) {
  const [items, setItems] = useState<DashboardProducao["por_talhao"]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    void api.get<DashboardProducao>("/producao/dashboard-integrado/", {
      params: {
        propriedade: selectedProperty?.id || undefined,
        safra: safra || undefined,
      },
    }).then((response) => {
      if (active) setItems(response.data.por_talhao);
    }).catch(() => {
      if (active) setError("Não foi possível calcular a produtividade por talhão.");
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [safra, selectedProperty?.id]);

  return (
    <SectionCard
      title="Produtividade por talhão"
      description="Sacas confirmadas divididas pela área cadastrada do talhão."
    >
      {loading ? <LoadingState label="Calculando produtividade..." /> : null}
      {error ? <ErrorState description={error} /> : null}
      {!loading && !error && items.length === 0 ? (
        <EmptyState title="Sem produtividade calculável" description="Vincule recebimentos confirmados a talhões com área cadastrada." />
      ) : (
        <div className="productivity-list">
          {items.map((item) => (
            <article key={item.talhao_id} className="production-ranking">
              <span>{item.talhao__nome}</span>
              <div className="productivity-values">
                <strong>{item.produtividade_sacas_ha === null ? "—" : `${Number(item.produtividade_sacas_ha).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} sc/ha`}</strong>
                <small>{Number(item.sacas || 0).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} sacas · {Number(item.talhao__area_hectares || 0).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} ha</small>
              </div>
            </article>
          ))}
        </div>
      )}
    </SectionCard>
  );
}
