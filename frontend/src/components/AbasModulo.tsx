import { KeyboardEvent, ReactNode, useEffect, useRef, useState } from "react";
export type AbaModulo = { id: string; titulo: string };
export function indiceAbaTeclado(tecla: string, indice: number, total: number) {
  if (!total) return null;
  if (tecla === "ArrowRight") return (indice + 1) % total;
  if (tecla === "ArrowLeft") return (indice - 1 + total) % total;
  if (tecla === "Home") return 0;
  if (tecla === "End") return total - 1;
  return null;
}
export default function AbasModulo({ modulo, abas, ativa, alterar, desabilitado = false }: { modulo: string; abas: AbaModulo[]; ativa: string; alterar: (id: string) => void; desabilitado?: boolean }) {
  const botoes = useRef<(HTMLButtonElement | null)[]>([]);
  function teclado(evento: KeyboardEvent, indice: number) {
    const destino = indiceAbaTeclado(evento.key, indice, abas.length);
    if (destino === null || desabilitado) return;
    evento.preventDefault();
    botoes.current[destino]?.focus();
    alterar(abas[destino].id);
  }
  return <nav className="abas-modulo nao-imprimir" role="tablist" aria-label={`Abas de ${modulo}`}>
    {abas.map((aba, indice) => <button key={aba.id} ref={el => { botoes.current[indice] = el; }} type="button" role="tab" id={`${modulo}-aba-${aba.id}`} aria-controls={`${modulo}-painel-${aba.id}`} aria-selected={ativa === aba.id} tabIndex={ativa === aba.id ? 0 : -1} disabled={desabilitado} onClick={() => alterar(aba.id)} onKeyDown={e => teclado(e, indice)}>{aba.titulo}</button>)}
  </nav>;
}
export function PainelAba({ modulo, aba, ativa, children }: { modulo: string; aba: string; ativa: string; children: ReactNode }) {
  const selecionada = aba === ativa;
  const [visitada, setVisitada] = useState(selecionada);
  useEffect(() => { if (selecionada) setVisitada(true); }, [selecionada]);
  // Mantém os componentes já visitados para preservar formulários e filtros.
  return <section className="aba-modulo-painel" role="tabpanel" id={`${modulo}-painel-${aba}`} aria-labelledby={`${modulo}-aba-${aba}`} hidden={!selecionada} tabIndex={0}>{visitada || selecionada ? children : null}</section>;
}
