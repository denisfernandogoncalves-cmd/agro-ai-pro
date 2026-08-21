import axios from "axios";
import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  atualizarGrupoColheita,
  CADPro,
  carregarOpcoesGrupoColheita,
  criarGrupoColheita,
  GrupoColheita,
  GrupoColheitaFiltros,
  GrupoColheitaInput,
  inativarGrupoColheita,
  listarGruposColheita,
} from "../../api/cargasColhidas";
import { Propriedade } from "../../api/propriedades";

const vazio: GrupoColheitaInput = {
  propriedade: 0,
  cad_pro: "",
  nome: "",
  cultura: "Soja",
  safra: "",
  observacoes: "",
  tolerancia_impureza_percentual: "1.00",
  desconto_impureza_por_ponto: "1.000",
  tolerancia_defeitos_percentual: "0.00",
  desconto_defeitos_por_ponto: "0.000",
  ph_minimo: "0.00",
  desconto_ph_por_ponto: "0.000",
};

const filtrosVazios: GrupoColheitaFiltros = {
  search: "",
  propriedade: "",
  cad_pro: "",
  cultura: "",
  safra: "",
  ativo: "",
};

function mensagemErro(falha: unknown) {
  if (axios.isAxiosError(falha)) {
    const dados = falha.response?.data;
    if (typeof dados?.detail === "string") return dados.detail;
    if (dados && typeof dados === "object") return Object.values(dados).flat(2).join(" ");
  }
  return "Não foi possível concluir a operação com o grupo de colheita.";
}

type Props = { propriedades: Propriedade[] };

