import { PosicaoSaldo } from "../../api/producaoSaldos";
import { Propriedade } from "../../api/propriedades";
import { CADPro } from "../../api/cargasColhidas";

export function chaveOrigemVenda(posicao: PosicaoSaldo) {
  return `${posicao.cad_pro}:${posicao.propriedade_id ?? "historico"}`;
}

export function opcoesOrigemVenda(
  posicoes: PosicaoSaldo[],
  propriedades: Pick<Propriedade, "id" | "nome" | "proprietario">[],
  cadpros: CADPro[] = [],
) {
  const cadastros = new Map(propriedades.map(p => [p.id, p]));
  const opcoes = new Map<string, { chave: string; rotulo: string; propriedade: number | null; cad_pro: string }>();
  for (const posicao of posicoes) {
    const cadastro = posicao.propriedade_id === null ? undefined : cadastros.get(posicao.propriedade_id);
    const propriedade = cadastro?.nome || posicao.propriedade_nome
      || (posicao.propriedade_id === null ? "Produção histórica sem propriedade" : `Propriedade #${posicao.propriedade_id}`);
    const proprietario = cadastro?.proprietario.trim() || "Proprietário não informado";
    const chave = chaveOrigemVenda(posicao);
    opcoes.set(chave, { chave, propriedade: posicao.propriedade_id, cad_pro: posicao.cad_pro, rotulo: `${propriedade} / CAD/PRO ${posicao.cad_pro_codigo} / ${proprietario}` });
  }
  for (const cad of cadpros.filter(c => c.ativo)) for (const id of cad.propriedades) {
    const propriedade = cadastros.get(id);
    if (!propriedade) continue;
    const chave = `${cad.id}:${id}`;
    opcoes.set(chave, { chave, propriedade: id, cad_pro: cad.id, rotulo: `${propriedade.nome} / CAD/PRO ${cad.codigo} / ${propriedade.proprietario.trim() || "Proprietário não informado"}` });
  }
  return [...opcoes.values()].sort((a, b) => a.rotulo.localeCompare(b.rotulo, "pt-BR"));
}

export function posicoesDaOrigemVenda(posicoes: PosicaoSaldo[], chave: string, cultura?: string) {
  return posicoes.filter(p => chaveOrigemVenda(p) === chave && (cultura === undefined || p.cultura === cultura));
}
