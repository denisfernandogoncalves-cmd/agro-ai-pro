import { FormEvent, useEffect, useRef, useState } from "react";
import axios from "axios";
import { Acao, ACOES, DadosUsuario, Modulo, MODULOS, Usuario, excluirUsuario, listarUsuarios, salvarUsuario } from "../../api/usuarios";
import { AREAS_MODULOS, nomeModulo } from "../../components/gruposModulos";
import PainelFormulario from "../../components/PainelFormulario";

export function filtrarUsuarios(usuarios: Usuario[], busca: string) {
  const normalizar = (texto: string) => texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");
  const termo = normalizar(busca.trim());
  return usuarios.filter(usuario => normalizar([usuario.username, usuario.first_name, usuario.last_name, usuario.email].join(" ")).includes(termo));
}

const vazio = (): DadosUsuario => ({ username: "", first_name: "", last_name: "", email: "", password: "", password_confirmation: "", is_active: true, modulos: MODULOS.map(([id]) => id) });
function mensagemErro(falha: unknown) {
  const dados = axios.isAxiosError(falha) ? falha.response?.data : null;
  return dados && typeof dados === "object" ? Object.values(dados).flat().join(" ") : "Não foi possível concluir a operação.";
}

export default function UsuariosPage({ usuarioAtualId, onAtualizado }: { usuarioAtualId?: number; onAtualizado?: () => void } = {}) {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [form, setForm] = useState(vazio);
  const [edicao, setEdicao] = useState<Usuario | null>(null);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const trava = useRef(false);
  const [busca, setBusca] = useState("");
  const filtrados = filtrarUsuarios(usuarios, busca);

  useEffect(() => {
    let ativo = true;
    listarUsuarios().then(data => { if (ativo) setUsuarios(data); })
      .catch(() => { if (ativo) setErro("Não foi possível carregar os usuários. É necessário acesso de administrador."); })
      .finally(() => { if (ativo) setCarregando(false); });
    return () => { ativo = false; };
  }, []);

  function cancelar() { setEdicao(null); setForm(vazio()); }
  function editar(usuario: Usuario) {
    setEdicao(usuario);
    setForm({ username: usuario.username, first_name: usuario.first_name, last_name: usuario.last_name, email: usuario.email, is_active: usuario.is_active, modulos: usuario.modulos, permissoes: usuario.permissoes, password: "", password_confirmation: "" });
    setErro(""); setSucesso("");
  }
  function alternarAcao(modulo: Modulo, acao: Acao, marcada: boolean) {
    setForm(atual => { let valores = [...(atual.permissoes?.[modulo] ?? ACOES)];
      valores = marcada ? [...new Set([...valores, "consultar" as Acao, acao])] : acao === "consultar" ? [] : valores.filter(item => item !== acao);
      return {...atual, permissoes:{...atual.permissoes, [modulo]:valores}};
    });
  }
  async function salvar(event: FormEvent) {
    event.preventDefault();
    if (trava.current) return;
    setErro(""); setSucesso("");
    if (form.password !== form.password_confirmation) { setErro("As senhas não coincidem."); return; }
    trava.current = true; setSalvando(true);
    const dados = { ...form, permissoes: Object.fromEntries(form.modulos.map(id => [id, form.permissoes?.[id] ?? [...ACOES]])) };
    if (edicao && !dados.password) { delete dados.password; delete dados.password_confirmation; }
    try {
      const data = await salvarUsuario(edicao?.id ?? null, dados);
      setUsuarios(atuais => [...atuais.filter(item => item.id !== data.id), data].sort((a, b) => a.username.localeCompare(b.username)));
      setSucesso(`Usuário ${data.username} ${edicao ? "atualizado" : "criado"}.`);
      cancelar(); onAtualizado?.();
    } catch (falha) {
      setErro(mensagemErro(falha));
      setForm(atual => ({ ...atual, password: "", password_confirmation: "" }));
    } finally { trava.current = false; setSalvando(false); }
  }
  async function excluir(usuario: Usuario) {
    if (trava.current) return;
    if (!window.confirm(`Excluir o usuário "${usuario.username}"? O login será bloqueado e seus lançamentos anteriores serão preservados.`)) return;
    trava.current = true; setErro(""); setSucesso(""); setSalvando(true);
    try {
      await excluirUsuario(usuario.id);
      setUsuarios(atuais => atuais.filter(item => item.id !== usuario.id));
      if (edicao?.id === usuario.id) cancelar();
      setSucesso(`Usuário ${usuario.username} excluído.`); onAtualizado?.();
    } catch (falha) { setErro(mensagemErro(falha)); }
    finally { trava.current = false; setSalvando(false); }
  }

  return <>
    {erro && <p className="erro card" role="alert">{erro}</p>}
    {sucesso && <p className="card" role="status">{sucesso}</p>}
    <section className="grade usuarios-grade">
      <PainelFormulario titulo={edicao ? `Editar usuário: ${edicao.username}` : "Novo usuário"} edicao={edicao?.id}>
      <form className="card formulario" onSubmit={salvar}>
        <fieldset className="campos-formulario" disabled={salvando}>
        <h2>{edicao ? `Editar usuário: ${edicao.username}` : "Novo usuário"}</h2>
        <label>Usuário<input required maxLength={150} autoComplete="off" value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} /></label>
        <label>Nome<input maxLength={150} value={form.first_name} onChange={e => setForm({ ...form, first_name: e.target.value })} /></label>
        <label>Sobrenome<input maxLength={150} value={form.last_name} onChange={e => setForm({ ...form, last_name: e.target.value })} /></label>
        <label>E-mail<input type="email" maxLength={254} value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></label>
        <label>{edicao ? "Nova senha (opcional)" : "Senha"}<input type="password" required={!edicao} minLength={8} maxLength={128} autoComplete="new-password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} /></label>
        <label>Confirmar senha<input type="password" required={!edicao || !!form.password} minLength={8} maxLength={128} autoComplete="new-password" value={form.password_confirmation} onChange={e => setForm({ ...form, password_confirmation: e.target.value })} /></label>
        <small>{edicao ? "Deixe as senhas vazias para manter a senha atual. " : ""}Use pelo menos 8 caracteres; evite senhas comuns ou somente números.</small>
        <label className="usuario-checkbox"><input type="checkbox" disabled={edicao?.id === usuarioAtualId} checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })} />Usuário ativo</label>
        <fieldset disabled={salvando || !!edicao?.is_staff} className="usuario-permissoes">
          <legend>Itens permitidos</legend>
          <p>{edicao?.is_staff ? "Administradores têm acesso completo." : "Marque os módulos que este usuário poderá consultar e utilizar. Relatórios e Assistente incluem informações consolidadas dos demais módulos."}</p>
          <div className="acoes"><button type="button" className="secundario" onClick={() => setForm({ ...form, modulos: MODULOS.map(([id]) => id) })}>Marcar todos</button><button type="button" className="secundario" onClick={() => setForm({ ...form, modulos: [] })}>Desmarcar todos</button></div>
          <p role="status">{form.modulos.length} de {MODULOS.length} módulos selecionados.</p>
          <div className="usuario-permissoes-areas">{AREAS_MODULOS.map(area => <section className="usuario-permissoes-area" key={area.nome}>
            <h3>{area.nome}</h3>
            <div className="acoes"><button className="secundario" type="button" onClick={() => setForm(atual => ({ ...atual, modulos: [...new Set([...atual.modulos, ...area.modulos])] }))}>Marcar {area.nome}</button><button className="secundario" type="button" onClick={() => setForm(atual => ({ ...atual, modulos: atual.modulos.filter(id => !area.modulos.includes(id)) }))}>Desmarcar {area.nome}</button></div>
            <div className="usuario-permissoes-lista">{area.modulos.map(id => <label className="usuario-checkbox" key={id}><input type="checkbox" checked={form.modulos.includes(id)} onChange={e => setForm(atual => ({ ...atual, modulos: e.target.checked ? [...new Set([...atual.modulos, id])] : atual.modulos.filter(item => item !== id) }))} />{nomeModulo(id)}</label>)}</div>
          </section>)}</div>
          <details className="permissoes-acoes"><summary>Definir ações em cada módulo</summary><p>Desmarque as ações que o usuário não poderá realizar. Consultar é necessário para as demais ações.</p>
          {form.modulos.map(id => <fieldset className="permissoes-modulo" key={id}><legend>{nomeModulo(id)}</legend><div>{ACOES.map(acao => <label className="usuario-checkbox" key={acao}><input type="checkbox" checked={(form.permissoes?.[id] ?? ACOES).includes(acao)} onChange={e => alternarAcao(id, acao, e.target.checked)} />{acao.charAt(0).toUpperCase()+acao.slice(1)}</label>)}</div></fieldset>)}
          </details>
        </fieldset>
        <div className="acoes"><button disabled={salvando || carregando} type="submit">{salvando ? "Salvando..." : edicao ? "Salvar alterações" : "Criar usuário"}</button>{edicao && <button disabled={salvando} className="secundario" type="button" onClick={cancelar}>Cancelar edição</button>}</div>
        </fieldset>
      </form>
      </PainelFormulario>
      <section className="card"><h2>Usuários cadastrados</h2>
        <label>Buscar usuários<input type="search" placeholder="Nome, usuário ou e-mail" value={busca} onChange={e => setBusca(e.target.value)} /></label>
        <p role="status">{carregando ? "Carregando usuários..." : `${filtrados.length} de ${usuarios.length} usuários`}</p>
        {!carregando && !filtrados.length && <p className="vazio">{busca.trim() ? "Nenhum usuário encontrado para a busca." : "Nenhum usuário cadastrado."}</p>}
        {!carregando && <div className="lista usuarios-lista">{filtrados.map(usuario => <article className="usuario-item" key={usuario.id}>
          <div><strong>{usuario.username}</strong><span>{[usuario.first_name, usuario.last_name].filter(Boolean).join(" ")}</span><small>{usuario.is_staff ? "Administrador" : "Usuário"} · {usuario.is_active ? "Ativo" : "Inativo"}{usuario.id === usuarioAtualId ? " · Sua conta" : ""}</small>
          <p>{usuario.is_staff ? "Todos os módulos" : usuario.modulos.length ? MODULOS.filter(([id]) => usuario.modulos.includes(id)).map(([, nome]) => nome).join(" · ") : "Nenhum módulo permitido"}</p></div>
          <div className="acoes"><button disabled={salvando} className="secundario" type="button" onClick={() => editar(usuario)}>Editar</button><button disabled={salvando || usuario.id === usuarioAtualId} className="perigo" type="button" onClick={() => void excluir(usuario)}>Excluir</button></div>
        </article>)}</div>}
      </section>
    </section>
  </>;
}
