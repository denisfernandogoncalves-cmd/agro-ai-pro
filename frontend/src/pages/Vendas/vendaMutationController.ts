type GerarChave = () => string;

function gerarChavePadrao() {
  const uuid = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
  return `vendas-ui:${uuid}`;
}

export function criarControladorMutacaoVenda(gerarChave: GerarChave = gerarChavePadrao) {
  let tentativa: { assinatura: string; chave: string } | null = null;
  let pendente: Promise<unknown> | null = null;

  return {
    emAndamento: () => pendente !== null,
    executar<T>(assinatura: string, enviar: (chave: string) => Promise<T>): Promise<T> {
      if (pendente) return pendente as Promise<T>;
      if (!tentativa || tentativa.assinatura !== assinatura) {
        tentativa = { assinatura, chave: gerarChave() };
      }
      const atual = enviar(tentativa.chave)
        .then((resultado) => {
          tentativa = null;
          return resultado;
        })
        .finally(() => { pendente = null; });
      pendente = atual;
      return atual;
    },
  };
}

