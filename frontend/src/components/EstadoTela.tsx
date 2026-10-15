import { Icon } from "./ModuloIcon";

export default function EstadoTela({ titulo = "Carregando dados…", detalhe, carregando = false }: { titulo?: string; detalhe?: string; carregando?: boolean }) {
  return <section className={`estado-tela ${carregando ? "estado-carregando" : ""}`} role="status" aria-live="polite" aria-busy={carregando}>
    <div className="estado-tela-titulo"><Icon name={carregando ? "chart" : "leaf"} /><div><strong>{titulo}</strong>{detalhe && <p>{detalhe}</p>}</div></div>
    {carregando && <div className="skeleton-grade" aria-hidden="true">{[0, 1, 2, 3].map(i => <span key={i} className="skeleton-card"><span /><span /></span>)}</div>}
  </section>;
}
