export type CoordenadasCadastradas = {
  formato_coordenadas?: "decimal" | "gms";
  latitude?: string | number | null; longitude?: string | number | null;
  latitude_gms?: string; longitude_gms?: string;
};

export function gmsParaDecimal(valor: string, eixo: "latitude" | "longitude") {
  const m = valor.trim().match(/^(\d{1,3})(?:[°º]|\s+)\s*(\d{1,2})(?:['′’´]|\s+)\s*(\d{1,2}(?:[.,]\d+)?)["″”'′’´]{0,2}\s*([NSEOW])$/i);
  if (!m) throw new Error('Informe graus, minutos, segundos e hemisfério, como 24°18\'28,97"S.');
  const graus = Number(m[1]), minutos = Number(m[2]), segundos = Number(m[3].replace(",", ".")), hemisferio = m[4].toUpperCase();
  const limite = eixo === "latitude" ? 90 : 180;
  if (!(eixo === "latitude" ? "NS" : "EOW").includes(hemisferio) || minutos >= 60 || segundos >= 60 || graus > limite || (graus === limite && (minutos || segundos))) throw new Error("Confira os limites e o hemisfério da coordenada.");
  const sinal = "SOW".includes(hemisferio) ? -1 : 1;
  return (sinal * (graus + minutos / 60 + segundos / 3600)).toFixed(6);
}

export function decimalParaGms(valor: string | number, eixo: "latitude" | "longitude") {
  if (String(valor).trim() === "") throw new Error("Informe as duas coordenadas decimais antes de converter.");
  const n = Number(String(valor).replace(",", ".")), limite = eixo === "latitude" ? 90 : 180;
  if (!Number.isFinite(n) || Math.abs(n) > limite) throw new Error("Coordenada decimal fora dos limites.");
  const centesimos = Math.round(Math.abs(n) * 360000);
  const graus = Math.floor(centesimos / 360000), minutos = Math.floor(centesimos % 360000 / 6000), segundos = (centesimos % 6000 / 100).toFixed(2).replace(".", ",");
  const hemisferio = eixo === "latitude" ? (n < 0 || Object.is(n, -0) ? "S" : "N") : (n < 0 || Object.is(n, -0) ? "O" : "E");
  return `${graus}°${String(minutos).padStart(2, "0")}'${segundos}"${hemisferio}`;
}

export function coordenadaCadastrada(item: CoordenadasCadastradas, eixo: "latitude" | "longitude") {
  const valor = item.formato_coordenadas === "gms" ? item[`${eixo}_gms`] : item[eixo];
  return valor === null || valor === undefined || valor === "" ? "Não informada" : String(valor);
}
