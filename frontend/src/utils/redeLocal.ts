export function enderecoRedeLocal(valor: string): string | null {
  const partes = valor.trim().split(".");
  if (partes.length !== 4 || partes.some(p => !/^\d{1,3}$/.test(p) || Number(p) > 255)) return null;
  const [a,b,c,d] = partes.map(Number);
  if (!(a === 10 || a === 192 && b === 168 || a === 172 && b >= 16 && b <= 31)) return null;
  return [a,b,c,d].join(".");
}
