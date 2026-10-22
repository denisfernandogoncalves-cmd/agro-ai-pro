import type { Propriedade } from "../api/propriedades";

type DadosOrdenaveis = Pick<
  Propriedade,
  "id" | "nome" | "latitude" | "longitude" | "cad_pro_numeros"
>;

export type GrupoPropriedades<T extends DadosOrdenaveis> = {
  chave: string;
  titulo: string;
  propriedades: T[];
};

const comparador = new Intl.Collator("pt-BR", {
  numeric: true,
  sensitivity: "base",
});

function compararNome(a: DadosOrdenaveis, b: DadosOrdenaveis): number {
  return comparador.compare(a.nome, b.nome) || a.id - b.id;
}

function normalizarCadPro(valor: string): string {
  // 123.456-7 e 1234567 representam o mesmo cadastro.
  return valor.normalize("NFKC").trim().toUpperCase().replace(/[^A-Z0-9]/g, "");
}

function codigosDaPropriedade(item: DadosOrdenaveis) {
  return (Array.isArray(item.cad_pro_numeros) ? item.cad_pro_numeros : [])
    .filter((numero): numero is string => typeof numero === "string")
    .map((numero) => ({ numero: numero.trim(), chave: normalizarCadPro(numero) }))
    .filter((cadPro) => cadPro.chave.length > 0);
}

function coordenadas(item: DadosOrdenaveis): [number, number] | null {
  if (
    item.latitude === null ||
    item.longitude === null ||
    String(item.latitude).trim() === "" ||
    String(item.longitude).trim() === ""
  ) {
    return null;
  }
  const lat = Number(item.latitude);
  const lng = Number(item.longitude);
  if (
    !Number.isFinite(lat) ||
    !Number.isFinite(lng) ||
    Math.abs(lat) > 90 ||
    Math.abs(lng) > 180
  ) {
    return null;
  }
  return [lat, lng];
}

function distanciaKm(a: [number, number], b: [number, number]) {
  const radianos = Math.PI / 180;
  const dLat = (b[0] - a[0]) * radianos;
  const dLng = (b[1] - a[1]) * radianos;
  const arco =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(a[0] * radianos) *
      Math.cos(b[0] * radianos) *
      Math.sin(dLng / 2) ** 2;

  return 2 * 6371.0088 * Math.asin(Math.min(1, Math.sqrt(arco)));
}

function ordenarPorProximidade<T extends DadosOrdenaveis>(itens: T[]): T[] {
  const localizados = itens
    .filter((item) => coordenadas(item) !== null)
    .sort((a, b) => {
      const pontoA = coordenadas(a)!;
      const pontoB = coordenadas(b)!;
      return (
        pontoA[0] - pontoB[0] ||
        pontoA[1] - pontoB[1] ||
        compararNome(a, b)
      );
    });
  const semCoordenadas = itens
    .filter((item) => coordenadas(item) === null)
    .sort(compararNome);

  if (localizados.length === 0) return semCoordenadas;

  // Mantém as propriedades mais próximas em sequência, começando pelo ponto
  // mais ao norte. O ponto inicial é determinístico, independentemente da API.
  const resultado = [localizados.shift()!];

  while (localizados.length > 0) {
    const origem = coordenadas(resultado[resultado.length - 1])!;
    let indiceMaisProximo = 0;
    let menorDistancia = Infinity;

    localizados.forEach((item, indice) => {
      const distancia = distanciaKm(origem, coordenadas(item)!);
      if (
        distancia < menorDistancia - 1e-9 ||
        (Math.abs(distancia - menorDistancia) <= 1e-9 &&
          compararNome(item, localizados[indiceMaisProximo]) < 0)
      ) {
        menorDistancia = distancia;
        indiceMaisProximo = indice;
      }
    });

    resultado.push(localizados.splice(indiceMaisProximo, 1)[0]);
  }

  return [...resultado, ...semCoordenadas];
}

/**
 * Junta propriedades com CAD/PRO em comum (inclusive vínculos de vários números)
 * e ordena as integrantes pela proximidade geográfica. Propriedades sem CAD/PRO
 * ficam em um último grupo, também ordenadas pela localização.
 *
 * Não modifica os objetos da API nem os dados persistidos.
 */
export function organizarPropriedades<T extends DadosOrdenaveis>(
  propriedades: readonly T[],
): GrupoPropriedades<T>[] {
  if (!propriedades.length) return [];

  const pais = propriedades.map((_, indice) => indice);

  function raiz(indice: number): number {
    if (pais[indice] !== indice) pais[indice] = raiz(pais[indice]);
    return pais[indice];
  }

  function unir(a: number, b: number) {
    const raizA = raiz(a);
    const raizB = raiz(b);
    if (raizA !== raizB) pais[raizB] = raizA;
  }

  const primeiroIndicePorCadPro = new Map<string, number>();

  propriedades.forEach((propriedade, indice) => {
    for (const { chave } of codigosDaPropriedade(propriedade)) {
      const primeiro = primeiroIndicePorCadPro.get(chave);
      if (primeiro === undefined) {
        primeiroIndicePorCadPro.set(chave, indice);
      } else {
        unir(primeiro, indice);
      }
    }
  });

  const componentes = new Map<number, T[]>();
  propriedades.forEach((propriedade, indice) => {
    const codigo = codigosDaPropriedade(propriedade);
    const grupo = codigo.length === 0 ? -1 : raiz(indice);
    const lista = componentes.get(grupo) ?? [];
    lista.push(propriedade);
    componentes.set(grupo, lista);
  });

  const grupos = [...componentes.entries()].map(([indice, itens]) => {
    const codigos = new Map<string, string>();

    for (const propriedade of itens) {
      for (const { chave, numero } of codigosDaPropriedade(propriedade)) {
        const atual = codigos.get(chave);
        if (!atual || comparador.compare(numero, atual) < 0) {
          codigos.set(chave, numero);
        }
      }
    }

    const chavesOrdenadas = [...codigos.keys()].sort(comparador.compare);
    const rotulos = chavesOrdenadas.map((chave) => codigos.get(chave)!);

    return {
      chave: indice === -1 ? "sem-cadpro" : `cadpro:${chavesOrdenadas.join("|")}`,
      titulo: rotulos.length ? `CAD/PRO ${rotulos.join(" · ")}` : "Sem CAD/PRO informado",
      propriedades: ordenarPorProximidade(itens),
      ordem: chavesOrdenadas[0] ?? "",
      semCadPro: !rotulos.length,
    };
  });

  grupos.sort(
    (a, b) =>
      Number(a.semCadPro) - Number(b.semCadPro) ||
      comparador.compare(a.ordem, b.ordem),
  );

  return grupos.map(({ chave, titulo, propriedades: itens }) => ({
    chave,
    titulo,
    propriedades: itens,
  }));
}
