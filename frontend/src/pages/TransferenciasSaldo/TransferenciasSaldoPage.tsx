import axios from "axios";
import FiltrosRapidos, { correspondeFiltrosRapidos, filtrosRapidosVazios } from "../../components/FiltrosRapidos";
import { useAlteracoesNaoSalvas } from "../../components/AlteracoesNaoSalvas";
import { useConfirmacaoCompacta } from "../../components/ConfirmacaoCompacta";
import { BotaoAcao, useAcoes } from "../../components/AcoesContext";
import { FormEvent, useEffect, useRef, useState } from "react";
import { carregarTransferenciasSaldo, transferirSaldo, alterarTransferenciaSaldo, excluirTransferenciaSaldo } from "../../api/transferenciasSaldo";
import { MovimentacaoSaldo, PosicaoSaldo } from "../../api/producaoSaldos";
import { CADPro } from "../../api/cargasColhidas";
import { Propriedade } from "../../api/propriedades";
import { quantidadeContrato } from "../CadastrosAgricolas/ContratosComerciais";

type Dados = Awaited<ReturnType<typeof carregarTransferenciasSaldo>>;
type PropriedadeResumo = Pick<Propriedade, "id" | "nome" | "proprietario">;
const vazio = { cultura: "", safra: "", posicao_origem: 0, posicao_destino: "", quantidade_kg: "", data_movimento: new Date().toISOString().slice(0, 10), referencia_externa: "", observacoes: "" };
const kg = (valor: string | number) => `${Number(valor).toLocaleString("pt-BR", { maximumFractionDigits: 3 })} kg`;

function propriedadeDaPosicao(posicao: Pick<PosicaoSaldo, "propriedade_id" | "propriedade_nome">, propriedades: PropriedadeResumo[]) {
  const cadastro = propriedades.find(item => item.id === posicao.propriedade_id);
  return {
    nome: cadastro?.nome || posicao.propriedade_nome || (posicao.propriedade_id ? `Propriedade #${posicao.propriedade_id}` : "Produção histórica"),
    proprietario: cadastro?.proprietario?.trim() || "Proprietário não informado",
  };
}

export function rotuloPosicaoTransferencia(posicao: PosicaoSaldo, propriedades: PropriedadeResumo[] = []) {
  const propriedade = propriedadeDaPosicao(posicao, propriedades);
  return `${propriedade.nome} / CAD/PRO ${posicao.cad_pro_codigo} / ${propriedade.proprietario} · ${posicao.classificacao_codigo} · ${posicao.armazem_nome}`;
}

export function culturasTransferencia(posicoes: PosicaoSaldo[]) {
  return Array.from(new Set(posicoes.filter(posicao => Number(posicao.saldo_disponivel_kg) > 0).map(posicao => posicao.cultura)))
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b, "pt-BR"));
}

export function safrasTransferencia(posicoes: PosicaoSaldo[], cultura: string) {
  return Array.from(new Set(posicoes
    .filter(posicao => Number(posicao.saldo_disponivel_kg) > 0 && posicao.cultura === cultura)
    .map(posicao => posicao.safra)))
    .filter(Boolean)
    .sort((a, b) => b.localeCompare(a, "pt-BR", { numeric: true }));
}

export function opcoesPosicaoTransferencia(posicoes: PosicaoSaldo[], propriedades: PropriedadeResumo[] = [], exigirSaldo = false) {
  return posicoes
    .filter(posicao => !exigirSaldo || Number(posicao.saldo_disponivel_kg) > 0)
    .map(posicao => ({ chave: posicao.id, posicao, rotulo: rotuloPosicaoTransferencia(posicao, propriedades) }))
    .sort((a, b) => a.rotulo.localeCompare(b.rotulo, "pt-BR"));
}

export function posicaoDestinoCompativel(origem: PosicaoSaldo, destino: PosicaoSaldo) {
  return destino.id !== origem.id
    && destino.cultura === origem.cultura
    && destino.safra === origem.safra
    && destino.classificacao_codigo === origem.classificacao_codigo;
}

