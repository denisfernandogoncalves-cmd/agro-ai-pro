import { api } from "./propriedades";
import type { CargaColhidaInput } from "./cargasColhidas";

export type MembroGrupo = {
  propriedade: number;
  propriedade_nome: string;
  cad_pro: string;
  cad_pro_codigo: string;
  disponivel: boolean;
  area_hectares?: string;
};
export type GrupoPropriedades = {
  id: number;
  nome: string;
  cultura: string;
  safra: string;
  ativo: boolean;
  vinculos: string[];
  membros: MembroGrupo[];
  excluido_em?: string | null;
  historico_area?: MembroGrupo[];
};
export type OpcaoGrupo = Omit<MembroGrupo, "disponivel"> & { id: string };
const caminho = "/talhoes/grupos-colheita/";
export async function listarGruposPropriedades(incluirExcluidos = false) {
  return (await api.get<GrupoPropriedades[]>(caminho, { params: incluirExcluidos ? { incluir_excluidos: true } : undefined })).data;
}
export async function excluirGrupoPropriedades(id: number) {
  await api.delete(`${caminho}${id}/`);
}
export async function listarOpcoesGrupo() {
  return (await api.get<OpcaoGrupo[]>(`${caminho}opcoes/`)).data;
}
export async function salvarGrupoPropriedades(
  id: number | null, dados: { nome: string; cultura: string; safra: string; ativo: boolean; vinculos: string[] },
) {
  return id === null
    ? (await api.post<GrupoPropriedades>(caminho, dados)).data
    : (await api.patch<GrupoPropriedades>(`${caminho}${id}/`, dados)).data;
}

export function aplicarGrupoNaCarga(
  carga: CargaColhidaInput, grupo: GrupoPropriedades,
): CargaColhidaInput {
  if (grupo.excluido_em || !grupo.ativo || !grupo.membros.length || grupo.membros.some(m => !m.disponivel)) {
    throw new Error("O grupo está excluído, inativo ou possui vínculo indisponível. Revise em Grupos de colheita.");
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
