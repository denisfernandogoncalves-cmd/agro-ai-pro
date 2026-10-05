import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import React from "react";
import {renderToStaticMarkup} from "react-dom/server";
import {createServer, transformWithOxc} from "vite";
const servidor = await createServer({appType:"custom",configLoader:"runner",logLevel:"silent",server:{middlewareMode:true}});
try {
  const {formatarNumero,formatarPercentual}=await servidor.ssrLoadModule("/src/utils/numeros.ts");
  assert.equal(formatarNumero("15000.500"),"15.000,5");assert.equal(formatarNumero(null),"—");assert.equal(formatarPercentual("3.715"),"3,715%");assert.equal(formatarPercentual("14.00"),"14%");
  const {expiracaoToken,sessaoPrecisaRenovar}=await servidor.ssrLoadModule("/src/auth/expiracao.ts");
  const token=exp=>`header.${Buffer.from(JSON.stringify({exp})).toString("base64url")}.signature`;
  assert.equal(expiracaoToken("invalido"),null);assert.equal(expiracaoToken(token("inválido")),null);
  assert.equal(sessaoPrecisaRenovar(token(1000),token(10000),0),false);
  assert.equal(sessaoPrecisaRenovar(token(100),token(10000),0),true);
  assert.equal(sessaoPrecisaRenovar(token(1000),token(250),0),true);
  assert.equal(sessaoPrecisaRenovar(null,token(250),0),false);
  const {default:Backup}=await servidor.ssrLoadModule("/src/pages/Backup/BackupPage.tsx");
  const backupHtml=renderToStaticMarkup(React.createElement(Backup));
  assert.match(backupHtml,/Baixar backup em Excel/);assert.match(backupHtml,/não restaura o sistema/);
  const {autorizado}=await servidor.ssrLoadModule("/src/components/AcoesContext.tsx");
  assert.equal(autorizado({is_staff:false,modulos:["relatorios"],permissoes:{relatorios:["consultar","imprimir"]}},"backup","consultar"),false);
  assert.equal(autorizado({is_staff:true,modulos:[]},"backup","consultar"),true);
  const {correspondeFiltrosRapidos,restaurarConsultaFavorita,default:FiltrosRapidos} = await servidor.ssrLoadModule("/src/components/FiltrosRapidos.tsx");
  assert.deepEqual(restaurarConsultaFavorita({search:"#52",mostrarHistorico:"true",cultura:"Soja",safra:"2026/2027",propriedade:2}),{busca:"#52",mostrarHistorico:true,filtros:{cultura:"Soja",safra:"2026/2027",propriedade:"2"}});
  assert.deepEqual(restaurarConsultaFavorita({search:"legado"}),{busca:"legado",mostrarHistorico:false,filtros:{cultura:"",safra:"",propriedade:""}});
  assert.deepEqual(restaurarConsultaFavorita({propriedade:null,cultura:{}}).filtros,{cultura:"",safra:"",propriedade:""});
  const filtros = {cultura:"Soja",safra:"2026/2027",propriedade:"2"};
  assert.equal(correspondeFiltrosRapidos(filtros,"Soja","2026/2027",[1,2]),true);
  assert.equal(correspondeFiltrosRapidos(filtros,"Milho","2026/2027",[2]),false);
  assert.equal(correspondeFiltrosRapidos(filtros,"Soja","2026",[2]),false);
  assert.equal(correspondeFiltrosRapidos(filtros,"Soja","2026/2027",[3]),false);
  const resumo=renderToStaticMarkup(React.createElement(FiltrosRapidos,{valor:filtros,alterar(){},culturas:["Soja"],safras:["2026/2027"],propriedades:[{id:2,nome:"Electra"}],busca:"#52",limparBusca(){},quantidade:1}));
  for(const texto of ["Busca: #52","Cultura: Soja","Safra: 2026/2027","Propriedade: Electra","Limpar filtros"]) assert.ok(resumo.includes(texto));
  const {cargaCorrespondeBusca} = await servidor.ssrLoadModule("/src/pages/CargasColhidas/CargasColhidasPage.tsx");
  const carga={id:52,contexto_colheita:{},propriedade:2,propriedade_nome:"Electra",cad_pro_codigo:"12345"};
  for(const busca of ["52","#52","carga 52"," CARGA #52 ","12345"]) assert.equal(cargaCorrespondeBusca(carga,busca),true,busca);
  assert.equal(cargaCorrespondeBusca(carga,"#5"),false,"Número explícito não aceita parcial");
  const {transferenciaCorrespondeBusca,previaSaldoTransferencia} = await servidor.ssrLoadModule("/src/pages/TransferenciasSaldo/TransferenciasSaldoPage.tsx");
  const par={saida:{id:126,posicao:1,quantidade_kg:"15000",propriedade_id:1,cad_pro_codigo:"123",cultura:"Milho",safra:"2026"},entrada:{id:127,posicao:2,quantidade_kg:"15000",propriedade_id:2}};
  for(const termo of ["#126","127","transferência 126"]) assert.equal(transferenciaCorrespondeBusca(par,termo,[]),true);
  assert.equal(transferenciaCorrespondeBusca(par,"#12",[]),false);
  const p=(id, fisico, disponivel=fisico)=>({id,propriedade_id:id,cad_pro:"cad",armazem:1,cultura:"Milho",safra:"2026",saldo_fisico_kg:String(fisico),saldo_disponivel_kg:String(disponivel),saldo_comprometido_kg:String(fisico-disponivel)});
  const posicoes=[p(1,0),p(2,15000,14000),p(3,5000)];
  const antes=structuredClone(posicoes);
  const mesmo=previaSaldoTransferencia(posicoes,par,posicoes[0],posicoes[1],14000);
  assert.deepEqual(mesmo.map(l=>[l.posicao.id,l.posterior,l.disponivel]),[[1,1000,1000],[2,14000,13000]]);
  const troca=previaSaldoTransferencia(posicoes,par,posicoes[0],posicoes[2],14000);
  assert.deepEqual(troca.map(l=>[l.posicao.id,l.posterior,l.disponivel]),[[1,1000,1000],[2,0,-1000],[3,19000,19000]],"Destino antigo reservado permanece no cálculo");
  assert.deepEqual(posicoes,antes,"Prévia nunca modifica os saldos recebidos");
  const {previaEdicaoVenda}=await servidor.ssrLoadModule("/src/pages/Vendas/previaEdicaoVenda.ts");
  const venda={posicao:1,quantidade_kg:"100",quantidade_entregue_kg:"60",quantidade_devolvida_kg:"10",quantidade_reservada_kg:"40",status:"parcial"};
  const saldos=[p(1,500,460),p(2,100)];
  const alvo={venda,natureza:"venda",excluir:false};
  assert.equal(previaEdicaoVenda(alvo,saldos,150,1).linhas[0].disponivel,410);
  assert.match(previaEdicaoVenda(alvo,saldos,50,1).bloqueio,/contratado/);
  assert.match(previaEdicaoVenda(alvo,saldos,100,2).bloqueio,/entregas/);
  assert.equal(previaEdicaoVenda({...alvo,excluir:true},saldos,100,1).linhas[0].posterior,550);
  const entrega=previaEdicaoVenda({...alvo,natureza:"entrega",movimento:{quantidade_kg:"20"}},saldos,30,1);
  assert.equal(entrega.linhas[0].posterior,490);assert.equal(entrega.linhas[0].disponivel,460,"Entrega ajusta físico e reserva juntos");
  const devolucao=previaEdicaoVenda({...alvo,natureza:"devolucao",movimento:{quantidade_kg:"10"}},saldos,15,1);
  assert.equal(devolucao.linhas[0].posterior,505);assert.equal(devolucao.linhas[0].disponivel,465);
  const {AcoesContext,BotaoAcao}=await servidor.ssrLoadModule("/src/components/AcoesContext.tsx");
  const bloqueado=renderToStaticMarkup(React.createElement(BotaoAcao,{acao:"excluir",disabled:true,motivoBloqueio:"Informe o motivo"},"Excluir"));
  assert.match(bloqueado,/role="status"[^>]*>Informe o motivo/);
  const semPermissao=renderToStaticMarkup(React.createElement(AcoesContext.Provider,{value:{modulo:"vendas",acesso:{is_staff:false,modulos:["vendas"],permissoes:{vendas:["consultar"]}}}},React.createElement(BotaoAcao,{acao:"excluir",disabled:true,motivoBloqueio:"Informe o motivo"},"Excluir")));
  assert.equal(semPermissao,"","Ajuda não revela ações sem permissão");
} finally {await servidor.close();}

