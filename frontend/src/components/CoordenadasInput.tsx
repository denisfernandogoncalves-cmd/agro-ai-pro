import { useState } from "react";
import { PropriedadeInput } from "../api/propriedades";
import { decimalParaGms, gmsParaDecimal } from "../utils/coordenadas";
import SeletorCoordenadasMapa, {
  type PontoCoordenadas,
} from "./SeletorCoordenadasMapa";

type Props = {
  dados: PropriedadeInput;
  alterar: (dados: PropriedadeInput) => void;
};

function obterPontoInicial(dados: PropriedadeInput): PontoCoordenadas | null {
  try {
    let latitude = dados.latitude;
    let longitude = dados.longitude;

    if (dados.formato_coordenadas === "gms" && dados.latitude_gms && dados.longitude_gms) {
      latitude = gmsParaDecimal(dados.latitude_gms, "latitude");
      longitude = gmsParaDecimal(dados.longitude_gms, "longitude");
    }

    if (latitude.trim() === "" || longitude.trim() === "") return null;
    const lat = Number(latitude);
    const lng = Number(longitude);

    if (
      !Number.isFinite(lat) ||
      !Number.isFinite(lng) ||
      Math.abs(lat) > 90 ||
      Math.abs(lng) > 180
    ) {
      return null;
    }

    return { latitude: lat, longitude: lng };
  } catch {
    return null;
  }
}

export default function CoordenadasInput({ dados, alterar }: Props) {
  const [erro, setErro] = useState("");
  const [mapaAberto, setMapaAberto] = useState(false);
  const gms = dados.formato_coordenadas === "gms";

  function converter(sentido: "decimal" | "gms") {
    try {
      if (sentido === "decimal") {
        const latitude = gmsParaDecimal(dados.latitude_gms || "", "latitude");
        const longitude = gmsParaDecimal(dados.longitude_gms || "", "longitude");
        alterar({ ...dados, latitude, longitude, converter_coordenadas: "true" });
      } else {
        const latitude_gms = decimalParaGms(dados.latitude, "latitude");
        const longitude_gms = decimalParaGms(dados.longitude, "longitude");
        alterar({
          ...dados,
          formato_coordenadas: "gms",
          latitude_gms,
          longitude_gms,
          converter_coordenadas: "true",
        });
      }
      setErro("");
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Confira as coordenadas.");
    }
  }

  function confirmarCoordenadas(ponto: PontoCoordenadas) {
    // Prioriza as novas coordenadas decimais e limpa valores GMS anteriores.
    alterar({
      ...dados,
      formato_coordenadas: "decimal",
      latitude: ponto.latitude.toFixed(6),
      longitude: ponto.longitude.toFixed(6),
      latitude_gms: "",
      longitude_gms: "",
      converter_coordenadas: "false",
    });
    setErro("");
    setMapaAberto(false);
  }

  return (
    <fieldset style={{ gridColumn: "1 / -1", minWidth: 0 }}>
      <legend>Coordenadas geográficas</legend>

      <button
        type="button"
        className="secundario"
        onClick={() => setMapaAberto(true)}
      >
        Selecionar coordenadas no mapa
      </button>
      <p className="seletor-coordenadas-ajuda">
        Escolha um ponto representativo da propriedade, como a sede. Isso não altera
        a delimitação cadastrada por KML.
      </p>

      <label>
        Formato cadastrado
        <select
          value={dados.formato_coordenadas || "decimal"}
          onChange={(evento) => {
            setErro("");
            alterar({
              ...dados,
              formato_coordenadas: evento.target.value as "decimal" | "gms",
              converter_coordenadas: "false",
            });
          }}
        >
          <option value="decimal">Graus decimais</option>
          <option value="gms">Graus, minutos e segundos (GMS)</option>
        </select>
      </label>

      {gms ? (
        <>
          <label>
            Latitude em GMS
            <input
              maxLength={60}
              value={dados.latitude_gms || ""}
              placeholder={'24°18\'28,97"S'}
              onChange={(evento) => {
                setErro("");
                alterar({
                  ...dados,
                  latitude_gms: evento.target.value,
                  latitude: "",
                  longitude: "",
                  converter_coordenadas: "false",
                });
              }}
            />
          </label>
          <label>
            Longitude em GMS
            <input
              maxLength={60}
              value={dados.longitude_gms || ""}
              placeholder={'51°42\'47,98"O'}
              onChange={(evento) => {
                setErro("");
                alterar({
                  ...dados,
                  longitude_gms: evento.target.value,
                  latitude: "",
                  longitude: "",
                  converter_coordenadas: "false",
                });
              }}
            />
          </label>
          <p>
            GMS é salvo como digitado. Para utilizar um novo ponto GMS no mapa,
            solicite a conversão pelo botão.
          </p>
          <button type="button" className="secundario" onClick={() => converter("decimal")}>
            Converter GMS para decimal
          </button>
          {dados.latitude !== "" && dados.longitude !== "" && (
            <p>Decimal: latitude {dados.latitude}; longitude {dados.longitude}.</p>
          )}
        </>
      ) : (
        <>
          <label>
            Latitude decimal
            <input
              step="any"
              min="-90"
              max="90"
              type="number"
              value={dados.latitude}
              onChange={(evento) =>
                alterar({
                  ...dados,
                  latitude: evento.target.value,
                  converter_coordenadas: "false",
                })
              }
            />
          </label>
          <label>
            Longitude decimal
            <input
              step="any"
              min="-180"
              max="180"
              type="number"
              value={dados.longitude}
              onChange={(evento) =>
                alterar({
                  ...dados,
                  longitude: evento.target.value,
                  converter_coordenadas: "false",
                })
              }
            />
          </label>
        </>
      )}

      <button type="button" className="secundario" onClick={() => converter("gms")}>
        Converter decimal para GMS
      </button>
      {erro && <p className="erro" role="alert">{erro}</p>}

      {mapaAberto && (
        <SeletorCoordenadasMapa
          pontoInicial={obterPontoInicial(dados)}
          onConfirmar={confirmarCoordenadas}
          onCancelar={() => setMapaAberto(false)}
        />
      )}
    </fieldset>
  );
}
