import { FormEvent, useEffect, useRef, useState } from "react";
import { ContratoComercial } from "../../api/contratosComerciais";
import { PosicaoSaldo } from "../../api/producaoSaldos";
import { alterarLancamentoVenda, AlvoEdicaoVenda } from "../../api/vendas";
import { quantidadeContrato } from "../CadastrosAgricolas/ContratosComerciais";

type Props = {
  alvo: AlvoEdicaoVenda; contratos: ContratoComercial[]; posicoes: PosicaoSaldo[];
  erroOperacao: string; processando: boolean; fechar: () => void;
  executar: (assinatura: string, acao: (chave: string) => Promise<unknown>, mensagem: string) => Promise<boolean>;
};

export default function EditorLancamentoVenda({ alvo, contratos, posicoes, processando, fechar, executar, erroOperacao }: Props) {
  const dialogo = useRef<HTMLDialogElement>(null);
  const venda = alvo.venda;
  const movimento = alvo.movimento;
  const [motivo, setMotivo] = useState("");
  const [erro, setErro] = useState("");
  const [form, setForm] = useState({
    contrato: venda.contrato || 0, posicao: venda.posicao, cliente_nome: venda.cliente_nome,
    quantidade_kg: Number(movimento?.quantidade_kg ?? venda.quantidade_kg).toLocaleString("pt-BR", { maximumFractionDigits: 3 }),
    data_contrato: venda.data_contrato, data_limite_entrega: venda.data_limite_entrega || "",
    observacoes: movimento?.observacoes ?? venda.observacoes,
    data_movimento: movimento?.data_entrega || movimento?.data_devolucao || venda.data_contrato,
    destino: movimento?.destino || "", placa: movimento?.placa || "", motorista: movimento?.motorista || "",
    nota_produtor: movimento?.nota_produtor || "", nota_empresa: movimento?.nota_empresa || "",
    referencia_externa: movimento?.referencia_externa || "",
  });
  useEffect(() => { dialogo.current?.showModal(); }, []);
  function campo(nome: keyof typeof form, valor: string) { setForm({ ...form, [nome]: valor }); }
  async function salvar(evento: FormEvent) {
    evento.preventDefault(); setErro("");
    let dados: Record<string, unknown> = { motivo };
    try {
      if (!alvo.excluir) {
        dados = { ...dados, quantidade_kg: quantidadeContrato(form.quantidade_kg), observacoes: form.observacoes };
        if (alvo.natureza === "venda") dados = { ...dados, ...(form.contrato ? { contrato: Number(form.contrato) } : { cliente_nome: form.cliente_nome }), posicao: Number(form.posicao), data_contrato: form.data_contrato, data_limite_entrega: form.data_limite_entrega || null };
        else dados = { ...dados, data_movimento: form.data_movimento, referencia_externa: form.referencia_externa, ...(alvo.natureza === "entrega" ? { destino: form.destino, placa: form.placa, motorista: form.motorista, nota_produtor: form.nota_produtor, nota_empresa: form.nota_empresa } : {}) };
      }
      const ok = await executar(JSON.stringify([alvo.venda.id, alvo.venda.versao, alvo.natureza, alvo.movimento?.id, alvo.excluir, dados]), chave => alterarLancamentoVenda(alvo, dados, chave), alvo.excluir ? "Lançamento excluído; histórico preservado e saldos ajustados." : "Lançamento corrigido e saldos atualizados.");
      if (ok) fechar();
    } catch (falha) { setErro(falha instanceof Error ? falha.message : "Revise os dados."); }
  }
  return <dialog ref={dialogo} className="editor-venda card" aria-labelledby="titulo-editor-venda" onCancel={e => { e.preventDefault(); if (!processando) fechar(); }}>
    <h3 id="titulo-editor-venda">{alvo.excluir ? "Excluir" : "Editar"} {alvo.natureza} · {venda.numero_contrato || "Sem contrato"} / {venda.cliente_nome}</h3>
    {(erro || erroOperacao) && <p className="erro" role="alert">{erro || erroOperacao}</p>}
    <p>{alvo.excluir ? "A exclusão preserva o histórico e desfaz os efeitos deste lançamento no estoque. Uma venda excluída também terá suas entregas e devoluções estornadas." : "A correção preserva a versão anterior e ajusta os saldos. Alterações incompatíveis com movimentos posteriores serão bloqueadas."}</p>
    <form className="formulario" onSubmit={salvar}><fieldset disabled={processando}>
      {!alvo.excluir && <>
        {alvo.natureza === "venda" ? <>
          <label>Contrato / empresa<select value={form.contrato} onChange={e => setForm({ ...form, contrato: Number(e.target.value) })}><option value={0} disabled={Boolean(venda.contrato)}>{venda.numero_contrato ? `Contrato histórico: ${venda.numero_contrato}` : "Sem contrato"}</option>{contratos.filter(c => c.ativo || c.id === venda.contrato).map(c => <option key={c.id} value={c.id}>{c.numero} · {c.empresa} · {c.produto}{!c.ativo ? " (inativo)" : ""}</option>)}</select></label>
          {!form.contrato && <label>Comprador / empresa<input required maxLength={160} value={form.cliente_nome} onChange={e => campo("cliente_nome", e.target.value)} /></label>}
          <label>Posição oficial<select required value={form.posicao} onChange={e => campo("posicao", e.target.value)}>{posicoes.map(p => <option key={p.id} value={p.id}>{p.propriedade_nome || "Histórica"} · {p.cad_pro_codigo} · {p.cultura} · {p.safra} · {p.armazem_nome}</option>)}</select></label>
          <label>Data do contrato<input required type="date" value={form.data_contrato} onChange={e => campo("data_contrato", e.target.value)} /></label>
          <label>Limite de entrega<input type="date" value={form.data_limite_entrega} onChange={e => campo("data_limite_entrega", e.target.value)} /></label>
        </> : <label>Data do lançamento<input required type="date" value={form.data_movimento} onChange={e => campo("data_movimento", e.target.value)} /></label>}
        <label>{alvo.natureza === "entrega" ? "Peso líquido (kg)" : "Quantidade (kg)"}<input required inputMode="decimal" value={form.quantidade_kg} onChange={e => campo("quantidade_kg", e.target.value)} /></label>
        {alvo.natureza === "entrega" && <><label>Destino<input maxLength={160} value={form.destino} onChange={e => campo("destino", e.target.value)} /></label><label>Placa<input maxLength={12} value={form.placa} onChange={e => campo("placa", e.target.value)} /></label><label>Motorista<input maxLength={160} value={form.motorista} onChange={e => campo("motorista", e.target.value)} /></label><label>Nº nota produtor<input maxLength={80} value={form.nota_produtor} onChange={e => campo("nota_produtor", e.target.value)} /></label><label>Nº nota empresa<input maxLength={80} value={form.nota_empresa} onChange={e => campo("nota_empresa", e.target.value)} /></label></>}
        {alvo.natureza !== "venda" && <><label>CAD/PRO<input readOnly value={venda.cad_pro_codigo} /></label><label>Nº do contrato<input readOnly value={venda.numero_contrato || "Sem contrato"} /></label></>}
        {alvo.natureza !== "venda" && <label>Referência externa<input maxLength={120} value={form.referencia_externa} onChange={e => campo("referencia_externa", e.target.value)} /></label>}
        <label>Observações<textarea value={form.observacoes} onChange={e => campo("observacoes", e.target.value)} /></label>
      </>}
      <label>Motivo da {alvo.excluir ? "exclusão" : "correção"}<textarea required maxLength={500} value={motivo} onChange={e => setMotivo(e.target.value)} /></label>
      <div className="acoes"><button type="submit" className={alvo.excluir ? "perigo" : ""}>{alvo.excluir ? "Confirmar exclusão" : "Salvar correção"}</button><button type="button" className="secundario" onClick={fechar}>Cancelar</button></div>
    </fieldset></form>
  </dialog>;
}
