import type { PontoMercadoEnterprise } from "../../api/mercado";
import { EmptyState } from "../../components/shared/ui";


type CotacaoLegada = {
  id: number;
  data: string;
  valor: string | number;
  produto_nome?: string;
};

type Props = {
  pontos?: PontoMercadoEnterprise[];
  titulo?: string;
  cotacoes?: CotacaoLegada[];
};

const formatar = (valor: number) => valor.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 4 });

export default function GraficoMercado({ pontos = [], titulo = "Evolução histórica", cotacoes = [] }: Props) {
  const serie: PontoMercadoEnterprise[] = pontos.length ? pontos : cotacoes.map((item) => ({
    id: item.id,
    ativo: "soja_cbot",
    intervalo: "diario",
    data_hora: `${item.data}T12:00:00Z`,
    abertura: null,
    maxima: null,
    minima: null,
    fechamento: String(item.valor),
    volume: null,
    unidade: "",
    moeda: "",
    fonte: "legado",
    criado_em: `${item.data}T12:00:00Z`,
  }));
  const tituloExibido = pontos.length ? titulo : cotacoes[0]?.produto_nome || titulo;
  if (serie.length < 2) {
    return <EmptyState title="Histórico insuficiente" description="A série será exibida após duas ou mais atualizações válidas." />;
  }
  const largura = 900;
  const altura = 280;
  const margem = 32;
  const valores = serie.map((item) => Number(item.fechamento));
  const minimo = Math.min(...valores);
  const maximo = Math.max(...valores);
  const amplitude = maximo - minimo || 1;
  const coordenadas = serie.map((item, indice) => {
    const x = margem + (indice / (serie.length - 1)) * (largura - margem * 2);
    const y = altura - margem - ((Number(item.fechamento) - minimo) / amplitude) * (altura - margem * 2);
    return { x, y, item };
  });
  const linha = coordenadas.map(({ x, y }) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");

  return (
    <figure className="market-chart">
      <svg aria-label={`${tituloExibido}: evolução da cotação`} role="img" viewBox={`0 0 ${largura} ${altura}`}>
        <line x1={margem} y1={margem} x2={margem} y2={altura - margem} className="market-chart__axis" />
        <line x1={margem} y1={altura - margem} x2={largura - margem} y2={altura - margem} className="market-chart__axis" />
        <polyline fill="none" points={linha} className="market-chart__line" />
        {coordenadas.map(({ x, y, item }) => <circle key={item.id} cx={x} cy={y} r="4" className="market-chart__point"><title>{new Date(item.data_hora).toLocaleString("pt-BR")}: {formatar(Number(item.fechamento))}</title></circle>)}
      </svg>
      <figcaption>
        <strong>{cotacoes.length ? "Evolução histórica" : tituloExibido}</strong>
        <span>Mínimo {formatar(minimo)} · Máximo {formatar(maximo)} · {serie.length} ponto(s)</span>
      </figcaption>
    </figure>
  );
}
