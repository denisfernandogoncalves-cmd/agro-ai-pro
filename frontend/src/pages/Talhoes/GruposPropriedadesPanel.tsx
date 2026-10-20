import { FormEvent, useEffect, useState } from "react";
import axios from "axios";
import { BotaoAcao, useAcoes } from "../../components/AcoesContext";
import { areaEmAlqueires } from "../../utils/areas";
import type { Propriedade } from "../../api/propriedades";
import {
  GrupoPropriedades, OpcaoGrupo, listarGruposPropriedades,
  listarOpcoesGrupo, salvarGrupoPropriedades, excluirGrupoPropriedades,
} from "../../api/gruposPropriedades";

export default function GruposPropriedadesPanel({ propriedades: cadastradas }: { propriedades: Propriedade[] }) {
  const pode = useAcoes();
  const [mostrarExcluidos, setMostrarExcluidos] = useState(false);
  const [grupos, setGrupos] = useState<GrupoPropriedades[]>([]);
  const [opcoes, setOpcoes] = useState<OpcaoGrupo[]>([]);
  const [id, setId] = useState<number | null>(null);
  const [nome, setNome] = useState("");
  const [cultura, setCultura] = useState("");
  const [safra, setSafra] = useState("");
  const [ativo, setAtivo] = useState(true);
  const [escolhas, setEscolhas] = useState<Record<string, string>>({});
  const [ocupado, setOcupado] = useState(true);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [busca, setBusca] = useState("");

  async function carregar(incluirExcluidos = mostrarExcluidos) {
    setOcupado(true);
    setErro("");
    try {
      const [lista, vinculos] = await Promise.all([listarGruposPropriedades(incluirExcluidos), listarOpcoesGrupo()]);
      setGrupos(lista);
      setOpcoes(vinculos);
    } catch {
      setErro("Não foi possível carregar os grupos. Tente novamente.");
    } finally { setOcupado(false); }
  }
  useEffect(() => { void carregar(); }, []);
  function limpar() {
    setId(null); setNome(""); setCultura(""); setSafra(""); setAtivo(true); setEscolhas({});
  }
  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    if (ocupado) return;
    if (!Object.keys(escolhas).length || Object.values(escolhas).some(v => !v)) {
      setErro("Selecione as propriedades e informe um CAD/PRO ativo para cada uma.");
      return;
    }
    setOcupado(true); setErro(""); setSucesso("");
    try {
      const salvo = await salvarGrupoPropriedades(id, {
        nome, cultura, safra, ativo, vinculos: Object.values(escolhas).filter(Boolean),
      });
      setGrupos(atual => [...atual.filter(g => g.id !== salvo.id), salvo].sort((a, b) => a.nome.localeCompare(b.nome)));
      limpar(); setSucesso("Grupo salvo. Disponível em Cargas colhidas quando ativo.");
    } catch (falha) {
      const dados = axios.isAxiosError(falha) ? falha.response?.data : null;
      setErro(dados && typeof dados === "object" ? Object.values(dados).flat().join(" ") : "Não foi possível salvar o grupo.");
    } finally { setOcupado(false); }
  }
  async function remover(grupo: GrupoPropriedades) {
    if (ocupado || !window.confirm(`Excluir o grupo "${grupo.nome}"? O histórico das áreas e das cargas será preservado.`)) return;
    setOcupado(true); setErro(""); setSucesso("");
    try {
      await excluirGrupoPropriedades(grupo.id);
      if (id === grupo.id) limpar();
      await carregar();
      setSucesso("Grupo excluído. O histórico das áreas e das cargas foi preservado.");
    } catch {
      setErro("Não foi possível excluir o grupo. Tente novamente.");
    } finally { setOcupado(false); }
  }
  const propriedades = [...new Map([
    ...opcoes.map(o => [o.propriedade, o.propriedade_nome] as const),
    ...cadastradas.map(p => {
      const apelidos = [...new Set([p.apelido, ...(p.apelidos ?? [])].map(a => (a ?? "").trim()).filter(Boolean))];
      return [p.id, apelidos.length ? `${p.nome} — ${apelidos.join(" / ")}` : p.nome] as const;
    }),
  ]).entries()];
  return <section className="card grupos-colheita">
    <h2>Grupos de colheita</h2>
    <p>Reúna propriedades colhidas juntas e escolha o CAD/PRO de cada uma. O rateio permanece proporcional à área de cada propriedade.</p>
    {erro && <p className="erro" role="alert">{erro}</p>}
    {sucesso && <p className="sucesso" role="status">{sucesso}</p>}
    <button type="button" disabled={ocupado} onClick={() => void carregar()}>Atualizar grupos e vínculos</button>
    <label className="opcao-checkbox"><input type="checkbox" checked={mostrarExcluidos} disabled={ocupado} onChange={e => { setMostrarExcluidos(e.target.checked); void carregar(e.target.checked); }} />Mostrar grupos excluídos e histórico das áreas</label>
    <form className="formulario grupo-formulario" onSubmit={salvar}>
      <fieldset disabled={ocupado || !pode(id === null ? "cadastrar" : "editar")}>
        <legend>{id === null ? "Novo grupo" : "Editar grupo"}</legend>
        <label>Nome do grupo<input required maxLength={100} value={nome} onChange={e => setNome(e.target.value)} placeholder="Fazenda Electra" /></label>
        <div className="grupo-cultura-safra">
          <label>Cultura<input maxLength={50} value={cultura} onChange={e => setCultura(e.target.value)} placeholder="Ex.: Soja" /></label>
          <label>Safra<input maxLength={20} value={safra} onChange={e => setSafra(e.target.value)} placeholder="Ex.: 2026/2027" /></label>
        </div>
        <label className="opcao-checkbox"><input type="checkbox" checked={ativo} onChange={e => setAtivo(e.target.checked)} />Grupo ativo</label>
        <label>Buscar propriedade para o grupo<input type="search" value={busca} onChange={e => setBusca(e.target.value)} /></label>
        <p>Marque todas as propriedades que serão colhidas juntas. Selecionadas: {Object.keys(escolhas).length}.</p>
        <div className="grupo-opcoes">{propriedades.filter(([, rotulo]) => rotulo.toLocaleLowerCase().includes(busca.toLocaleLowerCase())).map(([propriedade, rotulo]) => {
          const vinculos = opcoes.filter(o => o.propriedade === propriedade);
          return <label key={propriedade} className="opcao-checkbox"><input type="checkbox" checked={String(propriedade) in escolhas} disabled={!vinculos.length} onChange={e => {
            const marcada = e.target.checked;
            setEscolhas(atual => {
              const novas = { ...atual };
              if (marcada) novas[String(propriedade)] = vinculos.length === 1 ? vinculos[0].id : "";
              else delete novas[String(propriedade)];
              return novas;
            });
          }} />{rotulo}{!vinculos.length && " — cadastre um CAD/PRO ativo em Propriedades"}</label>;
        })}</div>
        <div className="grupo-propriedades">{propriedades.filter(([propriedade]) => String(propriedade) in escolhas).map(([propriedade, rotulo]) => <div key={propriedade}><label>CAD/PRO de {rotulo}
          <select required value={escolhas[String(propriedade)] || ""} onChange={e => setEscolhas({ ...escolhas, [String(propriedade)]: e.target.value })}>
            <option value="">Selecione o CAD/PRO</option>
            {opcoes.filter(o => o.propriedade === propriedade).map(o => <option key={o.id} value={o.id}>{o.cad_pro_codigo}</option>)}
          </select>
        </label><button type="button" aria-label={`Remover ${rotulo} do grupo`} onClick={() => setEscolhas(atual => {
          const novas = { ...atual };
          delete novas[String(propriedade)];
          return novas;
        })}>Remover do grupo</button></div>)}</div>
        {!ocupado && propriedades.length === 0 && <p>Cadastre primeiro os vínculos entre propriedades e CAD/PROs.</p>}
        <button disabled={!Object.keys(escolhas).length || Object.values(escolhas).some(v => !v)} type="submit">Salvar grupo</button>
        {id !== null && <button type="button" onClick={limpar}>Cancelar edição</button>}
      </fieldset>
    </form>
    <div className="grupos-lista">{grupos.map(grupo => <article key={grupo.id}>
      <h3>{grupo.nome}{grupo.excluido_em ? " (excluído)" : !grupo.ativo ? " (inativo)" : ""}</h3>
      <p><strong>Cultura:</strong> {grupo.cultura || "Não informada"} · <strong>Safra:</strong> {grupo.safra || "Não informada"}</p>
      {grupo.excluido_em && <p>Excluído em {new Date(grupo.excluido_em).toLocaleString("pt-BR")}. Áreas preservadas na data da exclusão.</p>}
      <p>{grupo.membros.map(m => `${m.propriedade_nome} — CAD/PRO ${m.cad_pro_codigo}${m.area_hectares ? ` — ${areaEmAlqueires(m.area_hectares, 4)} alq.` : ""}${!grupo.excluido_em && !m.disponivel ? " (vínculo indisponível)" : ""}`).join(" · ")}</p>
      {!grupo.excluido_em && <BotaoAcao acao="editar" type="button" disabled={ocupado} onClick={() => {
        setId(grupo.id); setNome(grupo.nome); setCultura(grupo.cultura || ""); setSafra(grupo.safra || ""); setAtivo(grupo.ativo); setSucesso("");
        setEscolhas(Object.fromEntries(grupo.membros.map(m => [String(m.propriedade), opcoes.find(o => o.propriedade === m.propriedade && o.cad_pro === m.cad_pro)?.id ?? ""])));
        setErro(grupo.membros.some(m => !m.disponivel) ? "Revise as propriedades: vínculos indisponíveis precisam ser substituídos antes de salvar." : "");
      }}>Editar grupo</BotaoAcao>}
      {!grupo.excluido_em && <BotaoAcao acao="excluir" type="button" className="perigo" disabled={ocupado} onClick={() => void remover(grupo)}>Excluir grupo</BotaoAcao>}
    </article>)}</div>
  </section>;
}