export function destinosTransferencia(origem: PosicaoSaldo, posicoes: PosicaoSaldo[], propriedades: PropriedadeResumo[], cadpros: CADPro[]) {
  const ativos = (posicao: PosicaoSaldo) => cadpros.some(cad => cad.ativo && cad.id === posicao.cad_pro && cad.propriedades.includes(posicao.propriedade_id ?? 0));
  const destinos = opcoesPosicaoTransferencia(posicoes.filter(item => posicaoDestinoCompativel(origem, item) && ativos(item)), propriedades)
    .map(item => ({ ...item, chave: `posicao:${item.chave}` }));
  for (const cad of cadpros.filter(item => item.ativo)) {
    for (const propriedade of propriedades.filter(item => cad.propriedades.includes(item.id))) {
      if (cad.id === origem.cad_pro && propriedade.id === origem.propriedade_id) continue;
      if (destinos.some(item => item.posicao.cad_pro === cad.id && item.posicao.propriedade_id === propriedade.id && item.posicao.armazem === origem.armazem)) continue;
      const posicao: PosicaoSaldo = { ...origem, id: 0, cad_pro: cad.id, cad_pro_codigo: cad.codigo,
        propriedade_id: propriedade.id, propriedade_nome: propriedade.nome,
        saldo_fisico_kg: "0", saldo_comprometido_kg: "0", saldo_disponivel_kg: "0", versao: 0 };
      destinos.push({ chave: `cadastro:${propriedade.id}:${cad.id}`, posicao, rotulo: rotuloPosicaoTransferencia(posicao, propriedades) });
    }
  }
  return destinos.sort((a, b) => a.rotulo.localeCompare(b.rotulo, "pt-BR"));
}

export function agruparHistoricoTransferencias(movimentos: MovimentacaoSaldo[]) {
  return Array.from(new Set(movimentos.map(item => item.origem_chave_idempotencia))).map(chave => ({
    chave,
    saida: movimentos.find(item => item.origem_chave_idempotencia === chave && item.operacao === "transferencia_saida"),
    entrada: movimentos.find(item => item.origem_chave_idempotencia === chave && item.operacao === "transferencia_entrada"),
  }));
}

type HistoricoTransferencia = ReturnType<typeof agruparHistoricoTransferencias>[number];
export function transferenciaCorrespondeBusca(item: HistoricoTransferencia, busca: string, propriedades: PropriedadeResumo[]) {
  const termo = busca.trim().toLocaleLowerCase("pt-BR");
  const numero = termo.match(/^(?:transfer[eê]ncia\s*)?#?(\d+)$/);
  if (numero && [item.saida?.id, item.entrada?.id].includes(Number(numero[1]))) return true;
  if (numero && /^(?:transfer|#)/.test(termo)) return false;
  return !termo || [item.saida, item.entrada].some(m => m && [nomePropriedadeTransferencia(m, propriedades), m.cad_pro_codigo, m.cultura, m.safra, m.referencia_externa, m.observacoes].join(" ").toLocaleLowerCase("pt-BR").includes(termo));
}
export function previaSaldoTransferencia(posicoes: PosicaoSaldo[], original: HistoricoTransferencia | null, origem: PosicaoSaldo, destino: PosicaoSaldo, quantidade: number) {
  const afetadas = new Map<string, { posicao: PosicaoSaldo; delta: number }>();
  const somar = (p: PosicaoSaldo | undefined, delta: number) => {
    if (!p) return;
    const chave = p.id ? String(p.id) : `nova:${p.propriedade_id}:${p.cad_pro}:${p.armazem}:${p.cultura}:${p.safra}:${p.classificacao_codigo}`;
    const item = afetadas.get(chave) || {posicao:p,delta:0}; item.delta += delta; afetadas.set(chave,item);
  };
  somar(posicoes.find(p => p.id === original?.saida?.posicao), Number(original?.saida?.quantidade_kg || 0));
  somar(posicoes.find(p => p.id === original?.entrada?.posicao), -Number(original?.entrada?.quantidade_kg || 0));
  somar(posicoes.find(p => p.id === origem.id) || origem, -quantidade);
  somar(posicoes.find(p => p.id === destino.id) || destino, quantidade);
  return [...afetadas.values()].map(({posicao,delta}) => ({posicao, anterior:Number(posicao.saldo_fisico_kg), posterior:Math.round((Number(posicao.saldo_fisico_kg)+delta)*1000)/1000, disponivel:Math.round((Number(posicao.saldo_disponivel_kg)+delta)*1000)/1000}));
}

export function statusTransferencia(item: HistoricoTransferencia) {
  if (item.saida?.correcao_transferencia?.acao === "editar") return "Editada";
  if (item.saida?.correcao_transferencia?.acao === "excluir") return "Excluída";
  return item.saida?.estornado || item.entrada?.estornado ? "Estornada" : "Ativa";
}
export function saldosAntesTransferencia(posicoes: PosicaoSaldo[], item: HistoricoTransferencia | null) {
  if (!item) return posicoes;
  return posicoes.map(posicao => {
    const delta = (posicao.id === item.saida?.posicao ? Number(item.saida.quantidade_kg) : 0)
      - (posicao.id === item.entrada?.posicao ? Number(item.entrada.quantidade_kg) : 0);
    return { ...posicao, saldo_fisico_kg: String(Number(posicao.saldo_fisico_kg) + delta),
      saldo_disponivel_kg: String(Number(posicao.saldo_disponivel_kg) + delta) };
  });
}

function dataBR(valor?: string) {
  const [ano, mes, dia] = (valor || "").slice(0, 10).split("-");
  return ano && mes && dia ? `${dia}/${mes}/${ano}` : "—";
}

export function numeroPlanilhaTransferencia(valor: string | number) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  });
}

