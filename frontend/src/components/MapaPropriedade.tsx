import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";

type Props = {
  latitude: number;
  longitude: number;
  nome: string;
};

export default function MapaPropriedade({latitude, longitude, nome}: Props) {
  return (
    <MapContainer center={[latitude, longitude]} zoom={15} style={{height:"500px", width:"100%"}}>
      <TileLayer
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Marker position={[latitude, longitude]}>
        <Popup>{nome}</Popup>
      </Marker>
    </MapContainer>
  );
}
