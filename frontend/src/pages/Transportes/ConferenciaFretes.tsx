import { useEffect, useState } from "react";
import { BotaoAcao, useAcoes } from "../../components/AcoesContext";
import { useAlteracoesNaoSalvas } from "../../components/AlteracoesNaoSalvas";
import { consultarFretes, CruzamentoFretes, salvarFreteConferido, ViagemFrete } from "../../api/transportes";
import { formatarData } from "../../utils/datas";
import axios from "axios";
import CorrecaoHistorico from "../../components/CorrecaoHistorico";
import SelecionarTransporte from "../../components/SelecionarTransporte";

const vazio = { placa: "", motorista: "", remuneracao: "", tarifa: "", frete: "", comissao: "", tratamento: "", observacoes: "" };
const moeda = (valor: string) => Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
export function calcularFreteTonelada(peso: string, tarifa: string, percentual: string | null) {
  function decimal(valor: string, casas: number) {
    if (!/^\d{1,14}(?:\.\d+)?$/.test(valor)) return null;
    const [inteiro, fracao = ""] = valor.split(".");
    if (fracao.length > casas && /[1-9]/.test(fracao.slice(casas))) return null;
    return BigInt(inteiro + fracao.slice(0, casas).padEnd(casas, "0"));
  }
  const kg = decimal(peso, 3), preco = decimal(tarifa, 2);
  const taxa = percentual === null ? null : decimal(percentual, 4);
  if (kg === null || kg <= 0n || preco === null || (percentual !== null && (taxa === null || taxa > 1000000n))) return null;
  const centavos = (kg * preco + 500000n) / 1000000n;
  const formatar = (valor: bigint) => `${valor / 100n}.${(valor % 100n).toString().padStart(2, "0")}`;
  return { frete: formatar(centavos), comissao: taxa === null ? null : formatar((centavos * taxa + 500000n) / 1000000n) };
}
export default function ConferenciaFretes({ ativo, revisao, atualizar }: { ativo: boolean; revisao: number; atualizar: () => void }) {
  const pode = useAcoes();
  const [mes, setMes] = useState(() => new Date().toLocaleDateString("en-CA", { timeZone: "America/Sao_Paulo" }).slice(0, 7));
  const [placa, setPlaca] = useState("");
  const [dados, setDados] = useState<CruzamentoFretes | null>(null);
  const [viagem, setViagem] = useState<ViagemFrete | null>(null);
  const [formulario, setFormulario] = useState(vazio);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [consulta, setConsulta] = useState(0);
  const protecao = useAlteracoesNaoSalvas(formulario, "frete e comissão da viagem", viagem?.conferencia?.id ?? null);
  const remuneracaoSelecionada = dados?.remuneracoes.find(rem => String(rem.id) === formulario.remuneracao);
  function alterarCalculo(atual: typeof vazio) {
    const rem = dados?.remuneracoes.find(r => String(r.id) === atual.remuneracao);
    const calculo = viagem && atual.tarifa ? calcularFreteTonelada(viagem.peso_kg, atual.tarifa, rem?.comissao_percentual ?? null) : null;
    setFormulario(calculo ? { ...atual, frete: calculo.frete, comissao: calculo.comissao ?? "" } : { ...atual, ...(atual.tarifa ? { frete: "", comissao: "" } : {}) });
  }
  useEffect(() => {
    if (!ativo) return;
    const controle = new AbortController(); setDados(null); setErro("");
    if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(mes)) { setErro("Escolha o mês da conferência."); return; }
    void consultarFretes(mes, placa, controle.signal).then(resultado => { if (!controle.signal.aborted) setDados(resultado); }).catch(() => { if (!controle.signal.aborted) setErro("Não foi possível cruzar as viagens. Tente novamente."); });
    return () => controle.abort();
  }, [ativo, mes, placa, revisao, consulta]);
  async function selecionar(item: ViagemFrete) {
    if (!(await protecao.confirmarDescarte())) return;
    const conf = item.conferencia;
    const sugestao = dados?.remuneracoes.find(rem => (!item.placa || rem.placa === item.placa) && rem.motorista.trim().toLocaleLowerCase("pt-BR") === item.motorista.trim().toLocaleLowerCase("pt-BR"));
    const rem = conf ? dados?.remuneracoes.find(r => r.id === conf.remuneracao) : sugestao;
    const transporte = { placa: rem?.placa ?? item.placa, motorista: rem?.motorista ?? item.motorista };
    const valores = conf ? { ...transporte, remuneracao: String(conf.remuneracao), tarifa: "", frete: conf.frete, comissao: conf.comissao, tratamento: conf.ja_contabilizado ? "ja" : "adicionar", observacoes: conf.observacoes } : { ...vazio, ...transporte, remuneracao: sugestao ? String(sugestao.id) : "" };
    setViagem(item); setFormulario(valores); protecao.marcarSalvo(valores); setErro(""); setSucesso("");
  }
  async function filtrar(tipo: "mes" | "placa", valor: string) {
    if (!(await protecao.confirmarDescarte())) return;
    setViagem(null); setFormulario(vazio); protecao.marcarSalvo(vazio); setSucesso("");
    if (tipo === "mes") setMes(valor); else setPlaca(valor);
  }
  async function salvar() {
    if (!viagem || ocupado) return;
    setOcupado(true); setErro(""); setSucesso("");
    try {
      await salvarFreteConferido(viagem.conferencia?.id ?? null, {
        carga: viagem.origem === "carga" ? viagem.id : null,
        entrega: viagem.origem === "venda" ? viagem.id : null,
        remuneracao: Number(formulario.remuneracao), frete: formulario.frete, comissao: formulario.comissao,
        ja_contabilizado: formulario.tratamento === "ja", observacoes: formulario.observacoes,
        ...(viagem.conferencia ? { atualizado_em_original: viagem.conferencia.atualizado_em } : {}),
      });
      setViagem(null); setFormulario(vazio); protecao.marcarSalvo(vazio);
      setSucesso(formulario.tratamento === "ja" ? "Conferência salva sem acrescentar comissão ao holerite." : "Comissão conferida adicionada à remuneração selecionada."); atualizar();
    } catch (falha) {
      if (axios.isAxiosError(falha) && falha.response?.data) {
        setErro(Object.entries(falha.response.data).map(([campo, valor]) => `${campo === "detail" ? "" : campo + ": "}${Array.isArray(valor) ? valor.join(" ") : valor}`).join(" "));
      } else setErro("Não foi possível salvar. Seus valores foram preservados para nova tentativa.");
    } finally { setOcupado(false); }
  }
  return <>
    <section className="card nao-imprimir"><h2>Cargas e vendas por placa e mês</h2><p>Informe o frete por tonelada. O frete total usa o peso bruto do produto e a comissão aplica o percentual cadastrado para o motorista. A comissão usa como referência o peso bruto do produto: peso total menos tara, antes dos descontos de umidade, impureza e avariados. O salário mensal continua no cadastro de Salário e comissão.</p><p>Escolha se a comissão deve ser adicionada ou se já está incluída nos valores de Transportes. Cargas canceladas/substituídas e entregas canceladas ficam fora do cálculo.</p><div className="transporte-campos">
      <label>Mês<input type="month" value={mes} disabled={ocupado} onChange={e => void filtrar("mes", e.target.value)} /></label>
      <label>Placa<input maxLength={12} placeholder="Todas as placas" value={placa} disabled={ocupado} onChange={e => void filtrar("placa", e.target.value.toUpperCase())} /></label>
      <button type="button" className="secundario" disabled={ocupado} onClick={() => setConsulta(v => v + 1)}>Atualizar consulta</button>
    </div></section>
    {erro && <p className="erro" role="alert">{erro}</p>}{sucesso && <p role="status">{sucesso}</p>}
    {viagem && <form className="card formulario nao-imprimir" onSubmit={e => { e.preventDefault(); void salvar(); }}><h3>{viagem.origem === "carga" ? "Carga colhida" : "Entrega de venda"} #{viagem.id} · {formatarData(viagem.data)} · {viagem.placa || "Placa ausente"}</h3><p>Motorista na origem: {viagem.motorista || "Não informado"}. Confira o motorista escolhido para a remuneração.</p><p>Base da comissão: {Number(viagem.peso_kg).toLocaleString("pt-BR", { maximumFractionDigits: 3 })} kg de peso bruto do produto, sem tara e antes dos descontos de qualidade. Frete total = peso bruto ÷ 1.000 × tarifa por tonelada; comissão = frete total × percentual do motorista.</p><div className="transporte-campos">
      <SelecionarTransporte placa={formulario.placa} motorista={formulario.motorista} disabled={ocupado} alterar={transporte => {
        const rem = dados?.remuneracoes.find(r => r.placa === transporte.placa && r.motorista === transporte.motorista);
        alterarCalculo({ ...formulario, ...transporte, remuneracao: rem ? String(rem.id) : "" });
      }} />
      {viagem.placa && formulario.placa !== viagem.placa && <p role="alert" className="erro">A placa precisa corresponder à viagem ({viagem.placa}). Para corrigir a origem, edite a carga ou venda antes da conferência.</p>}
      <label>Motorista / remuneração mensal<select required value={formulario.remuneracao} disabled={ocupado} onChange={e => alterarCalculo({ ...formulario, remuneracao: e.target.value })}><option value="">Selecione</option>{dados?.remuneracoes.filter(rem => (!viagem.placa || rem.placa === viagem.placa) && (!formulario.placa || rem.placa === formulario.placa) && (!formulario.motorista || rem.motorista === formulario.motorista)).map(rem => <option key={rem.id} value={rem.id}>{rem.motorista} · {rem.placa} · {mes}</option>)}</select></label>
      <label>Frete por tonelada (R$/t)<input required={!viagem.conferencia} type="number" min="0" step="0.01" value={formulario.tarifa} disabled={ocupado} onChange={e => alterarCalculo({ ...formulario, tarifa: e.target.value })} /></label><label>Frete total da viagem (R$)<input required readOnly={!!formulario.tarifa} type="number" min="0" step="0.01" value={formulario.frete} disabled={ocupado} onChange={e => setFormulario({ ...formulario, frete: e.target.value })} /></label>
      <label>Comissão cadastrada (%)<input readOnly value={remuneracaoSelecionada?.comissao_percentual == null ? "Não cadastrada" : Number(remuneracaoSelecionada.comissao_percentual).toLocaleString("pt-BR", { maximumFractionDigits: 4 })} /></label>
      <label>Comissão desta viagem (R$)<input required type="number" min="0" step="0.01" value={formulario.comissao} disabled={ocupado} onChange={e => setFormulario({ ...formulario, comissao: e.target.value })} /></label>
      <label>Como contabilizar<select required value={formulario.tratamento} disabled={ocupado} onChange={e => setFormulario({ ...formulario, tratamento: e.target.value })}><option value="">Escolha para evitar duplicação</option><option value="adicionar">Adicionar comissão ao holerite (ainda não incluída)</option><option value="ja">Já incluída em Transportes (não somar novamente)</option></select></label>
      <label>Observações<input maxLength={220} value={formulario.observacoes} disabled={ocupado} onChange={e => setFormulario({ ...formulario, observacoes: e.target.value })} /></label>
    </div>{remuneracaoSelecionada?.comissao_percentual == null && <p className="aviso-contexto">Percentual não cadastrado: informe a comissão manualmente ou cadastre o percentual em Salário e comissão.</p>}{viagem.conferencia && !formulario.tarifa && <p>Valores salvos preservados. Informe a tarifa por tonelada para recalcular esta viagem.</p>}<p>Se a remuneração deste motorista/placa não aparecer, cadastre primeiro o salário mensal na aba Salário e comissão. O valor do frete é conferência; não cria uma receita duplicada em Transportes.</p><div className="acoes"><BotaoAcao acao={viagem.conferencia ? "editar" : "cadastrar"} type="submit" disabled={ocupado}>Salvar conferência</BotaoAcao><button type="button" className="secundario" disabled={ocupado} onClick={() => { void protecao.confirmarDescarte().then(ok => { if (ok) { setViagem(null); setFormulario(vazio); protecao.marcarSalvo(vazio); } }); }}>Fechar</button></div></form>}
    {dados === null && !erro && <p role="status">Cruzando cargas e entregas...</p>}
    {dados && <section className="card"><h3>{dados.viagens.length} viagens no mês</h3><div className="transporte-tabela"><table><thead><tr><th>Origem</th><th>Data</th><th>Placa</th><th>Motorista na origem</th><th>Peso bruto do produto (kg)</th><th>Frete total (R$)</th><th>Comissão</th><th>Situação</th><th>Ações</th></tr></thead><tbody>{dados.viagens.map(item => <tr key={`${item.origem}-${item.id}`}><td>{item.origem === "carga" ? "Carga" : "Venda"} #{item.id}</td><td>{formatarData(item.data)}</td><td>{item.placa || "Não informada"}</td><td>{item.motorista || "Conferir manualmente"}</td><td>{Number(item.peso_kg).toLocaleString("pt-BR", { maximumFractionDigits: 3 })}</td><td>{item.conferencia ? moeda(item.conferencia.frete) : "Pendente"}</td><td>{item.conferencia ? moeda(item.conferencia.comissao) : "Pendente"}</td><td>{!item.conferencia ? "Não conferida" : item.conferencia.ja_contabilizado ? "Já contabilizada; não somada" : "Adicionada ao holerite"}</td><td><BotaoAcao acao={item.conferencia ? "editar" : "cadastrar"} type="button" className="secundario" disabled={ocupado} onClick={() => void selecionar(item)}>{item.conferencia ? "Editar conferência" : "Conferir"}</BotaoAcao>{item.conferencia && <CorrecaoHistorico base="/transportes/fretes/" dados={item.conferencia} campos={[]} somenteCancelar atualizar={atualizar} />}</td></tr>)}</tbody></table></div>{!dados.viagens.length && <p>Nenhuma carga ou entrega ativa encontrada nas origens às quais você tem acesso.</p>}</section>}
  </>;
}
