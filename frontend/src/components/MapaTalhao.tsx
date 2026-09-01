import { useEffect } from "react";
import { CircleMarker, LayersControl, MapContainer, Polygon, Popup, TileLayer } from "react-leaflet";
import { useMap } from "react-leaflet";

import { GeometriaTalhao } from "../api/talhoes";
import { converterGeometria, limitesGeometria } from "../utils/geometria";


type Props = {
  geometria: GeometriaTalhao;
  latitude: number;
  longitude: number;
  nome: string;
};

function AjustarEnquadramento({ geometria }: { geometria: GeometriaTalhao }) {
  const mapa = useMap();
  useEffect(() => {
    mapa.fitBounds(limitesGeometria(geometria), { padding: [24, 24] });
  }, [geometria, mapa]);
  return null;
}

export default function MapaTalhao({
  geometria,
  latitude,
  longitude,
  nome,
}: Props) {
  return (
    <MapContainer
      center={[latitude, longitude]}
      zoom={14}
      className="mapa"
      key={`${latitude}-${longitude}-${nome}`}
    >
      <LayersControl position="topright">
        <LayersControl.BaseLayer checked name="Satélite">
          <TileLayer attribution="Tiles &copy; Esri" url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" />
        </LayersControl.BaseLayer>
        <LayersControl.BaseLayer name="Mapa convencional">
          <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
        </LayersControl.BaseLayer>
      </LayersControl>
      <CircleMarker center={[latitude, longitude]} radius={7}>
        <Popup>{nome}</Popup>
      </CircleMarker>
      <Polygon positions={converterGeometria(geometria)} />
      <AjustarEnquadramento geometria={geometria} />
    </MapContainer>
  );
}
