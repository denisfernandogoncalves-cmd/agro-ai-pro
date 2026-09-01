import axios from "axios";
import { FormEvent, useEffect, useRef, useState } from "react";
import { carregarTransferenciasSaldo, transferirSaldo } from "../../api/transferenciasSaldo";
import { MovimentacaoSaldo, PosicaoSaldo } from "../../api/producaoSaldos";
import { Propriedade } from "../../api/propriedades";
import { quantidadeContrato } from "../CadastrosAgricolas/ContratosComerciais";

type Dados = Awaited<ReturnType<typeof carregarTransferenciasSaldo>>;
type PropriedadeResumo = Pick<Propriedade, "id" | "nome" | "proprietario">;
const vazio = { cultura: "", safra: "", posicao_origem: 0, posicao_destino: 0, quantidade_kg: "", data_movimento: new Date().toISOString().slice(0, 10), referencia_externa: "", observacoes: "" };
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

export function agruparHistoricoTransferencias(movimentos: MovimentacaoSaldo[]) {
  return Array.from(new Set(movimentos.map(item => item.origem_chave_idempotencia))).map(chave => ({
    chave,
    saida: movimentos.find(item => item.origem_chave_idempotencia === chave && item.operacao === "transferencia_saida"),
    entrada: movimentos.find(item => item.origem_chave_idempotencia === chave && item.operacao === "transferencia_entrada"),
  }));
}

function dataBR(valor?: string) {
  const [ano, mes, dia] = (valor || "").slice(0, 10).split("-");
  return ano && mes && dia ? `${dia}/${mes}/${ano}` : "—";
}

function mensagem(falha: unknown) {
  if (axios.isAxiosError(falha) && falha.response?.data) {
    const dados = falha.response.data;
    return typeof dados.detail === "string" ? dados.detail : typeof dados.mensagem === "string" ? dados.mensagem : Object.values(dados).flat(2).join(" ");
  }
  return falha instanceof Error ? falha.message : "Não foi possível transferir o saldo.";
}

