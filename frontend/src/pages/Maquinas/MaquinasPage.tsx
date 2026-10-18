import AbasModulo, { PainelAba } from "../../components/AbasModulo";
import { BotaoAcao } from "../../components/AcoesContext";
import { FormEvent, useEffect, useRef, useState } from "react";
import axios from "axios";
import CorrecaoHistorico from "../../components/CorrecaoHistorico";
import { useAlteracoesNaoSalvas } from "../../components/AlteracoesNaoSalvas";

import {
  HistoricoMaquina,
  atualizarMaquina, excluirMaquina, editarManutencao, excluirManutencao,
  agendarManutencao,
  carregarMaquinas,
  concluirManutencao,
  criarMaquina,
  Maquina,
  Manutencao,
  registrarAbastecimento,
  registrarUso,
} from "../../api/maquinas";
import { OperacaoAgricola } from "../../api/operacoes";
import { Propriedade, rotuloPropriedade } from "../../api/propriedades";
import PainelFormulario from "../../components/PainelFormulario";
import { formatarData } from "../../utils/datas";


const hoje = new Date().toISOString().slice(0, 10);

function erroDe(falha: unknown) {
  if (axios.isAxiosError(falha)) {
    const dados = falha.response?.data;
    if (typeof dados?.detail === "string") return dados.detail;
    if (dados && typeof dados === "object") return Object.values(dados).flat().join(" ");
  }
  return "Não foi possível registrar os dados da máquina.";
}

