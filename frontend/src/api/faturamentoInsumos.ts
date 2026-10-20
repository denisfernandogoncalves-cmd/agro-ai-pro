import { api } from "./propriedades";

export type ItemFaturamento = { propriedade: number; cad_pro: string; bep?: string; area_alqueires: string; quantidade_embalagens: string };
export type EntradaFaturamento = {
  id: string; fornecedor: string; produto: string; data_envio: string; safra?: string;
  embalagem: string; conteudo_embalagem: string; dosagem_alqueire: string;
  observacoes: string; itens: ItemFaturamento[];
};
export type ResumoFaturamento = {
  usa_bep?: boolean; safra?: string;
  fornecedor_nome: string; produto_nome: string; unidade: string; data_envio: string;
  embalagem: string; conteudo_embalagem: string; dosagem_alqueire: string; observacoes: string;
  total_embalagens: string; quantidade_total: string; saldo_anterior: string; saldo_posterior: string;
  itens: (ItemFaturamento & { cad_pro_identificacao?: string; formato_coordenadas?: "decimal" | "gms"; latitude?: string | null; longitude?: string | null; latitude_gms?: string; longitude_gms?: string; propriedade_nome: string; produtor: string; quantidade: string; quantidade_sugerida: string })[];
};
export type Faturamento = { id: string; fornecedor: number; produto: number; data_envio: string; criado_em: string; responsavel: string; resumo: ResumoFaturamento };
export const previaFaturamento = async (dados: EntradaFaturamento) => (await api.post<ResumoFaturamento>("/estoque/faturamentos/previa/", dados)).data;
export const confirmarFaturamento = async (dados: EntradaFaturamento) => (await api.post<Faturamento>("/estoque/faturamentos/confirmar/", dados)).data;
export const listarFaturamentos = async () => (await api.get<Faturamento[]>("/estoque/faturamentos/")).data;
export const excluirFaturamento = async (id: string) => { await api.delete(`/estoque/faturamentos/${id}/`); };
export const obterPdfFaturamento = async (id: string) => (await api.get<Blob>(`/estoque/faturamentos/${id}/pdf/`, { responseType: "blob" })).data;
export const obterExcelFaturamento = async (id: string) => (await api.get<Blob>(`/estoque/faturamentos/${id}/excel/`, { responseType: "blob" })).data;

export const empresaUsaBep = (nome: string) => /^c[\s.\-]*vale(?:\b|$)/i.test(nome.trim());

export function tituloFaturamento(resumo: ResumoFaturamento) {
  const quantidade = (valor: string) => Number(valor).toLocaleString("pt-BR", { useGrouping: false, maximumFractionDigits: 3 });
  return [resumo.produto_nome, `${quantidade(resumo.total_embalagens)} ${resumo.embalagem} DE ${quantidade(resumo.conteudo_embalagem)} ${resumo.unidade}`,
    `SAFRA ${resumo.safra?.trim() || "NÃO INFORMADA"}`, resumo.data_envio.split("-").reverse().join("-")]
    .join(" - ").toLocaleUpperCase("pt-BR").replace(/[<>:"/\\|?*\u0000-\u001f]/g, "-");
}

export function descricaoEmbalagens(resumo: ResumoFaturamento) {
  const nomes: Record<string, [string, string]> = {
    balde: ["BALDE", "BALDES"], baldes: ["BALDE", "BALDES"],
    "galão": ["GALÃO", "GALÕES"], "galões": ["GALÃO", "GALÕES"],
    saco: ["SACO", "SACOS"], sacos: ["SACO", "SACOS"],
    caixa: ["CAIXA", "CAIXAS"], caixas: ["CAIXA", "CAIXAS"],
    frasco: ["FRASCO", "FRASCOS"], frascos: ["FRASCO", "FRASCOS"],
    pacote: ["PACOTE", "PACOTES"], pacotes: ["PACOTE", "PACOTES"],
    tambor: ["TAMBOR", "TAMBORES"], tambores: ["TAMBOR", "TAMBORES"],
  };
  const unidades: Record<string, [string, string]> = {l:["LITRO", "LITROS"], ml:["MILILITRO", "MILILITROS"], kg:["QUILOGRAMA", "QUILOGRAMAS"], g:["GRAMA", "GRAMAS"], t:["TONELADA", "TONELADAS"], un:["UNIDADE", "UNIDADES"]};
  const embalagem = resumo.embalagem.trim();
  const unidade = resumo.unidade.trim();
  const nome = nomes[embalagem.toLocaleLowerCase("pt-BR")]?.[Number(resumo.total_embalagens) === 1 ? 0 : 1] ?? embalagem.toLocaleUpperCase("pt-BR");
  const medida = unidades[unidade.toLowerCase()]?.[Number(resumo.conteudo_embalagem) === 1 ? 0 : 1] ?? unidade.toLocaleUpperCase("pt-BR");
  const numero = (valor: string) => Number(valor).toLocaleString("pt-BR", {maximumFractionDigits:3});
  return `${numero(resumo.total_embalagens)} ${nome} DE ${numero(resumo.conteudo_embalagem)} ${medida}`;
}
