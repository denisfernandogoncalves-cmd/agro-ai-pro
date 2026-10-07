import { useAcoes } from "./AcoesContext";
import { ReactNode, useEffect, useRef, useState } from "react";

export default function PainelFormulario({ titulo, edicao, children, inicialmenteAberto = false }: { titulo: string; edicao?: string | number | null; children: ReactNode; inicialmenteAberto?: boolean }) {
  const pode = useAcoes();
  const [aberto, setAberto] = useState(!!edicao || inicialmenteAberto);
  const painel = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    if (!edicao) return;
    setAberto(true);
  }, [edicao]);
  useEffect(() => {
    if (!edicao || !aberto) return;
    const quadro = requestAnimationFrame(() => {
      const elemento = painel.current;
      elemento?.scrollIntoView({ block: "nearest" });
      elemento?.querySelector<HTMLInputElement>("input:not([type=hidden]):not(:disabled), select:not(:disabled), textarea:not(:disabled)")?.focus({ preventScroll: true });
    });
    return () => cancelAnimationFrame(quadro);
  }, [edicao, aberto]);
  if (!pode(edicao ? "editar" : "cadastrar")) return null;
  return <details ref={painel} className="painel-formulario" open={aberto} onToggle={e => setAberto(e.currentTarget.open)}>
    <summary>{titulo}<span>{aberto ? "Recolher formulário" : "Abrir formulário"}</span></summary>
    {children}
  </details>;
}
