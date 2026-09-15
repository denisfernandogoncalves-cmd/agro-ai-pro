export function calcularPreviaParcelas(valor: string, quantidade: number, vencimento: string) {
  if (!/^\d{1,12}(\.\d{1,2})?$/.test(valor) || !Number.isInteger(quantidade) || quantidade < 1 || quantidade > 120
    || !/^\d{4}-\d{2}-\d{2}$/.test(vencimento)) return [];
  const [inteiro, decimal = ""] = valor.split(".");
  const total = Number(inteiro) * 100 + Number(decimal.padEnd(2, "0"));
  const [ano, mes, dia] = vencimento.split("-").map(Number);
  if (total < quantidade || ano < 1000 || mes < 1 || mes > 12 || dia < 1 || dia > new Date(Date.UTC(ano, mes, 0)).getUTCDate()) return [];
  const base = Math.floor(total / quantidade), resto = total % quantidade;
  return Array.from({ length: quantidade }, (_, indice) => {
    const meses = ano * 12 + mes - 1 + indice;
    const anoParcela = Math.floor(meses / 12), mesParcela = meses % 12 + 1;
    const diaParcela = Math.min(dia, new Date(Date.UTC(anoParcela, mesParcela, 0)).getUTCDate());
    return {
      numero: indice + 1, centavos: base + (indice < resto ? 1 : 0),
      vencimento: `${anoParcela}-${String(mesParcela).padStart(2, "0")}-${String(diaParcela).padStart(2, "0")}`,
    };
  });
}

export default function ParcelasPreview({ valor, quantidade, vencimento }: { valor: string; quantidade: number; vencimento: string }) {
  const parcelas = calcularPreviaParcelas(valor, quantidade, vencimento);
  if (!parcelas.length) return <p>Informe o valor total, a quantidade e o primeiro vencimento para conferir as parcelas.</p>;
  return <section aria-label="Conferência das parcelas"><h3>Confira antes de salvar</h3>
    <p>Vencimentos mensais. Os centavos restantes ficam nas primeiras parcelas.</p>
    <div style={{ maxHeight: 280, overflow: "auto" }}><table><thead><tr><th>Parcela</th><th>Vencimento</th><th>Valor</th></tr></thead>
      <tbody>{parcelas.map(p => <tr key={p.numero}><td>{p.numero}/{quantidade}</td><td>{p.vencimento.split("-").reverse().join("/")}</td><td>{(p.centavos / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</td></tr>)}</tbody>
    </table></div>
  </section>;
}
