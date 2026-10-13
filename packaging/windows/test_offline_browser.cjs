// QA com dados sintéticos. O comportamento de gravação real é testado em apps.offline.
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require(process.env.AGRO_PLAYWRIGHT_PATH || 'C:/Users/DENIS/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');

const root = path.resolve(__dirname, '../../.packaging/frontend-offline-dist');
const mime = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.webmanifest': 'application/manifest+json' };
const server = http.createServer(async (req, res) => {
  try {
    const relative = new URL(req.url, 'http://localhost').pathname;
    const target = path.join(root, relative === '/' ? 'index.html' : relative);
    assert.ok(target.startsWith(root + path.sep));
    const body = await fs.readFile(target);
    res.writeHead(200, {'Content-Type': mime[path.extname(target)] || 'application/octet-stream'});
    res.end(body);
  } catch { res.writeHead(404); res.end(); }
});
const token = user => `e30.${Buffer.from(JSON.stringify({user_id:user, exp:Math.floor(Date.now()/1000)+3600})).toString('base64url')}.ficticio`;

(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless:true});
  const context = await browser.newContext({viewport:{width:1366,height:1000}, serviceWorkers:'block'});
  const page = await context.newPage();
  const erros = [];
  page.on('pageerror', erro => erros.push(erro.message));
  let offline = false, perderResposta = true;
  const recebidos = new Map();
  await context.addInitScript(access => {
    if (!localStorage.getItem('agro-ai-pro.access-token')) {
      localStorage.setItem('agro-ai-pro.access-token', access);
      localStorage.setItem('agro-ai-pro.refresh-token', 'refresh-ficticio');
    }
  }, token(1));
  await context.route('**/api/**', async route => {
    if (offline) return route.abort('internetdisconnected');
    const url = new URL(route.request().url()), endpoint = url.pathname;
    let data = [];
    if (endpoint === '/api/auth/me/') data = {id:1, username:'Operador QA', is_staff:false, modulos:['cargas'], permissoes:{cargas:['consultar','cadastrar','editar']}};
    if (endpoint === '/api/offline/contexto/') data = {usuario:1, servidor:'servidor-qa', modulos:['cargas'], versao:1};
    if (endpoint === '/api/propriedades/') data = [{id:1,nome:'Fazenda Exemplo',municipio:'Sorriso',uf:'MT',area_hectares:'100',cad_pro_numeros:['123'],criado_em:'2026-10-09'}];
    if (endpoint === '/api/cadpros/') data = [{id:'1',codigo:'123'}];
    if (endpoint === '/api/graos/armazens/') data = [{id:1,nome:'Armazém Exemplo'}];
    if (endpoint === '/api/core/painel/') data = {gerado_em:'2026-10-09T12:00:00Z',resumo:{},alertas:[],saldos:[],limite_saldos:100,limite_por_tipo:20};
    if (endpoint === '/api/offline/cargas/' && route.request().method() === 'POST') {
      const payload = route.request().postDataJSON();
      assert.equal(payload.usuario, 1);
      const previous = recebidos.get(payload.operacao);
      if (previous) assert.deepEqual(previous, payload);
      recebidos.set(payload.operacao, payload);
      if (perderResposta) { perderResposta = false; return route.abort('connectionreset'); }
      data = {operacao:payload.operacao, registro:{id:42},versao:'nova-versao'};
    }
    await route.fulfill({status:200, contentType:'application/json', body:JSON.stringify(data)});
  });
  try {
    const url = `http://127.0.0.1:${server.address().port}/`;
    await page.goto(url);
    const painel = page.locator('details').filter({has:page.locator('summary').filter({hasText:'Trabalho offline'})});
    await painel.locator('summary').click();
    await painel.getByRole('button', {name:'Preparar / atualizar aparelho'}).click();
    await painel.getByText('Aparelho preparado.', {exact:false}).waitFor();
    await painel.getByLabel('Propriedade', {exact:true}).selectOption('1');
    await painel.getByLabel('CAD/PRO', {exact:true}).selectOption('1');
    await painel.getByLabel('Armazém', {exact:true}).selectOption('1');
    await painel.getByLabel('Safra', {exact:true}).fill('2026/2027');
    await painel.getByLabel('Peso bruto do produto (kg)', {exact:true}).fill('1000');
    await painel.getByLabel('Placa', {exact:true}).fill('ABC1D23');
    await painel.getByRole('button',{name:'Salvar neste aparelho'}).click();
    await painel.getByText('Salvo neste aparelho.',{exact:false}).waitFor();
    await painel.getByRole('button',{name:'Editar lançamento local'}).click();
    await painel.getByLabel('Peso bruto do produto (kg)',{exact:true}).fill('1100');
    await painel.getByRole('button',{name:'Salvar neste aparelho'}).click();
    offline = true;
    await page.reload();
    await painel.locator('summary').click();
    await painel.getByText('1100 kg',{exact:false}).waitFor();
    const downloadPromise = page.waitForEvent('download');
    await painel.getByRole('button',{name:'Exportar pendentes'}).click();
    const download = await downloadPromise;
    const backup = await fs.readFile(await download.path());
    const conteudo = JSON.parse(backup.toString());
    assert.equal(conteudo.itens.length, 1);
    await page.evaluate(() => new Promise((resolve, reject) => {
      const pedido = indexedDB.open('agro-ai-pro.offline.v1', 2);
      pedido.onsuccess = () => {
        const db = pedido.result, tx = db.transaction('fila', 'readwrite');
        tx.objectStore('fila').clear();
        tx.oncomplete = () => { db.close(); resolve(); };
        tx.onerror = () => { db.close(); reject(tx.error); };
      };
    })); // Somente banco sintético do contexto descartável deste teste.
    const upload = () => painel.getByLabel('Recuperar fila de arquivo').setInputFiles({name:'fila.json',mimeType:'application/json',buffer:backup});
    await upload();
    await painel.getByText('1 lançamento(s) recuperado(s).',{exact:false}).waitFor();
    await upload();
    await painel.getByText('0 lançamento(s) recuperado(s).',{exact:false}).waitFor();
    const divergente = structuredClone(conteudo);
    const novo = structuredClone(divergente.itens[0]); novo.id = require('node:crypto').randomUUID();
    divergente.itens[0].dados.peso_bruto_kg = '9999';
    divergente.itens.unshift(novo);
    await painel.getByLabel('Recuperar fila de arquivo').setInputFiles({name:'divergente.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(divergente))});
    await painel.getByText('Nenhum lançamento foi recuperado.',{exact:false}).waitFor();
    await page.reload();
    await painel.locator('summary').click();
    assert.equal(await painel.getByText('1100 kg',{exact:false}).count(), 1);
    await page.screenshot({path:path.resolve(__dirname,'../../.packaging/offline-desktop.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    assert.ok(await painel.evaluate(el => el.scrollWidth <= el.clientWidth + 1), 'Painel não deve transbordar no celular');
    await page.screenshot({path:path.resolve(__dirname,'../../.packaging/offline-mobile.png'),fullPage:true});
    offline = false;
    await painel.getByRole('button',{name:'Sincronizar pendentes'}).click();
    await painel.getByText('Sem confirmação.',{exact:false}).waitFor();
    await painel.getByRole('button',{name:'Sincronizar pendentes'}).click();
    await painel.getByText('Confirmado pelo servidor.',{exact:false}).waitFor();
    assert.equal(recebidos.size,1);
    assert.equal([...recebidos.values()][0].dados.peso_bruto_kg,'1100');
    await page.evaluate(access => localStorage.setItem('agro-ai-pro.access-token',access),token(2));
    offline = true;
    await page.reload();
    await painel.locator('summary').click();
    assert.equal(await painel.getByText('Armazém Exemplo').count(),0);
    assert.equal(await painel.getByText('1100 kg',{exact:false}).count(),0);
    assert.deepEqual(erros,[]);
    console.log('Browser: exportação, recuperação real em IndexedDB, importação repetida, rollback de colisão, preparação, cadastro, edição, persistência offline, reenvio sem duplicação, isolamento e 390 px aprovados.');
  } catch (erro) {
    console.error('Erros da página:', erros);
    console.error((await page.locator('body').innerText()).slice(0, 3500));
    await page.screenshot({path:path.resolve(__dirname,'../../.packaging/offline-falha.png'),fullPage:true});
    throw erro;
  } finally { await browser.close(); await new Promise(resolve=>server.close(resolve)); }
})().catch(erro=>{console.error(erro);process.exitCode=1;server.close();});
