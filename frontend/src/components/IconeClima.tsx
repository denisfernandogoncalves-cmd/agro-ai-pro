export default function IconeClima({ condicao }: { condicao: string }) {
  const texto = condicao.toLocaleLowerCase("pt-BR");
  const chuva = /chuva|tempestade|garoa/.test(texto), sol = /claro|ensolarado/.test(texto);
  return <svg className="icone-clima" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
    {sol ? <><circle cx="24" cy="24" r="9" /><path d="M24 4v5m0 30v5M4 24h5m30 0h5M10 10l4 4m20 20 4 4M10 38l4-4m20-20 4-4" /></> : <path d="M12 32a8 8 0 1 1 0-16 12 12 0 0 1 23-2 9 9 0 1 1 0 18Z" />}
    {chuva && <path d="m16 37-3 6m12-6-3 6m12-6-3 6" />}
  </svg>;
}
