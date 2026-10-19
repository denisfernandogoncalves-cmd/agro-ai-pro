import { useEffect, useState } from "react";
import { api } from "../api/propriedades";
import type { Modulo } from "../api/usuarios";
import { nomeModulo } from "./gruposModulos";

export type ResultadoBusca = { modulo: Modulo; tipo: string; id: string; titulo: string; resumo: string };
export default function BuscaGeralResultados({ termo, abrir }: { termo: string; abrir: (item: ResultadoBusca) => void }) {
  const [dados, setDados] = useState<{ resultados: ResultadoBusca[]; limitado: boolean }>({ resultados: [], limitado: false });
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState("");
  useEffect(() => {
    const controle = new AbortController();
    setDados({ resultados: [], limitado: false });
    setErro("");
    if (!termo.trim()) { setOcupado(false); return; }
    setOcupado(true);
    const timer = setTimeout(() => {
      void api.get("/core/busca/", { params: { q: termo.trim() }, signal: controle.signal }).then(resposta => {
        if (!controle.signal.aborted) setDados(resposta.data);
      }).catch(() => {
        if (!controle.signal.aborted) setErro("Não foi possível buscar os registros. Altere o texto para tentar novamente.");
      }).finally(() => { if (!controle.signal.aborted) setOcupado(false); });
    }, 450);
    return () => { clearTimeout(timer); controle.abort(); };
  }, [termo]);
  if (!termo.trim()) return null;
  return <section className="busca-geral-resultados" aria-label="Registros encontrados">
    <h2>Registros do programa</h2>
    {ocupado ? <p role="status">Buscando registros…</p> : erro ? <p role="alert">{erro}</p> : <>
      <p role="status">{dados.resultados.length} registro(s) encontrado(s).{dados.limitado && " Até 5 por tipo; refine a busca para ver outros resultados."}</p>
      {dados.resultados.map(item => <button type="button" key={`${item.modulo}-${item.tipo}-${item.id}`} onClick={() => abrir(item)}>
        <strong>{item.titulo}</strong><small>{nomeModulo(item.modulo)} · {item.tipo} #{item.id}</small><small>{item.resumo}</small>
      </button>)}
    </>}
  </section>;
}
