import { EntradaTerceiro } from "../../api/terceiros";
import { DadosComprovante } from "../../components/ComprovanteLancamento";
import { formatarNumero } from "../../utils/numeros";
const dataBR=(data:string)=>data.split("-").reverse().join("/");
export function dadosRomaneioTerceiro(i:EntradaTerceiro):DadosComprovante { return {titulo:`Entrada de terceiros #${i.id}`,campos:[["Nome do terceiro",i.depositante],["Cultura / safra",`${i.cultura} / ${i.safra}`],["Armazém",i.armazem_nome],["Data",dataBR(i.data_entrada)],["Peso líquido recebido",`${formatarNumero(i.peso_liquido_kg)} kg`],["Saldo atual",`${formatarNumero(i.saldo_kg)} kg`],["Placa / motorista",`${i.placa||"—"} / ${i.motorista||"—"}`],["Documento",i.documento||"—"],["Situação",i.movimentos.some(m=>m.tipo==="entrada"&&m.estornado)?"Entrada estornada":"Registrada"],["Observações",i.observacoes||"—"]]}; }
