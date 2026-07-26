import type { GeometriaGeoJSON } from "../utils/geometria";
import AgriculturalMap from "./maps/AgriculturalMap";

type Props = {
  latitude: number;
  longitude: number;
  nome: string;
  geometria?: GeometriaGeoJSON | null;
};

export default function MapaPropriedade({ latitude, longitude, nome, geometria }: Props) {
  return <AgriculturalMap className="mapa-consolidado" features={[{ id: nome, kind: "propriedade", name: nome, latitude, longitude, geometry: geometria }]} />;
}
