import { useEffect, useState } from "react";
import axios from "axios";
import { api } from "../api/propriedades";

export type ResultadoAdapar = {
  nome: string; empresa: string; classe_agronomica: string; principios_ativos: string;
  concentracao: string; registro_mapa: string; fonte_adapar: string;
  atualizacao_fonte: string; consulta_adapar: string;
};

export default function ConsultaAdapar({ nome, aplicar }: { nome: string; aplicar: (item: ResultadoAdapar) => void }) {
  const [resultados, setResultados] = useState<ResultadoAdapar[]>([]);
  const [mensagem, setMensagem] = useState("");
  const [buscando, setBuscando] = useState(false);
  const [tentativa, setTentativa] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setResultados([]);
    setMensagem("");
    setBuscando(false);
    if (nome.trim().length < 3) return;
    const timer = window.setTimeout(async () => {
      setBuscando(true);
      try {
        const { data } = await api.get<{ resultados: ResultadoAdapar[]; total: number }>("/estoque/produtos/consultar-adapar/", { params: { nome }, signal: controller.signal, timeout: 120000 });
        if (controller.signal.aborted) return;
        setResultados(data.resultados);
        setMensagem(data.total ? `${data.total} resultado(s). Confira o nome e o registro antes de selecionar.${data.total > 20 ? " Mostrando 20: refine o nome." : ""}` : "Nenhum produto encontrado na lista consultada. Você pode preencher manualmente.");
      } catch (erro) {
        if (controller.signal.aborted) return;
        setMensagem(axios.isAxiosError(erro) && typeof erro.response?.data?.detail === "string" ? erro.response.data.detail : "Consulta indisponível. Tente novamente ou preencha manualmente.");
      } finally {
        if (!controller.signal.aborted) setBuscando(false);
      }
    }, 1200);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [nome, tentativa]);
  return <div className="conteudo" aria-label="Consulta de defensivos ADAPAR">
    <small>Busca automática na lista oficial de defensivos da ADAPAR. Selecione para preencher classe e princípios ativos.</small>
    <p role="status">{buscando ? "Consultando ADAPAR…" : mensagem}</p>
    {resultados.map(item => <article className="item" key={`${item.registro_mapa}-${item.nome}`}>
      <div><strong>{item.nome}</strong><p>{item.empresa} · registro {item.registro_mapa}</p><p>{item.classe_agronomica} · {item.principios_ativos}</p><small>{item.concentracao} · lista de {item.atualizacao_fonte}</small><div className="acoes"><button type="button" onClick={() => { aplicar(item); setResultados([]); setMensagem("Dados selecionados. Salve o cadastro para confirmar."); }}>Usar estes dados</button><a href={item.fonte_adapar} target="_blank" rel="noreferrer">Conferir fonte</a></div></div>
    </article>)}
    {!buscando && nome.trim().length >= 3 && <button className="secundario" type="button" onClick={() => setTentativa(v => v + 1)}>Buscar novamente</button>}
  </div>;
}
