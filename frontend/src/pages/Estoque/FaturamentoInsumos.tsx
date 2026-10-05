import AbasModulo, { PainelAba } from "../../components/AbasModulo";
import AnexosLancamento from "../../components/AnexosLancamento";
import { BotaoAcao, useAcoes } from "../../components/AcoesContext";
import { useAlteracoesNaoSalvas } from "../../components/AlteracoesNaoSalvas";
import { useConfirmacaoCompacta } from "../../components/ConfirmacaoCompacta";
import { FormEvent, useEffect, useRef, useState } from "react";
import axios from "axios";
import { api, Propriedade } from "../../api/propriedades";
import { listarProdutosEstoque, ProdutoEstoque } from "../../api/estoque";
import { ParceiroFinanceiro } from "../../api/financeiro";
import { obterGeracaoSessao } from "../../auth/sessionCoordinator";
import { quantidadeParaEnviar, sugerirEmbalagens } from "./embalagensFaturamento";
import { confirmarFaturamento, empresaUsaBep, excluirFaturamento, obterPdfFaturamento, EntradaFaturamento, Faturamento, ItemFaturamento, listarFaturamentos, previaFaturamento, ResumoFaturamento } from "../../api/faturamentoInsumos";

const numero = (valor: string | number) => Number(valor).toLocaleString("pt-BR", { maximumFractionDigits: 3 });
const dataLocal = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };
const chavePendente = () => `agro-faturamento-pendente:${obterGeracaoSessao()}`;
const mensagem = (erro: unknown) => axios.isAxiosError(erro) && erro.response?.data
  ? Object.values(erro.response.data).flat().map(v => typeof v === "object" ? JSON.stringify(v) : String(v)).join(" ")
  : "Não foi possível concluir. Confira sua conexão e tente novamente com os mesmos dados.";

export function RelatorioFaturamento({ resumo, confirmado }: { resumo: ResumoFaturamento; confirmado: boolean }) {
  const usaBep = resumo.usa_bep ?? empresaUsaBep(resumo.fornecedor_nome);
  return <section className="relatorio-faturamento card">
    <h2>{confirmado ? "Faturamento de insumos confirmado" : "Prévia de faturamento — sem baixa"}</h2>
    <p><strong>{resumo.fornecedor_nome}</strong> · {resumo.data_envio.split("-").reverse().join("/")}</p>
    <p>{resumo.produto_nome} · {resumo.embalagem} de {numero(resumo.conteudo_embalagem)} {resumo.unidade}</p>
    <div className="faturamento-tabela"><table><thead><tr><th>Propriedade</th><th>Produtor</th><th>CAD/PRO</th>{usaBep && <th>BEP</th>}<th>Área (alq.)</th><th>Embalagens</th><th>Quantidade ({resumo.unidade})</th></tr></thead>
      <tbody>{resumo.itens.map(item => <tr key={item.propriedade}><td>{item.propriedade_nome}</td><td>{item.produtor || "Não informado"}</td><td>{item.cad_pro || "Não informado"}</td>{usaBep && <td>{item.bep || "Não informado"}</td>}<td>{numero(item.area_alqueires)}</td><td>{numero(item.quantidade_embalagens)}</td><td>{numero(item.quantidade)}</td></tr>)}</tbody>
      <tfoot><tr><th colSpan={usaBep ? 5 : 4}>Total</th><td>{numero(resumo.total_embalagens)}</td><td>{numero(resumo.quantidade_total)} {resumo.unidade}</td></tr></tfoot>
    </table></div>
    {resumo.observacoes && <p>{resumo.observacoes}</p>}
    <p className="nao-imprimir">Saldo da empresa: {numero(resumo.saldo_anterior)} → <strong>{numero(resumo.saldo_posterior)} {resumo.unidade}</strong>.</p>
    {Number(resumo.saldo_posterior) < 0 && <p className="aviso-contexto nao-imprimir">Saldo negativo permitido. Ficarão faltando {numero(-Number(resumo.saldo_posterior))} {resumo.unidade} no estoque desta empresa.</p>}
  </section>;
}

