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
import AppShell from "./components/layout/AppShell";
import AgriculturalMap, { type AgriculturalMapFeature } from "./components/maps/AgriculturalMap";
import AplicativoStatus from "./components/AplicativoStatus";
import {
  ConfirmDialog,
  EmptyState,
  LoadingState,
  PageHeader,
  PermissionGuard,
  SearchInput,
} from "./components/shared/ui";
import { useTheme } from "./hooks/useTheme";
import { getUserIdentity } from "./utils/session";

import "./styles.css";

const emptyForm: PropriedadeInput = {
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

const emptyPermissions: PermissoesUsuario = {
  pode_criar_propriedade: false,
  superusuario: false,
};

const roleLabels = {
  administrador: "Administrador",
  gestor: "Gestor",
  operador: "Operador",
  leitura: "Somente leitura",
} as const;

function errorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data;
    if (error.response?.status === 403 && !data?.detail) {
      return "Seu perfil não permite concluir esta operação.";
    }
    if (error.response?.status === 404 && !data?.detail) {
      return "O recurso solicitado não foi encontrado ou não pertence às suas propriedades autorizadas.";
    }
    if (typeof data?.detail === "string") return data.detail;
    if (data && typeof data === "object") return Object.values(data).flat().join(" ");
  }
  return "Não foi possível concluir a operação.";
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(estaAutenticado());
  const [module, setModule] = useState<ModuleId>("dashboard");
  const [credentials, setCredentials] = useState({ username: "", password: "" });
  const [properties, setProperties] = useState<Propriedade[]>([]);
  const [permissions, setPermissions] = useState(emptyPermissions);
  const [selected, setSelected] = useState<Propriedade | null>(null);
  const [harvest, setHarvest] = useState("");
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<Propriedade | null>(null);
  const { theme, toggleTheme } = useTheme();

  const loadProperties = useCallback(async (term = "") => {
    setLoading(true);
    setError("");
    try {
      const [data, profile] = await Promise.all([
        listarPropriedades(term),
        obterPermissoesUsuario(),
      ]);
      setProperties(data);
      setPermissions(profile);
      setSelected((current) => data.find((item) => item.id === current?.id) ?? data[0] ?? null);
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authenticated) void loadProperties();
  }, [authenticated, loadProperties]);

  const availableNavigation = useMemo(() => {
    const hasPropertyScope = permissions.superusuario || properties.length > 0;
    return NAVIGATION_ITEMS.filter((item) => !item.requiresProperty || hasPropertyScope);
  }, [permissions.superusuario, properties.length]);

  useEffect(() => {
    if (!availableNavigation.some((item) => item.id === module)) setModule("dashboard");
  }, [availableNavigation, module]);

  async function submitLogin(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await autenticar(credentials.username, credentials.password);
      setAuthenticated(true);
      setModule("dashboard");
    } catch {
      setError("Usuário ou senha inválidos.");
    }
  }

  async function saveProperty(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (editId) await atualizarPropriedade(editId, form);
      else await criarPropriedade(form);
      setForm(emptyForm);
      setEditId(null);
      await loadProperties(search);
    } catch (failure) {
      setError(errorMessage(failure));
      setLoading(false);
    }
  }

  function editProperty(item: Propriedade) {
    if (!item.pode_editar) {
      setError("Seu perfil não permite editar esta propriedade.");
      return;
    }
    setEditId(item.id);
    setForm({
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
    setModule("propriedades");
  }

  function requestDelete(item: Propriedade) {
    if (!item.pode_excluir) {
      setError("Somente administradores podem excluir propriedades.");
      return;
    }
    setDeleteTarget(item);
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setError("");
    try {
      await excluirPropriedade(deleteTarget.id);
      setDeleteTarget(null);
      await loadProperties(search);
    } catch (failure) {
      setError(errorMessage(failure));
    }
  }

  function logout() {
    sair();
    setAuthenticated(false);
    setPermissions(emptyPermissions);
    setProperties([]);
    setSelected(null);
    setModule("dashboard");
  }

  if (!authenticated) {
    return (
      <main className="login enterprise-login">
        <form className="card" onSubmit={submitLogin}>
          <div className="enterprise-login__brand"><span>A</span><div><h1>AGRO-AI-PRO</h1><p>ERP agrícola inteligente</p></div></div>
          <label>Usuário<input autoComplete="username" value={credentials.username} onChange={(event) => setCredentials({ ...credentials, username: event.target.value })} required /></label>
          <label>Senha<input autoComplete="current-password" type="password" value={credentials.password} onChange={(event) => setCredentials({ ...credentials, password: event.target.value })} required /></label>
          {error && <p className="erro">{error}</p>}
          <button type="submit">Entrar</button>
        </form>
      </main>
    );
  }

  const identity = getUserIdentity();
  const roleLabel = permissions.superusuario
    ? "Superusuário"
    : selected?.papel_usuario
      ? roleLabels[selected.papel_usuario]
      : "Acesso autenticado";
  const selectedFeatures: AgriculturalMapFeature[] = selected ? [{
    id: selected.id,
    kind: "propriedade",
    name: selected.nome,
    subtitle: `${selected.municipio}/${selected.uf}`,
    latitude: selected.latitude === null ? null : Number(selected.latitude),
    longitude: selected.longitude === null ? null : Number(selected.longitude),
    geometry: selected.geometria_geojson,
  }] : [];

  const propertiesContent = (
    <section className="properties-page">
      <PageHeader eyebrow="Cadastros rurais" title="Propriedades" description="Consulte e gerencie somente as propriedades autorizadas para o seu perfil." />
      {error && <p className="erro card" role="alert">{error}</p>}
      <section className="grade properties-grid">
        <PermissionGuard
          allowed={permissions.pode_criar_propriedade || editId !== null}
          fallback={<div className="card vazio">Seu perfil permite consultar as propriedades autorizadas, sem criar ou editar cadastros.</div>}
        >
          <form className="card formulario" onSubmit={saveProperty}>
            <h2>{editId ? "Editar propriedade" : "Nova propriedade"}</h2>
            <label>Nome<input required value={form.nome} onChange={(event) => setForm({ ...form, nome: event.target.value })} /></label>
            <label>Proprietário<input value={form.proprietario} onChange={(event) => setForm({ ...form, proprietario: event.target.value })} /></label>
            <div className="linha">
              <label>Município<input required value={form.municipio} onChange={(event) => setForm({ ...form, municipio: event.target.value })} /></label>
              <label>UF<input maxLength={2} value={form.uf} onChange={(event) => setForm({ ...form, uf: event.target.value.toUpperCase() })} /></label>
            </div>
            <label>Área (ha)<input required min="0.01" step="0.01" type="number" value={form.area_hectares} onChange={(event) => setForm({ ...form, area_hectares: event.target.value })} /></label>
            <div className="linha">
              <label>Latitude<input step="any" type="number" value={form.latitude} onChange={(event) => setForm({ ...form, latitude: event.target.value })} /></label>
              <label>Longitude<input step="any" type="number" value={form.longitude} onChange={(event) => setForm({ ...form, longitude: event.target.value })} /></label>
            </div>
            <label>KML (até 5 MB)<input accept=".kml" type="file" onChange={(event) => setForm({ ...form, arquivo_kml: event.target.files?.[0] ?? null })} /></label>
            <label>Observações<textarea value={form.observacoes} onChange={(event) => setForm({ ...form, observacoes: event.target.value })} /></label>
            <div className="acoes">
              <button disabled={loading} type="submit">{loading ? "Salvando..." : "Salvar"}</button>
              {editId && <button className="secundario" type="button" onClick={() => { setEditId(null); setForm(emptyForm); }}>Cancelar</button>}
            </div>
          </form>
        </PermissionGuard>

        <section className="conteudo">
          <form className="busca" onSubmit={(event) => { event.preventDefault(); void loadProperties(search); }}>
            <SearchInput aria-label="Buscar propriedades" placeholder="Buscar por nome, município ou proprietário" value={search} onChange={(event) => setSearch(event.target.value)} />
            <button type="submit">Buscar</button>
          </form>
          {loading && properties.length === 0 ? <LoadingState label="Carregando propriedades..." /> : properties.length === 0 ? <EmptyState title="Nenhuma propriedade autorizada" description="Solicite um vínculo ou cadastre a primeira propriedade, quando permitido." /> : (
            <div className="lista">
              {properties.map((item) => (
                <article className={`card item ${selected?.id === item.id ? "ativo" : ""}`} key={item.id} onClick={() => setSelected(item)}>
                  <div>
                    <h3>{item.nome}</h3>
                    <p>{item.municipio}/{item.uf} · {item.area_hectares} ha declarados</p>
                    <p className="metadado-geografico">Perfil: {item.papel_usuario ? roleLabels[item.papel_usuario] : "Superusuário"}</p>
                    {item.area_calculada_hectares && <p className="metadado-geografico">{item.area_calculada_hectares} ha calculados{item.divergencia_area_percentual && ` · diferença ${item.divergencia_area_percentual}%`}</p>}
                  </div>
                  {(item.pode_editar || item.pode_excluir) && <div className="acoes">
                    {item.pode_editar && <button className="secundario" onClick={(event) => { event.stopPropagation(); editProperty(item); }}>Editar</button>}
                    {item.pode_excluir && <button className="perigo" onClick={(event) => { event.stopPropagation(); requestDelete(item); }}>Excluir</button>}
                  </div>}
                </article>
              ))}
            </div>
          )}
          <AgriculturalMap features={selectedFeatures} emptyMessage="A propriedade selecionada ainda não possui coordenadas ou KML processado." />
        </section>
      </section>
    </section>
  );

  return (
    <AppShell
      items={availableNavigation}
      activeModule={module}
      onNavigate={setModule}
      properties={properties}
      selectedPropertyId={selected ? String(selected.id) : ""}
      onSelectedPropertyChange={(id) => setSelected(id ? properties.find((item) => item.id === Number(id)) ?? null : null)}
      safra={harvest}
      onSafraChange={setHarvest}
      userLabel={identity.label}
      roleLabel={roleLabel}
      theme={theme}
      onToggleTheme={toggleTheme}
      onLogout={logout}
      statusSlot={<AplicativoStatus />}
    >
      <ModuleRenderer module={module} properties={properties} selectedProperty={selected} safra={harvest} propertiesContent={propertiesContent} />
      <ConfirmDialog
        open={deleteTarget !== null}
        title="Excluir propriedade"
        description={`Confirma a exclusão de “${deleteTarget?.nome ?? ""}”? As proteções do backend continuam ativas.`}
        confirmLabel="Excluir"
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => void confirmDelete()}
      />
    </AppShell>
  );
}
