import { api } from "./propriedades";

export type Insight = {
  codigo: string;
  nivel: "critico" | "atencao" | "informativo";
  titulo: string;
  evidencia: string;
  recomendacao: string;
  modulo: string;
};

export async function obterInsights(propriedade = "") {
  return (await api.get<{ gerado_em: string; metodo: string; insights: Insight[]; aviso: string }>(
    "/ai/insights/",
    { params: { propriedade: propriedade || undefined } },
  )).data;
}
