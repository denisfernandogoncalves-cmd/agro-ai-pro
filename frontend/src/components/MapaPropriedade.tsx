import { useEffect } from "react";
import {
  CircleMarker,
  LayersControl,
  MapContainer,
  Polygon,
  Popup,
  TileLayer,
  Tooltip,
  useMap,
} from "react-leaflet";

import { GeometriaGeoJSON, converterGeometria, limitesGeometria } from "../utils/geometria";


type Props = {
  latitude: number;
  longitude: number;
  nome: string;
  geometria?: GeometriaGeoJSON | null;
  talhoes?: {id:number;nome:string;area_hectares:string;cultura_atual:string;geometria_geojson:GeometriaGeoJSON|null}[];
};

function AjustarEnquadramento({ geometria }: { geometria: GeometriaGeoJSON }) {
  const mapa = useMap();
  useEffect(() => {
    mapa.fitBounds(limitesGeometria(geometria), { padding: [24, 24] });
  }, [geometria, mapa]);
  return null;
}

export default function MapaPropriedade({
  latitude,
  longitude,
  nome,
  geometria,
  talhoes = [],
}: Props) {
  return (
    <MapContainer
      center={[latitude, longitude]}
      zoom={13}
      className="mapa"
      key={`${latitude}-${longitude}`}
    >
      <LayersControl position="topright">
        <LayersControl.BaseLayer checked name="Satélite">
          <TileLayer attribution="Tiles &copy; Esri" url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" />
        </LayersControl.BaseLayer>
        <LayersControl.BaseLayer name="Mapa convencional">
          <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
        </LayersControl.BaseLayer>
      </LayersControl>
      <CircleMarker center={[latitude, longitude]} radius={8}>
        <Popup>{nome}</Popup>
      </CircleMarker>
      {geometria && (
        <>
          <Polygon positions={converterGeometria(geometria)} />
          <AjustarEnquadramento geometria={geometria} />
        </>
      )}
      {talhoes.filter(t=>t.geometria_geojson).map(t=><Polygon key={t.id} positions={converterGeometria(t.geometria_geojson!)} pathOptions={{color:"#61db68",fillColor:"#168443",fillOpacity:.28,weight:2}}><Tooltip sticky>{t.nome}</Tooltip><Popup><strong>{t.nome}</strong><br/>{Number(t.area_hectares).toLocaleString("pt-BR")} ha · {t.cultura_atual || "Cultura não informada"}</Popup></Polygon>)}
    </MapContainer>
  );
}
