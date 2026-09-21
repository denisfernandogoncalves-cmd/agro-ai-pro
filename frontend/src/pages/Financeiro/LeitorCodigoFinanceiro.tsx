import { FormEvent, useRef, useState } from "react";
import axios from "axios";
import { LancamentoInput, LeituraCodigoFinanceiro, lerCodigoFinanceiro } from "../../api/financeiro";

export function aplicarLeituraFinanceira(
  atual: LancamentoInput, leitura: LeituraCodigoFinanceiro, vencimento: string,
): LancamentoInput {
  return {
    ...atual,
    descricao: atual.descricao || leitura.descricao_sugerida || "",
    codigo_barras: leitura.codigo_barras,
    valor: leitura.valor ?? "",
    data_vencimento: vencimento,
  };
}

type Props = {
  desabilitado: boolean;
  aplicar: (leitura: LeituraCodigoFinanceiro, vencimento: string) => void;
};

export function ResumoCodigoFinanceiro({ leitura }: { leitura: LeituraCodigoFinanceiro }) {
  return <section aria-label="Informações do código associado">
    <h3>Informações extraídas pelo leitor</h3>
    {leitura.banco_codigo && <p>Banco: <strong>{leitura.banco_nome || "Nome não disponível"} ({leitura.banco_codigo})</strong></p>}
    {leitura.segmento && <p>Segmento: <strong>{leitura.segmento}</strong></p>}
    <p>Recebedor (nome e CPF/CNPJ): não disponível no código. Preencha “Quem vai receber”.</p>
    <dl>{leitura.detalhes?.map(item => <div key={item.campo}><dt>{item.campo}</dt><dd style={{ overflowWrap: "anywhere" }}>{item.valor}</dd></div>)}</dl>
    {leitura.linha_digitavel_formatada && <p>Linha digitável: <code style={{ overflowWrap: "anywhere" }}>{leitura.linha_digitavel_formatada}</code></p>}
  </section>;
}

export default function LeitorCodigoFinanceiro({ desabilitado, aplicar }: Props) {
  const [codigo, setCodigo] = useState("");
  const [leitura, setLeitura] = useState<LeituraCodigoFinanceiro | null>(null);
  const [vencimento, setVencimento] = useState("");
  const [consultando, setConsultando] = useState(false);
  const [erro, setErro] = useState("");
  const [mensagem, setMensagem] = useState("");
  const consulta = useRef(0);
  const campo = useRef<HTMLInputElement>(null);

  async function extrair(evento: FormEvent) {
    evento.preventDefault(); // O Enter do leitor somente extrai; nunca salva o lançamento.
    if (consultando || desabilitado || !codigo.trim()) return;
    const atual = ++consulta.current;
    setConsultando(true);
    setLeitura(null);
    setVencimento("");
    setErro("");
    setMensagem("");
    try {
      const resultado = await lerCodigoFinanceiro(codigo);
      if (atual === consulta.current) setLeitura(resultado);
    } catch (falha) {
      if (atual === consulta.current) setErro(
        axios.isAxiosError(falha) && typeof falha.response?.data?.detail === "string"
          ? falha.response.data.detail : "Não foi possível ler o código. Tente novamente.",
      );
    } finally {
      if (atual === consulta.current) setConsultando(false);
    }
  }

  return <form className="card formulario leitor-financeiro" onSubmit={extrair}>
    <h2>Ler código de barras</h2>
    <p>Clique no campo e use o leitor USB em modo teclado. Enter extrai os dados. Também é possível colar a linha digitável.</p>
    <label>Código de barras ou linha digitável<input
      ref={campo} value={codigo} inputMode="numeric" autoComplete="off" maxLength={100}
      placeholder="44, 47 ou 48 dígitos" disabled={desabilitado}
      onChange={e => {
        ++consulta.current;
        setCodigo(e.target.value); setLeitura(null); setVencimento("");
        setErro(""); setMensagem(""); setConsultando(false);
      }}
    /></label>
    <div className="acoes">
      <button type="button" disabled={desabilitado} onClick={() => { campo.current?.focus(); campo.current?.select(); }}>Posicionar leitor</button>
      <button type="submit" disabled={desabilitado || consultando || !codigo.trim()}>{consultando ? "Lendo..." : "Extrair dados"}</button>
    </div>
    {erro && <p role="alert" className="erro">{erro}</p>}
    {mensagem && <p role="status">{mensagem}</p>}
    {leitura && <section aria-label="Dados extraídos do código">
      <h3>{leitura.tipo === "boleto" ? "Boleto bancário" : "Conta de arrecadação"}</h3>
      {leitura.formato_entrada && <p>Leitura: {leitura.formato_entrada} · dígitos verificadores conferidos</p>}
      {leitura.descricao_sugerida && <p>Descrição sugerida: <strong>{leitura.descricao_sugerida}</strong></p>}
      {leitura.banco_codigo && <p>Banco: <strong>{leitura.banco_nome || "Nome não disponível"} ({leitura.banco_codigo})</strong></p>}
      <p>Nome e CPF/CNPJ do recebedor não estão disponíveis apenas pelo código de barras.</p>
      {leitura.segmento && <p>Segmento: <strong>{leitura.segmento}</strong> · Identificador do emissor: {leitura.identificacao_emissor}</p>}
      <p>Valor: <strong>{leitura.valor === null ? "Preencher manualmente" : Number(leitura.valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</strong></p>
      {leitura.linha_digitavel_formatada && <label>Linha digitável<input readOnly value={leitura.linha_digitavel_formatada} onFocus={e => e.target.select()} /></label>}
      <details><summary>Mais informações do código</summary>
        <label>Código de barras normalizado<input readOnly value={leitura.codigo_barras} onFocus={e => e.target.select()} /></label>
        <dl>{leitura.detalhes?.map(item => <div key={item.campo}><dt>{item.campo}</dt><dd style={{ overflowWrap: "anywhere" }}>{item.valor}</dd></div>)}</dl>
        <p>A conferência dos dígitos não comprova a autenticidade nem a situação de pagamento do documento.</p>
      </details>
      {leitura.vencimentos_possiveis.length > 0 && <label>Vencimento impresso no boleto<select value={vencimento} onChange={e => setVencimento(e.target.value)}>
        <option value="">Confira e selecione a data</option>
        {leitura.vencimentos_possiveis.map(data => <option key={data} value={data}>{data.split("-").reverse().join("/")}</option>)}
      </select></label>}
      <ul>{leitura.avisos.map(aviso => <li key={aviso}>{aviso}</li>)}</ul>
      {leitura.lancamentos_existentes.length > 0 && <p role="alert">Este código já aparece em lançamentos: {leitura.lancamentos_existentes.map(item => `#${item.id} ${item.descricao} (${item.status})`).join("; ")}. Confira antes de cadastrar novamente.</p>}
      <button type="button" disabled={desabilitado || (leitura.vencimentos_possiveis.length > 0 && !vencimento)} onClick={() => {
        aplicar(leitura, vencimento);
        setLeitura(null); setCodigo(""); setVencimento("");
        setMensagem("Dados aplicados. Informe quem vai receber e a identificação deste boleto, por exemplo 1 de 4. Confira o valor e o vencimento antes de salvar.");
      }}>Aplicar ao lançamento</button>
    </section>}
  </form>;
}
