import { api } from "../api/propriedades";
import { formatarNumero } from "../utils/numeros";
import { useConfirmacaoCompacta } from "./ConfirmacaoCompacta";

type Pesagem = {peso_total_kg?:string|null;tara_kg?:string|null;peso_bruto_kg:string;peso_liquido_kg:string;desconto_total_kg:string};
type Alerta = {rotulo:string;mediana_kg:string;valor_kg:string;desvio_percentual:string;amostras:number};
export function equacaoPesagem(dados:Pesagem) {
  const kg=(valor:string)=>`${formatarNumero(valor)} kg`;
  const bruto=dados.peso_total_kg!=null&&dados.tara_kg!=null
    ? `Total ${kg(dados.peso_total_kg)} − tara ${kg(dados.tara_kg)} = bruto do produto ${kg(dados.peso_bruto_kg)}.`
    : `Bruto do produto ${kg(dados.peso_bruto_kg)}. Total e tara não informados.`;
  return `${bruto} Bruto ${kg(dados.peso_bruto_kg)} − descontos ${kg(dados.desconto_total_kg)} = líquido ${kg(dados.peso_liquido_kg)}.`;
}
export function EquacaoPesagem({dados}:{dados:Pesagem}) {
  return <p className="conferencia-pesagem" role="status">{equacaoPesagem(dados)}</p>;
}
export function useConferirPesagem() {
  const confirmar=useConfirmacaoCompacta();
  return async (dados:Record<string,unknown>)=>{
    const {data}=await api.post<Pesagem&{alertas:Alerta[];duplicados?:number[]}>("/graos/cargas-colhidas/conferencia-pesagem/previa/", {...dados,ph:dados.ph||null});
    const avisos=data.alertas.map(a=>`${a.rotulo}: ${formatarNumero(a.valor_kg)} kg, ${formatarNumero(a.desvio_percentual)}% de diferença da mediana de ${formatarNumero(a.mediana_kg)} kg (${a.amostras} lançamentos semelhantes).`).join(" ");
    const repetidos=data.duplicados??[];
    const duplicidade=repetidos.length?`Possível duplicidade: romaneios ${repetidos.map(id=>`#${id}`).join(", ")} têm produtor/terceiro, placa, data, produto, safra e peso iguais. Confira os documentos; pode ser outro recebimento legítimo.`:"";
    return confirmar({titulo:repetidos.length?"Possível lançamento duplicado":data.alertas.length?"Peso fora do padrão: confira":"Conferir pesagem antes de salvar", confirmar:repetidos.length||data.alertas.length?"Conferi: salvar mesmo assim":"Confirmar pesagem e salvar",mensagem:`${equacaoPesagem(data)} ${avisos} ${duplicidade}`.trim()});
  };
}
