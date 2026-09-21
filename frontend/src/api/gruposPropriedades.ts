import { api } from "./propriedades";
import type { CargaColhidaInput } from "./cargasColhidas";

export type MembroGrupo = {
  propriedade: number;
  propriedade_nome: string;
  cad_pro: string;
  cad_pro_codigo: string;
  disponivel: boolean;
};
export type GrupoPropriedades = {
  id: number;
  nome: string;
  ativo: boolean;
  vinculos: string[];
  membros: MembroGrupo[];
};
export type OpcaoGrupo = Omit<MembroGrupo, "disponivel"> & { id: string };
const caminho = "/talhoes/grupos-colheita/";
export async function listarGruposPropriedades() {
  return (await api.get<GrupoPropriedades[]>(caminho)).data;
}
export async function listarOpcoesGrupo() {
  return (await api.get<OpcaoGrupo[]>(`${caminho}opcoes/`)).data;
}
export async function salvarGrupoPropriedades(
  id: number | null, dados: { nome: string; ativo: boolean; vinculos: string[] },
) {
  return id === null
    ? (await api.post<GrupoPropriedades>(caminho, dados)).data
    : (await api.patch<GrupoPropriedades>(`${caminho}${id}/`, dados)).data;
}

export function aplicarGrupoNaCarga(
  carga: CargaColhidaInput, grupo: GrupoPropriedades,
): CargaColhidaInput {
  if (!grupo.ativo || !grupo.membros.length || grupo.membros.some(m => !m.disponivel)) {
    throw new Error("O grupo possui vínculo indisponível. Revise seu cadastro em Talhões.");
  }
  return {
    ...carga,
    propriedade: String(grupo.membros[0].propriedade),
    cad_pro: grupo.membros[0].cad_pro,
    propriedades_selecionadas: grupo.membros.map(m => m.propriedade),
    cadpros_por_propriedade: Object.fromEntries(grupo.membros.map(m => [String(m.propriedade), m.cad_pro])),
    talhoes_selecionados: [],
  };
}
