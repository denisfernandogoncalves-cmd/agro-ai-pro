import { LatLngBoundsExpression, LatLngExpression } from "leaflet";


export type Coordenada = [number, number];

export type GeometriaGeoJSON =
  | { type: "Polygon"; coordinates: Coordenada[][] }
  | { type: "MultiPolygon"; coordinates: Coordenada[][][] };

export type PosicoesPoligono =
  | LatLngExpression[][]
  | LatLngExpression[][][];

function converterAnel(anel: Coordenada[]): LatLngExpression[] {
  return anel.map(([longitude, latitude]) => [latitude, longitude]);
}

export function converterGeometria(
  geometria: GeometriaGeoJSON,
): PosicoesPoligono {
  if (geometria.type === "Polygon") {
    return geometria.coordinates.map(converterAnel);
  }
  return geometria.coordinates.map((poligono) =>
    poligono.map(converterAnel)
  );
}

export function limitesGeometria(
  geometria: GeometriaGeoJSON,
): LatLngBoundsExpression {
  const poligonos =
    geometria.type === "Polygon"
      ? [geometria.coordinates]
      : geometria.coordinates;
  const pontos = poligonos.flat(2);
  const latitudes = pontos.map(([, latitude]) => latitude);
  const longitudes = pontos.map(([longitude]) => longitude);
  return [
    [Math.min(...latitudes), Math.min(...longitudes)],
    [Math.max(...latitudes), Math.max(...longitudes)],
  ];
}
