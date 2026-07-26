import { useEffect, useState } from "react";

import { Insight, obterInsights } from "../../api/insights";
import { Propriedade } from "../../api/propriedades";

export default function InsightsPage({ propriedades }: { propriedades: Propriedade[] }) {
  const [propriedade, setPropriedade] = useState("");
  const [insights, setInsights] = useState<Insight[]>([]);
  const [aviso, setAviso] = useState("");
  const [erro, setErro] = useState("");

  async function carregar() {
    try {
      const dados = await obterInsights(propriedade);
      setInsights(dados.insights);
      setAviso(dados.aviso);
      setErro("");
    } catch {
      setErro("Não foi possível gerar os insights.");
    }
  }
  useEffect(() => { void carregar(); }, []);

  return (
    <section className="modulo-insights">
      <section className="card controles-insights">
        <div><span className="kicker">Motor explicável</span><h2>Assistente gerencial</h2></div>
        <label>Propriedade<select value={propriedade} onChange={(e) => setPropriedade(e.target.value)}><option value="">Todas</option>{propriedades.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
        <button type="button" onClick={() => void carregar()}>Analisar dados atuais</button>
      </section>
      {erro && <p className="erro card">{erro}</p>}
      <div className="lista-insights">
        {insights.map((item) => <article className={`card insight ${item.nivel}`} key={item.codigo}><span className="kicker">{item.modulo} · {item.nivel}</span><h3>{item.titulo}</h3><p><strong>Evidência:</strong> {item.evidencia}</p><p><strong>Ação sugerida:</strong> {item.recomendacao}</p></article>)}
      </div>
      <p className="card aviso-mercado">{aviso}</p>
    </section>
  );
}
