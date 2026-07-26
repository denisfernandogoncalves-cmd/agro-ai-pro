import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";

import {
  atualizarPropriedade,
  autenticar,
  criarPropriedade,
  estaAutenticado,
  excluirPropriedade,
  listarPropriedades,
  obterPermissoesUsuario,
  type PermissoesUsuario,
  type Propriedade,
  type PropriedadeInput,
  sair,
} from "./api/propriedades";
import ModuleRenderer from "./app/ModuleRenderer";
import { NAVIGATION_ITEMS, type ModuleId } from "./app/navigation";
import AplicativoStatus from "./components/AplicativoStatus";
import AppShell from "./components/layout/AppShell";
import MapaPropriedade from "./components/MapaPropriedade";
import { AlertCard, EmptyState, PageHeader } from "./components/shared/ui";
import { useTheme } from "./hooks/useTheme";
import { getUserIdentity } from "./utils/session";

import "./styles/tokens.css";
import "./styles.css";
import "./styles/enterprise.css";


const formularioVazio: PropriedadeInput = {
  nome: "",
  proprietario: "",
  municipio: "",
  uf: "",
  area_hectares: "",
  latitude: "",
  longitude: "",
  observacoes: "",
  arquivo_kml: null,
};

const permissoesVazias: PermissoesUsuario = {
  pode_criar_propriedade: false,
  superusuario: false,
};

function mensagemDoErro(erro: unknown) {
  if (axios.isAxiosError(erro)) {
    const dados = erro.response?.data;
    if (erro.response?.status === 403 && !dados?.detail) {
      return "Seu perfil não permite concluir esta operação.";
    }
    if (erro.response?.status === 404 && !dados?.detail) {
      return "O registro não foi encontrado ou não pertence ao seu escopo autorizado.";
    }
    if (typeof dados?.detail === "string") {
      return dados.detail;
    }
    if (dados && typeof dados === "object") {
      return Object.values(dados).flat().join(" ");
    }
  }
  return "Não foi possível concluir a operação.";
}

