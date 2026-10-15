import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import { pathToFileURL } from 'node:url';
import os from 'node:os';
import { execFileSync } from 'node:child_process';
import assert from 'node:assert/strict';

// Isolated visual review: every API is intercepted, no operational database.
const work = process.env.AGRO_VISUAL_WORKTREE ?? process.cwd();
const artifacts = process.env.AGRO_VISUAL_EVIDENCIAS ?? path.join(work, 'docs/visual/layout-2-0');
const pwModule = process.env.AGRO_PLAYWRIGHT_MODULE ?? 'playwright';
const { chromium } = await import(path.isAbsolute(pwModule) ? pathToFileURL(pwModule).href : pwModule);
const { createServer } = await import(pathToFileURL(path.join(work, 'frontend/node_modules/vite/dist/node/index.js')));
const baselineFolder = await fs.mkdtemp(path.join(os.tmpdir(), 'agro-layout-review-'));
const sourceArchive = path.join(baselineFolder, 'frontend.tar');
execFileSync('git', ['archive', '--format=tar', '--output=' + sourceArchive, process.env.AGRO_VISUAL_BASE ?? '0892127', 'frontend'], {cwd: work});
execFileSync('tar', ['-xf', sourceArchive, '-C', baselineFolder]);
const baselineRoot = path.join(baselineFolder, 'frontend');
await fs.symlink(path.join(work, 'frontend/node_modules'), path.join(baselineRoot, 'node_modules'), process.platform === 'win32' ? 'junction' : 'dir');
const baseline = await createServer({ root: baselineRoot, configLoader: 'runner', server: { host:'127.0.0.1', port:5176, strictPort:true }, logLevel:'error' });
await baseline.listen();
const mime = {'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml','.png':'image/png','.json':'application/json'};
const dist = path.join(work, 'frontend/dist');
const staticServer = http.createServer(async (req,res) => {
  let name = path.resolve(dist, '.' + new URL(req.url, 'http://localhost').pathname);
  if (!name.startsWith(path.resolve(dist) + path.sep)) name = path.join(dist, 'index.html');
  try { if ((await fs.stat(name)).isDirectory()) name = path.join(name,'index.html'); } catch { name = path.join(dist,'index.html'); }
  try { res.writeHead(200,{'content-type':mime[path.extname(name)] ?? 'application/octet-stream'}); res.end(await fs.readFile(name)); } catch { res.writeHead(404);res.end(); }
});
await new Promise(resolve => staticServer.listen(5175,'127.0.0.1',resolve));
const out = artifacts; await fs.mkdir(out,{recursive:true});
const browser = await chromium.launch({ channel:process.env.AGRO_BROWSER_CHANNEL ?? 'msedge', headless:true });
const modules = ['propriedades','talhoes','cadastros-agricolas','cargas','producao-saldos','transferencias','vendas','clima','mercado','financeiro','estoque','operacoes','maquinas','transportes','relatorios','insights'];
const propriedade = {id:1,nome:'Fazenda de demonstração',proprietario:'Cadastro fictício para revisão',apelidos:[],municipio:'Município demonstrativo',uf:'PR',area_hectares:'242',cad_pro_numeros:['DEMO'],latitude:null,longitude:null,geometria_geojson:null,observacoes:'',bp_cvale:'',area_calculada_hectares:null};
const posicao = {id:1,cad_pro:'demo',cad_pro_codigo:'DEMO',cultura:'Soja',safra:'2026/2027',classificacao_codigo:'Comercial',armazem:1,armazem_nome:'Armazém demonstrativo',propriedade_id:1,propriedade_nome:propriedade.nome,saldo_fisico_kg:'28000',saldo_comprometido_kg:'7000',saldo_disponivel_kg:'21000',versao:1};
const hoje = new Date().toLocaleDateString('sv-SE',{timeZone:'America/Sao_Paulo'});
const old = '2025-01-01T12:00:00Z';
const weather = Array.from({length:7},(_,i) => {const d=new Date(hoje+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+i);return {id:i+1,propriedade:1,data:d.toISOString().slice(0,10),temperatura_min:'18',temperatura_max:'27',chuva_mm:String(i+1),probabilidade_chuva:50,umidade:70,vento_kmh:'12',condicao:i%2?'Chuva fraca':'Céu claro',alerta_agricola:'',fonte:'Demonstração da apresentação; não é previsão real',atualizado_em:old};});
const resumo={saldo_disponivel_kg:'21000',producao_kg:'28000',vendas_kg:'7000',a_pagar:'3000',propriedades:1,cargas:1,a_receber:'9000',estoque_baixo:1};
const painel={gerado_em:old,resumo,alertas:[{id:'demo',tipo:'estoque-baixo',titulo:'Exemplo de aviso para revisão visual',modulo:'estoque',filtros:{},nivel:'urgente'}],saldos:[{propriedade_id:1,propriedade:propriedade.nome,cultura:'Soja',safra:'2026/2027',fisico_kg:'28000',disponivel_kg:'21000'}],limite_saldos:100,limite_por_tipo:20};
const cotacoes = Array.from({length:6},(_,i)=>({id:i+1,produto:'soja',produto_nome:'Soja — série demonstrativa',data:`2026-0${i+1}-01`,valor:String(350+i*5),unidade:'US$/t',fonte:'Série fictícia de revisão visual',atualizado_em:old}));
const venda={id:1,contrato:null,versao:1,excluida_em:null,alteracoes:[],numero_contrato:'DEMO-001',cliente_nome:'Comprador demonstrativo',status:'parcial',posicao:1,lote_operacional:1,lote_operacional_codigo:'DEMO',origem_fisica_alocada:true,cad_pro:'demo',cad_pro_codigo:'DEMO',cultura:'Soja',safra:'2026/2027',classificacao_codigo:'Comercial',contrato_preco_venda:null,contrato_unidade_preco:null,armazem_nome:posicao.armazem_nome,propriedade:1,propriedade_nome:propriedade.nome,quantidade_kg:'12000',quantidade_reservada_kg:'7000',quantidade_entregue_kg:'5000',quantidade_devolvida_kg:'1000',quantidade_cancelada_kg:'0',quantidade_aberta_kg:'7000',data_contrato:hoje,data_limite_entrega:null,observacoes:'Demonstração',entregas:[],devolucoes:[]};
const requests=[], errors=[], checks=[];
async function context(mode='normal',restricted=false) {
  const ctx=await browser.newContext({viewport:{width:1440,height:1000},serviceWorkers:'block',reducedMotion:'reduce'});
  await ctx.addInitScript(()=>{ const payload=btoa(JSON.stringify({exp:Math.floor(Date.now()/1000)+3600}));localStorage.setItem('agro-ai-pro.access-token',`demo.${payload}.fixture`);localStorage.setItem('agro-ai-pro.refresh-token','fixture-only'); });
  await ctx.route('**/*',async route=>{
    const u=new URL(route.request().url()), p=u.pathname;
    if (!p.startsWith('/api/')) { if(['127.0.0.1','localhost'].includes(u.hostname)) return route.continue(); return route.abort(); }
    requests.push({path:p,method:route.request().method(),mode});
    const headers={'access-control-allow-origin':'*','access-control-allow-headers':'*','access-control-allow-methods':'*'};
    if(route.request().method()==='OPTIONS')return route.fulfill({status:204,headers});
    if(mode==='error' && p==='/api/core/painel/')return route.fulfill({status:503,headers,json:{detail:'Falha simulada para revisão'}});
    let data;
    if(p==='/api/auth/me/')data={id:1,username:'DEMONSTRAÇÃO',is_staff:false,modulos:restricted?['mercado']:modules,permissoes:restricted?{mercado:['consultar']}:undefined};
    else if(p==='/api/auth/logout/')data={};
    else if(p==='/api/propriedades/')data=mode==='empty'?[]:[propriedade];
    else if(p==='/api/core/painel/')data=mode==='empty'?{...painel,resumo:{},alertas:[],saldos:[]}:painel;
    else if(p==='/api/mercado/referencias/')data={cotacoes:mode==='empty'?[]:[{produto:'soja',valor:'10.5000',unidade:'US$/bushel',cotado_em:old,simbolo:'DEMO',contrato:'DEMO-2026',fonte:'Fonte demonstrativa',url:'https://example.com',valor_original:'1050',atraso_provedor:true,mercado_aberto:false,erro:'Dado antigo demonstrativo; fonte simulada'}],intervalo_segundos:60};
    else if(p==='/api/mercado/cotacoes/resumo/')data=mode==='empty'?[]:[{produto:'soja',produto_nome:'Soja — exemplo',data:'2026-06-01',valor:'375',unidade:'US$/t',variacao_percentual:'1',tendencia:'Exemplo',aviso:'Dados fictícios para revisão visual'}];
    else if(p==='/api/mercado/cotacoes/')data=mode==='empty'?[]:cotacoes;
    else if(p==='/api/clima/previsoes/')data=mode==='empty'?[]:weather;
    else if(p==='/api/graos/saldos/painel/')data={resumo:{saldo_fisico_kg:'28000',saldo_comprometido_kg:'7000',saldo_disponivel_kg:'21000',propriedades:1,cadpros:1,posicoes:1},posicoes:mode==='empty'?[]:[posicao],consolidado_cadpro:[],consolidado_propriedade:[]};
    else if(p==='/api/graos/saldos/')data=mode==='empty'?[]:[posicao];
    else if(p==='/api/cadpros/')data=[{id:'demo',codigo:'DEMO',descricao:'Cadastro demonstrativo',propriedades:[1],ativo:true}];
    else if(p==='/api/graos/armazens/')data=[{id:1,nome:'Armazém demonstrativo',ativo:true}];
    else if(p==='/api/graos/lotes/')data=[];
    else if(p==='/api/comercial/vendas/')data=mode==='empty'?[]:[venda];
    else if(p==='/api/talhoes/talhoes/')data=u.searchParams.has('page')?{count:0,results:[]}:[];
    else if(p==='/api/maquinas/maquinas/')data=mode==='empty'?[]:[{id:1,atualizado_em:old,identificacao:'Trator demonstrativo',tipo:'trator',marca:'Cadastro',modelo:'Exemplo',ano:2026,propriedade:1,propriedade_nome:propriedade.nome,status:'ativa',horimetro_atual:'120',observacoes:''}];
    else if(p==='/api/transportes/caminhoes/')data=mode==='empty'?[]:[{id:1,placa:'DEMO001',veiculo:'Caminhão demonstrativo',motorista:'Motorista demonstrativo',ativo:true}];
    else if(p==='/api/transportes/lancamentos/relatorio/')data={resumo:{nome:'Consulta demonstrativa',receita:'560',despesas_operacionais:'100',salario:'0',comissao:'44.80',despesas:'144.80',saldo:'415.20',margem:null,quantidade_lancamentos:1},por_placa:[],por_motorista:[],por_mes:[],categorias:[],ranking_financeiro:[],ranking_eficiencia:[],ranking_operacional:[],documentos_sem_motorista:0};
    else if(p==='/api/transportes/lancamentos/' || p==='/api/transportes/remuneracoes/')data={count:0,results:[]};
    else if(p==='/api/ai/insights/')data={insights:[],aviso:'Consulta demonstrativa'};
    else if(['/api/mercado/corn-belt/','/api/mercado/noticias/','/api/graos/movimentacoes/','/api/comercial/contratos/','/api/maquinas/manutencoes/','/api/maquinas/usos/','/api/maquinas/abastecimentos/','/api/producao/operacoes/'].includes(p))data=[];
    else return route.fulfill({status:503,headers,json:{detail:'Consulta fora dos dados desta demonstração visual; não há serviço operacional conectado.'}});
    return route.fulfill({status:200,headers,json:data});
  });
  return ctx;
}
async function label(page){ await page.evaluate(()=>{if(!document.getElementById('demo-label')){const div=document.createElement('div');div.id='demo-label';div.textContent='DEMONSTRAÇÃO VISUAL · DADOS FICTÍCIOS · API ISOLADA';Object.assign(div.style,{position:'fixed',bottom:'0',right:'0',zIndex:'9999',padding:'5px 9px',background:'#fff5de',color:'#654000',fontSize:'10px',border:'1px solid #C5A46B'});document.body.append(div);}}); }
async function screenshot(page,name) {await label(page);await page.screenshot({path:path.join(out,name+'.png'),fullPage:true}); const bounds=await page.evaluate(()=>({body:document.documentElement.scrollWidth,width:innerWidth}));if(name.startsWith('depois'))assert.ok(bounds.body<=bounds.width+1,`${name}: page overflow ${JSON.stringify(bounds)}`);checks.push(name+': '+(bounds.body<=bounds.width+1?'sem scroll horizontal da página':`overflow preexistente ${bounds.body-bounds.width}px`));}
async function openModule(page,name,isNew=true){ if(await page.locator('.alternar-menu-lateral').isVisible()) await page.locator('.alternar-menu-lateral').click(); try {await page.locator('.menu-lateral-completo button').filter({hasText:new RegExp('^'+name+'$')}).click({timeout:5000});} catch(e) {console.log('Navigation failure',name,await page.locator('body').innerText(),errors);throw e;}await page.waitForTimeout(300); }
try {
  for(const [version,port] of [['antes',5176],['depois',5175]]){
    const ctx=await context(); const page=await ctx.newPage();page.on('pageerror',e=>errors.push({version,message:e.message}));await page.goto(`http://127.0.0.1:${port}`);await page.getByText('Visão geral da gestão',{exact:true}).waitFor();await screenshot(page,version+'-painel-1440');
    for(const width of [1366,768,390]){await page.setViewportSize({width,height:1000});await screenshot(page,`${version}-painel-${width}`);}
    await page.setViewportSize({width:1440,height:1000});
    for(const name of ['Propriedades','Talhões','Produção e saldos','Vendas','Mercado','Clima','Máquinas','Transportes','Assistente']){await openModule(page,name);if(name==='Vendas')await page.getByRole('tab',{name:/Vendas registradas/}).click();await screenshot(page,version+'-'+name.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replaceAll(' ','-').toLowerCase()+'-1440');if(version==='depois'){await page.setViewportSize({width:390,height:1000});await screenshot(page,version+'-'+name.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replaceAll(' ','-').toLowerCase()+'-390');await page.setViewportSize({width:1440,height:1000});if(name==='Produção e saldos'||name==='Vendas'){await page.emulateMedia({media:'print'});assert.equal(await page.locator(name==='Vendas'?'.fluxo-venda':'.composicao-saldos').isVisible(),false);await page.pdf({path:path.join(out,`impressao-${name==='Vendas'?'vendas':'saldos'}.pdf`),format:'A4'});await page.emulateMedia({media:'screen'});checks.push(`${name}: componentes visuais novos ocultos em A4`);}}}
    if(version==='depois'){
      await page.keyboard.press('Control+k');await page.locator('.busca-navegacao input').fill('mercado');assert.equal(await page.locator('.menu-lateral-completo button').count(),1);await page.keyboard.press('Escape');checks.push('Ctrl K e Escape na busca de módulos');
      await page.getByRole('button',{name:'Sair',exact:true}).click();await page.getByRole('heading',{name:'Acesse sua conta'}).waitFor();assert.equal(await page.locator('[data-modulo]').count(),0);checks.push('Logout desmonta área privada na prévia');
    }
    await ctx.close();
  }
  for(const mode of ['empty','error']){const ctx=await context(mode);const page=await ctx.newPage();await page.goto('http://127.0.0.1:5175');await page.waitForTimeout(500);await screenshot(page,'depois-painel-'+mode);await ctx.close();}
  const restricted=await context('normal',true);const pg=await restricted.newPage();await pg.goto('http://127.0.0.1:5175');await pg.waitForTimeout(500);assert.equal(await pg.locator('.menu-lateral-completo button[title="Máquinas"]').count(),0);checks.push('Conta com Mercado não recebe navegação para Máquinas');await screenshot(pg,'depois-permissao-mercado');await restricted.close();
  assert.equal(errors.length,0,JSON.stringify(errors));
  await fs.writeFile(path.join(out,'checks.json'),JSON.stringify({fixture:true,realDatabaseAccess:false,checks,errors,apiRequests:requests.length},null,2));
  console.log(JSON.stringify({checks:checks.length,errors,output:out},null,2));
} finally {await browser.close();await baseline.close();await new Promise(resolve=>staticServer.close(resolve));}