export default function GruposColheitaPage({ propriedades }: Props) {
  const [grupos, setGrupos] = useState<GrupoColheita[]>([]);
  const [cadpros, setCadpros] = useState<CADPro[]>([]);
  const [formulario, setFormulario] = useState<GrupoColheitaInput>(vazio);
  const [filtros, setFiltros] = useState<GrupoColheitaFiltros>(filtrosVazios);
  const [edicaoId, setEdicaoId] = useState<number | null>(null);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function carregar(filtrosAtuais = filtros) {
    setCarregando(true);
    setErro("");
    try {
      const [lista, opcoes] = await Promise.all([
        listarGruposColheita(filtrosAtuais),
        carregarOpcoesGrupoColheita(),
      ]);
      setGrupos(lista);
      setCadpros(opcoes.cadpros);
    } catch (falha) {
      setErro(mensagemErro(falha));
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => { void carregar(filtrosVazios); }, []);

  const cadprosDaPropriedade = useMemo(
    () => cadpros.filter((item) => item.propriedades.includes(formulario.propriedade)),
    [cadpros, formulario.propriedade],
  );
  const cadprosDoFiltro = useMemo(
    () => filtros.propriedade
      ? cadpros.filter((item) => item.propriedades.includes(Number(filtros.propriedade)))
      : cadpros,
    [cadpros, filtros.propriedade],
  );

  function cancelar() {
    setEdicaoId(null);
    setFormulario(vazio);
  }

  function editar(grupo: GrupoColheita) {
    setEdicaoId(grupo.id);
    setFormulario({
      propriedade: grupo.propriedade,
      cad_pro: grupo.cad_pro,
      nome: grupo.nome,
      cultura: grupo.cultura,
      safra: grupo.safra,
      observacoes: grupo.observacoes,
      tolerancia_impureza_percentual: grupo.tolerancia_impureza_percentual,
      desconto_impureza_por_ponto: grupo.desconto_impureza_por_ponto,
      tolerancia_defeitos_percentual: grupo.tolerancia_defeitos_percentual,
      desconto_defeitos_por_ponto: grupo.desconto_defeitos_por_ponto,
      ph_minimo: grupo.ph_minimo,
      desconto_ph_por_ponto: grupo.desconto_ph_por_ponto,
    });
  }

  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    setErro("");
    setSucesso("");
    try {
      const salvo = edicaoId
        ? await atualizarGrupoColheita(edicaoId, formulario)
        : await criarGrupoColheita(formulario);
      setSucesso(`Grupo “${salvo.nome}” salvo.`);
      cancelar();
      await carregar();
    } catch (falha) {
      setErro(mensagemErro(falha));
    }
  }

  async function inativar(grupo: GrupoColheita) {
    if (!window.confirm(`Inativar o grupo “${grupo.nome}”?`)) return;
    setErro("");
    try {
      await inativarGrupoColheita(grupo.id);
      if (edicaoId === grupo.id) cancelar();
      setSucesso(`Grupo “${grupo.nome}” inativado.`);
      await carregar();
    } catch (falha) {
      setErro(mensagemErro(falha));
    }
  }

  return (
    <section className="modulo-grupos-colheita">
      <div><span className="kicker">Contexto produtivo</span><h2>Grupos de colheita</h2><p>Vincule propriedade, CAD/PRO, cultura e safra. A armazenagem é escolhida em cada carga.</p></div>
      {erro && <p className="erro card" role="alert">{erro}</p>}
      {sucesso && <p className="sucesso card">{sucesso}</p>}
      <section className="grade grupos-colheita-grade">
        <form className="card formulario" onSubmit={salvar}>
          <h3>{edicaoId ? "Editar grupo" : "Novo grupo"}</h3>
          <label>Propriedade<select required disabled={grupos.find((item) => item.id === edicaoId)?.contexto_congelado} value={formulario.propriedade || ""} onChange={(e) => setFormulario({ ...formulario, propriedade: Number(e.target.value), cad_pro: "" })}><option value="">Selecione</option>{propriedades.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
          <label>CAD/PRO da propriedade<select required disabled={!formulario.propriedade || grupos.find((item) => item.id === edicaoId)?.contexto_congelado} value={formulario.cad_pro} onChange={(e) => setFormulario({ ...formulario, cad_pro: e.target.value })}><option value="">Selecione</option>{cadprosDaPropriedade.map((item) => <option key={item.id} value={item.id}>{item.codigo} · {item.descricao}</option>)}</select></label>
          {formulario.propriedade && cadprosDaPropriedade.length === 0 && <p className="aviso-contexto">Cadastre o número CAD/PRO no formulário da propriedade antes de criar o grupo.</p>}
          <div className="linha"><label>Nome<input required value={formulario.nome} onChange={(e) => setFormulario({ ...formulario, nome: e.target.value })} /></label><label>Cultura<select required disabled={grupos.find((item) => item.id === edicaoId)?.contexto_congelado} value={formulario.cultura} onChange={(e) => setFormulario({ ...formulario, cultura: e.target.value })}><option>Soja</option><option>Milho</option><option>Trigo</option></select></label></div>
          <label>Safra<input required disabled={grupos.find((item) => item.id === edicaoId)?.contexto_congelado} placeholder="2026/2027" value={formulario.safra} onChange={(e) => setFormulario({ ...formulario, safra: e.target.value })} /></label>
          <label>Observações<textarea value={formulario.observacoes} onChange={(e) => setFormulario({ ...formulario, observacoes: e.target.value })} /></label>
          <p className="aviso-contexto">O desconto de umidade segue a tabela oficial por cultura, de 11,5% a 30% em passos de 0,5.</p>
          <div className="regras-desconto">{([ ["Impureza", "tolerancia_impureza_percentual", "desconto_impureza_por_ponto"], ["Quebrados", "tolerancia_defeitos_percentual", "desconto_defeitos_por_ponto"] ] as const).map(([rotulo, tolerancia, desconto]) => <fieldset key={rotulo}><legend>{rotulo}</legend><label>Tolerância (%)<input min="0" max="100" step="0.01" type="number" value={formulario[tolerancia]} onChange={(e) => setFormulario({ ...formulario, [tolerancia]: e.target.value })} /></label><label>Desconto/ponto (%)<input min="0" max="100" step="0.001" type="number" value={formulario[desconto]} onChange={(e) => setFormulario({ ...formulario, [desconto]: e.target.value })} /></label></fieldset>)}<fieldset><legend>PH</legend><label>PH mínimo<input min="0" max="100" step="0.01" type="number" value={formulario.ph_minimo} onChange={(e) => setFormulario({ ...formulario, ph_minimo: e.target.value })} /></label><label>Desconto/ponto abaixo (%)<input min="0" max="100" step="0.001" type="number" value={formulario.desconto_ph_por_ponto} onChange={(e) => setFormulario({ ...formulario, desconto_ph_por_ponto: e.target.value })} /></label></fieldset></div>
          {edicaoId && grupos.find((item) => item.id === edicaoId)?.contexto_congelado && <p className="aviso-contexto">Contexto estrutural congelado por cargas vinculadas.</p>}
          <div className="acoes"><button disabled={carregando} type="submit">Salvar grupo</button>{edicaoId && <button className="secundario" type="button" onClick={cancelar}>Cancelar</button>}</div>
        </form>
        <section className="conteudo">
          <form className="card filtros-grupos" onSubmit={(e) => { e.preventDefault(); void carregar(); }}><input aria-label="Buscar grupos" placeholder="Nome, cultura, propriedade ou CAD/PRO" value={filtros.search} onChange={(e) => setFiltros({ ...filtros, search: e.target.value })} /><select aria-label="Filtrar por propriedade" value={filtros.propriedade} onChange={(e) => setFiltros({ ...filtros, propriedade: e.target.value, cad_pro: "" })}><option value="">Todas as propriedades</option>{propriedades.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select><select aria-label="Filtrar por CAD/PRO" value={filtros.cad_pro} onChange={(e) => setFiltros({ ...filtros, cad_pro: e.target.value })}><option value="">Todos os CAD/PROs</option>{cadprosDoFiltro.map((item) => <option key={item.id} value={item.id}>{item.codigo}</option>)}</select><input aria-label="Filtrar por cultura" placeholder="Cultura" value={filtros.cultura} onChange={(e) => setFiltros({ ...filtros, cultura: e.target.value })} /><input aria-label="Filtrar por safra" placeholder="Safra" value={filtros.safra} onChange={(e) => setFiltros({ ...filtros, safra: e.target.value })} /><select aria-label="Filtrar por status" value={filtros.ativo} onChange={(e) => setFiltros({ ...filtros, ativo: e.target.value })}><option value="">Todos</option><option value="true">Ativos</option><option value="false">Inativos</option></select><button type="submit">Filtrar</button></form>
          <div className="lista">{grupos.length === 0 ? <div className="card vazio">Nenhum grupo de colheita encontrado.</div> : grupos.map((item) => <article className="card item grupo-colheita-item" key={item.id}><div><span className="kicker">{item.ativo ? "Ativo" : "Inativo"}{item.contexto_congelado ? " · contexto congelado" : ""}</span><h3>{item.nome}</h3><p>{item.propriedade_nome} · CAD/PRO {item.cad_pro_codigo}</p><p>{item.cultura} · {item.safra}</p>{item.observacoes && <p>{item.observacoes}</p>}</div><div className="acoes"><button className="secundario" onClick={() => editar(item)}>Editar</button>{item.ativo && <button className="perigo" onClick={() => void inativar(item)}>Inativar</button>}</div></article>)}</div>
        </section>
      </section>
    </section>
  );
}
