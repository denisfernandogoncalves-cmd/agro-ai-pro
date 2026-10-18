import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
const fonte=await readFile(new URL("../src/pages/Transportes/TransportesPage.tsx",import.meta.url),"utf8");
const guarda=fonte.indexOf('if (aba !== "relatorios"');
const inicio=fonte.lastIndexOf('useEffect(() => {',guarda)+'useEffect(() => {'.length;
const fim=fonte.indexOf('\n  }, [aba,',guarda);
assert.ok(guarda>=0 && fim>inicio,"Efeito de consulta encontrado");
const efeito=new Function("aba","setCarregando","setErro","setRelatorio","consultarRelatorio","aplicados","setRegistros","listarLancamentos","pagina","setRemuneracoes","listarRemuneracoes","paginaRem","motoristaRem","caminhaoRem",fonte.slice(inicio,fim));
let ocupado=false,chamadas=0,erro="",resolver;
let consulta=()=>{chamadas++;return new Promise(r=>{resolver=r;});};
const executar=aba=>efeito(aba,v=>{ocupado=v;},v=>{erro=v;},()=>{},(...args)=>consulta(...args),{},()=>{},()=>consulta(),1,()=>{},()=>consulta(),1,"","");
const limpar=executar("relatorios");assert.equal(ocupado,true);assert.equal(chamadas,1);
limpar();executar("diesel");assert.equal(ocupado,false,"Troca para diesel encerra o indicador do relatório cancelado");assert.equal(chamadas,1,"Aba independente não repete consulta do relatório");
resolver({});await new Promise(r=>setImmediate(r));assert.equal(ocupado,false);
for(const aba of ["diesel","novo","remuneracao","holerite","importar"]){ocupado=true;executar(aba);assert.equal(ocupado,false);}
for(const aba of ["relatorios","lancamentos","historico_remuneracao"]){executar(aba);assert.equal(ocupado,true);resolver({});await new Promise(r=>setImmediate(r));assert.equal(ocupado,false,"Consulta concluída libera a interface");}
assert.equal(erro,"");console.log("Transportes: troca de aba durante consulta e fim do carregamento aprovados.");
