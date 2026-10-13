import { FormEvent, useEffect, useRef, useState } from "react";
import axios from "axios";
import { api } from "../api/propriedades";
import { autorizado } from "../components/AcoesContext";
import type { UsuarioAtual } from "../api/usuarios";
import { geracaoSessaoValida, obterAccessToken, obterGeracaoSessao, estaAutenticado } from "../auth/sessionCoordinator";
import { ArmazenamentoOffline } from "./armazenamento.mjs";
import { FilaOffline, IdentidadeOffline, ItemOffline, novoUUID } from "./fila.mjs";

type Referencia = { id: number | string; nome?: string; codigo?: string };
type Snapshot = { registro: Record<string, unknown>; versao: string };
type Contexto = IdentidadeOffline & {
  preparadoEm: string; acesso: UsuarioAtual;
  propriedades: Referencia[]; cadpros: Referencia[]; armazens: Referencia[]; snapshots: Snapshot[];
};
const storage = new ArmazenamentoOffline();
function chaveContexto() {
  if (!estaAutenticado()) return null;
  try {
    const payload = obterAccessToken()!.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const usuario = JSON.parse(atob(payload)).user_id;
    return Number.isInteger(Number(usuario)) ? `${location.origin}:${usuario}` : null;
  } catch { return null; }
}
const vazio = () => ({ propriedade: "", cad_pro: "", armazem: "", cultura: "Soja", safra: "",
  data_colheita: new Date().toLocaleDateString("sv-SE"), peso_bruto_kg: "", umidade_percentual: "13",
  impureza_percentual: "0", defeitos_percentual: "0", ph: "", placa: "", motorista: "", observacoes: "", motivo_correcao: "" });
type Formulario = ReturnType<typeof vazio>;