export default function App() {
  const [autenticado, setAutenticado] = useState(estaAutenticado());
  const [modulo, setModulo] = useState<ModuleId>("dashboard");
  const [credenciais, setCredenciais] = useState({ username: "", password: "" });
  const [propriedades, setPropriedades] = useState<Propriedade[]>([]);
  const [permissoes, setPermissoes] = useState(permissoesVazias);
  const [selecionada, setSelecionada] = useState<Propriedade | null>(null);
  const [safra, setSafra] = useState("");
  const [edicaoId, setEdicaoId] = useState<number | null>(null);
  const [formulario, setFormulario] = useState(formularioVazio);
  const [busca, setBusca] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const { theme, toggleTheme } = useTheme();

  const carregar = useCallback(async (termo = "") => {
    setCarregando(true);
    setErro("");
    try {
      const [dados, perfil] = await Promise.all([
        listarPropriedades(termo),
        obterPermissoesUsuario(),
      ]);
      setPropriedades(dados);
      setPermissoes(perfil);
      setSelecionada((atual) =>
        dados.find((item) => item.id === atual?.id) ?? dados[0] ?? null
      );
    } catch (falha) {
      setErro(mensagemDoErro(falha));
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    if (autenticado) void carregar();
  }, [autenticado, carregar]);

  async function enviarLogin(evento: FormEvent) {
    evento.preventDefault();
    setErro("");
    try {
      await autenticar(credenciais.username, credenciais.password);
      setAutenticado(true);
      setModulo("dashboard");
    } catch {
      setErro("Usuário ou senha inválidos.");
    }
  }

  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    setCarregando(true);
    setErro("");
    try {
      if (edicaoId) await atualizarPropriedade(edicaoId, formulario);
      else await criarPropriedade(formulario);
      setFormulario(formularioVazio);
      setEdicaoId(null);
      await carregar(busca);
    } catch (falha) {
      setErro(mensagemDoErro(falha));
      setCarregando(false);
    }
  }

  function editar(item: Propriedade) {
    if (!item.pode_editar) {
      setErro("Seu perfil não permite editar esta propriedade.");
      return;
    }
    setEdicaoId(item.id);
    setFormulario({
      nome: item.nome,
      proprietario: item.proprietario,
      municipio: item.municipio,
      uf: item.uf,
      area_hectares: item.area_hectares,
      latitude: item.latitude ?? "",
      longitude: item.longitude ?? "",
      observacoes: item.observacoes,
      arquivo_kml: null,
    });
    setModulo("propriedades");
  }

  async function excluir(item: Propriedade) {
    if (!item.pode_excluir) {
      setErro("Somente administradores podem excluir propriedades.");
      return;
    }
    if (!window.confirm(`Excluir a propriedade "${item.nome}"?`)) return;
    setErro("");
    try {
      await excluirPropriedade(item.id);
      await carregar(busca);
    } catch (falha) {
      setErro(mensagemDoErro(falha));
    }
  }

  function logout() {
    sair();
    setAutenticado(false);
    setPermissoes(permissoesVazias);
    setPropriedades([]);
    setSelecionada(null);
  }

  const scopedProperties = selecionada ? [selecionada] : propriedades;
  const roles = useMemo(
    () => new Set(scopedProperties.map((item) => item.papel_usuario).filter(Boolean)),
    [scopedProperties],
  );
  const canManage = permissoes.superusuario || roles.has("administrador") || roles.has("gestor");
  const canOperate = canManage || roles.has("operador");
  const roleLabel = permissoes.superusuario
    ? "Superusuário"
    : selecionada?.papel_usuario === "administrador"
      ? "Administrador"
      : selecionada?.papel_usuario === "gestor"
        ? "Gestor"
        : selecionada?.papel_usuario === "operador"
          ? "Operador"
          : "Somente leitura";
  const navigationItems = NAVIGATION_ITEMS.filter(
    (item) => !item.requiresProperty || propriedades.length > 0,
  );
  const identity = getUserIdentity();

  const propertiesContent = (
    <section className="properties-page">
      <PageHeader
        eyebrow="Estrutura rural"
        title="Propriedades"
        description="Cadastre, consulte e selecione as unidades rurais autorizadas."
      />
      {erro && <AlertCard title="Não foi possível concluir" tone="danger"><p>{erro}</p></AlertCard>}
      <section className="grade">
        {(permissoes.pode_criar_propriedade || edicaoId !== null) ? (
          <form className="card formulario" onSubmit={salvar}>
            <h2>{edicaoId ? "Editar propriedade" : "Nova propriedade"}</h2>
            <label>Nome<input required value={formulario.nome} onChange={(event) => setFormulario({ ...formulario, nome: event.target.value })} /></label>
            <label>Proprietário<input value={formulario.proprietario} onChange={(event) => setFormulario({ ...formulario, proprietario: event.target.value })} /></label>
            <div className="linha">
              <label>Município<input required value={formulario.municipio} onChange={(event) => setFormulario({ ...formulario, municipio: event.target.value })} /></label>
              <label>UF<input maxLength={2} value={formulario.uf} onChange={(event) => setFormulario({ ...formulario, uf: event.target.value.toUpperCase() })} /></label>
            </div>
            <label>Área (ha)<input required min="0.01" step="0.01" type="number" value={formulario.area_hectares} onChange={(event) => setFormulario({ ...formulario, area_hectares: event.target.value })} /></label>
            <div className="linha">
              <label>Latitude<input step="any" type="number" value={formulario.latitude} onChange={(event) => setFormulario({ ...formulario, latitude: event.target.value })} /></label>
              <label>Longitude<input step="any" type="number" value={formulario.longitude} onChange={(event) => setFormulario({ ...formulario, longitude: event.target.value })} /></label>
            </div>
            <label>KML (até 5 MB)<input accept=".kml" type="file" onChange={(event) => setFormulario({ ...formulario, arquivo_kml: event.target.files?.[0] ?? null })} /></label>
            <label>Observações<textarea value={formulario.observacoes} onChange={(event) => setFormulario({ ...formulario, observacoes: event.target.value })} /></label>
            <div className="acoes">
              <button disabled={carregando} type="submit">Salvar</button>
              {edicaoId && <button className="secundario" type="button" onClick={() => { setEdicaoId(null); setFormulario(formularioVazio); }}>Cancelar</button>}
            </div>
          </form>
        ) : (
          <AlertCard title="Acesso de consulta" tone="info"><p>Seu perfil permite consultar somente as propriedades autorizadas.</p></AlertCard>
        )}

        <section className="conteudo">
          <form className="busca" onSubmit={(event) => { event.preventDefault(); void carregar(busca); }}>
            <input aria-label="Buscar propriedades" placeholder="Buscar por nome, município ou proprietário" value={busca} onChange={(event) => setBusca(event.target.value)} />
            <button type="submit">Buscar</button>
          </form>
          {carregando && propriedades.length === 0 ? (
            <p>Carregando propriedades...</p>
          ) : propriedades.length === 0 ? (
            <EmptyState title="Nenhuma propriedade autorizada" />
          ) : (
            <div className="lista">
              {propriedades.map((item) => (
                <article className={`card item ${selecionada?.id === item.id ? "ativo" : ""}`} key={item.id} onClick={() => setSelecionada(item)}>
                  <div>
                    <h3>{item.nome}</h3>
                    <p>{item.municipio}/{item.uf} · {item.area_hectares} ha declarados</p>
                    <p className="metadado-geografico">Perfil: {item.papel_usuario ?? "superusuário"}</p>
                    {item.area_calculada_hectares && <p className="metadado-geografico">{item.area_calculada_hectares} ha calculados{item.divergencia_area_percentual && ` · diferença ${item.divergencia_area_percentual}%`}</p>}
                  </div>
                  {(item.pode_editar || item.pode_excluir) && (
                    <div className="acoes">
                      {item.pode_editar && <button className="secundario" onClick={(event) => { event.stopPropagation(); editar(item); }}>Editar</button>}
                      {item.pode_excluir && <button className="perigo" onClick={(event) => { event.stopPropagation(); void excluir(item); }}>Excluir</button>}
                    </div>
                  )}
                </article>
              ))}
            </div>
          )}
          {selecionada?.latitude && selecionada.longitude && (
            <MapaPropriedade
              latitude={Number(selecionada.latitude)}
              longitude={Number(selecionada.longitude)}
              nome={selecionada.nome}
              geometria={selecionada.geometria_geojson}
            />
          )}
        </section>
      </section>
    </section>
  );

  if (!autenticado) {
    return (
      <main className="login enterprise-login">
        <form className="card" onSubmit={enviarLogin}>
          <span className="kicker">ERP agrícola</span>
          <h1>AGRO-AI-PRO</h1>
          <p>Gestão integrada, segura e orientada por dados.</p>
          <label>Usuário<input autoComplete="username" value={credenciais.username} onChange={(event) => setCredenciais({ ...credenciais, username: event.target.value })} required /></label>
          <label>Senha<input autoComplete="current-password" type="password" value={credenciais.password} onChange={(event) => setCredenciais({ ...credenciais, password: event.target.value })} required /></label>
          {erro && <p className="erro">{erro}</p>}
          <button type="submit">Entrar</button>
        </form>
      </main>
    );
  }

  return (
    <AppShell
      items={navigationItems}
      activeModule={modulo}
      onNavigate={setModulo}
      properties={propriedades}
      selectedPropertyId={selecionada ? String(selecionada.id) : ""}
      onSelectedPropertyChange={(id) => setSelecionada(propriedades.find((item) => String(item.id) === id) ?? null)}
      safra={safra}
      onSafraChange={setSafra}
      userLabel={identity.label}
      roleLabel={roleLabel}
      theme={theme}
      onToggleTheme={toggleTheme}
      onLogout={logout}
      statusSlot={<AplicativoStatus />}
    >
      <ModuleRenderer
        module={modulo}
        properties={propriedades}
        selectedProperty={selecionada}
        safra={safra}
        propertiesContent={propertiesContent}
        canManage={canManage}
        canOperate={canOperate}
      />
    </AppShell>
  );
}
