import { useEffect, useState } from "react";

export type DefinicaoColuna<T extends string> = readonly [T, string];

export function normalizarColunasImpressao<T extends string>(
  valor: unknown,
  disponiveis: readonly T[],
): T[] {
  if (!Array.isArray(valor)) return [...disponiveis];
  const validas = valor.filter(
    (item, indice): item is T =>
      typeof item === "string"
      && disponiveis.includes(item as T)
      && valor.indexOf(item) === indice,
  );
  return validas.length ? validas : [...disponiveis];
}

export function useColunasImpressao<T extends string>(
  chave: string,
  definicoes: readonly DefinicaoColuna<T>[],
) {
  const disponiveis = definicoes.map(([id]) => id);
  const [selecionadas, setSelecionadas] = useState<T[]>(() => {
    if (typeof localStorage === "undefined") return [...disponiveis];
    try {
      return normalizarColunasImpressao(JSON.parse(localStorage.getItem(chave) || "null"), disponiveis);
    } catch {
      return [...disponiveis];
    }
  });

  useEffect(() => {
    if (typeof localStorage !== "undefined") {
      localStorage.setItem(chave, JSON.stringify(selecionadas));
    }
  }, [chave, selecionadas]);

  return { selecionadas, setSelecionadas, todas: disponiveis };
}

export default function SeletorColunasImpressao<T extends string>({
  definicoes,
  selecionadas,
  alterar,
  descricao,
}: {
  definicoes: readonly DefinicaoColuna<T>[];
  selecionadas: T[];
  alterar: (colunas: T[]) => void;
  descricao: string;
}) {
  const todas = definicoes.map(([id]) => id);
  function alternar(id: T, marcada: boolean) {
    if (!marcada && selecionadas.length === 1) return;
    alterar(marcada
      ? todas.filter(item => selecionadas.includes(item) || item === id)
      : selecionadas.filter(item => item !== id));
  }

  return <section className="card seletor-colunas nao-imprimir" aria-label="Configurar informações da impressão">
    <div className="seletor-colunas-cabecalho">
      <div><h3>Informações da impressão</h3><p>{descricao}</p></div>
      <strong>{selecionadas.length} de {todas.length} colunas</strong>
    </div>
    <div className="seletor-colunas-opcoes">{definicoes.map(([id, nome]) => <label key={id}>
      <input
        type="checkbox"
        checked={selecionadas.includes(id)}
        disabled={selecionadas.length === 1 && selecionadas.includes(id)}
        onChange={evento => alternar(id, evento.target.checked)}
      /> {nome}
    </label>)}</div>
    <div className="seletor-colunas-acoes">
      <small>A escolha fica gravada neste navegador. Pelo menos uma coluna permanece selecionada.</small>
      <div>
        <button type="button" className="secundario" onClick={() => alterar([...todas])}>Selecionar todas</button>
        <button type="button" onClick={() => window.print()}>Imprimir com estas colunas</button>
      </div>
    </div>
  </section>;
}
