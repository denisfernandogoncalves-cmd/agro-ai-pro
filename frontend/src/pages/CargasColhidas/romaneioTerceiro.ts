import { EntradaTerceiro } from "../../api/terceiros";
import { DadosComprovante } from "../../components/ComprovanteLancamento";
import { formatarNumero } from "../../utils/numeros";
import { formatarDataHora } from "../../utils/datas";
const dataBR=(data:string)=>data.split("-").reverse().join("/");
export function dadosRomaneioTerceiro(i:EntradaTerceiro):DadosComprovante {
  const medicao=(valor:string|null|undefined,unidade="")=>valor==null?"Não informado":`${formatarNumero(valor)}${unidade}`;
  const qualidade=`Umidade ${medicao(i.umidade_percentual,"%")} · Impureza ${medicao(i.impureza_percentual,"%")} · Avariados ${medicao(i.defeitos_percentual,"%")}`
    +(i.cultura.trim().toLowerCase()==="trigo"?` · PH ${medicao(i.ph)}`:"");
  return {titulo:`Romaneio de entrada de terceiros #${i.id}`,modelo:"romaneio",tipoMovimento:"entrada",campos:[
    ["Romaneio",`#${i.id}`],["Registrado em",formatarDataHora(i.criado_em)],["Responsável pelo registro",i.criado_por_nome||"Não informado"],
    ["Origem","Produção de terceiros"],["Nome do terceiro",i.depositante],
    ["Cultura / safra",`${i.cultura} / ${i.safra}`],["Armazenagem",i.armazem_nome],["Data da entrada",dataBR(i.data_entrada)],
    ["Peso total",medicao(i.peso_total_kg," kg")],["Tara",medicao(i.tara_kg," kg")],["Peso bruto do produto",medicao(i.peso_bruto_kg," kg")],
    ["Peso líquido",`${formatarNumero(i.peso_liquido_kg)} kg`],["Sacas de 60 kg",formatarNumero(Number(i.peso_liquido_kg)/60)],
    ["Desconto (%)",medicao(i.desconto_total_percentual,"%")],["Desconto (kg)",medicao(i.desconto_total_kg," kg")],
    ["Qualidade",qualidade],["Saldo atual",`${formatarNumero(i.saldo_kg)} kg`],
    ["Motorista",i.motorista||"—"],["Placa",i.placa||"Sem placa"],["Documento",i.documento||"—"],
    ["Situação",i.movimentos.some(m=>m.tipo==="entrada"&&m.estornado)?"Entrada estornada":"Registrada"],["Observações",i.observacoes||"—"]
  ]};
}
