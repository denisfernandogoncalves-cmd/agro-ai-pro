import { FormEvent, useEffect, useRef, useState } from "react";
import axios from "axios";
import { atualizarLancamento, EdicaoLancamento, LancamentoFinanceiro } from "../../api/financeiro";

type Props = { item: LancamentoFinanceiro; onFechar: () => void; onSalvo: () => void };

export default function EditorLancamento({ item, onFechar, onSalvo }: Props) {
  const dialogo = useRef<HTMLDialogElement>(null);
  const trava = useRef(false);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState("");
  const [dados, setDados] = useState<EdicaoLancamento>({
    descricao: item.descricao, recebedor_nome: item.recebedor_nome,
    valor: item.valor, data_emissao: item.data_emissao,
    data_vencimento: item.data_vencimento, observacoes: item.observacoes,
    codigo_barras: item.codigo_barras,
  });
  useEffect(() => {
    const elemento = dialogo.current;
    elemento?.showModal();
    return () => elemento?.close();
  }, []);

  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    if (trava.current) return;
    trava.current = true; setOcupado(true); setErro("");
    try {
      await atualizarLancamento(item.id, dados);
      onSalvo();
    } catch (falha) {
      const resposta = axios.isAxiosError(falha) ? falha.response?.data : null;
      setErro(resposta && typeof resposta === "object" ? Object.values(resposta).flat().join(" ") : "Não foi possível salvar o lançamento. Tente novamente.");
    } finally { trava.current = false; setOcupado(false); }
  }

  return <dialog ref={dialogo} className="card editor-lancamento" aria-labelledby="titulo-editor-lancamento" onCancel={e => { e.preventDefault(); if (!trava.current) onFechar(); }}>
    <form onSubmit={salvar}>
      <h2 id="titulo-editor-lancamento">Editar lançamento</h2>
      <p>Altere os dados deste lançamento. Os demais boletos da compra permanecem como estão.</p>
      {item.status === "liquidado" && <p className="aviso-contexto">Este lançamento já foi liquidado. O valor pago/recebido de {Number(item.valor_liquidado).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })} e a data da liquidação serão preservados.</p>}
      {erro && <p className="erro" role="alert">{erro}</p>}
      <fieldset disabled={ocupado}>
        <label>Descrição<input autoFocus required maxLength={220} value={dados.descricao} onChange={e => setDados({ ...dados, descricao: e.target.value })} /></label>
        <label>Quem recebe / parceiro<input maxLength={160} value={dados.recebedor_nome} onChange={e => setDados({ ...dados, recebedor_nome: e.target.value })} /></label>
        <label>Valor do lançamento<input required type="number" min="0.01" max="999999999999.99" step="0.01" value={dados.valor} onChange={e => setDados({ ...dados, valor: e.target.value })} /></label>
        <div className="linha">
          <label>Emissão<input required type="date" value={dados.data_emissao} onChange={e => setDados({ ...dados, data_emissao: e.target.value })} /></label>
          <label>Vencimento<input required type="date" value={dados.data_vencimento} onChange={e => setDados({ ...dados, data_vencimento: e.target.value })} /></label>
        </div>
        <label>Código de barras / linha digitável<input maxLength={100} value={dados.codigo_barras} onChange={e => setDados({ ...dados, codigo_barras: e.target.value })} /></label>
        <label>Observações<textarea value={dados.observacoes} onChange={e => setDados({ ...dados, observacoes: e.target.value })} /></label>
        <div className="acoes"><button type="submit">{ocupado ? "Salvando..." : "Salvar alterações"}</button><button type="button" className="secundario" onClick={onFechar}>Cancelar edição</button></div>
      </fieldset>
    </form>
  </dialog>;
}