export default function MaquinasPage({ propriedades }: { propriedades: Propriedade[] }) {
  const [aba, setAba] = useState("frota");
  const [maquinas, setMaquinas] = useState<Maquina[]>([]);
  const [usos, setUsos] = useState<HistoricoMaquina[]>([]);
  const [abastecimentos, setAbastecimentos] = useState<HistoricoMaquina[]>([]);
  const [manutencoes, setManutencoes] = useState<Manutencao[]>([]);
  const [operacoes, setOperacoes] = useState<OperacaoAgricola[]>([]);
  const [maquina, setMaquina] = useState({ identificacao: "", tipo: "trator", marca: "", modelo: "", ano: "", propriedade: "", horimetro_atual: "0", observacoes: "", status: "ativa" });
  const [edicaoMaquina, setEdicaoMaquina] = useState<Maquina | null>(null);
  const [edicaoManutencao, setEdicaoManutencao] = useState<Manutencao | null>(null);
  const [registro, setRegistro] = useState({ tipo: "uso", maquina: "", operacao: "", operador: "", data: hoje, horimetro_inicial: "", horimetro_final: "", litros: "", valor_total: "", horimetro: "", documento: "", descricao: "", data_prevista: hoje, horimetro_previsto: "" });
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const trava = useRef(false);
  const protecaoMaquina = useAlteracoesNaoSalvas(maquina, "máquina", edicaoMaquina?.id ?? null);
  const protecaoRegistro = useAlteracoesNaoSalvas(registro, "registro de máquina", edicaoManutencao?.id ?? null);
  async function remover(nome: string, acao: () => Promise<unknown>) {
    if (trava.current || !(await protecaoMaquina.confirmarDescarte()) || !(await protecaoRegistro.confirmarDescarte()) || !window.confirm(`Excluir ${nome}? Registros com histórico vinculado podem impedir a exclusão.`)) return;
    trava.current = true; setSalvando(true); setErro("");
    try { await acao(); setSucesso("Registro excluído."); await carregar(); } catch (e) { setErro(erroDe(e)); } finally { trava.current = false; setSalvando(false); }
  }


  async function carregar() {
    setCarregando(true);
    try {
      const dados = await carregarMaquinas();
      setMaquinas(dados.maquinas);
      setManutencoes(dados.manutencoes);
      setOperacoes(dados.operacoes);
      setUsos(dados.usos); setAbastecimentos(dados.abastecimentos);
    } catch (falha) {
      setErro(erroDe(falha));
    } finally { setCarregando(false); }
  }

  useEffect(() => { void carregar(); }, []);

  async function salvarMaquina(evento: FormEvent) {
    evento.preventDefault();
    if (trava.current) return;
    trava.current = true; setSalvando(true); setErro(""); setSucesso("");
    try {
      if (edicaoMaquina) await atualizarMaquina(edicaoMaquina.id, maquina, edicaoMaquina.atualizado_em); else await criarMaquina(maquina);
      setMaquina({ ...maquina, identificacao: "", marca: "", modelo: "", ano: "", horimetro_atual: "0", observacoes: "" });
      protecaoMaquina.marcarSalvo({ ...maquina, identificacao: "", marca: "", modelo: "", ano: "", horimetro_atual: "0", observacoes: "" });
      setEdicaoMaquina(null);
      setSucesso("Máquina salva.");
      await carregar();
    } catch (falha) { setErro(erroDe(falha)); }
    finally { trava.current = false; setSalvando(false); }
  }

  async function salvarRegistro(evento: FormEvent, tipoRegistro = registro.tipo) {
    evento.preventDefault();
    if (trava.current) return;
    trava.current = true; setSalvando(true); setErro(""); setSucesso("");
    try {
      if (tipoRegistro === "uso") {
        await registrarUso({ maquina: registro.maquina, operacao: registro.operacao, operador: registro.operador, data: registro.data, horimetro_inicial: registro.horimetro_inicial, horimetro_final: registro.horimetro_final });
      } else if (tipoRegistro === "abastecimento") {
        await registrarAbastecimento({ maquina: registro.maquina, data: registro.data, litros: registro.litros, valor_total: registro.valor_total, horimetro: registro.horimetro, documento: registro.documento });
      } else {
        if (edicaoManutencao) await editarManutencao(edicaoManutencao.id, { maquina: registro.maquina, descricao: registro.descricao, data_prevista: registro.data_prevista, horimetro_previsto: registro.horimetro_previsto }); else await agendarManutencao({ maquina: registro.maquina, descricao: registro.descricao, data_prevista: registro.data_prevista, horimetro_previsto: registro.horimetro_previsto });
        setEdicaoManutencao(null);
      }
      setSucesso("Registro salvo com rastreabilidade.");
      protecaoRegistro.marcarSalvo({ ...registro, horimetro_inicial: "", horimetro_final: "", litros: "", valor_total: "", horimetro: "", descricao: "", documento: "" });
      setRegistro(atual => ({ ...atual, horimetro_inicial: "", horimetro_final: "", litros: "", valor_total: "", horimetro: "", descricao: "", documento: "" }));
      await carregar();
    } catch (falha) { setErro(erroDe(falha)); }
    finally { trava.current = false; setSalvando(false); }
  }

  async function concluir(item: Manutencao) {
    if (trava.current) return;
    const horimetro = window.prompt("Horímetro na conclusão:");
    if (!horimetro) return;
    const custo = window.prompt("Custo da manutenção:", "0") ?? "0";
    trava.current = true; setSalvando(true); setErro(""); setSucesso("");
    try {
      await concluirManutencao(item.id, { data_conclusao: hoje, horimetro_realizado: horimetro, custo });
      setSucesso("Manutenção concluída.");
      await carregar();
    } catch (falha) { setErro(erroDe(falha)); }
    finally { trava.current = false; setSalvando(false); }
  }

  const formularioRegistro = (tipoRegistro: string) => (
        <PainelFormulario edicao={edicaoManutencao?.id} key={edicaoManutencao?.id ?? tipoRegistro} titulo={tipoRegistro === "manutencao" ? "Agendar manutenção" : "Registrar uso ou combustível"} inicialmenteAberto>
        <form className="card formulario" onSubmit={e => void salvarRegistro(e,tipoRegistro)}>
          <fieldset className="campos-formulario" disabled={salvando || carregando}>
          <h2>{tipoRegistro === "manutencao" ? "Agendar manutenção" : "Uso e combustível"}</h2>
          {tipoRegistro !== "manutencao" && <label>Registro<select value={tipoRegistro} onChange={(e) => setRegistro({ ...registro, tipo: e.target.value })}><option value="uso">Uso em operação</option><option value="abastecimento">Abastecimento</option></select></label>}
          <label>Máquina<select required value={registro.maquina} onChange={(e) => setRegistro({ ...registro, maquina: e.target.value })}><option value="">Selecione</option>{maquinas.map((item) => <option key={item.id} value={item.id}>{item.identificacao} · {item.horimetro_atual} h</option>)}</select></label>
          {tipoRegistro === "uso" && <><label>Operação<select required value={registro.operacao} onChange={(e) => setRegistro({ ...registro, operacao: e.target.value })}><option value="">Selecione</option>{operacoes.map((item) => <option key={item.id} value={item.id}>{item.descricao}</option>)}</select></label><label>Operador<input value={registro.operador} onChange={(e) => setRegistro({ ...registro, operador: e.target.value })} /></label><div className="linha"><label>Horímetro inicial<input required step="0.1" type="number" value={registro.horimetro_inicial} onChange={(e) => setRegistro({ ...registro, horimetro_inicial: e.target.value })} /></label><label>Horímetro final<input required step="0.1" type="number" value={registro.horimetro_final} onChange={(e) => setRegistro({ ...registro, horimetro_final: e.target.value })} /></label></div></>}
          {tipoRegistro === "abastecimento" && <><div className="linha"><label>Litros<input required min="0.01" step="0.01" type="number" value={registro.litros} onChange={(e) => setRegistro({ ...registro, litros: e.target.value })} /></label><label>Valor total<input required min="0" step="0.01" type="number" value={registro.valor_total} onChange={(e) => setRegistro({ ...registro, valor_total: e.target.value })} /></label></div><label>Horímetro<input required step="0.1" type="number" value={registro.horimetro} onChange={(e) => setRegistro({ ...registro, horimetro: e.target.value })} /></label><label>Documento<input value={registro.documento} onChange={(e) => setRegistro({ ...registro, documento: e.target.value })} /></label></>}
          {tipoRegistro === "manutencao" && <><label>Descrição<input required value={registro.descricao} onChange={(e) => setRegistro({ ...registro, descricao: e.target.value })} /></label><label>Data prevista<input required type="date" value={registro.data_prevista} onChange={(e) => setRegistro({ ...registro, data_prevista: e.target.value })} /></label><label>Horímetro previsto<input step="0.1" type="number" value={registro.horimetro_previsto} onChange={(e) => setRegistro({ ...registro, horimetro_previsto: e.target.value })} /></label></>}
          {tipoRegistro !== "manutencao" && <label>Data<input required type="date" value={registro.data} onChange={(e) => setRegistro({ ...registro, data: e.target.value })} /></label>}
          <BotaoAcao acao={edicaoManutencao ? "editar" : "cadastrar"} disabled={salvando || carregando} type="submit">{salvando ? "Salvando..." : "Salvar registro"}</BotaoAcao>{edicaoManutencao && <button type="button" disabled={salvando} onClick={async () => { if (!(await protecaoRegistro.confirmarDescarte())) return; const dados={...registro, descricao:"", horimetro_previsto:""}; setEdicaoManutencao(null); setRegistro(dados); protecaoRegistro.marcarSalvo(dados); }}>Cancelar edição</button>}
          </fieldset>
        </form>
        </PainelFormulario>
  );
  return (
    <section className="modulo-maquinas">
      {carregando && <p className="card" role="status">Carregando frota e manutenções...</p>}
      {salvando && <p className="card" role="status">Salvando registro. Aguarde...</p>}
      {erro && <p className="erro card" role="alert">{erro}</p>}
      {sucesso && <p className="sucesso card" role="status">{sucesso}</p>}
      <section className="resumos-estoque">
        <article className="card"><span>Máquinas</span><strong>{maquinas.length}</strong></article>
        <article className="card"><span>Ativas</span><strong>{maquinas.filter((item) => item.status === "ativa").length}</strong></article>
        <article className="card alerta-estoque"><span>Manutenções agendadas</span><strong>{manutencoes.filter((item) => item.status === "agendada").length}</strong></article>
      </section>
<AbasModulo modulo="maquinas" ativa={aba} alterar={setAba} desabilitado={salvando} abas={[{id:"frota",titulo:"Frota"},{id:"uso",titulo:"Uso e combustível"},{id:"manutencoes",titulo:"Manutenções"}]} /><PainelAba modulo="maquinas" aba="frota" ativa={aba}>

        <PainelFormulario edicao={edicaoMaquina?.id} key={edicaoMaquina?.id ?? "nova"} titulo={edicaoMaquina ? "Editar máquina" : "Nova máquina"} inicialmenteAberto={!!edicaoMaquina}>
        <form className="card formulario" onSubmit={salvarMaquina}>
          <fieldset className="campos-formulario" disabled={salvando || carregando}>
          <h2>{edicaoMaquina ? "Editar máquina" : "Nova máquina"}</h2>
          <label>Identificação<input required value={maquina.identificacao} onChange={(e) => setMaquina({ ...maquina, identificacao: e.target.value })} /></label>
          <label>Situação<select value={maquina.status} onChange={e => setMaquina({...maquina, status:e.target.value})}><option value="ativa">Ativa</option><option value="manutencao">Manutenção</option><option value="inativa">Inativa</option></select></label><label>Tipo<select value={maquina.tipo} onChange={(e) => setMaquina({ ...maquina, tipo: e.target.value })}><option value="trator">Trator</option><option value="colheitadeira">Colheitadeira</option><option value="pulverizador">Pulverizador</option><option value="implemento">Implemento</option><option value="caminhao">Caminhão</option><option value="outro">Outro</option></select></label>
          <div className="linha"><label>Marca<input value={maquina.marca} onChange={(e) => setMaquina({ ...maquina, marca: e.target.value })} /></label><label>Modelo<input value={maquina.modelo} onChange={(e) => setMaquina({ ...maquina, modelo: e.target.value })} /></label></div>
          <div className="linha"><label>Ano<input min="1900" type="number" value={maquina.ano} onChange={(e) => setMaquina({ ...maquina, ano: e.target.value })} /></label><label>Horímetro<input min="0" step="0.1" type="number" value={maquina.horimetro_atual} onChange={(e) => setMaquina({ ...maquina, horimetro_atual: e.target.value })} /></label></div>
          <label>Propriedade<select value={maquina.propriedade} onChange={(e) => setMaquina({ ...maquina, propriedade: e.target.value })}><option value="">Sem vínculo</option>{propriedades.map((item) => <option key={item.id} value={item.id}>{rotuloPropriedade(item)}</option>)}</select></label>
          <label>Observações<textarea value={maquina.observacoes} onChange={(e) => setMaquina({ ...maquina, observacoes: e.target.value })} /></label>
          <BotaoAcao acao={edicaoMaquina ? "editar" : "cadastrar"} disabled={salvando || carregando} type="submit">{salvando ? "Salvando..." : edicaoMaquina ? "Salvar alterações" : "Cadastrar máquina"}</BotaoAcao>{edicaoMaquina && <button type="button" disabled={salvando} onClick={async () => { if (!(await protecaoMaquina.confirmarDescarte())) return; const dados={identificacao:"",tipo:"trator",marca:"",modelo:"",ano:"",propriedade:"",horimetro_atual:"0",observacoes:"",status:"ativa"}; setEdicaoMaquina(null); setMaquina(dados); protecaoMaquina.marcarSalvo(dados); }}>Cancelar edição</button>}
          </fieldset>
        </form>
        </PainelFormulario>


      <section className="card"><h2>Frota e horímetros</h2>{!carregando && !maquinas.length && <p className="vazio">Nenhuma máquina cadastrada.</p>}<div className="lista">{maquinas.map((item) => <article className="item" key={item.id}><div><h3>{item.identificacao}</h3><p>{item.marca} {item.modelo} · {item.propriedade_nome || "Sem propriedade"} · {item.status}</p></div><strong>{item.horimetro_atual} h</strong><div className="acoes"><BotaoAcao acao="editar" disabled={salvando} onClick={async () => { if (!(await protecaoMaquina.confirmarDescarte())) return; const dados = { identificacao:item.identificacao, tipo:item.tipo, marca:item.marca, modelo:item.modelo, ano:String(item.ano ?? ""), propriedade:String(item.propriedade ?? ""), horimetro_atual:item.horimetro_atual, observacoes:item.observacoes, status:item.status }; setEdicaoMaquina(item); setMaquina(dados); protecaoMaquina.marcarSalvo(dados); }}>Editar</BotaoAcao><BotaoAcao acao="excluir" className="perigo" disabled={salvando} onClick={() => void remover(item.identificacao, () => excluirMaquina(item.id))}>Excluir</BotaoAcao></div></article>)}</div></section>

</PainelAba><PainelAba modulo="maquinas" aba="uso" ativa={aba}>
{formularioRegistro(registro.tipo === "manutencao" ? "uso" : registro.tipo)}<section className="card"><h2>Histórico de uso</h2>{usos.map(item => <article className="card" key={item.id}><h3>{item.maquina_nome} · {formatarData(item.data)}</h3><p>{item.operacao_nome} · {item.horimetro_inicial} a {item.horimetro_final} h</p><CorrecaoHistorico base="/maquinas/usos/" dados={item} horimetro campos={[{nome:"operador",rotulo:"Operador",opcional:true},{nome:"data",rotulo:"Data",tipo:"date"},{nome:"horimetro_inicial",rotulo:"Horímetro inicial",tipo:"number"},{nome:"horimetro_final",rotulo:"Horímetro final",tipo:"number"},{nome:"observacoes",rotulo:"Observações",opcional:true}]} atualizar={() => void carregar()} /></article>)}</section><section className="card"><h2>Histórico de combustível</h2>{abastecimentos.map(item => <article className="card" key={item.id}><h3>{item.maquina_nome} · {formatarData(item.data)}</h3><p>{item.litros} litros · R$ {item.valor_total}</p><CorrecaoHistorico base="/maquinas/abastecimentos/" dados={item} horimetro campos={[{nome:"data",rotulo:"Data",tipo:"date"},{nome:"litros",rotulo:"Litros",tipo:"number"},{nome:"valor_total",rotulo:"Valor total (R$)",tipo:"number"},{nome:"horimetro",rotulo:"Horímetro do abastecimento",tipo:"number"},{nome:"documento",rotulo:"Documento",opcional:true},{nome:"observacoes",rotulo:"Observações",opcional:true}]} atualizar={() => void carregar()} /></article>)}</section>
</PainelAba><PainelAba modulo="maquinas" aba="manutencoes" ativa={aba}>
{formularioRegistro("manutencao")}      <section className="card"><h2>Manutenções</h2>{!carregando && !manutencoes.length && <p className="vazio">Nenhuma manutenção cadastrada.</p>}<div className="lista">{manutencoes.map((item) => <article className="item" key={item.id}><div><h3>{item.descricao}</h3><p>{item.maquina_nome} · prevista {formatarData(item.data_prevista)} · {item.status}</p></div>{item.status === "agendada" && <div className="acoes"><BotaoAcao acao="editar" disabled={salvando} onClick={async () => { if (!(await protecaoRegistro.confirmarDescarte())) return; const dados = {...registro, maquina:String(item.maquina), descricao:item.descricao, data_prevista:item.data_prevista, horimetro_previsto:item.horimetro_previsto ?? ""}; setEdicaoManutencao(item); setRegistro(dados); protecaoRegistro.marcarSalvo(dados); }}>Editar</BotaoAcao><BotaoAcao acao="excluir" className="perigo" disabled={salvando} onClick={() => void remover(item.descricao, () => excluirManutencao(item.id))}>Excluir</BotaoAcao></div>}{item.status === "agendada" && <BotaoAcao acao="editar" disabled={salvando || carregando} type="button" onClick={() => void concluir(item)}>Concluir</BotaoAcao>}<CorrecaoHistorico base="/maquinas/manutencoes/" dados={item} horimetro campos={[{nome:"descricao",rotulo:"Descrição"},{nome:"data_prevista",rotulo:"Data prevista",tipo:"date"},{nome:"horimetro_previsto",rotulo:"Horímetro previsto",tipo:"number",nullable:true},{nome:"data_conclusao",rotulo:"Data de conclusão",tipo:"date",nullable:true},{nome:"horimetro_realizado",rotulo:"Horímetro realizado",tipo:"number",nullable:true},{nome:"custo",rotulo:"Custo (R$)",tipo:"number"},{nome:"observacoes",rotulo:"Observações",opcional:true}]} atualizar={() => void carregar()} /></article>)}</div></section>

</PainelAba>    </section>
  );
}
