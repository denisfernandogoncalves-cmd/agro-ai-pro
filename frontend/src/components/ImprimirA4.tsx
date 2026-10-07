import { useAcoes } from "./AcoesContext";
import { useEffect } from "react";
import "../print.css";

/** A mesma preparação atende o botão e o atalho de impressão do navegador. */
export default function ImprimirA4() {
  const pode = useAcoes();
  const permitido = pode("imprimir");
  useEffect(() => {
    let restaurar: (() => void)[] = [];
    const limpar = () => {
      restaurar.reverse().forEach(acao => acao());
      restaurar = [];
    };
    const preparar = () => {
      limpar();
      if (!permitido) { document.body.classList.add("impressao-bloqueada"); restaurar.push(() => document.body.classList.remove("impressao-bloqueada")); return; }
      const pagina = document.querySelector("main.pagina");
      if (!pagina) return;
      const nota = document.createElement("p");
      nota.className = "somente-impressao impressao-contexto";
      const secoes = Array.from(pagina.querySelectorAll("nav button:not(.secundario)"))
        .map(botao => botao.textContent?.trim()).filter(Boolean).join(" / ");
      nota.textContent = `AGRO-AI-PRO · ${secoes} · ${new Date().toLocaleString("pt-BR")} · Dados da aba aberta, conforme a consulta e a página exibidas.`;
      pagina.querySelector("header")?.after(nota);
      restaurar.push(() => nota.remove());

      // Mantém a identificação dos seletores de consulta sem imprimir controles.
      pagina.querySelectorAll("select").forEach(seletor => {
        if (seletor.closest("form, dialog")) return;
        const valor = document.createElement("span");
        valor.className = "somente-impressao";
        valor.textContent = seletor.selectedOptions[0]?.textContent || "";
        seletor.after(valor);
        restaurar.push(() => valor.remove());
      });
      pagina.querySelectorAll<HTMLDetailsElement>("details:not([open])").forEach(detalhe => {
        if (detalhe.closest("form, dialog")) return;
        detalhe.open = true;
        restaurar.push(() => { detalhe.open = false; });
      });
      pagina.querySelectorAll("table").forEach(tabela => {
        const cabecalho = tabela.tHead?.rows[0];
        if (!cabecalho) return;
        Array.from(cabecalho.cells).forEach((celula, indice) => {
          if (celula.textContent?.trim() !== "Ações") return;
          Array.from(tabela.rows).forEach(linha => {
            const alvo = linha.cells[indice];
            if (!alvo || alvo.colSpan !== 1 || alvo.classList.contains("nao-imprimir")) return;
            alvo.classList.add("nao-imprimir");
            restaurar.push(() => alvo.classList.remove("nao-imprimir"));
          });
        });
      });
    };
    window.addEventListener("beforeprint", preparar);
    window.addEventListener("afterprint", limpar);
    return () => {
      limpar();
      window.removeEventListener("beforeprint", preparar);
      window.removeEventListener("afterprint", limpar);
    };
  }, [permitido]);

  if (!permitido) return null;
  return <button type="button" className="secundario" onClick={() => window.print()}
    title="Imprimir os dados desta aba em A4 retrato.">
    Imprimir A4
  </button>;
}
