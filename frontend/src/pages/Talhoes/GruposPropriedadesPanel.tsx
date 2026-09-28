import { FormEvent, useEffect, useState } from "react";
import axios from "axios";
import {
  GrupoPropriedades, OpcaoGrupo, listarGruposPropriedades,
  listarOpcoesGrupo, salvarGrupoPropriedades,
} from "../../api/gruposPropriedades";

export default function GruposPropriedadesPanel() {
  const [grupos, setGrupos] = useState<GrupoPropriedades[]>([]);
  const [opcoes, setOpcoes] = useState<OpcaoGrupo[]>([]);
  const [id, setId] = useState<number | null>(null);
  const [nome, setNome] = useState("");
  const [ativo, setAtivo] = useState(true);
  const [escolhas, setEscolhas] = useState<Record<string, string>>({});
  const [ocupado, setOcupado] = useState(true);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");

  async function carregar() {
    setOcupado(true);
    setErro("");
    try {
      const [lista, vinculos] = await Promise.all([listarGruposPropriedades(), listarOpcoesGrupo()]);
      setGrupos(lista);
      setOpcoes(vinculos);
    } catch {
      setErro("Não foi possível carregar os grupos. Tente novamente.");
    } finally { setOcupado(false); }
  }
  useEffect(() => { void carregar(); }, []);
  function limpar() {
    setId(null); setNome(""); setAtivo(true); setEscolhas({});
  }
  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    if (ocupado) return;
    setOcupado(true); setErro(""); setSucesso("");
    try {
      const salvo = await salvarGrupoPropriedades(id, {
        nome, ativo, vinculos: Object.values(escolhas).filter(Boolean),
      });
      setGrupos(atual => [...atual.filter(g => g.id !== salvo.id), salvo].sort((a, b) => a.nome.localeCompare(b.nome)));
      limpar(); setSucesso("Grupo salvo. Disponível em Cargas colhidas quando ativo.");
    } catch (falha) {
      const dados = axios.isAxiosError(falha) ? falha.response?.data : null;
      setErro(dados && typeof dados === "object" ? Object.values(dados).flat().join(" ") : "Não foi possível salvar o grupo.");
    } finally { setOcupado(false); }
  }
  const propriedades = [...new Map(opcoes.map(o => [o.propriedade, o.propriedade_nome])).entries()];
  return <section className="card grupos-colheita">
    <h2>Grupos de colheita</h2>
    <p>Reúna propriedades colhidas juntas e escolha o CAD/PRO de cada uma. O rateio permanece proporcional à área de cada propriedade.</p>
    {erro && <p className="erro" role="alert">{erro}</p>}
    {sucesso && <p className="sucesso" role="status">{sucesso}</p>}
    <button type="button" disabled={ocupado} onClick={() => void carregar()}>Atualizar grupos e vínculos</button>
    <form className="formulario grupo-formulario" onSubmit={salvar}>
      <fieldset disabled={ocupado}>
        <legend>{id === null ? "Novo grupo" : "Editar grupo"}</legend>
        <label>Nome do grupo<input required maxLength={100} value={nome} onChange={e => setNome(e.target.value)} placeholder="Fazenda Electra" /></label>
        <label className="opcao-checkbox"><input type="checkbox" checked={ativo} onChange={e => setAtivo(e.target.checked)} />Grupo ativo</label>
        <div className="grupo-propriedades">{propriedades.map(([propriedade, rotulo]) => <label key={propriedade}>{rotulo}
          <select value={escolhas[String(propriedade)] || ""} onChange={e => setEscolhas({ ...escolhas, [String(propriedade)]: e.target.value })}>
            <option value="">Não incluir no grupo</option>
            {opcoes.filter(o => o.propriedade === propriedade).map(o => <option key={o.id} value={o.id}>{o.cad_pro_codigo}</option>)}
          </select>
        </label>)}</div>
        {!ocupado && propriedades.length === 0 && <p>Cadastre primeiro os vínculos entre propriedades e CAD/PROs.</p>}
        <button disabled={!Object.values(escolhas).some(Boolean)} type="submit">Salvar grupo</button>
        {id !== null && <button type="button" onClick={limpar}>Cancelar edição</button>}
      </fieldset>
    </form>
    <div className="grupos-lista">{grupos.map(grupo => <article key={grupo.id}>
      <h3>{grupo.nome}{!grupo.ativo && " (inativo)"}</h3>
      <p>{grupo.membros.map(m => `${m.propriedade_nome} — ${m.cad_pro_codigo}${!m.disponivel ? " (vínculo indisponível)" : ""}`).join(" · ")}</p>
      <button type="button" disabled={ocupado} onClick={() => {
        setId(grupo.id); setNome(grupo.nome); setAtivo(grupo.ativo); setSucesso("");
        setEscolhas(Object.fromEntries(opcoes.filter(o => grupo.vinculos.includes(o.id)).map(o => [String(o.propriedade), o.id])));
        setErro(grupo.membros.some(m => !m.disponivel) ? "Revise as propriedades: vínculos indisponíveis precisam ser substituídos antes de salvar." : "");
      }}>Editar grupo</button>
    </article>)}</div>
  </section>;
}
