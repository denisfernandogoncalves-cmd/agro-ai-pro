import { CotacaoMercado } from "../../api/mercado";


type Props = {
  cotacoes: CotacaoMercado[];
};

export default function GraficoMercado({ cotacoes }: Props) {
  if (cotacoes.length < 2) {
    return <div className="vazio">Histórico insuficiente para o gráfico.</div>;
  }
  const largura = 720;
  const altura = 240;
  const margem = 24;
  const valores = cotacoes.map((item) => Number(item.valor));
  const minimo = Math.min(...valores);
  const maximo = Math.max(...valores);
  const amplitude = maximo - minimo || 1;
  const pontos = cotacoes
    .map((item, indice) => {
      const x =
        margem + (indice / (cotacoes.length - 1)) * (largura - margem * 2);
      const y =
        altura -
        margem -
        ((Number(item.valor) - minimo) / amplitude) * (altura - margem * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <figure className="card grafico-mercado">
      <svg
        aria-label="Evolução histórica da cotação"
        role="img"
        viewBox={`0 0 ${largura} ${altura}`}
      >
        <polyline fill="none" points={pontos} stroke="#237447" strokeWidth="4" />
      </svg>
      <figcaption>
        {cotacoes[0].data} a {cotacoes[cotacoes.length - 1].data} · mínimo {minimo.toFixed(2)} ·
        máximo {maximo.toFixed(2)}
      </figcaption>
    </figure>
  );
}