export function nomePropriedadeTransferencia(
  movimento: MovimentacaoSaldo | undefined,
  propriedades: PropriedadeResumo[],
) {
  return propriedades.find(item => item.id === movimento?.propriedade_id)?.nome
    || (movimento?.propriedade_id ? `Propriedade #${movimento.propriedade_id}` : "Produção histórica");
}

export function TabelaImpressaoTransferencias({
  historico,
  propriedades,
}: {
  historico: HistoricoTransferencia[];
  propriedades: PropriedadeResumo[];
}) {
  const quantidadeTotal = historico.filter(item => statusTransferencia(item) === "Ativa").reduce((total, item) => total + Number(
    (item.saida || item.entrada)?.quantidade_kg || 0,
  ), 0);
  return <div className="tabela-responsiva"><table className="tabela-relatorio tabela-controle transferencias-planilha">
    <caption>Transferências registradas e total das linhas impressas</caption>
    <thead><tr><th>Data</th><th>Origem</th><th>Destino</th><th>Produto / safra</th><th>Quantidade (kg)</th><th>Referência / documento</th><th>Observações</th><th>Registro</th><th>Situação</th></tr></thead>
    <tbody>{historico.length ? historico.map(item => { const movimento = item.saida || item.entrada; return <tr key={`transferencia-impressao-${item.chave}`}><td>{dataBR(movimento?.data_movimento)}</td><td><strong>{nomePropriedadeTransferencia(item.saida, propriedades)}</strong><small>CAD/PRO {item.saida?.cad_pro_codigo || "—"} · {item.saida?.armazem_nome || "—"}</small></td><td><strong>{nomePropriedadeTransferencia(item.entrada, propriedades)}</strong><small>CAD/PRO {item.entrada?.cad_pro_codigo || "—"} · {item.entrada?.armazem_nome || "—"}</small></td><td>{movimento?.cultura || "—"}<small>{movimento?.safra || "—"} · {movimento?.classificacao_codigo || "—"}</small></td><td><strong>{numeroPlanilhaTransferencia(movimento?.quantidade_kg || 0)}</strong></td><td>{movimento?.referencia_externa || "—"}</td><td>{movimento?.observacoes || "—"}</td><td>{movimento?.criado_por_nome || "—"}<small>{movimento?.criado_em ? new Date(movimento.criado_em).toLocaleString("pt-BR") : "—"}</small></td><td>{statusTransferencia(item)}</td></tr>; }) : <tr><td colSpan={9}>Nenhuma transferência registrada.</td></tr>}</tbody>
    {historico.length > 0 && <tfoot><tr><td><strong>TOTAL</strong><small>Total das linhas impressas ativas</small></td><td>—</td><td>—</td><td>—</td><td><strong>{numeroPlanilhaTransferencia(quantidadeTotal)}</strong></td><td>—</td><td>—</td><td>—</td><td>Ativas</td></tr></tfoot>}
  </table></div>;
}

