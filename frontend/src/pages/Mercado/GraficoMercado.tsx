import { CotacaoMercado } from "../../api/mercado";
import { useState } from "react";


type Props = {
  cotacoes: CotacaoMercado[];
};

export default function GraficoMercado({ cotacoes }: Props) {
  const [selecionado, setSelecionado] = useState<number | null>(null);
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
        role="group"
        viewBox={`0 0 ${largura} ${altura}`}
      >
        <polyline fill="none" points={pontos} stroke="#237447" strokeWidth="4" />
        {cotacoes.map((item, indice) => <circle key={item.id} className="chart-point"
          cx={margem + (indice / (cotacoes.length - 1)) * (largura - margem * 2)}
          cy={altura - margem - ((Number(item.valor) - minimo) / amplitude) * (altura - margem * 2)}
          r="5" tabIndex={0} aria-label={`${item.data}: ${item.valor} ${item.unidade}`}
          onFocus={() => setSelecionado(indice)} onMouseEnter={() => setSelecionado(indice)}
          onClick={() => setSelecionado(indice)}><title>{`${item.data}: ${item.valor} ${item.unidade}`}</title></circle>)}
      </svg>
      <figcaption>
        {cotacoes[0].data} a {cotacoes[cotacoes.length - 1].data} · mínimo {minimo.toFixed(2)} ·
        máximo {maximo.toFixed(2)}
      </figcaption>
      <div className="chart-detail" role="status">{selecionado != null && cotacoes[selecionado]
        ? `${cotacoes[selecionado].data} · ${Number(cotacoes[selecionado].valor).toLocaleString("pt-BR")} ${cotacoes[selecionado].unidade}`
        : "Passe sobre os pontos ou use Tab para consultar as cotações."}</div>
    </figure>
  );
}
