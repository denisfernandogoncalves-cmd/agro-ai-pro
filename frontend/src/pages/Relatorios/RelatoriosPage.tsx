import { FormEvent, useEffect, useState } from "react";

import { Dashboard, obterDashboard } from "../../api/relatorios";
import { Propriedade } from "../../api/propriedades";


const moeda = (valor: string) => Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export default function RelatoriosPage({ propriedades }: { propriedades: Propriedade[] }) {
  const [dados, setDados] = useState<Dashboard | null>(null);
  const [filtros, setFiltros] = useState({ propriedade: "", safra: "" });
  const [erro, setErro] = useState("");

  async function carregar() {
    try { setDados(await obterDashboard(filtros.propriedade, filtros.safra)); setErro(""); }
    catch { setErro("Não foi possível gerar o relatório gerencial."); }
  }
  useEffect(() => { void carregar(); }, []);

  if (!dados) return <section className="card">{erro || "Gerando indicadores..."}</section>;
  const maior = Math.max(1, ...dados.fluxo_mensal.flatMap((item) => [Number(item.entradas), Number(item.saidas)]));

  return (
    <section className="modulo-relatorios">
      {erro && <p className="erro card">{erro}</p>}
      <form className="card filtros-relatorio" onSubmit={(e: FormEvent) => { e.preventDefault(); void carregar(); }}>
        <label>Propriedade<select value={filtros.propriedade} onChange={(e) => setFiltros({ ...filtros, propriedade: e.target.value })}><option value="">Todas</option>{propriedades.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
        <label>Safra<input placeholder="2026/2027" value={filtros.safra} onChange={(e) => setFiltros({ ...filtros, safra: e.target.value })} /></label>
        <button type="submit">Atualizar relatório</button>
      </form>
      <section className="resumos-estoque">
        <article className="card"><span>Saldo realizado</span><strong>{moeda(dados.financeiro.saldo_realizado)}</strong></article>
        <article className="card"><span>Saldo previsto</span><strong>{moeda(dados.financeiro.saldo_previsto)}</strong></article>
        <article className="card"><span>Custo operacional</span><strong>{moeda(dados.operacoes.custo_realizado)}</strong></article>
        <article className="card"><span>Área em talhões</span><strong>{dados.estrutura.area_talhoes} ha</strong></article>
        <article className="card"><span>Operações concluídas</span><strong>{dados.operacoes.concluidas}</strong></article>
        <article className="card"><span>Máquinas ativas</span><strong>{dados.maquinas.ativas}</strong></article>
      </section>
      <section className="grade relatorios-grade">
        <article className="card"><h2>Alertas gerenciais</h2><p>Financeiro atrasado: <strong>{moeda(dados.financeiro.valor_atrasado)}</strong></p><p>Lotes vencidos: <strong>{dados.estoque.lotes_vencidos}</strong></p><p>Estoque abaixo do mínimo: <strong>{dados.estoque.itens_abaixo_minimo}</strong></p><p>Manutenções pendentes: <strong>{dados.maquinas.manutencoes_pendentes}</strong></p><p>Operações em execução: <strong>{dados.operacoes.em_execucao}</strong></p></article>
        <article className="card"><h2>Fluxo mensal</h2><div className="grafico-barras">{dados.fluxo_mensal.length === 0 ? <p>Sem movimentos liquidados.</p> : dados.fluxo_mensal.map((item) => <div className="grupo-barras" key={item.mes}><span>{item.mes}</span><div title={`Entradas ${moeda(item.entradas)}`} className="barra entrada" style={{ height: `${Math.max(3, Number(item.entradas) / maior * 120)}px` }} /><div title={`Saídas ${moeda(item.saidas)}`} className="barra saida" style={{ height: `${Math.max(3, Number(item.saidas) / maior * 120)}px` }} /></div>)}</div><small>Verde: entradas · vermelho: saídas</small></article>
      </section>
      <p className="kicker">Gerado em {new Date(dados.gerado_em).toLocaleString("pt-BR")}</p>
    </section>
  );
}
