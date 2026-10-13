// Sem tokens ou senhas nos lançamentos locais.
export function novoUUID() {
  if (crypto.randomUUID) return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  const hex = [...bytes].map(v => v.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
}

export class FilaOffline {
  constructor(armazenamento, identidade, enviar, uuid = novoUUID, identidadeRecuperacao = identidade) {
    this.armazenamento = armazenamento;
    this.identidade = identidade;
    this.enviar = enviar;
    this.uuid = uuid;
    this.identidadeRecuperacao = identidadeRecuperacao;
    this.execucao = null;
  }

  async exportar() {
    const dono = await this.identidadeRecuperacao();
    if (!dono) throw new Error('Entre na conta que preparou este aparelho para exportar a fila.');
    const itens = (await this.armazenamento.listar()).filter(i => i.usuario === dono.usuario && i.servidor === dono.servidor && i.estado !== 'sincronizado');
    return JSON.stringify({ formato: 'agro-fila-offline', versao: 1, exportadoEm: new Date().toISOString(), servidor: dono.servidor, usuario: dono.usuario, itens }, null, 2);
  }

  async recuperar(texto) {
    const dono = await this.identidadeRecuperacao();
    if (!dono) throw new Error('Entre na conta e prepare o aparelho antes de recuperar a fila.');
    if (texto.length > 10 * 1024 * 1024) throw new Error('Arquivo excede 10 MB.');
    let backup;
    try { backup = JSON.parse(texto); } catch { throw new Error('Arquivo de recuperação inválido.'); }
    if (backup?.formato !== 'agro-fila-offline' || backup.versao !== 1 || !Array.isArray(backup.itens) || backup.itens.length > 10000) throw new Error('Formato de recuperação inválido.');
    this.validarDono(backup, dono);
    const ids = new Set();
    const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    const itens = backup.itens.map(item => {
      this.validarDono(item, dono);
      if (!uuid.test(item.id) || !uuid.test(item.dispositivo) || ids.has(item.id) ||
          !['pendente', 'enviando', 'conflito', 'bloqueado', 'verificar'].includes(item.estado) ||
          !Number.isSafeInteger(item.tentativas) || item.tentativas < 0 || !Number.isFinite(Date.parse(item.criadoEm)) ||
          !item.dados || typeof item.dados !== 'object' || Array.isArray(item.dados) ||
          !(item.registro === null && item.versao_original === null || Number.isSafeInteger(item.registro) && item.registro > 0 && typeof item.versao_original === 'string' && item.versao_original.length > 0)) throw new Error('Lançamento inválido ou duplicado no arquivo.');
      ids.add(item.id);
      return { id: item.id, servidor: item.servidor, usuario: item.usuario, dispositivo: item.dispositivo,
        estado: item.estado === 'enviando' ? 'pendente' : item.estado, tentativas: item.tentativas,
        criadoEm: item.criadoEm, dados: item.dados, registro: item.registro, versao_original: item.versao_original };
    });
    return this.armazenamento.recuperar(itens);
  }

  async cadastrar(dados, original = null) {
    const identidade = await this.identidade();
    if (!identidade) throw new Error('Entre na sua conta antes de trabalhar offline.');
    const item = {
      id: this.uuid(), servidor: identidade.servidor, usuario: identidade.usuario,
      dispositivo: identidade.dispositivo, estado: 'pendente', tentativas: 0,
      criadoEm: new Date().toISOString(), dados: structuredClone(dados),
      registro: original?.registro ?? null, versao_original: original?.versao ?? null,
    };
    if (original && (!Number.isInteger(original.registro) || !original.versao)) {
      throw new Error('Baixe a versão original da carga antes de editar offline.');
    }
    await this.armazenamento.inserir(item);
    return item;
  }

  async listar() {
    const dono = await this.identidade();
    if (!dono) return [];
    return (await this.armazenamento.listar()).filter(item =>
      item.usuario === dono.usuario && item.servidor === dono.servidor);
  }

  async editar(id, dados) {
    const dono = await this.identidade();
    if (!dono) throw new Error('Sessão encerrada.');
    return this.armazenamento.alterar(id, item => {
      this.validarDono(item, dono);
      if (item.tentativas > 0 || item.estado !== 'pendente') {
        throw new Error('Operação já enviada. Confira a confirmação antes de alterar seu conteúdo.');
      }
      return { ...item, dados: structuredClone(dados) };
    });
  }

  validarDono(item, dono) {
    if (!item || item.usuario !== dono.usuario || item.servidor !== dono.servidor) {
      throw new Error('Lançamento pertence a outra conta ou servidor.');
    }
  }

  sincronizar() {
    if (!this.execucao) this.execucao = this.processar().finally(() => { this.execucao = null; });
    return this.execucao;
  }

  async processar() {
    for (const local of await this.listar()) {
      if (!['pendente', 'enviando'].includes(local.estado)) continue;
      const dono = await this.identidade(true);
      if (!dono) break;
      this.validarDono(local, dono);
      const item = await this.armazenamento.alterar(local.id, atual => {
        this.validarDono(atual, dono);
        if (!['pendente', 'enviando'].includes(atual.estado)) return atual;
        return { ...atual, estado: 'enviando', tentativas: atual.tentativas + 1 };
      });
      if (item.estado !== 'enviando') continue;
      let resposta;
      try {
        resposta = await this.enviar({
          servidor: item.servidor, usuario: item.usuario, operacao: item.id, dispositivo: item.dispositivo,
          registro: item.registro, versao_original: item.versao_original, dados: item.dados,
        }, dono);
      } catch {
        // Pode ter sido confirmado no servidor: só reenviar o mesmo identificador e conteúdo.
        await this.armazenamento.alterar(item.id, atual => ({ ...atual, estado: 'pendente',
          mensagem: 'Sem confirmação. Conteúdo preservado para reenvio seguro.' }));
        break;
      }
      if (resposta.status === 401) {
        await this.armazenamento.alterar(item.id, atual => ({ ...atual, estado: 'pendente',
          mensagem: 'Entre novamente para sincronizar.' }));
        break;
      }
      if (resposta.status >= 500) {
        await this.armazenamento.alterar(item.id, atual => ({ ...atual, estado: 'pendente',
          mensagem: 'Servidor indisponível. Conteúdo preservado.' }));
        break;
      }
      const confirmado = resposta.status === 200 && resposta.dados?.operacao === item.id;
      await this.armazenamento.alterar(item.id, atual => ({
        ...atual,
        estado: confirmado ? 'sincronizado' : resposta.status >= 200 && resposta.status < 400 ? 'verificar' : resposta.status === 409 ? 'conflito' : 'bloqueado',
        recibo: confirmado ? resposta.dados : null,
        mensagem: confirmado ? 'Confirmado pelo servidor.' :
          resposta.status === 409 ? 'Conflito: confira a versão do servidor e a alteração local.' :
          'Não confirmado. Confira permissões e os dados antes de tentar outra operação.',
      }));
    }
    return this.listar();
  }
}
