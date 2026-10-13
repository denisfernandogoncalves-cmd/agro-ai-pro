import { useEffect, useState } from "react";
import { api } from "./propriedades";

export type PaginaRomaneios<T> = {
  itens:T[]; total:number; pagina:number; paginas:number; por_pagina:number;
  inicio:number; fim:number; peso_ativo_kg:string; consultado_em:string; culturas?:string[];
};

/** Uma resposta só é exibida se ainda corresponder aos filtros e à revisão atuais. */
export function useConsultaRomaneios<T>(url:string, params:Record<string,string|number|boolean>, ativo:boolean, revisao:unknown, periodoInvalido:boolean) {
  const chave = JSON.stringify(params);
  const [atualizacao,setAtualizacao] = useState(0);
  const [estado,setEstado] = useState<{chave:string; revisao:unknown; atualizacao:number; dados?:PaginaRomaneios<T>; erro?:string}>();
  useEffect(()=>{
    if(!ativo || periodoInvalido) return;
    let atual = true;
    const controle = new AbortController();
    setEstado(undefined);
    const agendamento = window.setTimeout(()=>{
      void api.get<PaginaRomaneios<T>>(url,{params:JSON.parse(chave),signal:controle.signal})
        .then(resposta=>{if(atual)setEstado({chave,revisao,atualizacao,dados:resposta.data});})
        .catch(()=>{if(atual)setEstado({chave,revisao,atualizacao,erro:"Não foi possível consultar os romaneios. Atualize para tentar novamente."});});
    },250);
    return ()=>{atual=false;window.clearTimeout(agendamento);controle.abort();};
  },[url,chave,ativo,revisao,atualizacao,periodoInvalido]);
  const atual = !periodoInvalido && estado?.chave===chave && estado.revisao===revisao && estado.atualizacao===atualizacao;
  const dados = atual ? estado.dados : undefined;
  const erro = atual ? estado.erro : undefined;
  return {dados,erro,carregando:ativo && !periodoInvalido && !dados && !erro,atualizar:()=>setAtualizacao(v=>v+1)};
}