function mensagem(falha: unknown) {
  if (axios.isAxiosError(falha) && falha.response?.data) {
    const dados = falha.response.data;
    return typeof dados.detail === "string" ? dados.detail : typeof dados.mensagem === "string" ? dados.mensagem : Object.values(dados).flat(2).join(" ");
  }
  return falha instanceof Error ? falha.message : "Não foi possível transferir o saldo.";
}

export default function TransferenciasSaldoPage() {
  const confirmar = useConfirmacaoCompacta();
  const pode = useAcoes();
  const editorRef = useRef<HTMLFormElement>(null);
  const exclusaoRef = useRef<HTMLFormElement>(null);
  const [editando, setEditando] = useState<HistoricoTransferencia | null>(null);
  const [excluindo, setExcluindo] = useState<HistoricoTransferencia | null>(null);
  const [motivo, setMotivo] = useState("");
  const [mostrarHistorico, setMostrarHistorico] = useState(false);
  const [dados, setDados] = useState<Dados>();
  const [form, setForm] = useState(vazio);
  const protecao = useAlteracoesNaoSalvas({form,motivo}, "Transferência", editando?.saida?.id || (excluindo ? `excluir:${excluindo.saida?.id}` : null));
  const [busca, setBusca] = useState("");
  const [filtrosRapidos, setFiltrosRapidos] = useState(filtrosRapidosVazios);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [carregando, setCarregando] = useState(true);
  const trava = useRef(false);
  const tentativa = useRef<{ assinatura: string; chave: string } | null>(null);

  async function carregar() {
    setCarregando(true);
    try { setDados(await carregarTransferenciasSaldo()); }
    catch (falha) { setErro(mensagem(falha)); }
    finally { setCarregando(false); }
  }
  useEffect(() => { void carregar(); }, []);
  useEffect(() => { if (editando) editorRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }); if (excluindo) exclusaoRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }); }, [editando, excluindo]);

  const posicoes = saldosAntesTransferencia(dados?.posicoes || [], editando);
  const propriedades = dados?.propriedades || [];
  const culturas = culturasTransferencia(posicoes);
  const safras = safrasTransferencia(posicoes, form.cultura);
  const posicoesDaSafra = form.cultura && form.safra
    ? posicoes.filter(item => item.cultura === form.cultura && item.safra === form.safra)
    : [];
  const origens = opcoesPosicaoTransferencia(posicoesDaSafra, propriedades, true);
  const origem = posicoes.find(item => item.id === form.posicao_origem);
  const destinos = origem ? destinosTransferencia(origem, posicoesDaSafra, propriedades, dados?.cadpros || []) : [];
  const destino = destinos.find(item => item.chave === form.posicao_destino)?.posicao;
  let quantidadePrevia = 0;
  try { quantidadePrevia = Number(quantidadeContrato(form.quantidade_kg)); } catch { /* Campo ainda incompleto. */ }
  const previaSaldos = origem && destino && quantidadePrevia > 0 ? previaSaldoTransferencia(dados?.posicoes || [], editando, origem, destino, quantidadePrevia) : [];
  const bloqueio = ocupado ? "Aguarde a operação em andamento." : carregando ? "Aguarde o carregamento dos saldos." : !form.cultura ? "Selecione a cultura." : !form.safra ? "Selecione a safra." : !origem ? "Selecione uma origem com saldo disponível." : !destino ? "Selecione o destino." : !quantidadePrevia ? "Informe uma quantidade maior que zero." : previaSaldos.some(p => p.posterior < 0 || p.disponivel < 0) ? "A operação deixaria uma posição sem saldo físico ou disponível. Reveja a quantidade e os lançamentos posteriores." : editando && !motivo.trim() ? "Informe o motivo da edição." : "";

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (trava.current) return;
    setErro(""); setSucesso("");
    try {
      if (editando && !motivo.trim()) throw new Error("Informe o motivo da edição.");
      if (!form.cultura || !form.safra) throw new Error("Selecione a cultura e o ano/safra.");
      if (!origem || !destino || !posicaoDestinoCompativel(origem, destino)) throw new Error("Selecione posições diferentes com cultura, safra e classificação iguais.");
      const quantidade = quantidadeContrato(form.quantidade_kg);
      if (Number(quantidade) > Number(origem.saldo_disponivel_kg)) throw new Error("Quantidade superior ao saldo disponível na origem.");
      if (!(await confirmar({titulo:editando ? "Salvar correção da transferência" : "Confirmar transferência", mensagem:`Transferir ${kg(quantidade)} de ${form.cultura}, safra ${form.safra}, de ${rotuloPosicaoTransferencia(origem, propriedades)} para ${rotuloPosicaoTransferencia(destino, propriedades)}? O débito e o crédito serão registrados juntos.`}))) return;
      trava.current = true; setOcupado(true);
      const payload = { posicao_origem: origem.id, ...(destino.id ? { posicao_destino: destino.id } : { propriedade_destino: destino.propriedade_id!, cad_pro_destino: destino.cad_pro }), quantidade_kg: quantidade, data_movimento: form.data_movimento, referencia_externa: form.referencia_externa, observacoes: form.observacoes };
      const assinatura = JSON.stringify([editando?.saida?.id, motivo, payload]);
      if (tentativa.current?.assinatura !== assinatura) tentativa.current = { assinatura, chave: `transferencia-ui:${crypto.randomUUID()}` };
      if (editando?.saida) await alterarTransferenciaSaldo(editando.saida.id, { ...payload, motivo: motivo.trim(), chave_idempotencia: tentativa.current.chave });
      else await transferirSaldo({ ...payload, chave_idempotencia: tentativa.current.chave });
      tentativa.current = null; setForm(vazio); setEditando(null); setMotivo(""); protecao.marcarSalvo({form:vazio,motivo:""}); setSucesso(editando ? "Transferência corrigida nas duas posições. O original foi preservado no histórico." : "Transferência registrada nas duas posições oficiais. O saldo total foi preservado.");
      await carregar();
    } catch (falha) { setErro(mensagem(falha)); }
    finally { trava.current = false; setOcupado(false); }
  }

  async function iniciarEdicao(item: HistoricoTransferencia) {
    if (!(await protecao.confirmarDescarte())) return;
    const origem = dados?.posicoes.find(p => p.id === item.saida?.posicao);
    if (!origem || !item.saida || !item.entrada) { setErro("Atualize a lista para localizar as posições da transferência."); return; }
    setEditando(item); setExcluindo(null); setMotivo(""); setErro(""); setSucesso(""); tentativa.current = null;
    setForm({ cultura: origem.cultura, safra: origem.safra, posicao_origem: origem.id,
      posicao_destino: `posicao:${item.entrada.posicao}`, quantidade_kg: numeroPlanilhaTransferencia(item.saida.quantidade_kg),
      data_movimento: item.saida.data_movimento, referencia_externa: item.saida.referencia_externa || "", observacoes: item.saida.observacoes || "" });
  }
  function cancelarCorrecao() { setEditando(null); setExcluindo(null); setMotivo(""); setForm(vazio); protecao.marcarSalvo({form:vazio,motivo:""}); tentativa.current = null; }
  async function confirmarExclusao(evento: FormEvent) {
    evento.preventDefault();
    if (!excluindo?.saida || trava.current || !motivo.trim()) return;
    if (!(await confirmar({titulo:"Excluir transferência", perigo:true, confirmar:"Excluir", mensagem:`Excluir a transferência de ${kg(excluindo.saida.quantidade_kg)}? O saldo retornará à origem e será retirado do destino.`}))) return;
    trava.current = true; setOcupado(true); setErro(""); setSucesso("");
    const assinatura = JSON.stringify(["excluir", excluindo.saida.id, motivo.trim()]);
    if (tentativa.current?.assinatura !== assinatura) tentativa.current = { assinatura, chave: `transferencia-ui:${crypto.randomUUID()}` };
    try { await excluirTransferenciaSaldo(excluindo.saida.id, motivo.trim(), tentativa.current.chave); cancelarCorrecao(); setSucesso("Transferência excluída. O saldo voltou à origem; o registro original permanece no histórico."); await carregar(); }
    catch (falha) { setErro(mensagem(falha)); }
    finally { trava.current = false; setOcupado(false); }
  }

  const historicoCompleto = agruparHistoricoTransferencias(dados?.movimentos || []);
  const historico = historicoCompleto.filter(item => (mostrarHistorico || statusTransferencia(item) === "Ativa") && transferenciaCorrespondeBusca(item,busca,propriedades) && correspondeFiltrosRapidos(filtrosRapidos,(item.saida || item.entrada)?.cultura || "",(item.saida || item.entrada)?.safra || "",[item.saida?.propriedade_id || 0,item.entrada?.propriedade_id || 0]));
  const movimentosHistorico = historico.map(item => item.saida || item.entrada).filter(Boolean) as MovimentacaoSaldo[];
  const propriedadesImpressao = [...new Set(historico.flatMap(item => [
    nomePropriedadeTransferencia(item.saida, propriedades),
    nomePropriedadeTransferencia(item.entrada, propriedades),
  ]))];
  const cadprosImpressao = [...new Set(historico.flatMap(item => [
    item.saida?.cad_pro_codigo,
    item.entrada?.cad_pro_codigo,
  ]).filter((codigo): codigo is string => Boolean(codigo)))];
  const culturasImpressao = [...new Set(movimentosHistorico.map(item => item.cultura))];
  const safrasImpressao = [...new Set(movimentosHistorico.map(item => item.safra))];
  const quantidadeImpressao = historico.filter(item => statusTransferencia(item) === "Ativa").reduce((total, item) => total + Number(
    (item.saida || item.entrada)?.quantidade_kg || 0,
  ), 0);

  return <section className="modulo-producao-saldos modulo-transferencias-saldo">
    <h2>Transferência de saldo entre CAD/PROs</h2>
    <p>Selecione a cultura e o ano/safra e, em seguida, as propriedades e os CAD/PROs de origem e destino. O destino pode receber saldo mesmo sem colheita dessa cultura. Para um novo saldo, serão mantidos a safra, a classificação e o armazém da origem; débito e crédito ficam vinculados no histórico.</p>
    {erro && <p className="erro card" role="alert">{erro}</p>}{sucesso && <p className="sucesso card" role="status">{sucesso}</p>}
    <section className="card controle-planilha controle-planilha-impressao controle-planilha-transferencias somente-impressao" hidden={carregando}>
      <h2 className="somente-impressao titulo-impressao-planilha">Transferência de saldo</h2>
      <div className="controle-planilha-titulo"><div><span className="kicker">Controle de transferências entre posições</span><h3>{propriedadesImpressao.join(" · ") || "Todas as propriedades"}</h3><p>CAD/PRO {cadprosImpressao.join(", ") || "—"} · {culturasImpressao.join(", ") || "todas as culturas"} · safra {safrasImpressao.join(", ") || "todas"}</p></div><div className="controle-planilha-total"><span>Total transferido</span><strong>{numeroPlanilhaTransferencia(quantidadeImpressao)} kg</strong><small>{numeroPlanilhaTransferencia(quantidadeImpressao / 60)} sacas de 60 kg</small></div></div>
      <TabelaImpressaoTransferencias historico={historico} propriedades={propriedades} />
    </section>
    {(editando ? pode("editar") : pode("cadastrar")) && <form ref={editorRef} className="card formulario transferencia-saldo" onSubmit={enviar}><fieldset disabled={ocupado || carregando}>
      <h3>{editando ? "Editar transferência" : "Nova transferência"}</h3>{editando && erro && <p className="erro" role="alert">{erro}</p>}
      {editando && <><p>A correção estorna a transferência original e registra a nova. Os saldos abaixo consideram a devolução do lançamento original.</p><label>Motivo da edição<textarea required maxLength={500} value={motivo} onChange={e => setMotivo(e.target.value)} /></label></>}
      <div className="linha"><label>Cultura<select required value={form.cultura} onChange={e => setForm({ ...form, cultura: e.target.value, safra: "", posicao_origem: 0, posicao_destino: "" })}><option value="">Selecione a cultura</option>{culturas.map(cultura => <option key={cultura} value={cultura}>{cultura}</option>)}</select></label><label>Ano / safra<select required disabled={!form.cultura} value={form.safra} onChange={e => setForm({ ...form, safra: e.target.value, posicao_origem: 0, posicao_destino: "" })}><option value="">{form.cultura ? "Selecione o ano / safra" : "Selecione primeiro a cultura"}</option>{safras.map(safra => <option key={safra} value={safra}>{safra}</option>)}</select></label></div>
      <div className="linha"><label>Propriedade / CAD/PRO de origem / Proprietário<select required disabled={!form.safra} value={form.posicao_origem || ""} onChange={e => setForm({ ...form, posicao_origem: Number(e.target.value), posicao_destino: "" })}><option value="">{form.safra ? "Selecione a propriedade e o CAD/PRO" : "Selecione primeiro a cultura e o ano / safra"}</option>{origens.map(opcao => <option key={opcao.chave} value={opcao.chave}>{opcao.rotulo}</option>)}</select></label><label>Propriedade / CAD/PRO de destino / Proprietário<select required disabled={!origem} value={form.posicao_destino || ""} onChange={e => setForm({ ...form, posicao_destino: e.target.value })}><option value="">{origem ? "Selecione a propriedade e o CAD/PRO" : "Selecione primeiro a origem"}</option>{destinos.map(opcao => <option key={opcao.chave} value={opcao.chave}>{opcao.rotulo}</option>)}</select></label></div>
      {origem && !destinos.length && <p role="status">Não há outra propriedade com CAD/PRO ativo vinculado para receber o saldo.</p>}
      <div className="linha"><p>Disponível na origem: <strong>{kg(origem?.saldo_disponivel_kg || "0")}</strong></p><p>Físico no destino: <strong>{kg(destino?.saldo_fisico_kg || "0")}</strong></p></div>
      <div className="linha"><label>Quantidade (kg)<input required inputMode="decimal" placeholder="Ex.: 1.000,500" value={form.quantidade_kg} onChange={e => setForm({ ...form, quantidade_kg: e.target.value })} /></label><label>Data<input required type="date" value={form.data_movimento} onChange={e => setForm({ ...form, data_movimento: e.target.value })} /></label></div>
      {editando && <div className="comparacao-edicao"><span>Quantidade atual <strong>{kg(editando.saida?.quantidade_kg || 0)}</strong></span><span>Nova quantidade <strong>{kg(quantidadePrevia)}</strong></span></div>}
      {!!previaSaldos.length && <div className="previa-edicao"><h4>Saldos antes e depois · prévia sem lançamento</h4>{previaSaldos.map((p,i) => <div className="comparacao-edicao" key={i}><span>{p.posicao.propriedade_nome || "Posição histórica"} · CAD/PRO {p.posicao.cad_pro_codigo}<strong>Atual: {kg(p.anterior)}</strong></span><span>Após confirmar<strong>{kg(p.posterior)}</strong><small>Disponível: {kg(p.disponivel)}</small></span></div>)}<small>O servidor confere novamente os saldos, reservas e compatibilidade ao confirmar.</small></div>}
      <label>Referência / documento<input maxLength={160} value={form.referencia_externa} onChange={e => setForm({ ...form, referencia_externa: e.target.value })} /></label><label>Observações<textarea value={form.observacoes} onChange={e => setForm({ ...form, observacoes: e.target.value })} /></label>
      <div className="acoes"><BotaoAcao acao={editando ? "editar" : "cadastrar"} type="submit" disabled={!!bloqueio} motivoBloqueio={bloqueio}>{editando ? "Salvar alterações" : "Transferir saldo"}</BotaoAcao>{editando && <button className="secundario" type="button" onClick={async () => {if (await protecao.confirmarDescarte()) cancelarCorrecao();}}>Cancelar edição</button>}</div>
    </fieldset></form>}
    {excluindo && <form ref={exclusaoRef} className="card formulario confirmacao-compacta" onSubmit={confirmarExclusao}><h3>Excluir transferência</h3>{erro && <p role="alert" className="erro">{erro}</p>}<p>{nomePropriedadeTransferencia(excluindo.saida, propriedades)} → {nomePropriedadeTransferencia(excluindo.entrada, propriedades)} · {kg(excluindo.saida?.quantidade_kg || 0)}.</p><p>A exclusão pode ser bloqueada se o saldo recebido já tiver sido vendido, transferido ou reservado. Nesse caso, reveja os lançamentos posteriores.</p><label>Motivo da exclusão<textarea required maxLength={500} disabled={ocupado} value={motivo} onChange={e => setMotivo(e.target.value)} /></label><div className="acoes"><BotaoAcao acao="excluir" type="submit" className="perigo" disabled={ocupado || !motivo.trim()} motivoBloqueio={ocupado ? "Aguarde o processamento." : "Informe o motivo da exclusão."}>Confirmar exclusão</BotaoAcao><button type="button" className="secundario" disabled={ocupado} onClick={async () => {if (await protecao.confirmarDescarte()) cancelarCorrecao();}}>Cancelar exclusão</button></div></form>}
    <section className="card"><div className="acoes"><h3>Histórico de transferências</h3><button type="button" className="secundario" disabled={ocupado || carregando} onClick={() => void carregar()}>Atualizar</button></div>
      <label>Buscar transferências<input type="search" placeholder="Número de um dos movimentos, propriedade, CAD/PRO ou documento" value={busca} onChange={e => setBusca(e.target.value)} /></label>
      <FiltrosRapidos valor={filtrosRapidos} alterar={setFiltrosRapidos} culturas={[...new Set((dados?.movimentos || []).map(m => m.cultura))].sort()} safras={[...new Set((dados?.movimentos || []).map(m => m.safra))].sort()} propriedades={propriedades} busca={busca} limparBusca={() => setBusca("")} quantidade={historico.length} />
      <label className="opcao-checkbox"><input type="checkbox" checked={mostrarHistorico} onChange={e => setMostrarHistorico(e.target.checked)} /> Mostrar editadas, excluídas e estornadas</label>
      <p>Editar e excluir corrigem o débito e o crédito juntos. Os registros anteriores permanecem no histórico.</p>
      <div className="tabela-responsiva"><table className="tabela-relatorio tabela-transferencias"><thead><tr><th>Data</th><th>Origem</th><th>Destino</th><th>Produto / safra</th><th>Quantidade</th><th>Referência / documento</th><th>Observações</th><th>Registro</th><th>Situação / ações</th></tr></thead><tbody>{historico.map(item => {
        const movimento = item.saida || item.entrada;
        const ativa = statusTransferencia(item) === "Ativa" && item.saida && item.entrada;
        return <tr key={item.chave}><td><strong>#{item.saida?.id || item.entrada?.id}</strong><small>{dataBR(movimento?.data_movimento)}</small></td><td><strong>{nomePropriedadeTransferencia(item.saida, propriedades)}</strong><small>CAD/PRO {item.saida?.cad_pro_codigo || "—"} · {item.saida?.armazem_nome || "—"}</small></td><td><strong>{nomePropriedadeTransferencia(item.entrada, propriedades)}</strong><small>CAD/PRO {item.entrada?.cad_pro_codigo || "—"} · {item.entrada?.armazem_nome || "—"}</small></td><td>{movimento?.cultura || "—"} · {movimento?.safra || "—"}<small>{movimento?.classificacao_codigo || "—"}</small></td><td>{kg(movimento?.quantidade_kg || "0")}</td><td>{movimento?.referencia_externa || "—"}</td><td>{movimento?.observacoes || "—"}{item.saida?.correcao_transferencia && <small>Motivo: {item.saida.correcao_transferencia.motivo} · {item.saida.correcao_transferencia.criado_por_nome}</small>}</td><td>{movimento?.criado_por_nome || "—"}<small>{movimento?.criado_em ? new Date(movimento.criado_em).toLocaleString("pt-BR") : "—"}</small><small>Movimentos #{item.saida?.id} / #{item.entrada?.id}</small></td><td><strong>{statusTransferencia(item)}</strong>{ativa && <div className="acoes"><BotaoAcao acao="editar" type="button" className="secundario" disabled={ocupado || carregando} onClick={() => iniciarEdicao(item)}>Editar</BotaoAcao><BotaoAcao acao="excluir" type="button" className="perigo" disabled={ocupado || carregando} onClick={async () => { if (!(await protecao.confirmarDescarte())) return; cancelarCorrecao(); setExcluindo(item); setErro(""); setSucesso(""); }}>Excluir</BotaoAcao></div>}</td></tr>;
      })}{!historico.length && <tr><td colSpan={9}>{carregando ? "Carregando..." : "Nenhuma transferência encontrada."}</td></tr>}</tbody></table></div></section>
  </section>;
}
