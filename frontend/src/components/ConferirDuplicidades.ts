import { api } from "../api/propriedades";
import { useConfirmacaoCompacta } from "./ConfirmacaoCompacta";
type Resultado = {total:number;itens:{id:number;referencia:string}[];aviso:string};
export function useConferirDuplicidades() {
  const confirmar = useConfirmacaoCompacta();
  return async (entidade: "carga"|"venda"|"financeiro", dados: Record<string,unknown>) => {
    const {data} = await api.post<Resultado>(`/core/duplicidades/${entidade}/`, dados);
    if (!data.total) return true;
    return confirmar({titulo:"Possível lançamento repetido", confirmar:"Continuar mesmo assim", mensagem:`${data.total} registro(s) semelhante(s): ${data.itens.map(i=>i.referencia).join("; ")}. ${data.aviso}`});
  };
}
