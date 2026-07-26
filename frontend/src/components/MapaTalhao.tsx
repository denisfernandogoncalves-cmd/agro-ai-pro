import type { GeometriaTalhao } from "../api/talhoes";
import AgriculturalMap from "./maps/AgriculturalMap";

type Props = {
  geometria: GeometriaTalhao;
  latitude: number;
  longitude: number;
  nome: string;
};

export default function MapaTalhao({ geometria, latitude, longitude, nome }: Props) {
  return <AgriculturalMap className="mapa-consolidado" features={[{ id: nome, kind: "talhao", name: nome, latitude, longitude, geometry: geometria }]} />;
}
