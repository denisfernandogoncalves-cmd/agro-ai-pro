import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { excluirMotorista, listarMotoristas, Motorista, salvarMotorista } from "../../api/transportes";
import { BotaoAcao } from "../../components/AcoesContext";
import { useAlteracoesNaoSalvas } from "../../components/AlteracoesNaoSalvas";
import { useConfirmacaoCompacta } from "../../components/ConfirmacaoCompacta";

const vazio = { nome: "", apelido: "", ativo: true };

export function ListaMotoristas({ itens, ocupado, editar, excluir, reativar }: {
  itens: Motorista[]; ocupado: boolean; editar: (m: Motorista) => void;
  excluir: (m: Motorista) => void; reativar: (m: Motorista) => void;
}) {
  const ativos = itens.filter(m => m.ativo);
  const inativos = itens.filter(m => !m.ativo);
  const linha = (m: Motorista) => <div className="item" key={m.id}>
    <span>{m.apelido ? `${m.apelido} · ${m.nome}` : m.nome} · {m.ativo ? "Ativo" : "Inativo"}</span>
    <div className="acoes"><BotaoAcao acao="editar" type="button" className="secundario" disabled={ocupado} onClick={() => editar(m)}>Editar motorista</BotaoAcao>
      {m.ativo ? <BotaoAcao acao="excluir" type="button" className="perigo" disabled={ocupado} onClick={() => excluir(m)}>Excluir motorista</BotaoAcao>
        : <BotaoAcao acao="editar" type="button" disabled={ocupado} onClick={() => reativar(m)}>Reativar motorista</BotaoAcao>}
    </div>
  </div>;
  return <><div className="lista" aria-label="Motoristas ativos">{ativos.map(linha)}{!ativos.length && <p>Nenhum motorista ativo.</p>}</div>
    {inativos.length > 0 && <details className="motoristas-inativos"><summary>Motoristas excluídos / inativos ({inativos.length})</summary><p>Histórico e vínculos preservados. Reative o cadastro para utilizá-lo novamente.</p><div className="lista">{inativos.map(linha)}</div></details>}
  </>;
}

export default function CadastroMotoristas() {
  const confirmar = useConfirmacaoCompacta();
  const trava = useRef(false);
  const [itens, setItens] = useState<Motorista[]>([]);
  const [item, setItem] = useState<Motorista | null>(null);
  const [form, setForm] = useState(vazio);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [revisao, setRevisao] = useState(0);
  const protecao = useAlteracoesNaoSalvas(form, "cadastro do motorista", item?.id ?? null);
  async function alterarSituacao(m: Motorista, reativar: boolean) {
    if (trava.current) return;
    trava.current = true;
    try {
      if (item?.id === m.id && !(await protecao.confirmarDescarte())) return;
      if (!reativar && !(await confirmar({ titulo:"Excluir motorista", perigo:true, confirmar:"Excluir motorista", mensagem:`Excluir ${m.nome} da lista de ativos? Ele ficará na seção de excluídos/inativos, com todo o histórico preservado.` }))) return;
      setOcupado(true); setErro(""); setSucesso("");
      const salvo = reativar
        ? await salvarMotorista(m.id, { nome:m.nome, apelido:m.apelido, ativo:true, versao_correcao_original:m.versao_correcao })
        : await excluirMotorista(m);
      setItens(atuais => atuais.map(atual => atual.id === m.id ? salvo : atual));
      if (item?.id === m.id) { setItem(null); setForm(vazio); protecao.marcarSalvo(vazio); }
      setSucesso(reativar ? "Motorista reativado." : "Motorista excluído da lista de ativos. Histórico preservado.");
    } catch (falha) { setErro(axios.isAxiosError(falha) && falha.response?.data ? Object.values(falha.response.data).flat().join(" ") : "Não foi possível atualizar o motorista."); }
    finally { trava.current = false; setOcupado(false); }
  }
  useEffect(() => {
    let ativo = true;
    void listarMotoristas().then(d => { if (ativo) setItens(d); }).catch(() => { if (ativo) setErro("Não foi possível consultar os motoristas."); });
    return () => { ativo = false; };
  }, [revisao]);
  return <section className="card"><h2>Cadastro de motoristas</h2><p>Cadastre o motorista uma vez e selecione-o nas cargas, independentemente do caminhão. Inativar preserva os registros anteriores.</p>
    {erro && <p role="alert" className="erro">{erro}</p>}{sucesso && <p role="status">{sucesso}</p>}
    <form className="formulario" onSubmit={async e => {
      e.preventDefault(); if (trava.current) return; trava.current = true; setOcupado(true); setErro(""); setSucesso("");
      try {
        await salvarMotorista(item?.id ?? null, { ...form, ...(item ? { versao_correcao_original: item.versao_correcao } : {}) });
        setItem(null); setForm(vazio); protecao.marcarSalvo(vazio); setSucesso("Motorista salvo."); setRevisao(r => r + 1);
      } catch (falha) { setErro(axios.isAxiosError(falha) && falha.response?.data ? Object.values(falha.response.data).flat().join(" ") : "Não foi possível salvar o motorista."); }
      finally { trava.current = false; setOcupado(false); }
    }}>
      <label>Nome do motorista<input required maxLength={120} value={form.nome} onChange={e => setForm({ ...form, nome: e.target.value })} /></label>
      <label>Apelido do motorista<input maxLength={80} value={form.apelido} onChange={e => setForm({ ...form, apelido: e.target.value })} /></label>
      <label>Situação do motorista<select value={String(form.ativo)} onChange={e => setForm({ ...form, ativo: e.target.value === "true" })}><option value="true">Ativo</option><option value="false">Inativo</option></select></label>
      <div className="acoes"><BotaoAcao acao={item ? "editar" : "cadastrar"} disabled={ocupado}>Salvar motorista</BotaoAcao><button type="button" className="secundario" disabled={ocupado} onClick={async () => { if (await protecao.confirmarDescarte()) { setItem(null); setForm(vazio); protecao.marcarSalvo(vazio); } }}>Cancelar</button></div>
    </form>
    <ListaMotoristas itens={itens} ocupado={ocupado} editar={async m => { if (await protecao.confirmarDescarte()) { const dados = { nome:m.nome, apelido:m.apelido, ativo:m.ativo }; setItem(m); setForm(dados); protecao.marcarSalvo(dados); } }} excluir={m => void alterarSituacao(m, false)} reativar={m => void alterarSituacao(m, true)} />
    {!itens.length && <p>Nenhum motorista cadastrado.</p>}
  </section>;
}
