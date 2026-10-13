import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {transformWithOxc} from "vite";

const dataUrl=source=>`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
const react=dataUrl('export const useState=(...a)=>globalThis.romaneiosHooks.state(...a);export const useEffect=(...a)=>globalThis.romaneiosHooks.effect(...a);');
const api=dataUrl('export const api={get:(...a)=>globalThis.romaneiosApi(...a)};');
const source=(await readFile(new URL("../src/api/romaneios.ts",import.meta.url),"utf8"))
  .replace('from "react"',`from "${react}"`).replace('from "./propriedades"',`from "${api}"`);
const compiled=await transformWithOxc(source,"romaneios.ts",{lang:"ts",sourceType:"module",target:"es2022"});
const {useConsultaRomaneios}=await import(dataUrl(compiled.code));
class Hooks {
  values=[];effects=[];cursor=0;pending=[];
  state(initial){const i=this.cursor++;if(!(i in this.values))this.values[i]=initial;return[this.values[i],v=>{this.values[i]=typeof v==="function"?v(this.values[i]):v;}];}
  effect(fn,deps){const i=this.cursor++,old=this.effects[i];if(!old||deps.some((v,k)=>!Object.is(v,old.deps[k])))this.pending.push(()=>{old?.cleanup?.();this.effects[i]={deps,cleanup:fn()};});}
  render(fn){this.cursor=0;const result=fn();this.pending.splice(0).forEach(fn=>fn());return result;}
  close(){this.effects.forEach(e=>e?.cleanup?.());}
}
const janelaAntes=globalThis.window;
try {
  const timers=new Map(),requests=[];
  let sequence=0,ativo=false,invalido=false,revisao=[],params={busca:"",pagina:1};
  globalThis.romaneiosHooks=new Hooks();
  globalThis.window={setTimeout:fn=>{timers.set(++sequence,fn);return sequence;},clearTimeout:id=>timers.delete(id)};
  globalThis.romaneiosApi=(_url,config)=>new Promise((resolve,reject)=>requests.push({config,resolve,reject}));
  const render=()=>romaneiosHooks.render(()=>useConsultaRomaneios("/romaneios/",params,ativo,revisao,invalido));
  const tick=()=>{const jobs=[...timers.values()];timers.clear();jobs.forEach(fn=>fn());};
  const settle=async()=>{for(let i=0;i<6;i++)await Promise.resolve();return render();};
  const resposta={itens:[{id:1}],total:8,pagina:1,paginas:2,peso_ativo_kg:"800"};
  render();tick();assert.equal(requests.length,0,"Aba oculta não consulta");
  ativo=true;render();tick();assert.equal(requests.length,1);assert.equal(render().carregando,true);
  params={busca:"José",pagina:1};assert.equal(render().dados,undefined,"Filtro novo não exibe resultado antigo");
  assert.equal(requests[0].config.signal.aborted,true);tick();
  requests[0].resolve({data:{...resposta,total:999}});assert.equal((await settle()).dados,undefined,"Resposta antiga é descartada mesmo se não respeitar abort");
  requests[1].resolve({data:resposta});assert.equal((await settle()).dados.total,8);
  ativo=false;render();revisao=[];render();tick();assert.equal(requests.length,2,"Revisão enquanto oculta não consulta");
  ativo=true;render();tick();assert.equal(requests.length,3);requests[2].reject(new Error("rede"));
  let resultado=await settle();assert.match(resultado.erro,/Não foi possível/);assert.equal(resultado.dados,undefined);
  resultado.atualizar();render();tick();assert.equal(requests.length,4);requests[3].resolve({data:resposta});await settle();
  invalido=true;resultado=render();tick();assert.equal(resultado.dados,undefined);assert.equal(resultado.carregando,false);assert.equal(requests.length,4,"Período inválido não consulta nem mostra total zero");
  invalido=false;render();tick();assert.equal(requests.length,5);ativo=false;render();
  assert.equal(requests[4].config.signal.aborted,true,"Sair da aba cancela consulta pendente");
  requests[4].resolve({data:{...resposta,total:999}});assert.notEqual((await settle()).dados?.total,999);
  romaneiosHooks.close();
  console.log("Romaneios: abas ocultas, cancelamento, respostas antigas, filtros, período inválido e recuperação de erro aprovados.");
} finally {
  globalThis.window=janelaAntes;
  delete globalThis.romaneiosHooks;
  delete globalThis.romaneiosApi;
}
