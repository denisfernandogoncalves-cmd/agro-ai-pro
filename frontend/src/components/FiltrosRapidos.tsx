export type FiltrosRapidosValor = { cultura: string; safra: string; propriedade: string };
export const filtrosRapidosVazios: FiltrosRapidosValor = { cultura: "", safra: "", propriedade: "" };
export function restaurarConsultaFavorita(valores: Record<string, unknown>) {
  const texto = (chave: string) => typeof valores[chave] === "string" || typeof valores[chave] === "number" ? String(valores[chave]) : "";
  return { busca: texto("search"), mostrarHistorico: valores.mostrarHistorico === true || valores.mostrarHistorico === "true",
    filtros: {cultura:texto("cultura"), safra:texto("safra"), propriedade:texto("propriedade")} };
}
export function correspondeFiltrosRapidos(filtros: FiltrosRapidosValor, cultura: string, safra: string, propriedades: number[]) {
  return (!filtros.cultura || filtros.cultura === cultura) && (!filtros.safra || filtros.safra === safra)
    && (!filtros.propriedade || propriedades.includes(Number(filtros.propriedade)));
}
export default function FiltrosRapidos({ valor, alterar, culturas, safras, propriedades, busca, limparBusca, quantidade }: {
  valor: FiltrosRapidosValor; alterar: (valor: FiltrosRapidosValor) => void; culturas: string[]; safras: string[];
  propriedades: { id: number; nome: string }[]; busca: string; limparBusca: () => void; quantidade: number;
}) {
  const ativos = [busca.trim() && `Busca: ${busca.trim()}`, valor.cultura && `Cultura: ${valor.cultura}`, valor.safra && `Safra: ${valor.safra}`,
    valor.propriedade && `Propriedade: ${propriedades.find(p => String(p.id) === valor.propriedade)?.nome || valor.propriedade}`].filter(Boolean);
  return <div className="filtros-rapidos nao-imprimir">
    <div className="filtros-rapidos-campos"><label>Filtrar cultura<select value={valor.cultura} onChange={e => alterar({...valor,cultura:e.target.value})}><option value="">Todas</option>{culturas.map(c => <option key={c}>{c}</option>)}</select></label>
    <label>Filtrar safra<select value={valor.safra} onChange={e => alterar({...valor,safra:e.target.value})}><option value="">Todas</option>{safras.map(s => <option key={s}>{s}</option>)}</select></label>
    <label>Filtrar propriedade<select value={valor.propriedade} onChange={e => alterar({...valor,propriedade:e.target.value})}><option value="">Todas</option>{propriedades.map(p => <option key={p.id} value={p.id}>{p.nome}</option>)}</select></label></div>
    <p className="resumo-consulta" role="status">{quantidade} registro(s) · {ativos.length ? ativos.join(" · ") : "Sem filtros de busca, cultura, safra ou propriedade"}</p>
    {!!ativos.length && <button className="secundario" type="button" onClick={() => {alterar(filtrosRapidosVazios); limparBusca();}}>Limpar filtros</button>}
  </div>;
}
