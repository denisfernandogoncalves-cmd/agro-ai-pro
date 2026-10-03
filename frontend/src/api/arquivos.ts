import { api } from "./propriedades";

export function salvarArquivo(blob: Blob, nome: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url; link.download = nome; link.click();
  // Manter o URL até o navegador iniciar o download.
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}
export async function baixarArquivo(endpoint: string, nome: string, params?: Record<string, unknown>) {
  const resposta = await api.get<Blob>(endpoint, {responseType:"blob", params});
  salvarArquivo(resposta.data, nome);
}
export async function erroArquivo(erro: unknown, padrao: string) {
  const dados = (erro as {response?:{data?:unknown}}).response?.data;
  if (dados instanceof Blob) {
    try { const valor = JSON.parse(await dados.text()); return typeof valor.detail === "string" ? valor.detail : Array.isArray(valor) ? valor.join(" ") : padrao; } catch { return padrao; }
  }
  return typeof (dados as {detail?:unknown})?.detail === "string" ? (dados as {detail:string}).detail : padrao;
}
