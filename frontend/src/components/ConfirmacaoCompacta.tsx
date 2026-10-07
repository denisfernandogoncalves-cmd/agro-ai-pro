import { createContext, ReactNode, useContext, useEffect, useRef, useState } from "react";
type Pedido = { titulo: string; mensagem: string; confirmar?: string; perigo?: boolean };
const Contexto = createContext<((pedido: Pedido) => Promise<boolean>) | null>(null);
export function ConfirmacoesCompactas({ children }: { children: ReactNode }) {
  const [pedido, setPedido] = useState<Pedido | null>(null);
  const resposta = useRef<((aceita: boolean) => void) | null>(null);
  const dialogo = useRef<HTMLDialogElement>(null);
  const solicitar = (novo: Pedido) => new Promise<boolean>(resolver => {
    resposta.current?.(false); resposta.current = resolver; setPedido(novo);
  });
  function fechar(aceita: boolean) { resposta.current?.(aceita); resposta.current = null; setPedido(null); }
  useEffect(() => { if (pedido && !dialogo.current?.open) dialogo.current?.showModal(); }, [pedido]);
  useEffect(() => () => { resposta.current?.(false); }, []);
  return <Contexto.Provider value={solicitar}>{children}{pedido && <dialog ref={dialogo} className="card confirmacao-compacta" aria-labelledby="titulo-confirmacao" onCancel={e => {e.preventDefault(); fechar(false);}}>
    <h3 id="titulo-confirmacao">{pedido.titulo}</h3><p>{pedido.mensagem}</p>
    <div className="acoes"><button autoFocus type="button" className="secundario" onClick={() => fechar(false)}>Cancelar</button><button type="button" className={pedido.perigo ? "perigo" : ""} onClick={() => fechar(true)}>{pedido.confirmar || "Confirmar"}</button></div>
  </dialog>}</Contexto.Provider>;
}
export function useConfirmacaoCompacta() {
  const solicitar = useContext(Contexto);
  return solicitar || (async (pedido: Pedido) => window.confirm(pedido.mensagem));
}
