import { api } from "./propriedades";

export type MovimentoTerceiro = {id:number;tipo:"entrada"|"saida"|"estorno";quantidade_kg:string;saldo_anterior_kg:string;saldo_posterior_kg:string;data_movimento:string;destino:string;placa:string;motorista:string;documento:string;observacoes:string;estornado:boolean;criado_por_nome:string};
export type EntradaTerceiro = {id:number;depositante:string;propriedade_origem:string;cad_pro:string;cultura:string;safra:string;armazem:number;armazem_nome:string;peso_liquido_kg:string;saldo_kg:string;data_entrada:string;placa:string;motorista:string;documento:string;observacoes:string;movimentos:MovimentoTerceiro[]};
export type NovaEntradaTerceiro = Omit<EntradaTerceiro,"id"|"armazem_nome"|"saldo_kg"|"movimentos">;
export type SaidaTerceiro = {quantidade_kg:string;data_movimento:string;destino:string;documento:string;placa:string;motorista:string;observacoes:string};
const headers=(chave:string)=>({headers:{"Idempotency-Key":chave}});
export async function listarTerceiros(){return (await api.get<EntradaTerceiro[]>("/graos/terceiros/entradas/")).data;}
export async function registrarEntradaTerceiro(dados:NovaEntradaTerceiro,chave:string){return (await api.post<EntradaTerceiro>("/graos/terceiros/entradas/",dados,headers(chave))).data;}
export async function registrarSaidaTerceiro(id:number,dados:SaidaTerceiro,chave:string){return (await api.post<EntradaTerceiro>(`/graos/terceiros/entradas/${id}/registrar-saida/`,dados,headers(chave))).data;}
export async function estornarTerceiro(id:number,motivo:string,data_movimento:string,chave:string){return (await api.post<EntradaTerceiro>(`/graos/terceiros/movimentos/${id}/estornar/`,{motivo,data_movimento},headers(chave))).data;}
