import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polygon
} from "react-leaflet";

import "leaflet/dist/leaflet.css";

import { useEffect, useState } from "react";


type Props = {
  latitude: number;
  longitude: number;
  nome: string;
  kml?: string;
};


export default function MapaPropriedade({
  latitude,
  longitude,
  nome,
  kml
}: Props) {


  const [poligono, setPoligono] = useState<
    [number, number][]
  >([]);


  useEffect(() => {

    if (!kml) return;

    console.log("Arquivo KML recebido:", kml);


  }, [kml]);



  return (

    <MapContainer

      center={[
        latitude,
        longitude
      ]}

      zoom={15}

      style={{
        height:"500px",
        width:"100%"
      }}

    >

      <TileLayer

        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"

      />


      <Marker

        position={[
          latitude,
          longitude
        ]}

      >

        <Popup>

          {nome}

        </Popup>

      </Marker>


      {
        poligono.length > 0 &&

        <Polygon

          positions={poligono}

        />

      }


    </MapContainer>

  );

}