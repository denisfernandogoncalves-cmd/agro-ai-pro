import { useEffect, useRef, useState } from "react";

import { Insight, obterInsights } from "../../api/insights";
import { Propriedade, rotuloPropriedade } from "../../api/propriedades";

export default function InsightsPage({ propriedades }: { propriedades: Propriedade[] }) {
  const [propriedade, setPropriedade] = useState("");
  const [insights, setInsights] = useState<Insight[]>([]);
  const [aviso, setAviso] = useState("");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [analisado, setAnalisado] = useState(false);
  const trava = useRef(false);

  async function carregar() {
    if (trava.current) return;
    trava.current = true; setCarregando(true); setErro(""); setAnalisado(false);
    setInsights([]); setAviso("");
    try {
      const dados = await obterInsights(propriedade);
      setInsights(dados.insights);
      setAviso(dados.aviso);
      setErro("");
      setAnalisado(true);
    } catch {
      setErro("Não foi possível gerar os insights.");
    } finally { trava.current = false; setCarregando(false); }
  }
  useEffect(() => { void carregar(); }, []);

  return (
    <section className="modulo-insights">
      <section className="card controles-insights">
        <div><span className="kicker">Motor explicável</span><h2>Assistente gerencial</h2></div>
        <label>Propriedade<select disabled={carregando} value={propriedade} onChange={(e) => { setPropriedade(e.target.value); setAnalisado(false); setInsights([]); setAviso(""); }}><option value="">Todas</option>{propriedades.map((item) => <option key={item.id} value={item.id}>{rotuloPropriedade(item)}</option>)}</select></label>
        <button disabled={carregando} type="button" onClick={() => void carregar()}>{carregando ? "Analisando..." : "Analisar dados atuais"}</button>
      </section>
      {erro && <p className="erro card" role="alert">{erro}</p>}
      <p className="card" role="status">{carregando ? "Analisando os dados. Aguarde..." : analisado ? insights.length ? `${insights.length} alerta(s) encontrado(s).` : "Nenhum alerta encontrado para a seleção." : "Selecione a propriedade e clique em Analisar dados atuais."}</p>
      <div className="lista-insights">
        {insights.map((item) => <article className={`card insight ${item.nivel}`} key={item.codigo}><span className="kicker">{item.modulo} · {item.nivel}</span><h3>{item.titulo}</h3><p><strong>Evidência:</strong> {item.evidencia}</p><p><strong>Ação sugerida:</strong> {item.recomendacao}</p></article>)}
      </div>
      {aviso && <p className="card aviso-mercado">{aviso}</p>}
    </section>
  );
}
