import { useEffect, useRef, useState } from "react";
import { obterAccessToken, obterRefreshToken, observarSessao } from "../auth/sessionCoordinator";
import { sessaoPrecisaRenovar } from "../auth/expiracao";
import { renovarSessaoAgora } from "../api/propriedades";

export default function AvisoSessao() {
  const [aviso,setAviso]=useState(false),[ocupado,setOcupado]=useState(false),[erro,setErro]=useState("");
  const trava=useRef(false), montado=useRef(true);
  useEffect(()=>{montado.current=true;const conferir=()=>setAviso(sessaoPrecisaRenovar(obterAccessToken(),obterRefreshToken()));conferir();const cancelar=observarSessao(conferir);const timer=setInterval(conferir,30000);return()=>{montado.current=false;cancelar();clearInterval(timer);};},[]);
  async function renovar(){if(trava.current)return;trava.current=true;setOcupado(true);setErro("");try{await renovarSessaoAgora();if(montado.current)setAviso(sessaoPrecisaRenovar(obterAccessToken(),obterRefreshToken()));}catch{if(montado.current)setErro("Não foi possível renovar. Seu preenchimento foi mantido; tente novamente antes de sair da tela.");}finally{trava.current=false;if(montado.current)setOcupado(false);}}
  return aviso ? <aside className="card aviso-sessao nao-imprimir" role="status"><div><strong>Renove sua sessão</strong><p>A sessão está próxima de precisar de renovação. Você pode renovar sem sair desta tela nem perder o preenchimento. As consultas também renovam o acesso automaticamente.</p>{erro&&<p className="erro" role="alert">{erro}</p>}</div><button type="button" disabled={ocupado} onClick={()=>void renovar()}>{ocupado?"Renovando…":"Renovar sessão"}</button></aside> : null;
}
