import axios from "axios";
import { FormEvent, useEffect, useRef, useState } from "react";
import { carregarContratos, ContratoComercial, DadosContrato, excluirContrato, reativarContrato, salvarContrato } from "../../api/contratosComerciais";

const vazio: DadosContrato = { empresa: "", numero: "", quantidade_kg: "", produto: "" };

export function quantidadeContrato(valor: string) {
  const limpo = valor.trim();
  if (!/^\d+(?:\.\d{3})*(?:,\d{1,3})?$/.test(limpo)) throw new Error("Use ponto para milhares e vírgula para decimais. Exemplo: 35.000,500.");
  const normalizado = limpo.replace(/\./g, "").replace(",", ".");
  if (Number(normalizado) <= 0) throw new Error("A quantidade deve ser maior que zero.");
  return normalizado;
}

export default function ContratosComerciais() {
  const [itens, setItens] = useState<ContratoComercial[]>([]);
  const [form, setForm] = useState<DadosContrato>(vazio);
  const [edicao, setEdicao] = useState<number>();
  const [historico, setHistorico] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const trava = useRef(false);
  const carregar = async () => setItens(await carregarContratos());
  function falhou(falha: unknown) {
    if (axios.isAxiosError(falha) && falha.response?.data) setErro(Object.values(falha.response.data).flat().join(" "));
    else setErro(falha instanceof Error ? falha.message : "Não foi possível carregar os contratos.");
  }
  useEffect(() => { void carregar().catch(falhou).finally(() => setCarregando(false)); }, []);
  async function executar(acao: () => Promise<unknown>, mensagem: string) {
    if (trava.current) return;
    trava.current = true; setOcupado(true); setErro(""); setSucesso("");
    try { await acao(); setForm(vazio); setEdicao(undefined); setSucesso(mensagem); await carregar(); }
    catch (falha) { falhou(falha); }
    finally { trava.current = false; setOcupado(false); }
  }
  function salvar(e: FormEvent) {
    e.preventDefault();
    void executar(() => salvarContrato({ ...form, quantidade_kg: quantidadeContrato(form.quantidade_kg) }, edicao), "Contrato salvo.");
  }
  return <section className="card" aria-label="Cadastro de contratos">
    <h3>Contratos</h3><p>Cadastre empresa, número, quantidade e produto para selecionar o contrato em Vendas. Este cadastro não movimenta estoque.</p>
    {erro && <p className="erro" role="alert">{erro}</p>}{sucesso && <p className="sucesso" role="status">{sucesso}</p>}
    <form className="conteudo" onSubmit={salvar}>
      <label>Empresa<input required maxLength={160} value={form.empresa} onChange={e => setForm({ ...form, empresa: e.target.value })} /></label>
      <label>Nº do contrato<input required maxLength={80} value={form.numero} onChange={e => setForm({ ...form, numero: e.target.value })} /></label>
      <label>Quantidade (kg)<input required inputMode="decimal" placeholder="Ex.: 35.000,500" value={form.quantidade_kg} onChange={e => setForm({ ...form, quantidade_kg: e.target.value })} /></label>
      <label>Produto<input required maxLength={80} list="produtos-contrato" placeholder="Ex.: Soja" value={form.produto} onChange={e => setForm({ ...form, produto: e.target.value })} /></label>
      <datalist id="produtos-contrato"><option value="Soja" /><option value="Milho" /><option value="Trigo" /></datalist>
      <div className="acoes"><button disabled={ocupado} type="submit">{edicao ? "Salvar contrato" : "Cadastrar contrato"}</button>{edicao && <button type="button" className="secundario" disabled={ocupado} onClick={() => { setForm(vazio); setEdicao(undefined); }}>Cancelar edição</button>}</div>
    </form>
    <label><input type="checkbox" checked={historico} onChange={e => setHistorico(e.target.checked)} /> Mostrar contratos excluídos</label>
    <div className="lista">{itens.filter(i => historico || i.ativo).map(item => <article className="item" key={item.id}><div><h4>{item.empresa} · {item.numero}</h4><p>{item.produto || "Produto não informado"} · {item.quantidade_kg === null ? "Quantidade não informada" : `${Number(item.quantidade_kg).toLocaleString("pt-BR", { maximumFractionDigits: 3 })} kg`}</p><small>{item.ativo ? "Ativo" : "Excluído da seleção; histórico preservado"}</small><div className="acoes"><button type="button" className="secundario" disabled={ocupado} onClick={() => { setEdicao(item.id); setForm({ empresa: item.empresa, numero: item.numero, produto: item.produto, quantidade_kg: item.quantidade_kg === null ? "" : Number(item.quantidade_kg).toLocaleString("pt-BR", { maximumFractionDigits: 3 }) }); }}>Editar</button>{item.ativo ? <button type="button" className="perigo" disabled={ocupado} onClick={() => { if (window.confirm(`Excluir contrato ${item.numero} / ${item.empresa} da seleção de novas vendas? O histórico será preservado.`)) void executar(() => excluirContrato(item.id), "Contrato excluído da seleção."); }}>Excluir</button> : <button type="button" disabled={ocupado} onClick={() => void executar(() => reativarContrato(item.id), "Contrato reativado.")}>Reativar</button>}</div></div></article>)}{!itens.some(i => historico || i.ativo) && <p>{carregando ? "Carregando contratos..." : "Nenhum contrato cadastrado."}</p>}</div>
  </section>;
}
