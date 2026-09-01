import {
  listarFornecedores,
  ParceiroFinanceiro,
} from "./financeiro";
import {
  listarLocaisEstoque,
  listarProdutosEstoque,
  LocalEstoque,
  ProdutoEstoque,
} from "./estoque";
import axios from "axios";
import { api } from "./propriedades";


export type ArmazemGraos = {
  id: number;
  propriedade: number | null;
  propriedade_nome: string | null;
  nome: string;
  capacidade_kg: string;
  ocupacao_kg: string;
  ativo: boolean;
};

export type ArmazemGraosInput = {
  nome: string;
  capacidade_kg: string;
};

export type CadastrosAgricolas = {
  armazens: ArmazemGraos[];
  locais: LocalEstoque[];
  produtos: ProdutoEstoque[];
  fornecedores: ParceiroFinanceiro[];
  falhas: string[];
};

export async function listarArmazensGraos() {
  return (
    await api.get<ArmazemGraos[]>("/graos/armazens/", {
      params: { ordering: "nome" },
    })
  ).data;
}

export async function carregarCadastrosAgricolas(): Promise<CadastrosAgricolas> {
  const resultados = await Promise.allSettled([
    listarArmazensGraos(),
    listarLocaisEstoque(),
    listarProdutosEstoque(),
    listarFornecedores(),
  ]);
  const falhas: string[] = [];
  function valor<T>(indice: number, nome: string): T[] {
    const resultado = resultados[indice] as PromiseSettledResult<T[]>;
    if (resultado.status === "fulfilled") return resultado.value;
    falhas.push(nome);
    return [];
  }
  return {
    armazens: valor<ArmazemGraos>(0, "armazenagens de grãos"),
    locais: valor<LocalEstoque>(1, "depósitos"),
    produtos: valor<ProdutoEstoque>(2, "produtos"),
    fornecedores: valor<ParceiroFinanceiro>(3, "fornecedores"),
    falhas,
  };
}

export async function criarArmazemGraos(dados: ArmazemGraosInput) {
  return (
    await api.post<ArmazemGraos>("/graos/armazens/", {
      ...dados,
      ativo: true,
    })
  ).data;
}

export async function atualizarArmazemGraos(id: number, dados: ArmazemGraosInput) {
  return (await api.patch<ArmazemGraos>(`/graos/armazens/${id}/`, dados)).data;
}

export async function excluirArmazemGraos(id: number) {
  try {
    await api.delete(`/graos/armazens/${id}/`);
  } catch (falha) {
    if (!axios.isAxiosError(falha) || falha.response?.status !== 409) throw falha;
    await api.patch(`/graos/armazens/${id}/`, { ativo: false });
  }
}
