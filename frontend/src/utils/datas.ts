/** Datas de calendário são formatadas sem conversão de fuso horário. */
export function formatarData(valor?: string | null) {
  if (!valor) return "—";
  const data = /^(\d{4})-(\d{2})-(\d{2})(?:T.*)?$/.exec(valor);
  return data ? `${data[3]}/${data[2]}/${data[1]}` : valor;
}