export default function TrabalhoOffline() {
  const [contexto, setContexto] = useState<Contexto | null>(null);
  const [itens, setItens] = useState<ItemOffline[]>([]);
  const [dados, setDados] = useState<Formulario>(vazio);
  const [mensagem, setMensagem] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [idCarga, setIdCarga] = useState("");
  const [original, setOriginal] = useState<Snapshot | null>(null);
  const [edicaoLocal, setEdicaoLocal] = useState<string | null>(null);
  const trava = useRef(false);

  async function identidade(online = false): Promise<IdentidadeOffline | null> {
    const chave = chaveContexto();
    if (!chave) return null;
    const salvo = await storage.lerContexto<Contexto>(chave);
    if (!salvo || Date.now() - Date.parse(salvo.preparadoEm) > 7 * 86400000) return null;
    if (online) {
      const geracao = obterGeracaoSessao();
      const atual = (await api.get<IdentidadeOffline>("/offline/contexto/")).data;
      if (!geracaoSessaoValida(geracao) || atual.servidor !== salvo.servidor || atual.usuario !== salvo.usuario) {
        throw new Error("Conta ou servidor mudou. Prepare este aparelho novamente; lançamentos anteriores foram preservados.");
      }
    }
    return salvo;
  }
  const fila = new FilaOffline(storage, identidade, async payload => {
    const geracao = obterGeracaoSessao();
    if (!geracaoSessaoValida(geracao)) throw new Error("Sessão encerrada.");
    try {
      const resposta = await api.post<Record<string, unknown>>("/offline/cargas/", payload);
      return {status: resposta.status, dados: resposta.data};
    } catch (erro) {
      if (axios.isAxiosError(erro) && erro.response) return {status: erro.response.status};
      throw erro;
    }
  }, novoUUID, async () => {
    const chave = chaveContexto();
    return chave ? storage.lerContexto<Contexto>(chave) : null;
  });
  async function atualizar() {
    const chave = chaveContexto();
    setContexto(chave ? await storage.lerContexto<Contexto>(chave) : null);
    setItens(await fila.listar());
  }
  useEffect(() => { void atualizar().catch(() => setMensagem("Armazenamento offline indisponível neste aparelho.")); }, []);
  useEffect(() => {
    const tentar = async () => {
      if (trava.current || !estaAutenticado()) return;
      try {
        if (!(await fila.listar()).some(i => ['pendente', 'enviando'].includes(i.estado))) return;
        await executar(async () => { await fila.sincronizar(); });
      } catch { /* Uma nova tentativa ocorrerá quando a conexão retornar. */ }
    };
    const conectar = () => { void tentar(); };
    window.addEventListener('online', conectar);
    const intervalo = window.setInterval(conectar, 30000);
    return () => { window.removeEventListener('online', conectar); window.clearInterval(intervalo); };
  }, []);
  async function executar(acao: () => Promise<void>) {
    if (trava.current) return;
    trava.current = true; setOcupado(true); setMensagem("");
    try { await acao(); await atualizar(); }
    catch (erro) { setMensagem(erro instanceof Error ? erro.message : "Operação não concluída. Os dados locais foram preservados."); }
    finally { trava.current = false; setOcupado(false); }
  }
  async function preparar() {
    const geracao = obterGeracaoSessao(), chave = chaveContexto();
    if (!chave) throw new Error("Entre na sua conta antes de preparar o aparelho.");
    const [id, acesso, propriedades, cadpros, armazens] = await Promise.all([
      api.get<IdentidadeOffline>("/offline/contexto/"), api.get<UsuarioAtual>("/auth/me/"),
      api.get<Referencia[]>("/propriedades/"), api.get<Referencia[]>("/cadpros/"), api.get<Referencia[]>("/graos/armazens/"),
    ]);
    if (!geracaoSessaoValida(geracao) || chaveContexto() !== chave || id.data.usuario !== acesso.data.id) throw new Error("Sessão alterada durante a preparação.");
    const anterior = await storage.lerContexto<Contexto>(chave);
    await storage.salvarContexto(chave, { ...id.data, acesso: acesso.data,
      dispositivo: anterior?.servidor === id.data.servidor ? anterior.dispositivo : novoUUID(),
      propriedades: propriedades.data, cadpros: cadpros.data, armazens: armazens.data,
      snapshots: anterior?.servidor === id.data.servidor ? anterior.snapshots : [], preparadoEm: new Date().toISOString() });
    setMensagem("Aparelho preparado. Referências disponíveis por 7 dias. Lançamentos pendentes não são apagados ao vencer esse prazo.");
  }
  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    await executar(async () => {
      const salvo = await identidade();
      if (!salvo || !contexto || !autorizado(contexto.acesso, "cargas", original ? "editar" : "cadastrar")) throw new Error("Prepare o aparelho com uma conta autorizada.");
      if (!dados.placa.trim() && !dados.motorista.trim()) throw new Error("Informe a placa ou o motorista.");
      const payload = {...dados, ph: dados.ph || null, propriedade: Number(dados.propriedade), armazem: Number(dados.armazem)};
      if (edicaoLocal) await fila.editar(edicaoLocal, payload);
      else await fila.cadastrar(payload, original ? {registro: Number(original.registro.id), versao: original.versao} : null);
      setDados(vazio()); setOriginal(null); setEdicaoLocal(null);
      setMensagem("Salvo neste aparelho. Pendente de confirmação do servidor; saldo oficial ainda não foi alterado.");
    });
  }
  function preencher(registro: Record<string, unknown>) {
    const novo = vazio();
    for (const campo of Object.keys(novo) as (keyof Formulario)[]) if (registro[campo] != null) novo[campo] = String(registro[campo]);
    setDados(novo);
  }
  const selecao = (campo: "propriedade" | "cad_pro" | "armazem", rotulo: string, referencias: Referencia[]) => <label>{rotulo}<select aria-label={rotulo} required value={dados[campo]} onChange={e => setDados({...dados, [campo]: e.target.value})}><option value="">Selecione</option>{referencias.map(r => <option key={r.id} value={r.id}>{r.nome || r.codigo || r.id}</option>)}</select></label>;
  return <details className="card nao-imprimir" style={{margin: "12px 0"}}><summary>Trabalho offline · cargas {itens.filter(i => i.estado !== "sincronizado").length > 0 && `· ${itens.filter(i => i.estado !== "sincronizado").length} pendentes`}</summary>
    <p>Cadastre cargas e edite lançamentos locais sem conexão. Para corrigir uma carga já registrada, baixe a versão original enquanto estiver conectado. Os demais módulos ainda exigem o servidor. A fila tenta sincronizar ao reconectar e a cada 30 segundos.</p>
    <button disabled={ocupado} onClick={() => void executar(preparar)}>Preparar / atualizar aparelho</button>
    <button disabled={ocupado} onClick={() => void executar(async () => {
      const texto = await fila.exportar();
      const url = URL.createObjectURL(new Blob([texto], {type: 'application/json'}));
      const link = document.createElement('a'); link.href = url;
      link.download = `agro-fila-offline-${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
      link.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setMensagem('Arquivo de recuperação gerado. Guarde-o em local privado antes de atualizar ou limpar o aparelho. Ele contém os dados dos lançamentos pendentes.');
    })}>Exportar pendentes</button>
    <label>Recuperar fila de arquivo<input type="file" accept=".json,application/json" disabled={ocupado} onChange={e => {
      const arquivo = e.target.files?.[0]; e.target.value = '';
      if (arquivo) void executar(async () => {
        if (arquivo.size > 10 * 1024 * 1024) throw new Error('Arquivo excede 10 MB.');
        const quantidade = await fila.recuperar(await arquivo.text());
        setMensagem(`${quantidade} lançamento(s) recuperado(s). Os já existentes foram preservados. Confira a fila antes de sincronizar.`);
      });
    }}/></label>
    {mensagem && <p role="status">{mensagem}</p>}
    {contexto && <><p>Referências baixadas em {new Date(contexto.preparadoEm).toLocaleString("pt-BR")} · usuário {contexto.acesso.username}</p>
      <label>Carga existente para baixar<input type="number" min="1" value={idCarga} onChange={e => setIdCarga(e.target.value)} /></label>
      <button disabled={ocupado || !idCarga} onClick={() => void executar(async () => {
        const chave = chaveContexto();
        if (!chave || !await identidade(true)) throw new Error("Prepare o aparelho novamente.");
        const versao = (await api.get<Snapshot>(`/offline/cargas/${Number(idCarga)}/`)).data;
        await storage.salvarContexto(chave, {...contexto, snapshots: [...contexto.snapshots.filter(s => s.registro.id !== versao.registro.id), versao]});
        setMensagem("Versão original armazenada para edição offline.");
      })}>Baixar carga para editar offline</button>
      <label>Editar carga baixada<select value={original ? String(original.registro.id) : ""} onChange={e => {
        const selecionada = contexto.snapshots.find(s => String(s.registro.id) === e.target.value) || null;
        setOriginal(selecionada); setEdicaoLocal(null); if (selecionada) preencher(selecionada.registro); else setDados(vazio());
      }}><option value="">Nova carga</option>{contexto.snapshots.map(s => <option key={String(s.registro.id)} value={String(s.registro.id)}>Carga #{String(s.registro.id)}</option>)}</select></label>
      <form onSubmit={e => void salvar(e)}><div style={{display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 12}}>
        {selecao("propriedade", "Propriedade", contexto.propriedades)}{selecao("cad_pro", "CAD/PRO", contexto.cadpros)}{selecao("armazem", "Armazém", contexto.armazens)}
        {([['cultura','Produto'],['safra','Safra'],['data_colheita','Data da colheita'],['peso_bruto_kg','Peso bruto do produto (kg)'],['umidade_percentual','Umidade (%)'],['impureza_percentual','Impureza (%)'],['defeitos_percentual','Avariados (%)'],['placa','Placa'],['motorista','Motorista']] as [keyof Formulario,string][]).map(([campo,rotulo]) => <label key={campo}>{rotulo}<input required={!['placa','motorista'].includes(campo)} type={campo === 'data_colheita' ? 'date' : 'text'} value={dados[campo]} onChange={e => setDados({...dados,[campo]:e.target.value})}/></label>)}
        <label>Observações<textarea value={dados.observacoes} onChange={e => setDados({...dados,observacoes:e.target.value})}/></label>
        {dados.cultura.toLocaleLowerCase('pt-BR') === 'trigo' && <label>PH<input value={dados.ph} onChange={e => setDados({...dados,ph:e.target.value})}/></label>}
        {original && <label>Motivo da correção<input required value={dados.motivo_correcao} onChange={e => setDados({...dados,motivo_correcao:e.target.value})}/></label>}
      </div><button disabled={ocupado} type="submit">Salvar neste aparelho</button></form>
      <button disabled={ocupado} onClick={() => void executar(async () => { await fila.sincronizar(); setMensagem("Sincronização verificada. Confira a situação de cada lançamento."); })}>Sincronizar pendentes</button>
      <ul>{itens.map(item => <li key={item.id}><strong>{item.registro ? `Correção da carga #${item.registro}` : 'Nova carga'} · {item.estado}</strong> · {String(item.dados.peso_bruto_kg || '')} kg · {item.mensagem || 'Salvo localmente'} {item.estado === 'pendente' && item.tentativas === 0 && <button onClick={() => {setEdicaoLocal(item.id); preencher(item.dados); setOriginal(item.registro ? contexto.snapshots.find(s => s.registro.id === item.registro) || null : null);}}>Editar lançamento local</button>}</li>)}</ul>
    </>}
  </details>;
}