export function HistoricoFaturamento({ historico, ocupado, onVer, onPdf, onExcluir }: {
  historico: Faturamento[]; ocupado: boolean;
  onVer: (f: Faturamento) => void; onPdf: (f: Faturamento) => void; onExcluir: (f: Faturamento) => void;
}) {
  return <section className="card nao-imprimir"><h2>Histórico de envios confirmados</h2>{!historico.length && <p>Nenhum faturamento registrado.</p>}
    {historico.map(h => <article className="item" key={h.id}><AnexosLancamento entidade="faturamento" registro={h.id} />
      <div><strong>{h.resumo.fornecedor_nome} · {h.resumo.produto_nome}</strong><p>{h.data_envio.split("-").reverse().join("/")} · {numero(h.resumo.total_embalagens)} {h.resumo.embalagem} · {numero(h.resumo.quantidade_total)} {h.resumo.unidade}</p></div>
      <div className="acoes">
        <button type="button" className="secundario" disabled={ocupado} onClick={() => onVer(h)}>Ver relatório</button>
        <BotaoAcao acao="imprimir" type="button" className="secundario" disabled={ocupado} onClick={() => onPdf(h)}>Exportar PDF</BotaoAcao>
        <BotaoAcao acao="excluir" type="button" className="perigo" disabled={ocupado} onClick={() => onExcluir(h)}>Excluir lançamento</BotaoAcao>
      </div>
    </article>)}
  </section>;
}

