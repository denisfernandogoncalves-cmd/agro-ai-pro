import type { PosicaoSaldo } from "../api/producaoSaldos";

const kg = (v: string) => `${Number(v).toLocaleString("pt-BR", { maximumFractionDigits: 3 })} kg`;
export function proporcoesSaldo(fisico: string, comprometido: string, disponivel: string) {
  if (![fisico, comprometido, disponivel].every(v => typeof v === "string" && v.trim())) return null;
  const [f, c, d] = [fisico, comprometido, disponivel].map(Number);
  if (![f, c, d].every(Number.isFinite) || f <= 0 || c < 0 || d < 0 || Math.abs(f - c - d) > .0005) return null;
  return { comprometido: c / f * 100, disponivel: d / f * 100 };
}
export default function ComposicaoSaldo({ posicoes }: { posicoes: PosicaoSaldo[] }) {
  return <section className="card composicao-saldos nao-imprimir"><div><span className="kicker">Posições oficiais da consulta</span><h2>Composição do saldo</h2><p>Físico, comprometido e disponível por propriedade, cultura, safra e CAD/PRO. Valores do livro existente.</p></div>
    {!posicoes.length ? <p className="vazio">Nenhuma posição corresponde aos filtros aplicados.</p> : <div className="composicao-lista">{posicoes.map(p => {
      const proporcao = proporcoesSaldo(p.saldo_fisico_kg, p.saldo_comprometido_kg, p.saldo_disponivel_kg);
      return <article key={p.id}><div className="composicao-identidade"><strong>{p.propriedade_nome || "Origem histórica sem propriedade"}</strong><small>{p.cultura} · {p.safra} · CAD/PRO {p.cad_pro_codigo} · {p.classificacao_codigo} · {p.armazem_nome}</small></div>
        <dl className="composicao-valores"><div><dt>Físico</dt><dd>{kg(p.saldo_fisico_kg)}</dd></div><div><dt>Comprometido</dt><dd>{kg(p.saldo_comprometido_kg)}</dd></div><div><dt>Disponível</dt><dd>{kg(p.saldo_disponivel_kg)}</dd></div></dl>
        {proporcao ? <div className="composicao-barra" role="img" aria-label={`Do saldo físico, ${proporcao.comprometido.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}% comprometido e ${proporcao.disponivel.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}% disponível`}><span className="saldo-comprometido" style={{ width: `${proporcao.comprometido}%` }} /><span className="saldo-disponivel" style={{ width: `${proporcao.disponivel}%` }} /></div> : <small className="composicao-nota">{Number(p.saldo_fisico_kg) === 0 ? "Sem saldo físico para compor o gráfico." : "Composição não representável em proporções positivas. Confira os valores e o histórico da posição."}</small>}
      </article>;
    })}</div>}
    <div className="composicao-legenda"><span><i className="saldo-comprometido" />Comprometido</span><span><i className="saldo-disponivel" />Disponível</span></div>
  </section>;
}
