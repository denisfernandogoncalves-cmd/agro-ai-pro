import { LatLngExpression } from "leaflet";
import { CircleMarker, MapContainer, Polygon, Popup, TileLayer } from "react-leaflet";

import { GeometriaTalhao } from "../api/talhoes";


type Props = {
  geometria: GeometriaTalhao;
  latitude: number;
  longitude: number;
  nome: string;
};

function converterAnel(anel: [number, number][]): LatLngExpression[] {
  return anel.map(([longitude, latitude]) => [latitude, longitude]);
}

function converterGeometria(geometria: GeometriaTalhao) {
  if (geometria.type === "Polygon") {
    return geometria.coordinates.map(converterAnel);
  }
  return geometria.coordinates.map((poligono) => poligono.map(converterAnel));
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
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <CircleMarker center={[latitude, longitude]} radius={7}>
        <Popup>{nome}</Popup>
      </CircleMarker>
      <Polygon positions={converterGeometria(geometria)} />
    </MapContainer>
  );
}
