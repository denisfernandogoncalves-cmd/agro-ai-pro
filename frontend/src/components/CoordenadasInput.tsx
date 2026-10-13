import { useState } from "react";
import { PropriedadeInput } from "../api/propriedades";
import { decimalParaGms, gmsParaDecimal } from "../utils/coordenadas";

export default function CoordenadasInput({ dados, alterar }: { dados: PropriedadeInput; alterar: (dados: PropriedadeInput) => void }) {
  const [erro, setErro] = useState("");
  const gms = dados.formato_coordenadas === "gms";
  function converter(sentido: "decimal" | "gms") {
    try {
      if (sentido === "decimal") {
        const latitude = gmsParaDecimal(dados.latitude_gms || "", "latitude"), longitude = gmsParaDecimal(dados.longitude_gms || "", "longitude");
        alterar({ ...dados, latitude, longitude, converter_coordenadas: "true" });
      } else {
        const latitude_gms = decimalParaGms(dados.latitude, "latitude"), longitude_gms = decimalParaGms(dados.longitude, "longitude");
        alterar({ ...dados, formato_coordenadas: "gms", latitude_gms, longitude_gms, converter_coordenadas: "true" });
      }
      setErro("");
    } catch (e) { setErro(e instanceof Error ? e.message : "Confira as coordenadas."); }
  }
  return <fieldset style={{ gridColumn: "1 / -1", minWidth: 0 }}><legend>Coordenadas geográficas</legend>
    <label>Formato cadastrado<select value={dados.formato_coordenadas || "decimal"} onChange={e => { setErro(""); alterar({ ...dados, formato_coordenadas: e.target.value as "decimal" | "gms", converter_coordenadas: "false" }); }}><option value="decimal">Graus decimais</option><option value="gms">Graus, minutos e segundos (GMS)</option></select></label>
    {gms ? <>
      <label>Latitude em GMS<input maxLength={60} value={dados.latitude_gms || ""} placeholder={'24°18\'28,97"S'} onChange={e => { setErro(""); alterar({ ...dados, latitude_gms: e.target.value, latitude: "", longitude: "", converter_coordenadas: "false" }); }} /></label>
      <label>Longitude em GMS<input maxLength={60} value={dados.longitude_gms || ""} placeholder={'51°42\'47,98"O'} onChange={e => { setErro(""); alterar({ ...dados, longitude_gms: e.target.value, latitude: "", longitude: "", converter_coordenadas: "false" }); }} /></label>
      <p>GMS é salvo como digitado. Para utilizar um novo ponto GMS no mapa, solicite a conversão pelo botão.</p>
      <button type="button" className="secundario" onClick={() => converter("decimal")}>Converter GMS para decimal</button>
      {dados.latitude !== "" && dados.longitude !== "" && <p>Decimal: latitude {dados.latitude}; longitude {dados.longitude}.</p>}
    </> : <>
      <label>Latitude decimal<input step="any" min="-90" max="90" type="number" value={dados.latitude} onChange={e => alterar({ ...dados, latitude: e.target.value, converter_coordenadas: "false" })} /></label>
      <label>Longitude decimal<input step="any" min="-180" max="180" type="number" value={dados.longitude} onChange={e => alterar({ ...dados, longitude: e.target.value, converter_coordenadas: "false" })} /></label>
    </>}
    <button type="button" className="secundario" onClick={() => converter("gms")}>Converter decimal para GMS</button>
    {erro && <p className="erro" role="alert">{erro}</p>}
  </fieldset>;
}
