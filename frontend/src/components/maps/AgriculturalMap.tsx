import { useEffect } from "react";
import { latLngBounds } from "leaflet";
import {
  CircleMarker,
  MapContainer,
  Polygon,
  Popup,
  ScaleControl,
  TileLayer,
  useMap,
} from "react-leaflet";

import type { GeometriaGeoJSON } from "../../utils/geometria";
import { converterGeometria, limitesGeometria } from "../../utils/geometria";
import { EmptyState } from "../shared/ui";

export type AgriculturalMapFeature = {
  id: string | number;
  kind: "propriedade" | "talhao";
  name: string;
  subtitle?: string;
  latitude?: number | null;
  longitude?: number | null;
  geometry?: GeometriaGeoJSON | null;
};

function FitFeatures({ features }: { features: AgriculturalMapFeature[] }) {
  const map = useMap();
  useEffect(() => {
    const bounds = latLngBounds([]);
    features.forEach((feature) => {
      if (feature.geometry) {
        const [southWest, northEast] = limitesGeometria(feature.geometry);
        bounds.extend(southWest);
        bounds.extend(northEast);
      }
      if (Number.isFinite(feature.latitude) && Number.isFinite(feature.longitude)) {
        bounds.extend([feature.latitude as number, feature.longitude as number]);
      }
    });
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [32, 32], maxZoom: 15 });
    }
  }, [features, map]);
  return null;
}

export default function AgriculturalMap({
  features,
  className = "",
  emptyMessage = "Nenhuma geometria ou coordenada disponível.",
}: {
  features: AgriculturalMapFeature[];
  className?: string;
  emptyMessage?: string;
}) {
  const visible = features.filter((feature) =>
    feature.geometry
    || (Number.isFinite(feature.latitude) && Number.isFinite(feature.longitude)),
  );

  if (visible.length === 0) {
    return <EmptyState title="Mapa indisponível" description={emptyMessage} />;
  }

  const first = visible.find((feature) => Number.isFinite(feature.latitude) && Number.isFinite(feature.longitude));
  const center: [number, number] = first
    ? [first.latitude as number, first.longitude as number]
    : [-14.235, -51.9253];
  const kinds = new Set(visible.map((feature) => feature.kind));

  return (
    <div className={`agricultural-map ${className}`}>
      <MapContainer center={center} zoom={5} className="agricultural-map__canvas" zoomControl>
        <TileLayer
          className="agricultural-map__tiles"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <ScaleControl imperial={false} />
        {visible.map((feature) => (
          <span key={`${feature.kind}-${feature.id}`}>
            {feature.geometry && (
              <Polygon
                positions={converterGeometria(feature.geometry)}
                pathOptions={{
                  color: feature.kind === "propriedade" ? "var(--map-property)" : "var(--map-field)",
                  fillOpacity: feature.kind === "propriedade" ? 0.1 : 0.24,
                  weight: feature.kind === "propriedade" ? 3 : 2,
                }}
              >
                <Popup><strong>{feature.name}</strong>{feature.subtitle && <><br />{feature.subtitle}</>}</Popup>
              </Polygon>
            )}
            {Number.isFinite(feature.latitude) && Number.isFinite(feature.longitude) && (
              <CircleMarker
                center={[feature.latitude as number, feature.longitude as number]}
                radius={feature.kind === "propriedade" ? 8 : 6}
                pathOptions={{ color: feature.kind === "propriedade" ? "var(--map-property)" : "var(--map-field)" }}
              >
                <Popup><strong>{feature.name}</strong>{feature.subtitle && <><br />{feature.subtitle}</>}</Popup>
              </CircleMarker>
            )}
          </span>
        ))}
        <FitFeatures features={visible} />
      </MapContainer>
      <div className="agricultural-map__legend" aria-label="Legenda do mapa">
        {kinds.has("propriedade") && <span><i className="legend-property" />Propriedades</span>}
        {kinds.has("talhao") && <span><i className="legend-field" />Talhões</span>}
        <small>Camadas futuras poderão ser adicionadas sem alterar o contrato atual.</small>
      </div>
    </div>
  );
}
