export function periodoInvertido(inicio:string,fim:string) {
  return Boolean(inicio && fim && inicio > fim);
}

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

/** Idade do registro, sem pressupor prazo obrigatório de atualização. */
export function idadeDoDado(valor?: string | null, agora = Date.now()) {
  if (!valor) return "Atualização não informada";
  const instante = new Date(valor).getTime();
  if (!Number.isFinite(instante)) return "Atualização não informada";
  if (instante > agora) return "Data de atualização posterior ao horário atual";
  const minutos = Math.floor((agora - instante) / 60000);
  if (minutos < 1) return "Atualizado há menos de 1 minuto";
  if (minutos < 60) return `Atualizado há ${minutos} min`;
  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `Atualizado há ${horas} h`;
  return `Atualizado há ${Math.floor(horas / 24)} dia(s)`;
}
