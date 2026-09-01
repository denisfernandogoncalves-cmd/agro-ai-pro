export const HECTARES_POR_ALQUEIRE_PAULISTA = 2.42;

function numeroArea(valor: string | number | null | undefined) {
  if (valor === null || valor === undefined || valor === "") return 0;
  const normalizado = typeof valor === "number" ? valor : Number(String(valor).replace(",", "."));
  return Number.isFinite(normalizado) ? normalizado : 0;
}

export function alqueiresDeHectares(valor: string | number | null | undefined) {
  return numeroArea(valor) / HECTARES_POR_ALQUEIRE_PAULISTA;
}

export function hectaresDeAlqueires(valor: string | number | null | undefined) {
  return (numeroArea(valor) * HECTARES_POR_ALQUEIRE_PAULISTA).toFixed(2);
}

export function areaEmAlqueires(valorHectares: string | number | null | undefined, casas = 3) {
  return alqueiresDeHectares(valorHectares).toLocaleString("pt-BR", {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  });
}

export function valorAlqueiresParaFormulario(valorHectares: string | number | null | undefined) {
  if (valorHectares === null || valorHectares === undefined || valorHectares === "") return "";
  return String(Number(alqueiresDeHectares(valorHectares).toFixed(4)));
}
