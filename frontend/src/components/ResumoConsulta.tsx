import { formatarNumero } from "../utils/numeros";
export type OrdemConsulta = "data-desc" | "data-asc" | "propriedade" | "quantidade-desc" | "quantidade-asc";
export function ordenarConsulta<T>(itens:T[], ordem:OrdemConsulta, campos:(item:T)=>{data:string;propriedade:string;quantidade:number;id:number}) {
  return [...itens].sort((a,b)=>{const x=campos(a),y=campos(b);let comparacao=0;
    if(ordem==="propriedade")comparacao=x.propriedade.localeCompare(y.propriedade,"pt-BR");
    else if(ordem.startsWith("quantidade"))comparacao=(x.quantidade-y.quantidade)*(ordem.endsWith("desc")?-1:1);
    else comparacao=x.data.localeCompare(y.data)*(ordem.endsWith("desc")?-1:1);
    return comparacao || y.id-x.id;
  });
}
export function noPeriodo(data:string,inicio="",fim="") {return (!inicio||data.slice(0,10)>=inicio)&&(!fim||data.slice(0,10)<=fim);}
export function totalConsulta<T>(itens:T[],valor:(item:T)=>string|number) {return itens.reduce((total,item)=>total+Number(valor(item)),0);}
export default function ResumoConsulta({quantidade,totais,ordem,alterar,descricao}:{quantidade:number;totais:{nome:string;valor:number;unidade?:string}[];ordem:OrdemConsulta;alterar:(v:OrdemConsulta)=>void;descricao:string}) {
  return <section className="resumo-listagem" aria-label="Resumo dos resultados"><p>{quantidade} registro(s) · {descricao}</p><div className="resumo-listagem-totais">{totais.map(t=><span key={t.nome}>{t.nome}<strong>{formatarNumero(t.valor)} {t.unidade}</strong></span>)}</div><label className="nao-imprimir">Ordenar resultados<select value={ordem} onChange={e=>alterar(e.target.value as OrdemConsulta)}><option value="data-desc">Data: mais recentes</option><option value="data-asc">Data: mais antigas</option><option value="propriedade">Propriedade: A–Z</option><option value="quantidade-desc">Quantidade: maior primeiro</option><option value="quantidade-asc">Quantidade: menor primeiro</option></select></label></section>;
}
