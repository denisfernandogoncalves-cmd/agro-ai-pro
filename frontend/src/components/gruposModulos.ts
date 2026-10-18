import { MODULOS, Modulo } from "../api/usuarios";

export const AREAS_MODULOS: { nome: string; modulos: Modulo[] }[] = [
  { nome: "Cadastros", modulos: ["propriedades", "talhoes", "cadastros-agricolas"] },
  { nome: "Produção", modulos: ["cargas", "producao-saldos", "transferencias"] },
  { nome: "Comercial", modulos: ["vendas", "faturamento-insumos"] },
  { nome: "Financeiro e estoque", modulos: ["financeiro", "estoque", "cavaco"] },
  { nome: "Operações", modulos: ["operacoes", "maquinas", "transportes"] },
  { nome: "Gestão", modulos: ["relatorios", "importacoes", "insights"] },
];

export const nomeModulo = (id: Modulo) => MODULOS.find(([chave]) => chave === id)?.[1] ?? id;
