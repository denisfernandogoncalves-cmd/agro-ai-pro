import { FormEvent, useEffect, useRef, useState } from "react";
import ChatLocal from "../../components/ChatLocal";

import { Insight, obterInsights } from "../../api/insights";
import { Propriedade, rotuloPropriedade } from "../../api/propriedades";

export function filtrarInsights(insights: Insight[], pergunta: string) {
  const texto = pergunta.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const assuntos = [
    [/estoque|saldo|armaz/, /estoque|saldo|armaz/],
    [/clima|chuva|seca|tempo/, /clima|chuva|seca|tempo/],
    [/venda|vender|mercado|soja|preco/, /venda|mercado|preco|cotac/],
    [/talh|produt|colheita|safra/, /talh|produt|colheita|safra/],
    [/custo|financ|conta|pagar|receber/, /custo|financ|conta|pagar|receber/],
  ];
  const filtros = assuntos.filter(([entrada]) => entrada.test(texto)).map(([,saida]) => saida);
  if (!texto.trim()) return insights;
  if (!filtros.length) return [];
  return insights.filter(i => {
    const conteudo = `${i.modulo} ${i.titulo} ${i.evidencia} ${i.recomendacao}`.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    return filtros.some(filtro => filtro.test(conteudo));
  });
}

export default function InsightsPage({ propriedades }: { propriedades: Propriedade[] }) {
  const [propriedade, setPropriedade] = useState("");
  const [insights, setInsights] = useState<Insight[]>([]);
  const [aviso, setAviso] = useState("");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [analisado, setAnalisado] = useState(false);
  const [texto, setTexto] = useState("");
  const [pergunta, setPergunta] = useState("");
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
  async function perguntar(event?: FormEvent, sugestao?: string) {
    event?.preventDefault();
    const consulta = (sugestao ?? texto).trim();
    if (!consulta || trava.current) return;
    setPergunta(consulta); setTexto("");
    await carregar();
  }
  const respostas = filtrarInsights(insights, pergunta);

  return (
    <section className="modulo-insights">
      <section className="card controles-insights">
        <div><span className="kicker">Motor explicável</span><h2>Assistente gerencial</h2></div>
        <label>Propriedade<select disabled={carregando} value={propriedade} onChange={(e) => { setPropriedade(e.target.value); setAnalisado(false); setInsights([]); setAviso(""); setPergunta(""); setTexto(""); }}><option value="">Todas</option>{propriedades.map((item) => <option key={item.id} value={item.id}>{rotuloPropriedade(item)}</option>)}</select></label>
        <button disabled={carregando} type="button" onClick={() => void carregar()}>{carregando ? "Analisando..." : "Analisar dados atuais"}</button>
      </section>
      {erro && <p className="erro card" role="alert">{erro}</p>}
      <p className="card" role="status">{carregando ? "Analisando os dados. Aguarde..." : analisado ? insights.length ? `${insights.length} alerta(s) encontrado(s).` : "Nenhum alerta encontrado para a seleção." : "Selecione a propriedade e clique em Analisar dados atuais."}</p>
      <div className="assistente-layout">
      <section className="card assistente-conversa" aria-label="Conversa com o assistente">
        <div><span className="kicker">Assistente AGRO AI</span><h2>Como posso ajudar sua gestão?</h2><p>Consulte as análises disponíveis para sua propriedade. As respostas abaixo selecionam evidências do motor explicável existente; o quadro de IA local abaixo depende da disponibilidade do serviço e informa falhas de consulta.</p></div>
        {pergunta && <div className="assistente-pergunta">{pergunta}</div>}
        <div className="assistente-resposta" aria-live="polite" aria-busy={carregando}>
          {carregando ? <p>Consultando as análises atuais…</p> : erro ? <p>Consulta indisponível. Tente analisar novamente.</p> : !analisado ? <p>Escolha a propriedade e analise os dados atuais.</p> : <>
          {respostas.map(item => <article className="insight" key={item.codigo}><span className="kicker">{item.modulo} · {item.nivel}</span><h3>{item.titulo}</h3><p><strong>Evidência:</strong> {item.evidencia}</p><p><strong>Recomendação:</strong> {item.recomendacao}</p></article>)}
          {!respostas.length && <p>{pergunta ? "O serviço atual não retornou evidências para responder a essa pergunta. Consulte o módulo correspondente; nenhuma recomendação foi estimada." : "Nenhuma recomendação encontrada na consulta atual."}</p>}
          </>}
        </div>
        <form className="tw:grid tw:gap-3" onSubmit={e => { void perguntar(e); }}><label>Pergunte sobre sua operação<input maxLength={500} value={texto} onChange={e => setTexto(e.target.value)} placeholder="Ex.: Há alertas no estoque?" disabled={carregando} /></label><button type="submit" disabled={carregando || !texto.trim()}>Consultar análises</button></form>
      </section>
      <aside className="card assistente-sugestoes"><h2>Comece por uma pergunta</h2>{["Como está meu estoque disponível?", "Há risco climático para os próximos dias?", "Quais análises de produtividade estão disponíveis?", "Há recomendações de mercado?", "Quais contas precisam de atenção?"].map(sugestao => <button type="button" key={sugestao} disabled={carregando} onClick={() => { void perguntar(undefined,sugestao); }}>{sugestao}</button>)}<p className="executivo-nota">A análise respeita os acessos da sua conta e a propriedade selecionada.</p></aside>
      </div>
      <ChatLocal key={propriedade} propriedade={propriedade}/>
      <h2>Todas as análises e recomendações</h2><div className="lista-insights">
        {insights.map((item) => <article className={`card insight ${item.nivel}`} key={item.codigo}><span className="kicker">{item.modulo} · {item.nivel}</span><h3>{item.titulo}</h3><p><strong>Evidência:</strong> {item.evidencia}</p><p><strong>Ação sugerida:</strong> {item.recomendacao}</p></article>)}
      </div>
      {aviso && <p className="card aviso-mercado">{aviso}</p>}
    </section>
  );
}
