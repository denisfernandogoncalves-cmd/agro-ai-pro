import { useEffect, useState } from "react";
import {
  CircleMarker,
  MapContainer,
  Polygon,
  Popup,
  TileLayer,
} from "react-leaflet";

import "leaflet/dist/leaflet.css";


type Props = {
  latitude: number;
  longitude: number;
  nome: string;
  kml?: string | null;
};

function extrairPoligonoKml(conteudo: string): [number, number][] {
  const xml = new DOMParser().parseFromString(conteudo, "application/xml");
  if (xml.querySelector("parsererror")) {
    throw new Error("KML inválido");
  }
  const coordenadas = xml.querySelector("coordinates")?.textContent;
  if (!coordenadas) {
    return [];
  }
  return coordenadas
    .trim()
    .split(/\s+/)
    .map((coordenada) => coordenada.split(",").map(Number))
    .filter(([longitudeKml, latitudeKml]) =>
      Number.isFinite(longitudeKml) && Number.isFinite(latitudeKml)
    )
    .map(([longitudeKml, latitudeKml]) => [latitudeKml, longitudeKml]);
}

export default function MapaPropriedade({
  latitude,
  longitude,
  nome,
  kml,
}: Props) {
  const [poligono, setPoligono] = useState<[number, number][]>([]);

  useEffect(() => {
    let ativo = true;
    setPoligono([]);
    if (!kml) {
      return () => {
        ativo = false;
      };
    }

    fetch(kml)
      .then((resposta) => {
        if (!resposta.ok) {
          throw new Error("Não foi possível carregar o KML.");
        }
        return resposta.text();
      })
      .then((conteudo) => {
        if (ativo) {
          setPoligono(extrairPoligonoKml(conteudo));
        }
      })
      .catch(() => {
        if (ativo) {
          setPoligono([]);
        }
      });

    return () => {
      ativo = false;
    };
  }, [kml]);

  return (
    <MapContainer
      center={[latitude, longitude]}
      zoom={13}
      className="mapa"
      key={`${latitude}-${longitude}`}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <CircleMarker center={[latitude, longitude]} radius={8}>
        <Popup>{nome}</Popup>
      </CircleMarker>
      {poligono.length >= 3 && <Polygon positions={poligono} />}
    </MapContainer>
  );
}
