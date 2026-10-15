import { api } from "./propriedades";

export type Caminhao = { versao_correcao?: string; id: number; placa: string; veiculo: string; motorista: string; ativo: boolean };
export type Lancamento = { versao_correcao?: string; id: number; caminhao: number; placa: string; motorista: string; data: string; tipo: "receita" | "despesa"; descricao: string; local: string; nota: string; unidade: string; quantidade: string; valor_unitario: string; total: string; origem: string };
export type Remuneracao = { versao_correcao?: string; comissao_manual?: string; id: number; caminhao: number; placa: string; motorista: string; competencia: string; salario: string; comissao: string; comissao_percentual: string | null; base_comissao: string; comissao_fretes?: string; comissao_transportes?: string; observacoes: string };
export type Grupo = { nome: string; receita: string; despesas_operacionais: string; salario: string; comissao: string; despesas: string; saldo: string; margem: string | null; quantidade_lancamentos: number; remuneracao_cadastrada?: boolean; despesas_registradas?: boolean };
export type Relatorio = { resumo: Grupo; por_placa: Grupo[]; por_motorista: Grupo[]; por_mes: Grupo[]; categorias: { nome: string; total: string }[]; criterio_remuneracao: string; ranking_financeiro: Grupo[]; ranking_eficiencia: Grupo[]; ranking_operacional: { nome: string; documentos: number; toneladas: string; toneladas_por_documento: string }[]; criterio_ranking: string; documentos_sem_motorista: number };
export type Filtros = { data_inicio: string; data_fim: string; caminhao: string; motorista: string };
export type Pagina<T> = { count: number; results: T[] };
export type Previa = { veiculos: Omit<Caminhao, "id" | "ativo">[]; quantidade: number; duplicados: number; receitas: string; despesas_operacionais: string; remuneracoes: Omit<Remuneracao, "id" | "caminhao">[]; amostra: (Omit<Lancamento, "id" | "caminhao" | "total">)[]; aviso: string };
const base = "/transportes/";
export const listarCaminhoes = async () => (await api.get<Caminhao[]>(base + "caminhoes/")).data;
export const excluirCaminhao = async (id: number) => api.delete(base + `caminhoes/${id}/`);
export const excluirLancamentoTransporte = async (id: number) => api.delete(base + `lancamentos/${id}/`);
export const excluirRemuneracao = async (id: number) => api.delete(base + `remuneracoes/${id}/`);
export const desvincularMotorista = async (id: number, motorista: string) => (await api.delete<Caminhao>(base + `caminhoes/${id}/motorista/`, { data: { motorista_original: motorista } })).data;
export const salvarCaminhao = async (id: number | null, dados: Omit<Caminhao, "id"> & { versao_correcao_original?: string }) => (await (id ? api.patch<Caminhao>(base + `caminhoes/${id}/`, dados) : api.post<Caminhao>(base + "caminhoes/", dados))).data;
export const listarLancamentos = async (filtros: Filtros, page: number, signal?: AbortSignal) => (await api.get<Pagina<Lancamento>>(base + "lancamentos/", { params: { ...filtros, page }, signal })).data;
export const consultarRelatorio = async (filtros: Filtros, signal?: AbortSignal) => (await api.get<Relatorio>(base + "lancamentos/relatorio/", { params: filtros, signal })).data;
export const salvarLancamento = async (id: number | null, dados: Omit<Lancamento, "id" | "placa" | "total" | "origem"> & { versao_correcao_original?: string }) => (await (id ? api.patch(base + `lancamentos/${id}/`, dados) : api.post(base + "lancamentos/", dados))).data;
export const listarRemuneracoes = async (page: number, signal?: AbortSignal, motorista = "", caminhao = "") => (await api.get<Pagina<Remuneracao>>(base + "remuneracoes/", { params: { page, motorista, caminhao }, signal })).data;
export const salvarRemuneracao = async (id: number | null, dados: Omit<Remuneracao, "id" | "placa" | "comissao" | "base_comissao"> & { versao_correcao_original?: string }) => (await (id ? api.patch(base + `remuneracoes/${id}/`, dados) : api.post(base + "remuneracoes/", dados))).data;
function formulario(arquivo: File) { const dados = new FormData(); dados.append("arquivo", arquivo); return dados; }
export const previaPlanilha = async (arquivo: File) => (await api.post<Previa>(base + "lancamentos/previa/", formulario(arquivo))).data;
export const importarPlanilha = async (arquivo: File) => (await api.post<{ lancamentos_criados: number; remuneracoes_criadas: number; duplicados: number }>(base + "lancamentos/importar/", formulario(arquivo))).data;
export async function exportarRelatorio(filtros: Filtros) {
  const resposta = await api.get(base + "lancamentos/exportar/", { params: filtros, responseType: "blob" });
  const url = URL.createObjectURL(resposta.data); const link = document.createElement("a");
  link.href = url; link.download = "transportes.csv"; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const calcularComissao = async (dados: { caminhao: number; motorista: string; competencia: string; comissao_percentual: string; id: number | null }, signal?: AbortSignal) => (await api.get<{ base_comissao: string; comissao: string }>(base + "remuneracoes/calculo/", { params: dados, signal })).data;

export type DemonstrativoMotorista = { motorista: string; competencia: string; salario: string; comissao: string; total: string; comissao_fretes?: string; itens: Remuneracao[] };
export const consultarDemonstrativos = async (mes: string, signal?: AbortSignal) => (await api.get<DemonstrativoMotorista[]>(base + "remuneracoes/imprimir/", { params: { mes }, signal })).data;

export type FreteConferido = { versao_correcao?:string; id: number; carga: number | null; entrega: number | null; remuneracao: number; frete: string; comissao: string; ja_contabilizado: boolean; observacoes: string; atualizado_em: string };
export type ViagemFrete = { origem: "carga" | "venda"; id: number; data: string; placa: string; motorista: string; peso_kg: string; conferencia: FreteConferido | null };
export type CruzamentoFretes = { mes: string; remuneracoes: Remuneracao[]; viagens: ViagemFrete[] };
export const consultarFretes = async (mes: string, placa: string, signal?: AbortSignal) => (await api.get<CruzamentoFretes>(base + "fretes/cruzamento/", { params: { mes, placa }, signal })).data;
export const salvarFreteConferido = async (id: number | null, dados: Omit<FreteConferido, "id" | "atualizado_em"> & { atualizado_em_original?: string }) => (await (id ? api.patch<FreteConferido>(base + `fretes/${id}/`, dados) : api.post<FreteConferido>(base + "fretes/", dados))).data;
