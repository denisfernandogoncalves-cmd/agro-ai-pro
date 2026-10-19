import { MODULOS, Modulo } from "../api/usuarios";

export const AREAS_MODULOS: { nome: string; modulos: Modulo[] }[] = [
  { nome: "Cadastros", modulos: ["propriedades", "talhoes", "cadastros-agricolas"] },
  { nome: "Produção", modulos: ["cargas", "producao-saldos", "transferencias"] },
  { nome: "Comercial", modulos: ["vendas", "faturamento-insumos"] },
  { nome: "Financeiro e estoque", modulos: ["financeiro", "estoque", "cavaco"] },
  { nome: "Operações", modulos: ["operacoes", "maquinas", "transportes"] },
  { nome: "Gestão", modulos: ["relatorios", "importacoes", "insights"] },
];

export const AREAS_NAVEGACAO = AREAS_MODULOS.map(area => area.nome === "Cadastros" ? { ...area, modulos: [...area.modulos, "grupos-colheita" as const] } : area);
export const nomeModulo = (id: Modulo) => id === "grupos-colheita" ? "Grupos de colheita" : MODULOS.find(([chave]) => chave === id)?.[1] ?? id;
