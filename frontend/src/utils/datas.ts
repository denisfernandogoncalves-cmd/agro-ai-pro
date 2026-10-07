/** Datas de calendário são formatadas sem conversão de fuso horário. */
export function formatarData(valor?: string | null) {
  if (!valor) return "—";
  const data = /^(\d{4})-(\d{2})-(\d{2})(?:T.*)?$/.exec(valor);
  return data ? `${data[3]}/${data[2]}/${data[1]}` : valor;
}

/** Instantes de registro no fuso utilizado pelo aplicativo. */
export function formatarDataHora(valor?:string|null) {
  if(!valor)return "Não informado";
  const data=new Date(valor);
  return Number.isNaN(data.getTime())?"Não informado":data.toLocaleString("pt-BR",{timeZone:"America/Sao_Paulo",day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit"});
}
