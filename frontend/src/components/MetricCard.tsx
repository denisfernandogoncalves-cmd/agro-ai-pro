export default function MetricCard({ titulo, valor, detalhe }: { titulo: string; valor: string; detalhe: string }) {
  return <article className="card executivo-metrica tw:min-w-0"><span>{titulo}</span><strong>{valor}</strong><small>{detalhe}</small></article>;
}
