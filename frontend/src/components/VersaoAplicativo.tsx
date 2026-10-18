export default function VersaoAplicativo() {
  const versao = __APP_BUILD__;
  const data = new Date(versao.compiladoEm).toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" });
  return <small className="versao-aplicativo nao-imprimir" title={`Interface ${versao.interface} · compilada em ${data} (Brasília)`}>
    {versao.canal} · versão {versao.versao}<br />
    Interface {versao.interface} · {data}
  </small>;
}
