import { useEffect, useRef, useState } from "react";
import { divIcon, type Marker as LeafletMarker } from "leaflet";
import {
  LayersControl,
  MapContainer,
  Marker,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet";

export type PontoCoordenadas = {
  latitude: number;
  longitude: number;
};

type Props = {
  pontoInicial: PontoCoordenadas | null;
  onConfirmar: (ponto: PontoCoordenadas) => void;
  onCancelar: () => void;
};

const MARCADOR = divIcon({
  className: "seletor-coordenadas-marcador",
  iconSize: [22, 22],
  iconAnchor: [11, 11],
});

function CapturarClique({
  onSelecionar,
}: {
  onSelecionar: (ponto: PontoCoordenadas) => void;
}) {
  useMapEvents({
    click: (evento) => {
      onSelecionar({
        latitude: evento.latlng.lat,
        longitude: evento.latlng.lng,
      });
    },
  });
  return null;
}

function AtualizarTamanhoMapa() {
  const mapa = useMap();

  useEffect(() => {
    // O mapa é montado antes da abertura do dialog: recalcular após torná-lo visível.
    const frame = window.requestAnimationFrame(() => mapa.invalidateSize());
    return () => window.cancelAnimationFrame(frame);
  }, [mapa]);

  return null;
}

export default function SeletorCoordenadasMapa({
  pontoInicial,
  onConfirmar,
  onCancelar,
}: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const marcadorRef = useRef<LeafletMarker | null>(null);
  const [ponto, setPonto] = useState<PontoCoordenadas | null>(pontoInicial);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) dialog.showModal();
    return () => {
      if (dialog?.open) dialog.close();
    };
  }, []);

  const centro: [number, number] = ponto
    ? [ponto.latitude, ponto.longitude]
    : [-24.25, -51.7]; // Referência inicial no Paraná; o usuário pode navegar livremente.

  return (
    <dialog
      ref={dialogRef}
      className="seletor-coordenadas-dialog"
      aria-labelledby="seletor-coordenadas-titulo"
      aria-describedby="seletor-coordenadas-instrucoes"
      onCancel={(evento) => {
        evento.preventDefault();
        onCancelar();
      }}
    >
      <div className="seletor-coordenadas-cabecalho">
        <div>
          <h2 id="seletor-coordenadas-titulo">Escolher localização da propriedade</h2>
          <p id="seletor-coordenadas-instrucoes">
            Aproxime o mapa e clique na localização desejada. Arraste o marcador para ajustar.
          </p>
        </div>
        <button type="button" className="secundario" onClick={onCancelar}>
          Fechar
        </button>
      </div>

      <MapContainer
        center={centro}
        zoom={ponto ? 15 : 7}
        scrollWheelZoom
        className="seletor-coordenadas-mapa"
      >
        <AtualizarTamanhoMapa />
        <LayersControl position="topright">
          <LayersControl.BaseLayer checked name="Satélite">
            <TileLayer
              attribution="Tiles &copy; Esri, Maxar, Earthstar Geographics"
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="Mapa convencional">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
          </LayersControl.BaseLayer>
        </LayersControl>
        <CapturarClique onSelecionar={setPonto} />
        {ponto && (
          <Marker
            draggable
            ref={marcadorRef}
            icon={MARCADOR}
            position={[ponto.latitude, ponto.longitude]}
            eventHandlers={{
              dragend: () => {
                const posicao = marcadorRef.current?.getLatLng();
                if (posicao) {
                  setPonto({ latitude: posicao.lat, longitude: posicao.lng });
                }
              },
            }}
          />
        )}
      </MapContainer>

      <div className="seletor-coordenadas-rodape">
        <output aria-live="polite" className="seletor-coordenadas-resultado">
          {ponto
            ? `Latitude: ${ponto.latitude.toFixed(6)} | Longitude: ${ponto.longitude.toFixed(6)}`
            : "Nenhum ponto selecionado."}
        </output>
        <div className="acoes">
          <button type="button" className="secundario" onClick={onCancelar}>
            Cancelar
          </button>
          <button
            type="button"
            disabled={!ponto}
            onClick={() => {
              if (ponto) onConfirmar(ponto);
            }}
          >
            Usar estas coordenadas
          </button>
        </div>
      </div>
    </dialog>
  );
}
