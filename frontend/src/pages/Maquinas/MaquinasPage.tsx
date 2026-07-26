import { FormEvent, useEffect, useState } from "react";
import axios from "axios";

import {
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
import { Propriedade } from "../../api/propriedades";


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
  const [maquinas, setMaquinas] = useState<Maquina[]>([]);
  const [manutencoes, setManutencoes] = useState<Manutencao[]>([]);
  const [operacoes, setOperacoes] = useState<OperacaoAgricola[]>([]);
  const [maquina, setMaquina] = useState({ identificacao: "", tipo: "trator", marca: "", modelo: "", ano: "", propriedade: "", horimetro_atual: "0", observacoes: "" });
  const [registro, setRegistro] = useState({ tipo: "uso", maquina: "", operacao: "", operador: "", data: hoje, horimetro_inicial: "", horimetro_final: "", litros: "", valor_total: "", horimetro: "", documento: "", descricao: "", data_prevista: hoje, horimetro_previsto: "" });
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");

  async function carregar() {
    try {
      const dados = await carregarMaquinas();
      setMaquinas(dados.maquinas);
      setManutencoes(dados.manutencoes);
      setOperacoes(dados.operacoes);
    } catch (falha) {
      setErro(erroDe(falha));
    }
  }

  useEffect(() => { void carregar(); }, []);

  async function salvarMaquina(evento: FormEvent) {
    evento.preventDefault();
    try {
      await criarMaquina(maquina);
      setMaquina({ ...maquina, identificacao: "", marca: "", modelo: "", ano: "", horimetro_atual: "0", observacoes: "" });
      setSucesso("Máquina cadastrada.");
      await carregar();
    } catch (falha) { setErro(erroDe(falha)); }
  }

  async function salvarRegistro(evento: FormEvent) {
    evento.preventDefault();
    setErro("");
    try {
      if (registro.tipo === "uso") {
        await registrarUso({ maquina: registro.maquina, operacao: registro.operacao, operador: registro.operador, data: registro.data, horimetro_inicial: registro.horimetro_inicial, horimetro_final: registro.horimetro_final });
      } else if (registro.tipo === "abastecimento") {
        await registrarAbastecimento({ maquina: registro.maquina, data: registro.data, litros: registro.litros, valor_total: registro.valor_total, horimetro: registro.horimetro, documento: registro.documento });
      } else {
        await agendarManutencao({ maquina: registro.maquina, descricao: registro.descricao, data_prevista: registro.data_prevista, horimetro_previsto: registro.horimetro_previsto });
      }
      setSucesso("Registro salvo com rastreabilidade.");
      await carregar();
    } catch (falha) { setErro(erroDe(falha)); }
  }

  async function concluir(item: Manutencao) {
    const horimetro = window.prompt("Horímetro na conclusão:");
    if (!horimetro) return;
    const custo = window.prompt("Custo da manutenção:", "0") ?? "0";
    try {
      await concluirManutencao(item.id, { data_conclusao: hoje, horimetro_realizado: horimetro, custo });
      setSucesso("Manutenção concluída.");
      await carregar();
    } catch (falha) { setErro(erroDe(falha)); }
  }

  return (
    <section className="modulo-maquinas">
      {erro && <p className="erro card">{erro}</p>}
      {sucesso && <p className="sucesso card">{sucesso}</p>}
      <section className="resumos-estoque">
        <article className="card"><span>Máquinas</span><strong>{maquinas.length}</strong></article>
        <article className="card"><span>Ativas</span><strong>{maquinas.filter((item) => item.status === "ativa").length}</strong></article>
        <article className="card alerta-estoque"><span>Manutenções agendadas</span><strong>{manutencoes.filter((item) => item.status === "agendada").length}</strong></article>
      </section>
      <section className="grade maquinas-grade">
        <form className="card formulario" onSubmit={salvarMaquina}>
          <h2>Nova máquina</h2>
          <label>Identificação<input required value={maquina.identificacao} onChange={(e) => setMaquina({ ...maquina, identificacao: e.target.value })} /></label>
          <label>Tipo<select value={maquina.tipo} onChange={(e) => setMaquina({ ...maquina, tipo: e.target.value })}><option value="trator">Trator</option><option value="colheitadeira">Colheitadeira</option><option value="pulverizador">Pulverizador</option><option value="implemento">Implemento</option><option value="caminhao">Caminhão</option><option value="outro">Outro</option></select></label>
          <div className="linha"><label>Marca<input value={maquina.marca} onChange={(e) => setMaquina({ ...maquina, marca: e.target.value })} /></label><label>Modelo<input value={maquina.modelo} onChange={(e) => setMaquina({ ...maquina, modelo: e.target.value })} /></label></div>
          <div className="linha"><label>Ano<input min="1900" type="number" value={maquina.ano} onChange={(e) => setMaquina({ ...maquina, ano: e.target.value })} /></label><label>Horímetro<input min="0" step="0.1" type="number" value={maquina.horimetro_atual} onChange={(e) => setMaquina({ ...maquina, horimetro_atual: e.target.value })} /></label></div>
          <label>Propriedade<select value={maquina.propriedade} onChange={(e) => setMaquina({ ...maquina, propriedade: e.target.value })}><option value="">Sem vínculo</option>{propriedades.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
          <label>Observações<textarea value={maquina.observacoes} onChange={(e) => setMaquina({ ...maquina, observacoes: e.target.value })} /></label>
          <button type="submit">Cadastrar máquina</button>
        </form>
        <form className="card formulario" onSubmit={salvarRegistro}>
          <h2>Uso, combustível e manutenção</h2>
          <label>Registro<select value={registro.tipo} onChange={(e) => setRegistro({ ...registro, tipo: e.target.value })}><option value="uso">Uso em operação</option><option value="abastecimento">Abastecimento</option><option value="manutencao">Agendar manutenção</option></select></label>
          <label>Máquina<select required value={registro.maquina} onChange={(e) => setRegistro({ ...registro, maquina: e.target.value })}><option value="">Selecione</option>{maquinas.map((item) => <option key={item.id} value={item.id}>{item.identificacao} · {item.horimetro_atual} h</option>)}</select></label>
          {registro.tipo === "uso" && <><label>Operação<select required value={registro.operacao} onChange={(e) => setRegistro({ ...registro, operacao: e.target.value })}><option value="">Selecione</option>{operacoes.map((item) => <option key={item.id} value={item.id}>{item.descricao}</option>)}</select></label><label>Operador<input value={registro.operador} onChange={(e) => setRegistro({ ...registro, operador: e.target.value })} /></label><div className="linha"><label>Horímetro inicial<input required step="0.1" type="number" value={registro.horimetro_inicial} onChange={(e) => setRegistro({ ...registro, horimetro_inicial: e.target.value })} /></label><label>Horímetro final<input required step="0.1" type="number" value={registro.horimetro_final} onChange={(e) => setRegistro({ ...registro, horimetro_final: e.target.value })} /></label></div></>}
          {registro.tipo === "abastecimento" && <><div className="linha"><label>Litros<input required min="0.01" step="0.01" type="number" value={registro.litros} onChange={(e) => setRegistro({ ...registro, litros: e.target.value })} /></label><label>Valor total<input required min="0" step="0.01" type="number" value={registro.valor_total} onChange={(e) => setRegistro({ ...registro, valor_total: e.target.value })} /></label></div><label>Horímetro<input required step="0.1" type="number" value={registro.horimetro} onChange={(e) => setRegistro({ ...registro, horimetro: e.target.value })} /></label><label>Documento<input value={registro.documento} onChange={(e) => setRegistro({ ...registro, documento: e.target.value })} /></label></>}
          {registro.tipo === "manutencao" && <><label>Descrição<input required value={registro.descricao} onChange={(e) => setRegistro({ ...registro, descricao: e.target.value })} /></label><label>Data prevista<input required type="date" value={registro.data_prevista} onChange={(e) => setRegistro({ ...registro, data_prevista: e.target.value })} /></label><label>Horímetro previsto<input step="0.1" type="number" value={registro.horimetro_previsto} onChange={(e) => setRegistro({ ...registro, horimetro_previsto: e.target.value })} /></label></>}
          {registro.tipo !== "manutencao" && <label>Data<input required type="date" value={registro.data} onChange={(e) => setRegistro({ ...registro, data: e.target.value })} /></label>}
          <button type="submit">Salvar registro</button>
        </form>
      </section>
      <section className="card"><h2>Frota e horímetros</h2><div className="lista">{maquinas.map((item) => <article className="item" key={item.id}><div><h3>{item.identificacao}</h3><p>{item.marca} {item.modelo} · {item.propriedade_nome || "Sem propriedade"} · {item.status}</p></div><strong>{item.horimetro_atual} h</strong></article>)}</div></section>
      <section className="card"><h2>Manutenções</h2><div className="lista">{manutencoes.map((item) => <article className="item" key={item.id}><div><h3>{item.descricao}</h3><p>{item.maquina_nome} · prevista {item.data_prevista} · {item.status}</p></div>{item.status === "agendada" && <button type="button" onClick={() => void concluir(item)}>Concluir</button>}</article>)}</div></section>
    </section>
  );
}
