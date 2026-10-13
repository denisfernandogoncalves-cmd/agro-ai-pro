import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { FilaOffline } from '../src/offline/fila.mjs';

class Memoria {
  itens = new Map();
  async inserir(item) { if (this.itens.has(item.id)) throw Error('Duplicado'); this.itens.set(item.id, structuredClone(item)); }
  async listar() { return structuredClone([...this.itens.values()]); }
  async alterar(id, fn) { const novo = fn(structuredClone(this.itens.get(id))); this.itens.set(id, structuredClone(novo)); return novo; }
  async recuperar(itens) {
    const copia = new Map(this.itens); let total = 0;
    for (const item of itens) {
      const atual = copia.get(item.id);
      if (atual) {
        for (const campo of ['servidor', 'usuario', 'dispositivo', 'registro', 'versao_original', 'dados']) {
          if (JSON.stringify(atual[campo]) !== JSON.stringify(item[campo])) throw Error('conteúdo diferente');
        }
      } else { copia.set(item.id, structuredClone(item)); total++; }
    }
    this.itens = copia; return total;
  }
}
let dono = { usuario: 1, servidor: 'servidor-a', dispositivo: randomUUID() };
const memoria = new Memoria();
const recebidos = new Map();
let perderResposta = true, envios = 0;
const fila = new FilaOffline(memoria, async () => dono, async payload => {
  envios++;
  recebidos.set(payload.operacao, payload);
  if (perderResposta) { perderResposta = false; throw Error('Conexão perdida depois da gravação'); }
  return { status: 200, dados: { operacao: payload.operacao, registro: { id: 42 } } };
}, randomUUID);
const item = await fila.cadastrar({ peso_bruto_kg: '1000' });
await fila.editar(item.id, { peso_bruto_kg: '1100' });
await fila.sincronizar();
assert.equal((await fila.listar())[0].estado, 'pendente');
await assert.rejects(fila.editar(item.id, { peso_bruto_kg: '2000' }), /já enviada/);
await Promise.all([fila.sincronizar(), fila.sincronizar()]);
assert.equal(envios, 2);
assert.equal(recebidos.size, 1);
assert.equal((await fila.listar())[0].estado, 'sincronizado');
assert.equal(recebidos.get(item.id).dados.peso_bruto_kg, '1100');
assert.ok(!JSON.stringify(await memoria.listar()).includes('token'));

dono = { ...dono, usuario: 2 };
assert.equal((await fila.listar()).length, 0);
await assert.rejects(fila.editar(item.id, {}), /outra conta/);
dono = { ...dono, usuario: 1, servidor: 'outro-servidor' };
assert.equal((await fila.listar()).length, 0);
await assert.rejects(fila.cadastrar({}, { registro: 1 }), /versão original/);
dono = null;
await assert.rejects(fila.cadastrar({}), /Entre/);
assert.equal((await fila.listar()).length, 0);

for (const [status, esperado] of [[409, 'conflito'], [403, 'bloqueado'], [400, 'bloqueado'], [500, 'pendente'], [401, 'pendente']]) {
  const storage = new Memoria();
  const f = new FilaOffline(storage, async () => ({ usuario: 1, servidor: 'a', dispositivo: 'd' }),
    async () => ({ status }), randomUUID);
  await f.cadastrar({});
  await f.sincronizar();
  assert.equal((await f.listar())[0].estado, esperado);
}
const semEspaco = new FilaOffline({ inserir: async () => { throw Error('Disco cheio'); } }, async () => ({}), async () => {}, randomUUID);
await assert.rejects(semEspaco.cadastrar({}), /Disco cheio/);
console.log('Offline: edição local, perda de resposta, reenvio, isolamento, conflitos, permissões, autenticação e falha de armazenamento aprovados.');

const identidadeBackup = { usuario: 7, servidor: 'backup', dispositivo: randomUUID() };
const origem = new Memoria();
const fonte = new FilaOffline(origem, async () => identidadeBackup, async () => { throw Error('sem conexão'); }, randomUUID);
const pendente = await fonte.cadastrar({ peso_bruto_kg: '3210', motorista: 'Teste' });
await fonte.sincronizar();
const arquivo = await fonte.exportar();
const destino = new Memoria();
const recuperada = new FilaOffline(destino, async () => identidadeBackup, async p => ({status: 200, dados: {operacao: p.operacao}}), randomUUID);
assert.equal(await recuperada.recuperar(arquivo), 1);
assert.equal(await recuperada.recuperar(arquivo), 0);
assert.equal((await recuperada.listar())[0].id, pendente.id);
await assert.rejects(recuperada.editar(pendente.id, {}), /já enviada/);
const adulterado = JSON.parse(arquivo);
adulterado.itens[0].dados.peso_bruto_kg = '9999';
await assert.rejects(recuperada.recuperar(JSON.stringify(adulterado)), /conteúdo diferente/);
assert.equal((await recuperada.listar())[0].dados.peso_bruto_kg, '3210');
adulterado.usuario = 8;
await assert.rejects(recuperada.recuperar(JSON.stringify(adulterado)), /outra conta/);
await assert.rejects(recuperada.recuperar('{'), /inválido/);
const duplicado = JSON.parse(arquivo); duplicado.itens.push(duplicado.itens[0]);
await assert.rejects(recuperada.recuperar(JSON.stringify(duplicado)), /duplicado/);
await recuperada.sincronizar();
assert.equal(await recuperada.recuperar(arquivo), 0);
assert.equal((await recuperada.listar())[0].estado, 'sincronizado');
assert.equal(JSON.parse(await recuperada.exportar()).itens.length, 0);
const vencida = new FilaOffline(origem, async () => null, async () => {}, randomUUID, async () => identidadeBackup);
assert.equal(JSON.parse(await vencida.exportar()).itens.length, 1);
console.log('Recuperação: preservação de IDs e tentativas, importação repetida, isolamento, arquivos inválidos, conteúdo divergente, recibos existentes e exportação após expiração aprovados.');