export default function FaturamentoInsumos() {
  const confirmarPedido = useConfirmacaoCompacta();
  const pode = useAcoes();
  const [aba, setAba] = useState(pode("cadastrar") ? "novo" : "historico");
  const [produtos, setProdutos] = useState<ProdutoEstoque[]>([]);
  const [empresas, setEmpresas] = useState<ParceiroFinanceiro[]>([]);
  const [propriedades, setPropriedades] = useState<Propriedade[]>([]);
  const [historico, setHistorico] = useState<Faturamento[]>([]);
  const [form, setForm] = useState({ fornecedor: "", produto: "", data_envio: dataLocal(), embalagem: "Balde", conteudo_embalagem: "20", dosagem_alqueire: "0", observacoes: "" });
  const [itens, setItens] = useState<Record<number, ItemFaturamento>>({});
  const [busca, setBusca] = useState("");
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [ocupado, setOcupado] = useState(false);
  const [previa, setPrevia] = useState<ResumoFaturamento | null>(null);
  const [confirmado, setConfirmado] = useState<Faturamento | null>(null);
  const [pendente, setPendente] = useState<EntradaFaturamento | null>(null);
  const [incerto, setIncerto] = useState(false);
  const protecao = useAlteracoesNaoSalvas({form,itens}, "Faturamento de insumos", null, !confirmado);
  const trava = useRef(false);
  const versao = useRef(0);
  const embalagensEditadas = useRef(new Set<number>());
  const produto = produtos.find(p => String(p.id) === form.produto);
  const usaBep = empresaUsaBep(empresas.find(e => String(e.id) === form.fornecedor)?.nome || "");

  useEffect(() => {
    let ativo = true;
    Promise.all([listarProdutosEstoque(), api.get<ParceiroFinanceiro[]>("/financeiro/parceiros/"), api.get<Propriedade[]>("/propriedades/"), listarFaturamentos()])
      .then(([p, e, props, h]) => { if (ativo) { setProdutos(p.filter(i => i.ativo)); setEmpresas(e.data.filter(i => i.ativo && i.tipo !== "cliente")); setPropriedades(props.data); setHistorico(h); } })
      .catch(e => { if (ativo) setErro(mensagem(e)); }).finally(() => { if (ativo) setCarregando(false); });
    return () => { ativo = false; };
  }, []);

  function invalidar() { versao.current++; setPrevia(null); setPendente(null); setConfirmado(null); setErro(""); setAviso(""); }
  function selecionar(p: Propriedade, marcada: boolean) {
    invalidar();
    embalagensEditadas.current.delete(p.id);
    setItens(atuais => {
      const novos = { ...atuais };
      if (marcada) novos[p.id] = { propriedade: p.id, cad_pro: p.cad_pro_numeros.length === 1 ? p.cad_pro_numeros[0] : "", bep: usaBep ? p.bp_cvale || "" : "", area_alqueires: (Number(p.area_hectares) / 2.42).toFixed(6), quantidade_embalagens: "" };
      else delete novos[p.id];
      return novos;
    });
  }
  function atualizarItem(id: number, campo: keyof ItemFaturamento, valor: string) {
    if (campo === "quantidade_embalagens") embalagensEditadas.current.add(id);
    invalidar(); setItens(atuais => ({ ...atuais, [id]: { ...atuais[id], [campo]: valor } }));
  }
  async function simular(event: FormEvent) {
    event.preventDefault();
    if (trava.current) return;
    if (!Object.keys(itens).length) { setErro("Selecione ao menos uma propriedade."); return; }
    trava.current = true; setOcupado(true); setErro(""); setConfirmado(null); setPrevia(null);
    const v = ++versao.current;
    const dados = { ...form, id: pendente?.id || crypto.randomUUID(), itens: Object.values(itens).map(item => ({ ...item, quantidade_embalagens: quantidadeParaEnviar(item, form.dosagem_alqueire, form.conteudo_embalagem, embalagensEditadas.current.has(item.propriedade)) })) };
    try { const resultado = await previaFaturamento(dados); if (v === versao.current) { setPrevia(resultado); setPendente(dados); } }
    catch (e) { setErro(mensagem(e)); }
    finally { trava.current = false; setOcupado(false); }
  }
  async function confirmar() {
    if (!pendente || trava.current) return;
    if (!(await confirmarPedido({titulo:"Confirmar faturamento", mensagem:"Confirmar este envio e baixar as quantidades do estoque da empresa? O saldo poderá ficar negativo."}))) return;
    trava.current = true; setOcupado(true); setErro("");
    // Mantém a mesma chave e os mesmos dados em falhas de rede e recargas.
    try {
      sessionStorage.setItem(chavePendente(), JSON.stringify(pendente));
      setIncerto(true);
      const salvo = await confirmarFaturamento(pendente);
      setConfirmado(salvo); setPrevia(salvo.resumo); setPendente(null); setIncerto(false);
      protecao.marcarSalvo({form,itens});
      sessionStorage.removeItem(chavePendente());
      setHistorico(atuais => [salvo, ...atuais.filter(i => i.id !== salvo.id)]);
    } catch (e) {
      setErro(mensagem(e));
      if (axios.isAxiosError(e) && e.response && e.response.status < 500 && e.response.status !== 409) {
        sessionStorage.removeItem(chavePendente()); setIncerto(false);
      }
    }
    finally { trava.current = false; setOcupado(false); }
  }
  async function exportarPdf(faturamento: Faturamento) {
    if (trava.current) return;
    trava.current = true; setOcupado(true); setErro("");
    try {
      const arquivo = await obterPdfFaturamento(faturamento.id);
      const url = URL.createObjectURL(arquivo);
      const link = document.createElement("a");
      link.href = url; link.download = `faturamento-insumos-${faturamento.data_envio}-${faturamento.id}.pdf`;
      document.body.appendChild(link); link.click(); link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      setErro("Não foi possível exportar o PDF. Confira sua conexão e se o lançamento ainda está disponível.");
    } finally { trava.current = false; setOcupado(false); }
  }
  async function excluir(faturamento: Faturamento) {
    if (trava.current) return;
    if (!(await confirmarPedido({titulo:"Excluir faturamento", perigo:true, confirmar:"Excluir lançamento", mensagem:`Excluir ${faturamento.resumo.produto_nome} para ${faturamento.resumo.fornecedor_nome}, de ${faturamento.data_envio.split("-").reverse().join("/")}? As ${numero(faturamento.resumo.quantidade_total)} ${faturamento.resumo.unidade} serão devolvidas ao estoque da empresa.`}))) return;
    trava.current = true; setOcupado(true); setErro("");
    try {
      await excluirFaturamento(faturamento.id);
      setHistorico(atuais => atuais.filter(h => h.id !== faturamento.id));
      invalidar();
      setAviso("Lançamento excluído e quantidade devolvida ao estoque. Para um novo envio, simule novamente.");
    } catch (e) { setErro(mensagem(e)); }
    finally { trava.current = false; setOcupado(false); }
  }
  useEffect(() => {
    const salvo = sessionStorage.getItem(chavePendente());
    if (salvo) {
      try { const dados: EntradaFaturamento = JSON.parse(salvo); setPendente(dados); setIncerto(true); setForm(dados); setItens(Object.fromEntries(dados.itens.map(i => [i.propriedade, i]))); embalagensEditadas.current = new Set(dados.itens.filter(i => i.quantidade_embalagens.trim() !== "").map(i => i.propriedade)); }
      catch { setErro("Não foi possível recuperar o envio pendente. Confira o histórico antes de repetir."); }
    }
  }, []);

  const visiveis = propriedades.filter(p => `${p.nome} ${p.proprietario} ${p.cad_pro_numeros.join(" ")}`.toLocaleLowerCase().includes(busca.toLocaleLowerCase()));
  return <section className="modulo-faturamento">
    <div className="nao-imprimir"><h2>Faturamento de insumos por empresa</h2><p>Selecione as propriedades, confira as embalagens e confirme a baixa. O relatório pode ser impresso ou salvo em PDF para encaminhar à empresa.</p></div>
    {erro && <p className="erro card nao-imprimir" role="alert">{erro}</p>}
    {aviso && <p className="sucesso card nao-imprimir" role="status">{aviso}</p>}
    {carregando && <p role="status">Carregando cadastros e histórico...</p>}
    {incerto && <div className="card nao-imprimir"><p>Existe uma confirmação pendente. Consulte o resultado com os mesmos dados para evitar uma segunda baixa.</p><BotaoAcao acao="cadastrar" type="button" disabled={ocupado} onClick={() => void confirmar()}>Verificar / repetir confirmação</BotaoAcao></div>}
<AbasModulo modulo="faturamento" ativa={aba} alterar={setAba} abas={[{id:"novo",titulo:pode("cadastrar") ? "Novo faturamento" : "Conferir envio"},{id:"historico",titulo:"Envios realizados"}]} /><PainelAba modulo="faturamento" aba="novo" ativa={aba}>
    {pode("cadastrar") && <form onSubmit={simular} className="card nao-imprimir">
      <fieldset disabled={carregando || ocupado || incerto || Boolean(confirmado)}>
        <div className="faturamento-campos">
          <label>Empresa / fornecedor<select required value={form.fornecedor} onChange={e => { invalidar(); setForm({ ...form, fornecedor: e.target.value }); const cvale = empresaUsaBep(empresas.find(empresa => String(empresa.id) === e.target.value)?.nome || ""); setItens(atuais => Object.fromEntries(Object.entries(atuais).map(([id, item]) => [id, { ...item, bep: cvale ? propriedades.find(p => p.id === item.propriedade)?.bp_cvale || "" : "" }]))); }}><option value="">Selecione</option>{empresas.map(e => <option key={e.id} value={e.id}>{e.nome}</option>)}</select></label>
          <label>Produto<select required value={form.produto} onChange={e => { invalidar(); setForm({ ...form, produto: e.target.value }); }}><option value="">Selecione</option>{produtos.map(p => <option key={p.id} value={p.id}>{p.nome} ({p.unidade})</option>)}</select></label>
          <label>Data do envio<input type="date" required value={form.data_envio} onChange={e => { invalidar(); setForm({ ...form, data_envio: e.target.value }); }} /></label>
          <label>Embalagem<input required maxLength={40} value={form.embalagem} onChange={e => { invalidar(); setForm({ ...form, embalagem: e.target.value }); }} /></label>
          <label>Conteúdo por embalagem ({produto?.unidade || "unidade do produto"})<input type="number" required min="0.001" step="0.001" value={form.conteudo_embalagem} onChange={e => { invalidar(); setForm({ ...form, conteudo_embalagem: e.target.value }); }} /></label>
          <label>Dosagem por alqueire ({produto?.unidade || "unidade"}/alq.)<input type="number" required min="0" step="0.001" value={form.dosagem_alqueire} onChange={e => { invalidar(); setForm({ ...form, dosagem_alqueire: e.target.value }); }} /></label>
        </div>
        <p>As embalagens são sugeridas pela dosagem e pelo conteúdo da embalagem, arredondando para cima. Você pode editar a quantidade a enviar; alterações manuais serão mantidas. 1 alqueire paulista = 2,42 ha.</p>
        {usaBep && <p>O BP cadastrado na propriedade preenche o BEP da C.Vale. Você pode ajustá-lo para este envio; ele será incluído no PDF.</p>}
        <label>Buscar propriedade, produtor ou CAD/PRO<input value={busca} onChange={e => setBusca(e.target.value)} /></label>
        <p>{Object.keys(itens).length} propriedade(s) selecionada(s), inclusive fora da busca.</p>
        {!propriedades.length && !carregando && <p>Cadastre as propriedades na aba Propriedades. Cadastre produtos e fornecedores em Estoque.</p>}
        <div className="faturamento-tabela"><table><thead><tr><th>Selecionar / propriedade</th><th>Produtor</th><th>CAD/PRO</th>{usaBep && <th>BEP C.Vale</th>}<th>Área faturada (alq.)</th><th>Sugestão ({produto?.unidade})</th><th>Embalagens a enviar</th></tr></thead>
          <tbody>{visiveis.map(p => { const item = itens[p.id]; return <tr key={p.id}>
            <td><label className="faturamento-checkbox"><input type="checkbox" checked={Boolean(item)} onChange={e => selecionar(p, e.target.checked)} />{p.nome}</label></td><td>{p.proprietario || "Não informado"}</td>
            <td>{item ? <select aria-label={`CAD/PRO de ${p.nome}`} required={Boolean(p.cad_pro_numeros.length)} value={item.cad_pro} onChange={e => atualizarItem(p.id, "cad_pro", e.target.value)}><option value="">{p.cad_pro_numeros.length ? "Selecione" : "Não informado"}</option>{p.cad_pro_numeros.map(c => <option key={c}>{c}</option>)}</select> : p.cad_pro_numeros.join(", ")}</td>
            {usaBep && <td>{item && <input aria-label={`BEP de ${p.nome}`} type="text" inputMode="numeric" pattern="[0-9]*" maxLength={40} value={item.bep || ""} onChange={e => atualizarItem(p.id, "bep", e.target.value)} />}</td>}
            <td>{item ? <input aria-label={`Área de ${p.nome}`} type="number" required min="0.000001" step="0.000001" value={item.area_alqueires} onChange={e => atualizarItem(p.id, "area_alqueires", e.target.value)} /> : numero(Number(p.area_hectares) / 2.42)}</td>
            <td>{item ? numero(Number(item.area_alqueires) * Number(form.dosagem_alqueire)) : "—"}</td>
            <td>{item && <input aria-label={`Embalagens de ${p.nome}`} type="number" min="0.001" step="0.001" required value={quantidadeParaEnviar(item, form.dosagem_alqueire, form.conteudo_embalagem, embalagensEditadas.current.has(p.id))} onChange={e => atualizarItem(p.id, "quantidade_embalagens", e.target.value)} />}{item && embalagensEditadas.current.has(p.id) && <button type="button" className="secundario sugestao-embalagens" onClick={() => {embalagensEditadas.current.delete(p.id); atualizarItem(p.id, "area_alqueires", item.area_alqueires);}}>Usar sugestão ({sugerirEmbalagens(item.area_alqueires, form.dosagem_alqueire, form.conteudo_embalagem) || "—"})</button>}</td>
          </tr>; })}</tbody></table></div>
        <label>Observações<textarea maxLength={1000} value={form.observacoes} onChange={e => { invalidar(); setForm({ ...form, observacoes: e.target.value }); }} /></label>
        <button type="submit">{ocupado ? "Calculando..." : "Simular e conferir"}</button>
      </fieldset>
    </form>}
    {previa && <RelatorioFaturamento resumo={previa} confirmado={Boolean(confirmado)} />}
    <div className="acoes nao-imprimir">
      {previa && !confirmado && <BotaoAcao acao="cadastrar" type="button" disabled={ocupado || incerto} motivoBloqueio={incerto ? "Existe confirmação pendente. Use Verificar / repetir confirmação para evitar baixa duplicada." : "Aguarde o processamento."} onClick={() => void confirmar()}>Confirmar envio e baixar estoque</BotaoAcao>}
      {previa && <BotaoAcao acao="imprimir" type="button" className="secundario" disabled={ocupado} onClick={() => window.print()}>Imprimir / salvar PDF</BotaoAcao>}
      {confirmado && <BotaoAcao acao="imprimir" type="button" className="secundario" disabled={ocupado} onClick={() => void exportarPdf(confirmado)}>Exportar PDF deste lançamento</BotaoAcao>}
      {confirmado && <button type="button" onClick={() => { invalidar(); setItens({}); protecao.marcarSalvo({form,itens:{}}); embalagensEditadas.current.clear(); }}>Novo faturamento</button>}
    </div>
    {confirmado && <p className="sucesso card nao-imprimir" role="status">Baixa registrada. Protocolo {confirmado.id} · {confirmado.responsavel}.</p>}

</PainelAba><PainelAba modulo="faturamento" aba="historico" ativa={aba}>
    <HistoricoFaturamento historico={historico} ocupado={ocupado || incerto} onVer={async h => { if (!(await protecao.confirmarDescarte())) return; setAba("novo"); setConfirmado(h); setPrevia(h.resumo); setPendente(null); }} onPdf={h => void exportarPdf(h)} onExcluir={h => void excluir(h)} />

</PainelAba>  </section>;
}
