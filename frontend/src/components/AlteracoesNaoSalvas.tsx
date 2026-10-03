import { createContext, ReactNode, useContext, useEffect, useId, useMemo, useRef, useState } from "react";
import { useConfirmacaoCompacta } from "./ConfirmacaoCompacta";

export function criarRegistroAlteracoes() {
  const pendentes = new Map<string, string>();
  return {
    atualizar(id: string, descricao: string, alterado: boolean) { if (alterado) pendentes.set(id, descricao); else pendentes.delete(id); },
    remover(id: string) { pendentes.delete(id); },
    descricoes() { return [...new Set(pendentes.values())]; },
  };
}
const Contexto = createContext<ReturnType<typeof criarRegistroAlteracoes> | null>(null);
export function ProtecaoAlteracoes({ children }: { children: ReactNode }) {
  const registro = useMemo(criarRegistroAlteracoes, []);
  useEffect(() => {
    const avisar = (evento: BeforeUnloadEvent) => { if (registro.descricoes().length) { evento.preventDefault(); evento.returnValue = ""; } };
    window.addEventListener("beforeunload", avisar);
    return () => window.removeEventListener("beforeunload", avisar);
  }, [registro]);
  return <Contexto.Provider value={registro}>{children}</Contexto.Provider>;
}
export function useConfirmarSaida() {
  const registro = useContext(Contexto);
  const confirmar = useConfirmacaoCompacta();
  return async () => !registro?.descricoes().length || await confirmar({titulo:"Alterações não salvas", confirmar:"Sair sem salvar", mensagem:`Há alterações não salvas em: ${registro.descricoes().join(", ")}. Sair desta tela? Rascunhos automáticos já gravados permanecem disponíveis para recuperação.`});
}
export function useAlteracoesNaoSalvas(valor: unknown, descricao: string, identidade: string | number | null = null, ativo = true) {
  const registro = useContext(Contexto);
  const confirmar = useConfirmacaoCompacta();
  const id = useId();
  const assinatura = JSON.stringify(valor);
  const base = useRef({ identidade, assinatura });
  const [, atualizar] = useState(0);
  if (base.current.identidade !== identidade) base.current = { identidade, assinatura };
  const alterado = ativo && assinatura !== base.current.assinatura;
  useEffect(() => { registro?.atualizar(id, descricao, alterado); }, [registro, id, descricao, alterado]);
  useEffect(() => () => registro?.remover(id), [registro, id]);
  return {
    alterado,
    marcarSalvo(novoValor: unknown = valor) { base.current = { identidade, assinatura: JSON.stringify(novoValor) }; registro?.remover(id); atualizar(v => v + 1); },
    async confirmarDescarte() { return !alterado || await confirmar({titulo:"Descartar alterações?", confirmar:"Descartar", mensagem:`Descartar as alterações não salvas em ${descricao}?`}); },
  };
}
