import { formatarData } from "../../utils/datas";
import { CotacaoMercado } from "../../api/mercado";


export function seriesMercado(cotacoes: CotacaoMercado[]) {
  const grupos = new Map<string, CotacaoMercado[]>();
  for (const item of cotacoes) {
    if (!Number.isFinite(Number(item.valor))) continue;
    const chave = `${item.produto}|${item.unidade}|${item.fonte}`;
    grupos.set(chave, [...(grupos.get(chave) ?? []), item]);
  }
  return [...grupos.values()].map(serie => serie.sort((a,b) => a.data.localeCompare(b.data) || a.id-b.id));
}
type Props = {
  cotacoes: CotacaoMercado[];
};

export default function GraficoMercado({ cotacoes }: Props) {
  const series = seriesMercado(cotacoes);
  if (series.length > 1) return <div className="graficos-series">{series.map(serie => <GraficoMercado key={`${serie[0].produto}|${serie[0].unidade}|${serie[0].fonte}`} cotacoes={serie}/>)}</div>;
  cotacoes = series[0] ?? [];
  if (cotacoes.length < 2) {
    return <div className="vazio">Histórico insuficiente para o gráfico.</div>;
  }
  const largura = 720;
  const altura = 240;
  const margem = 60;
  const valores = cotacoes.map((item) => Number(item.valor));
  const minimo = Math.min(...valores);
  const maximo = Math.max(...valores);
  const amplitude = maximo - minimo || 1;
  const inicio = Date.parse(cotacoes[0].data), fim = Date.parse(cotacoes[cotacoes.length-1].data);
  const posicaoX = (item: CotacaoMercado) => margem + (fim === inicio ? .5 : (Date.parse(item.data)-inicio)/(fim-inicio))*(largura-margem*2);
  const formato = (valor: number) => valor.toLocaleString("pt-BR", {minimumFractionDigits:2,maximumFractionDigits:2});
  const diferenca = Number(cotacoes[cotacoes.length-1].valor)-Number(cotacoes[0].valor);
  const pontos = cotacoes
    .map((item) => {
      const x = posicaoX(item);
      const y =
        altura -
        margem -
        ((Number(item.valor) - minimo) / amplitude) * (altura - margem * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <figure className="card grafico-mercado">
      <div className="grafico-legenda"><strong>{cotacoes[0].produto_nome} · {cotacoes[0].unidade}</strong> · {cotacoes[0].fonte}</div>
      <svg
        aria-label="Evolução histórica da cotação"
        role="img"
        viewBox={`0 0 ${largura} ${altura}`}
      >
        {[0,1,2,3,4].map(i => {const valor = minimo+amplitude*i/4;const y = altura-margem-i/4*(altura-margem*2);return <g key={i}><line x1={margem} x2={largura-margem} y1={y} y2={y} stroke="#dce6e0"/><text x={margem-8} y={y+4} textAnchor="end" fontSize="13">{valor.toLocaleString("pt-BR",{maximumFractionDigits:2})}</text></g>;})}
        <polyline fill="none" points={pontos} stroke="#237447" strokeWidth="4" />
        {cotacoes.map(item => <circle key={item.id} cx={posicaoX(item)} cy={altura-margem-(Number(item.valor)-minimo)/amplitude*(altura-margem*2)} r="4" fill="#237447"><title>{`${formatarData(item.data)}: ${formato(Number(item.valor))} ${item.unidade}`}</title></circle>)}
        <text x={margem} y={altura-20} fontSize="14">{formatarData(cotacoes[0].data)}</text><text x={largura-margem} y={altura-20} fontSize="14" textAnchor="end">{formatarData(cotacoes[cotacoes.length-1].data)}</text>
      </svg>
      <figcaption>
        {formatarData(cotacoes[0].data)} a {formatarData(cotacoes[cotacoes.length - 1].data)} · mínimo {formato(minimo)} ·
        máximo {formato(maximo)} · {cotacoes[0].unidade} · Variação no período: {diferenca>0?"+":""}{formato(diferenca)} {cotacoes[0].unidade}{Number(cotacoes[0].valor)!==0?` (${formato(diferenca/Number(cotacoes[0].valor)*100)}%)`:""}
      </figcaption>
    </figure>
  );
}
