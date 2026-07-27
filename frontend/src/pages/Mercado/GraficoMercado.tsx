import type { PontoMercadoEnterprise } from "../../api/mercado";
import { EmptyState } from "../../components/shared/ui";


type Props = {
  pontos: PontoMercadoEnterprise[];
  titulo: string;
};

const formatar = (valor: number) => valor.toLocaleString("pt-BR", { maximumFractionDigits: 4 });

export default function GraficoMercado({ pontos, titulo }: Props) {
  if (pontos.length < 2) {
    return <EmptyState title="Histórico insuficiente" description="A série será exibida após duas ou mais atualizações válidas." />;
  }
  const largura = 900;
  const altura = 280;
  const margem = 32;
  const valores = pontos.map((item) => Number(item.fechamento));
  const minimo = Math.min(...valores);
  const maximo = Math.max(...valores);
  const amplitude = maximo - minimo || 1;
  const coordenadas = pontos.map((item, indice) => {
    const x = margem + (indice / (pontos.length - 1)) * (largura - margem * 2);
    const y = altura - margem - ((Number(item.fechamento) - minimo) / amplitude) * (altura - margem * 2);
    return { x, y, item };
  });
  const linha = coordenadas.map(({ x, y }) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");

  return (
    <figure className="market-chart">
      <svg aria-label={`${titulo}: evolução da cotação`} role="img" viewBox={`0 0 ${largura} ${altura}`}>
        <line x1={margem} y1={margem} x2={margem} y2={altura - margem} className="market-chart__axis" />
        <line x1={margem} y1={altura - margem} x2={largura - margem} y2={altura - margem} className="market-chart__axis" />
        <polyline fill="none" points={linha} className="market-chart__line" />
        {coordenadas.map(({ x, y, item }) => <circle key={item.id} cx={x} cy={y} r="4" className="market-chart__point"><title>{new Date(item.data_hora).toLocaleString("pt-BR")}: {formatar(Number(item.fechamento))}</title></circle>)}
      </svg>
      <figcaption>
        <strong>{titulo}</strong>
        <span>Mínimo {formatar(minimo)} · Máximo {formatar(maximo)} · {pontos.length} ponto(s)</span>
      </figcaption>
    </figure>
  );
}
