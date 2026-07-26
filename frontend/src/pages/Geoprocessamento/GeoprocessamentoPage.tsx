import { useEffect, useMemo, useState } from "react";

import type { Propriedade } from "../../api/propriedades";
import { listarTalhoes, type Talhao } from "../../api/talhoes";
import AgriculturalMap, { type AgriculturalMapFeature } from "../../components/maps/AgriculturalMap";
import { ErrorState, LoadingState, PageHeader, SectionCard, StatCard, ResponsiveGrid } from "../../components/shared/ui";

export default function GeoprocessamentoPage({
  properties,
  selectedProperty,
  safra,
}: {
  properties: Propriedade[];
  selectedProperty: Propriedade | null;
  safra: string;
}) {
  const [fields, setFields] = useState<Talhao[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    void listarTalhoes({
      propriedade: selectedProperty ? String(selectedProperty.id) : "",
      safra,
      ordering: "nome",
      page: 1,
      pageSize: 100,
    }).then((result) => {
      if (active) setFields(result.results);
    }).catch(() => {
      if (active) setError("Não foi possível carregar os talhões autorizados.");
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [safra, selectedProperty]);

  const scopedProperties = selectedProperty ? [selectedProperty] : properties;
  const features = useMemo<AgriculturalMapFeature[]>(() => [
    ...scopedProperties.map((property) => ({
      id: property.id,
      kind: "propriedade" as const,
      name: property.nome,
      subtitle: `${property.municipio}/${property.uf}`,
      latitude: property.latitude === null ? null : Number(property.latitude),
      longitude: property.longitude === null ? null : Number(property.longitude),
      geometry: property.geometria_geojson,
    })),
    ...fields.map((field) => ({
      id: field.id,
      kind: "talhao" as const,
      name: field.nome,
      subtitle: `${field.propriedade_nome}${field.safra ? ` · ${field.safra}` : ""}`,
      latitude: field.latitude_centro === null ? null : Number(field.latitude_centro),
      longitude: field.longitude_centro === null ? null : Number(field.longitude_centro),
      geometry: field.geometria_geojson,
    })),
  ], [fields, scopedProperties]);

  return (
    <section className="geoprocessing-page">
      <PageHeader eyebrow="Mapa agrícola" title="Geoprocessamento" description="Propriedades, talhões e geometrias KML já processadas pelo backend." />
      <ResponsiveGrid className="stat-grid stat-grid--compact">
        <StatCard label="Propriedades no mapa" value={scopedProperties.length} />
        <StatCard label="Talhões carregados" value={fields.length} />
        <StatCard label="Geometrias disponíveis" value={features.filter((feature) => feature.geometry).length} tone="info" />
      </ResponsiveGrid>
      <SectionCard title="Mapa consolidado" description="OpenStreetMap, marcadores, escala, legenda e enquadramento automático.">
        {loading ? <LoadingState label="Carregando geometrias..." /> : error ? <ErrorState description={error} /> : <AgriculturalMap features={features} emptyMessage="Cadastre coordenadas ou importe KML para visualizar o mapa." />}
      </SectionCard>
    </section>
  );
}
