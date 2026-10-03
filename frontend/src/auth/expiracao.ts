export function expiracaoToken(token: string | null): number | null {
  if (!token) return null;
  try {
    const parte = token.split(".")[1];
    if (!parte) return null;
    const dados = JSON.parse(atob(parte.replace(/-/g,"+").replace(/_/g,"/")));
    return typeof dados.exp === "number" && Number.isFinite(dados.exp) && dados.exp > 0 ? dados.exp * 1000 : null;
  } catch { return null; }
}
export function sessaoPrecisaRenovar(access: string | null, refresh: string | null, agora = Date.now()) {
  const expAccess=expiracaoToken(access), expRefresh=expiracaoToken(refresh);
  return expAccess !== null && expRefresh !== null && (expAccess-agora<=120000 || expRefresh-agora<=300000);
}
