import MetricCard from "../../components/MetricCard";

type Resumo = Record<string, string | number>;
export function indicadorExecutivo(resumo: Resumo, campo: string, moeda = false) {
  const valor = resumo[campo];
  if (valor === undefined || valor === null || String(valor).trim() === "" || !Number.isFinite(Number(valor))) return "Indisponível";
  return Number(valor).toLocaleString("pt-BR", moeda ? { style: "currency", currency: "BRL" } : { maximumFractionDigits: 3 }) + (moeda ? "" : " kg");
}
export default function ResumoExecutivo({ resumo }: { resumo: Resumo }) {
  const valores = [
    ["Produção líquida", "producao_kg", false, "Produção registrada na seleção"],
    ["Estoque físico próprio", "saldo_fisico_kg", false, "Posições de CAD/PRO autorizadas"],
    ["Estoque disponível", "saldo_disponivel_kg", false, "Saldo após os compromissos"],
    ["Vendas registradas", "vendas_kg", false, "Quantidade dos contratos na seleção"],
    ["Contas a pagar", "a_pagar", true, "Compromissos financeiros pendentes"],
    ["Contas a receber", "a_receber", true, "Recebimentos financeiros pendentes"],
    ["Entradas realizadas", "entradas_realizadas", true, "Valores liquidados das contas a receber"],
    ["Saídas realizadas", "saidas_realizadas", true, "Valores liquidados das contas a pagar"],
    ["Saldo realizado", "saldo_realizado", true, "Entradas menos saídas registradas; não é lucro"],
    ["Saldo previsto pendente", "saldo_previsto", true, "Receber menos pagar pendentes"],
  ] as const;
  const comparativo = valores.filter(([,campo,moeda]) => !moeda && resumo[campo] !== undefined && String(resumo[campo]).trim() !== "" && Number.isFinite(Number(resumo[campo])) && Number(resumo[campo]) >= 0);
  const maximo = Math.max(1, ...comparativo.map(([,campo]) => Number(resumo[campo])));
  return <section className="resumo-executivo tw:grid tw:gap-5" aria-label="Resumo Executivo">
    <div className="executivo-grade">{valores.map(([titulo,campo,moeda,detalhe]) => <MetricCard key={campo} titulo={titulo} valor={indicadorExecutivo(resumo,campo,moeda)} detalhe={detalhe} />)}</div>
    <article className="card"><h2>Panorama produtivo e comercial</h2><p className="executivo-nota">Volumes em kg da consulta atual. Vendas e estoque são indicadores distintos; este comparativo não calcula disponibilidade nem altera os saldos.</p><div className="executivo-grafico">{comparativo.map(([titulo,campo]) => <div key={campo}><span>{titulo} · <b>{indicadorExecutivo(resumo,campo)}</b></span><meter min={0} max={maximo} value={Number(resumo[campo])} aria-label={titulo} /></div>)}</div>{!comparativo.length && <p className="vazio">Nenhum indicador de volume disponível para seus acessos.</p>}</article>
    <article className="card"><h2>Base financeira e informações ausentes</h2><p className="executivo-nota">Valores do módulo Financeiro na propriedade e safra aplicadas. Vendas, compras e vínculos contratuais não são somados novamente. Cancelados são excluídos. Contas a receber representam compromissos, não faturamento. Saldo realizado não representa rentabilidade.</p>{Number(resumo.liquidacoes_sem_valor)>0&&<p role="status">{resumo.liquidacoes_sem_valor} liquidação(ões) sem valor efetivo: totais realizados incompletos.</p>}<p className="executivo-nota">Faturamento consolidado, margem e custo por hectare exigem classificação e vínculos suficientes de receitas, custos e área produtiva. Não são estimados pelo saldo de caixa.</p></article>
  </section>;
}
