const DB = 'agro-ai-pro.offline.v1';

export class ArmazenamentoOffline {
  async abrir() {
    return new Promise((resolve, reject) => {
      const pedido = indexedDB.open(DB, 2);
      pedido.onupgradeneeded = () => {
        if (!pedido.result.objectStoreNames.contains('fila')) pedido.result.createObjectStore('fila', { keyPath: 'id' });
        if (!pedido.result.objectStoreNames.contains('contextos')) pedido.result.createObjectStore('contextos', { keyPath: 'id' });
      };
      pedido.onsuccess = () => resolve(pedido.result);
      pedido.onerror = () => reject(pedido.error);
      pedido.onblocked = () => reject(new Error('Feche as outras janelas para atualizar o armazenamento offline.'));
    });
  }

  async executar(modo, operacao, tabela = 'fila') {
    const db = await this.abrir();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(tabela, modo);
      let resultado;
      tx.oncomplete = () => { db.close(); resolve(resultado); };
      tx.onerror = () => { db.close(); reject(tx.error); };
      tx.onabort = () => { db.close(); reject(tx.error || new Error('Gravação local interrompida.')); };
      operacao(tx.objectStore(tabela), valor => { resultado = valor; }, tx);
    });
  }

  inserir(item) {
    return this.executar('readwrite', (store, retorno) => {
      store.add(item);
      retorno(item);
    });
  }

  listar() {
    return this.executar('readonly', (store, retorno) => {
      store.getAll().onsuccess = evento => retorno(evento.target.result);
    });
  }

  recuperar(itens) {
    let erro;
    return this.executar('readwrite', (store, retorno, tx) => {
      let inseridos = 0;
      for (const item of itens) store.get(item.id).onsuccess = evento => {
        try {
          const atual = evento.target.result;
          if (atual) {
            for (const campo of ['servidor', 'usuario', 'dispositivo', 'registro', 'versao_original', 'dados']) {
              if (JSON.stringify(atual[campo]) !== JSON.stringify(item[campo])) throw new Error('Identificador já existente com conteúdo diferente. Nenhum lançamento foi recuperado.');
            }
          } else { store.add(item); inseridos++; }
          retorno(inseridos);
        } catch (falha) { erro = falha; tx.abort(); }
      };
      retorno(0);
    }).catch(falha => { throw erro || falha; });
  }

  alterar(id, transformar) {
    let erro;
    return this.executar('readwrite', (store, retorno, tx) => {
      store.get(id).onsuccess = evento => {
        try {
          const novo = transformar(evento.target.result);
          store.put(novo);
          retorno(novo);
        } catch (falha) { erro = falha; tx.abort(); }
      };
    }).catch(falha => { throw erro || falha; });
  }

  salvarContexto(id, dados) {
    return this.executar('readwrite', (store, retorno) => { store.put({ id, dados }); retorno(dados); }, 'contextos');
  }

  lerContexto(id) {
    return this.executar('readonly', (store, retorno) => {
      store.get(id).onsuccess = evento => retorno(evento.target.result?.dados ?? null);
    }, 'contextos');
  }
}