// Exercita o hook real com ciclos de renderização, sem persistir formulários.
let sequence=0;
const url=code=>`data:text/javascript;base64,${Buffer.from(code+"\n//"+sequence++).toString("base64")}`;
const shim=url(`export const createContext=()=>({Provider:"provider"});export const useContext=()=>globalThis.registry;export const useState=(...a)=>globalThis.hooks.state(...a);export const useRef=(...a)=>globalThis.hooks.ref(...a);export const useId=()=>globalThis.hooks.ref("form").current;export const useMemo=fn=>globalThis.hooks.ref(fn()).current;export const useEffect=(...a)=>globalThis.hooks.effect(...a);`);
const confirma=url(`export const useConfirmacaoCompacta=()=>globalThis.ask;`);
let source=await readFile(new URL("../src/components/AlteracoesNaoSalvas.tsx",import.meta.url),"utf8");
source=source.replace('from "react"',`from "${shim}"`).replace('from "./ConfirmacaoCompacta"',`from "${confirma}"`);
const transformed=await transformWithOxc(source,"guard.tsx",{lang:"tsx",sourceType:"module",target:"es2022",jsx:{runtime:"automatic"}});
const {criarRegistroAlteracoes,useAlteracoesNaoSalvas,useConfirmarSaida,ProtecaoAlteracoes}=await import(url(transformed.code.replaceAll('"react/jsx-runtime"',JSON.stringify(import.meta.resolve("react/jsx-runtime")))));
class Hooks {
  values=[];effects=[];cursor=0;pending=[];
  state(initial){const i=this.cursor++;if(!(i in this.values))this.values[i]=typeof initial==="function"?initial():initial;return[this.values[i],v=>{this.values[i]=typeof v==="function"?v(this.values[i]):v;}];}
  ref(initial){const i=this.cursor++;if(!(i in this.values))this.values[i]={current:initial};return this.values[i];}
  effect(fn,deps){const i=this.cursor++;const old=this.effects[i];if(!old||deps.some((v,k)=>!Object.is(v,old.deps[k])))this.pending.push(()=>{old?.cleanup?.();this.effects[i]={deps,cleanup:fn()};});}
  render(fn){this.cursor=0;const result=fn();this.pending.splice(0).forEach(fn=>fn());return result;}
  close(){this.effects.forEach(e=>e?.cleanup?.());}
}
globalThis.registry=criarRegistroAlteracoes();globalThis.hooks=new Hooks();
let decisions=[], aceitar=false;
globalThis.window={confirm:text=>{decisions.push(text);return aceitar;}};
globalThis.ask=async pedido=>{decisions.push(pedido.mensagem);return aceitar;};
let valor={peso:"100"},identidade=52,ativo=true;
const render=()=>hooks.render(()=>useAlteracoesNaoSalvas(valor,"Carga",identidade,ativo));
let guard=render();assert.equal(guard.alterado,false);assert.deepEqual(registry.descricoes(),[]);
valor={peso:"120"};guard=render();assert.equal(guard.alterado,true);assert.equal(await useConfirmarSaida()(),false);assert.equal(decisions.length,1);
assert.equal(await guard.confirmarDescarte(),false);assert.equal(guard.alterado,true,"Cancelar saída mantém formulário");
aceitar=true;assert.equal(await useConfirmarSaida()(),true);
guard.marcarSalvo();guard=render();assert.equal(guard.alterado,false);assert.deepEqual(registry.descricoes(),[]);
valor={peso:"121"};render();valor={peso:"300"};identidade=53;guard=render();assert.equal(guard.alterado,false,"Abrir outro registro estabelece referência limpa");
valor={peso:"301"};render();ativo=false;render();assert.deepEqual(registry.descricoes(),[]);
ativo=true;render();assert.equal(registry.descricoes().length,1);hooks.close();assert.deepEqual(registry.descricoes(),[],"Desmontagem não deixa avisos em outra tela/conta");
const eventos=new Map();globalThis.hooks=new Hooks();
window.addEventListener=(nome,fn)=>eventos.set(nome,fn);window.removeEventListener=nome=>eventos.delete(nome);
const provider=hooks.render(()=>ProtecaoAlteracoes({children:null}));const registro=provider.props.value;
let prevented=false;const ev={preventDefault(){prevented=true;}};
eventos.get("beforeunload")(ev);assert.equal(prevented,false);
registro.atualizar("1","Venda",true);eventos.get("beforeunload")(ev);assert.equal(prevented,true);assert.equal(ev.returnValue,"");
hooks.close();assert.equal(eventos.size,0);
delete globalThis.hooks;delete globalThis.registry;delete globalThis.window;delete globalThis.ask;
console.log("Usabilidade aprovada: busca por número/CAD, filtros combinados, prévias de saldos/reservas, ajuda com permissões e proteção de alterações/saída.");