export default function TransferenciasSaldoPage() {
  const [dados, setDados] = useState<Dados>();
  const [form, setForm] = useState(vazio);
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

  const posicoes = dados?.posicoes || [];
  const propriedades = dados?.propriedades || [];
  const culturas = culturasTransferencia(posicoes);
  const safras = safrasTransferencia(posicoes, form.cultura);
  const posicoesDaSafra = form.cultura && form.safra
    ? posicoes.filter(item => item.cultura === form.cultura && item.safra === form.safra)
    : [];
  const origens = opcoesPosicaoTransferencia(posicoesDaSafra, propriedades, true);
  const origem = posicoes.find(item => item.id === form.posicao_origem);
  const destinos = origem ? opcoesPosicaoTransferencia(posicoesDaSafra.filter(item => posicaoDestinoCompativel(origem, item)), propriedades) : [];
  const destino = posicoes.find(item => item.id === form.posicao_destino);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (trava.current) return;
    setErro(""); setSucesso("");
    try {
      if (!form.cultura || !form.safra) throw new Error("Selecione a cultura e o ano/safra.");
      if (!origem || !destino || !posicaoDestinoCompativel(origem, destino)) throw new Error("Selecione posições diferentes com cultura, safra e classificação iguais.");
      const quantidade = quantidadeContrato(form.quantidade_kg);
      if (Number(quantidade) > Number(origem.saldo_disponivel_kg)) throw new Error("Quantidade superior ao saldo disponível na origem.");
      if (!window.confirm(`Transferir ${kg(quantidade)} de ${form.cultura}, safra ${form.safra}, de ${rotuloPosicaoTransferencia(origem, propriedades)} para ${rotuloPosicaoTransferencia(destino, propriedades)}? O débito e o crédito serão registrados juntos.`)) return;
      trava.current = true; setOcupado(true);
      const payload = { posicao_origem: origem.id, posicao_destino: destino.id, quantidade_kg: quantidade, data_movimento: form.data_movimento, referencia_externa: form.referencia_externa, observacoes: form.observacoes };
      const assinatura = JSON.stringify(payload);
      if (tentativa.current?.assinatura !== assinatura) tentativa.current = { assinatura, chave: `transferencia-ui:${crypto.randomUUID()}` };
      await transferirSaldo({ ...payload, chave_idempotencia: tentativa.current.chave });
      tentativa.current = null; setForm(vazio); setSucesso("Transferência registrada nas duas posições oficiais. O saldo total foi preservado.");
      await carregar();
    } catch (falha) { setErro(mensagem(falha)); }
    finally { trava.current = false; setOcupado(false); }
  }

  const historico = agruparHistoricoTransferencias(dados?.movimentos || []);
  const nomePropriedade = (movimento?: MovimentacaoSaldo) => propriedades.find(item => item.id === movimento?.propriedade_id)?.nome || (movimento?.propriedade_id ? `Propriedade #${movimento.propriedade_id}` : "Produção histórica");

  return <section className="modulo-producao-saldos">
    <h2>Transferência de saldo entre CAD/PROs</h2>
    <p>Selecione a cultura e o ano/safra e, em seguida, as propriedades e os CAD/PROs de origem e destino. Não é necessário escolher lotes; débito e crédito ficam vinculados no histórico.</p>
    {erro && <p className="erro card" role="alert">{erro}</p>}{sucesso && <p className="sucesso card" role="status">{sucesso}</p>}
    <form className="card formulario transferencia-saldo" onSubmit={enviar}><fieldset disabled={ocupado || carregando}>
      <div className="linha"><label>Cultura<select required value={form.cultura} onChange={e => setForm({ ...form, cultura: e.target.value, safra: "", posicao_origem: 0, posicao_destino: 0 })}><option value="">Selecione a cultura</option>{culturas.map(cultura => <option key={cultura} value={cultura}>{cultura}</option>)}</select></label><label>Ano / safra<select required disabled={!form.cultura} value={form.safra} onChange={e => setForm({ ...form, safra: e.target.value, posicao_origem: 0, posicao_destino: 0 })}><option value="">{form.cultura ? "Selecione o ano / safra" : "Selecione primeiro a cultura"}</option>{safras.map(safra => <option key={safra} value={safra}>{safra}</option>)}</select></label></div>
      <div className="linha"><label>Propriedade / CAD/PRO de origem / Proprietário<select required disabled={!form.safra} value={form.posicao_origem || ""} onChange={e => setForm({ ...form, posicao_origem: Number(e.target.value), posicao_destino: 0 })}><option value="">{form.safra ? "Selecione a propriedade e o CAD/PRO" : "Selecione primeiro a cultura e o ano / safra"}</option>{origens.map(opcao => <option key={opcao.chave} value={opcao.chave}>{opcao.rotulo}</option>)}</select></label><label>Propriedade / CAD/PRO de destino / Proprietário<select required disabled={!origem} value={form.posicao_destino || ""} onChange={e => setForm({ ...form, posicao_destino: Number(e.target.value) })}><option value="">{origem ? "Selecione a propriedade e o CAD/PRO" : "Selecione primeiro a origem"}</option>{destinos.map(opcao => <option key={opcao.chave} value={opcao.chave}>{opcao.rotulo}</option>)}</select></label></div>
      {origem && !destinos.length && <p role="status">Não há posição compatível para destino com a mesma cultura, safra e classificação.</p>}
      <div className="linha"><p>Disponível na origem: <strong>{kg(origem?.saldo_disponivel_kg || "0")}</strong></p><p>Físico no destino: <strong>{kg(destino?.saldo_fisico_kg || "0")}</strong></p></div>
      <div className="linha"><label>Quantidade (kg)<input required inputMode="decimal" placeholder="Ex.: 1.000,500" value={form.quantidade_kg} onChange={e => setForm({ ...form, quantidade_kg: e.target.value })} /></label><label>Data<input required type="date" value={form.data_movimento} onChange={e => setForm({ ...form, data_movimento: e.target.value })} /></label></div>
      <label>Referência / documento<input maxLength={160} value={form.referencia_externa} onChange={e => setForm({ ...form, referencia_externa: e.target.value })} /></label><label>Observações<textarea value={form.observacoes} onChange={e => setForm({ ...form, observacoes: e.target.value })} /></label>
      <button type="submit" disabled={!origem || !destino}>Transferir saldo</button>
    </fieldset></form>
    <section className="card"><div className="acoes"><h3>Histórico de transferências</h3><button type="button" className="secundario" disabled={ocupado || carregando} onClick={() => void carregar()}>Atualizar</button></div><p>Todos os dados inseridos são apresentados abaixo; as duas movimentações pertencem ao mesmo lançamento.</p><div className="tabela-responsiva"><table className="tabela-relatorio tabela-transferencias"><thead><tr><th>Data</th><th>Origem</th><th>Destino</th><th>Produto / safra</th><th>Quantidade</th><th>Referência / documento</th><th>Observações</th><th>Registro</th></tr></thead><tbody>{historico.map(item => { const movimento = item.saida || item.entrada; return <tr key={item.chave}><td>{dataBR(movimento?.data_movimento)}</td><td><strong>{nomePropriedade(item.saida)}</strong><small>CAD/PRO {item.saida?.cad_pro_codigo || "—"} · {item.saida?.armazem_nome || "—"}</small></td><td><strong>{nomePropriedade(item.entrada)}</strong><small>CAD/PRO {item.entrada?.cad_pro_codigo || "—"} · {item.entrada?.armazem_nome || "—"}</small></td><td>{movimento?.cultura || "—"} · {movimento?.safra || "—"}<small>{movimento?.classificacao_codigo || "—"}</small></td><td>{kg(movimento?.quantidade_kg || "0")}</td><td>{movimento?.referencia_externa || "—"}</td><td>{movimento?.observacoes || "—"}</td><td>{movimento?.criado_por_nome || "—"}<small>{movimento?.criado_em ? new Date(movimento.criado_em).toLocaleString("pt-BR") : "—"}</small></td></tr>; })}{!historico.length && <tr><td colSpan={8}>{carregando ? "Carregando..." : "Nenhuma transferência registrada."}</td></tr>}</tbody></table></div></section>
  </section>;
}
