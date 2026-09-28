import { FormEvent, useEffect, useState } from "react";
import axios from "axios";
import { api } from "../../api/propriedades";

type Usuario = { id: number; username: string; first_name: string; last_name: string; email: string; is_active: boolean; is_staff: boolean };
const vazio = { username: "", first_name: "", last_name: "", email: "", password: "", password_confirmation: "" };

export default function UsuariosPage() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [form, setForm] = useState(vazio);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    let ativo = true;
    api.get<Usuario[]>("/auth/users/").then(({ data }) => { if (ativo) setUsuarios(data); })
      .catch(() => { if (ativo) setErro("Não foi possível carregar os usuários. É necessário acesso de administrador."); })
      .finally(() => { if (ativo) setCarregando(false); });
    return () => { ativo = false; };
  }, []);

  async function salvar(event: FormEvent) {
    event.preventDefault();
    setErro(""); setSucesso("");
    if (form.password !== form.password_confirmation) { setErro("As senhas não coincidem."); return; }
    setSalvando(true);
    try {
      const { data } = await api.post<Usuario>("/auth/users/", form);
      setUsuarios((atuais) => [...atuais, data].sort((a, b) => a.username.localeCompare(b.username)));
      setForm(vazio);
      setSucesso(`Usuário ${data.username} criado. Ele já pode entrar com a senha definida.`);
    } catch (falha) {
      const dados = axios.isAxiosError(falha) ? falha.response?.data : null;
      setErro(dados && typeof dados === "object" ? Object.values(dados).flat().join(" ") : "Não foi possível criar o usuário.");
      setForm((atual) => ({ ...atual, password: "", password_confirmation: "" }));
    } finally { setSalvando(false); }
  }

  return <>
    {erro && <p className="erro card" role="alert">{erro}</p>}
    {sucesso && <p className="card" role="status">{sucesso}</p>}
    <section className="grade">
      <form className="card formulario" onSubmit={salvar}>
        <h2>Novo usuário</h2>
        <p>Crie uma conta para acessar o sistema. Novas contas não administram usuários.</p>
        <label>Usuário<input required maxLength={150} autoComplete="off" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></label>
        <label>Nome<input maxLength={150} value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} /></label>
        <label>Sobrenome<input maxLength={150} value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} /></label>
        <label>E-mail<input type="email" maxLength={254} value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
        <label>Senha<input type="password" required minLength={8} maxLength={128} autoComplete="new-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></label>
        <label>Confirmar senha<input type="password" required minLength={8} maxLength={128} autoComplete="new-password" value={form.password_confirmation} onChange={(e) => setForm({ ...form, password_confirmation: e.target.value })} /></label>
        <p>Use pelo menos 8 caracteres. Evite senhas comuns, somente números ou semelhantes ao nome.</p>
        <button disabled={salvando || carregando} type="submit">{salvando ? "Criando..." : "Criar usuário"}</button>
      </form>
      <section className="card"><h2>Usuários cadastrados</h2>
        {carregando ? <p role="status">Carregando...</p> : <ul>{usuarios.map((usuario) => <li key={usuario.id}>
          <strong>{usuario.username}</strong> · {usuario.first_name} {usuario.last_name} · {usuario.is_staff ? "Administrador" : "Usuário"} · {usuario.is_active ? "Ativo" : "Inativo"}
        </li>)}</ul>}
      </section>
    </section>
  </>;
}
