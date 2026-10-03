import { ButtonHTMLAttributes, createContext, ReactNode, useContext, useEffect, useRef } from "react";
import { Acao, Modulo, Pagina, UsuarioAtual } from "../api/usuarios";
export type DestinoConsulta = { modulo: Modulo; filtros: Record<string, string | number | boolean>; registro?: number; chave: number };
export function autorizado(acesso: UsuarioAtual | null, modulo: Pagina, acao: Acao): boolean {
  if (!acesso) return false;
  if (acesso.is_staff) return true;
  if (modulo === "usuarios" || modulo === "historico") return false;
  if (modulo === "inicio") return acao === "consultar" || (acao === "imprimir" && acesso.modulos.every(id => autorizado(acesso, id, "imprimir")));
  return acesso.modulos.includes(modulo) && (!acesso.permissoes || (acesso.permissoes[modulo] ?? []).includes(acao));
}
export const AcoesContext = createContext<{ acesso: UsuarioAtual | null; modulo: Pagina; destino?: DestinoConsulta } | null>(null);
export function useAcoes() { const atual = useContext(AcoesContext); return (acao: Acao) => atual === null || autorizado(atual.acesso, atual.modulo, acao); }
export function BotaoAcao({ acao, children, motivoBloqueio, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { acao: Acao; children: ReactNode; motivoBloqueio?: string }) {
  const pode = useAcoes();
  if (!pode(acao)) return null;
  return props.disabled && motivoBloqueio ? <span className="acao-com-aviso"><button {...props} title={motivoBloqueio}>{children}</button><small role="status">{motivoBloqueio}</small></span> : <button {...props}>{children}</button>;
}
export function useDestinoConsulta(modulo: Modulo, aplicar: (filtros: Record<string, string | number | boolean>, registro?: number) => void) {
  const contexto = useContext(AcoesContext); const aplicado = useRef<number | undefined>(undefined); const callback = useRef(aplicar); callback.current = aplicar;
  useEffect(() => { const destino = contexto?.destino; if (!destino || destino.modulo !== modulo || destino.chave === aplicado.current) return;
    aplicado.current = destino.chave; callback.current(destino.filtros, destino.registro);
  }, [contexto?.destino, modulo]);
}

export function useEntradaPainel(modulo: Modulo) { return useContext(AcoesContext)?.destino?.modulo === modulo; }
