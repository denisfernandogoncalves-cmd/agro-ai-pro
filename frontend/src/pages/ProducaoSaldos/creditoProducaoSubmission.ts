import { CreditoProducaoInput } from "../../api/producaoSaldos";

type DadosCredito = Omit<CreditoProducaoInput, "chave_idempotencia">;
type GerarChave = () => string;

function chaveIdempotencia() {
  const uuid = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
  return `producao-ui:${uuid}`;
}

export function criarControladorCreditoProducao(
  gerarChave: GerarChave = chaveIdempotencia,
) {
  let tentativa: { assinatura: string; chave: string } | null = null;
  let requisicaoPendente: Promise<unknown> | null = null;

  return {
    emAndamento() {
      return requisicaoPendente !== null;
    },

    enviar<T>(
      dados: DadosCredito,
      enviarCredito: (payload: CreditoProducaoInput) => Promise<T>,
    ): Promise<T> {
      if (requisicaoPendente) {
        return requisicaoPendente as Promise<T>;
      }

      const assinatura = JSON.stringify(dados);
      if (!tentativa || tentativa.assinatura !== assinatura) {
        tentativa = { assinatura, chave: gerarChave() };
      }

      const requisicao = enviarCredito({
        ...dados,
        chave_idempotencia: tentativa.chave,
      });
      const tentativaPendente = requisicao
        .then((resultado) => {
          tentativa = null;
          return resultado;
        })
        .finally(() => {
          requisicaoPendente = null;
        });
      requisicaoPendente = tentativaPendente;
      return tentativaPendente;
    },
  };
}
