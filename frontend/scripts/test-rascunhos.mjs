import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {transformWithOxc} from "vite";
let sequence=0;
const url=(code)=>`data:text/javascript;base64,${Buffer.from(code+"\n//"+sequence++).toString("base64")}`;
const shim=url(`export const useState=(...a)=>globalThis.hooks.state(...a);export const useRef=(...a)=>globalThis.hooks.ref(...a);export const useEffect=(...a)=>globalThis.hooks.effect(...a);`);
const api=url(`export const api={get:(...a)=>globalThis.draftApi.get(...a),put:(...a)=>globalThis.draftApi.put(...a),delete:(...a)=>globalThis.draftApi.delete(...a)};`);
const permission=url(`export const useAcoes=()=>()=>globalThis.allowed;`);
const session=url(`export const obterGeracaoSessao=()=>globalThis.generation;`);
let source=await readFile(new URL("../src/components/RascunhoAutomatico.tsx",import.meta.url),"utf8");
source=source.replace('from "react"',`from "${shim}"`).replace('from "../api/propriedades"',`from "${api}"`).replace('from "./AcoesContext"',`from "${permission}"`).replace('from "../auth/sessionCoordinator"',`from "${session}"`);
const transformed=await transformWithOxc(source,"draft.tsx",{lang:"tsx",sourceType:"module",target:"es2022",jsx:{runtime:"automatic"}});
const code=transformed.code.replaceAll('"react/jsx-runtime"',JSON.stringify(import.meta.resolve("react/jsx-runtime")));
const {useRascunhoAutomatico}=await import(url(code));
class Hooks {
 values=[];effects=[];cursor=0;pending=[];
 state(initial){const i=this.cursor++;if(!(i in this.values))this.values[i]=typeof initial==="function"?initial():initial;return[this.values[i],v=>{this.values[i]=typeof v==="function"?v(this.values[i]):v;}];}
 ref(initial){const i=this.cursor++;if(!(i in this.values))this.values[i]={current:initial};return this.values[i];}
 effect(fn,deps){const i=this.cursor++;const old=this.effects[i];if(!old||deps.some((v,k)=>!Object.is(v,old.deps[k])))this.pending.push(()=>{old?.cleanup?.();this.effects[i]={deps,cleanup:fn()};});}
 render(fn){this.cursor=0;const result=fn();this.pending.splice(0).forEach(fn=>fn());return result;}
 close(){this.effects.forEach(e=>e?.cleanup?.());}
}
let timers=new Map(),nextTimer=0,calls=[],saved=null,current,output;
const initial={credito:{lote:0,quantidade_kg:""}};
function setup(existing=null,allowed=true){globalThis.hooks=new Hooks();globalThis.allowed=allowed;globalThis.generation="user-one";timers=new Map();calls=[];saved=existing;current=structuredClone(initial);globalThis.window={setTimeout:fn=>{const id=++nextTimer;timers.set(id,fn);return id;},clearTimeout:id=>timers.delete(id)};globalThis.draftApi={get:async()=>{calls.push("GET");return{data:{dados:structuredClone(saved)}};},put:async(_,{dados})=>{calls.push(["PUT",structuredClone(dados)]);saved=structuredClone(dados);return{};},delete:async()=>{calls.push("DELETE");saved=null;return{};}};}
function render(){output=hooks.render(()=>useRascunhoAutomatico("producao-saldos",current,v=>{current=v;}));return output;}
async function settle(){for(let i=0;i<8;i++)await Promise.resolve();render();}
async function tick(){const jobs=[...timers.values()];timers.clear();jobs.forEach(fn=>fn());await settle();}
function buttons(element,result=[]){if(!element||typeof element!=="object")return result;if(element.type==="button")result.push(element);const children=element.props?.children;(Array.isArray(children)?children:[children]).forEach(c=>buttons(c,result));return result;}
setup();render();await settle();await tick();assert.deepEqual(calls,["GET"],"Formulário intocado não cria rascunho");
current={credito:{lote:1,quantidade_kg:"50"}};render();await tick();assert.equal(saved.credito.quantidade_kg,"50");
output.limpar(initial);current=structuredClone(initial);render();await settle();await tick();assert.equal(saved,null);assert.equal(calls.at(-1),"DELETE","Sucesso remove o rascunho sem salvar vazio novamente");
setup({credito:{lote:2,quantidade_kg:"100"}});render();await settle();current={credito:{lote:3,quantidade_kg:"90"}};render();await tick();assert.equal(saved.credito.quantidade_kg,"100","Rascunho existente não é sobrescrito antes da decisão");
buttons(output.aviso).find(b=>b.props.children==="Restaurar rascunho").props.onClick();render();assert.equal(current.credito.quantidade_kg,"100");
current={credito:{lote:2,quantidade_kg:"105"}};render();await tick();assert.equal(saved.credito.quantidade_kg,"105");
setup();render();await settle();current={credito:{lote:1,quantidade_kg:"60"}};render();hooks.close();for(let i=0;i<8;i++)await Promise.resolve();assert.equal(saved.credito.quantidade_kg,"60","Sair do módulo salva a última edição sem aguardar o debounce");
setup();render();await settle();current={credito:{lote:1,quantidade_kg:"70"}};render();generation="user-two";await tick();assert.equal(saved,null,"Geração anterior nunca grava na nova conta");
setup(null,false);render();await settle();current={credito:{lote:1,quantidade_kg:"80"}};render();await tick();assert.deepEqual(calls,[],"Consulta sem cadastro não acessa rascunhos");
console.log("6 cenários de rascunhos aprovados: debounce, recuperação, saída do módulo, limpeza, troca de conta e permissão.");
