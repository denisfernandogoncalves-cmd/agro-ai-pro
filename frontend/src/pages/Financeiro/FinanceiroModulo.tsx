import { useState } from "react";
import { Propriedade } from "../../api/propriedades";
import AbasModulo, { PainelAba } from "../../components/AbasModulo";
import FinanceiroPage from "./FinanceiroPage";
import CalculoPrestacoes from "./CalculoPrestacoes";

export default function FinanceiroModulo({ propriedades }: { propriedades: Propriedade[] }) {
  const [aba, setAba] = useState("lancamentos");
  return <>
    <AbasModulo modulo="financeiro-secoes" ativa={aba} alterar={setAba} abas={[
      { id: "lancamentos", titulo: "Lançamentos financeiros" },
      { id: "prestacoes", titulo: "Cálculo de prestações" },
    ]} />
    <PainelAba modulo="financeiro-secoes" aba="lancamentos" ativa={aba}><FinanceiroPage propriedades={propriedades} /></PainelAba>
    <PainelAba modulo="financeiro-secoes" aba="prestacoes" ativa={aba}><CalculoPrestacoes /></PainelAba>
  </>;
}
