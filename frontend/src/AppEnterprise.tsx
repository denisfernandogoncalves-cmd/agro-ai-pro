import axios from "axios";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  atualizarPropriedade,
  autenticar,
  criarPropriedade,
  estaAutenticado,
  excluirPropriedade,
  listarPropriedades,
  obterPermissoesUsuario,
  sair,
  type PermissoesUsuario,
  type Propriedade,
  type PropriedadeInput,
} from "./api/propriedades";
import ModuleRenderer from "./app/ModuleRenderer";
import { NAVIGATION_ITEMS, type ModuleId } from "./app/navigation";
import AplicativoStatus from "./components/AplicativoStatus";
import AppShell from "./components/layout/AppShell";
import MapaPropriedade from "./components/MapaPropriedade";
import {
  AlertCard,
  EmptyState,
  LoadingState,
  PageHeader,
  PermissionGuard,
  SearchInput,
  SectionCard,
} from "./components/shared/ui";
import { useTheme } from "./hooks/useTheme";
import { getUserIdentity } from "./utils/session";

import "./styles.css";
import "./styles/tokens.css";
import "./styles/enterprise.css";


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

function errorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data;
    if (error.response?.status === 403 && !data?.detail) {
      return "Seu perfil não permite concluir esta operação.";
    }
    if (error.response?.status === 404 && !data?.detail) {
      return "O registro não foi encontrado ou não pertence ao seu escopo autorizado.";
    }
    if (typeof data?.detail === "string") return data.detail;
    if (data && typeof data === "object") return Object.values(data).flat().join(" ");
  }
  return "Não foi possível concluir a operação.";
}

export default function AppEnterprise() {
  const [authenticated, setAuthenticated] = useState(estaAutenticado());
  const [activeModule, setActiveModule] = useState<ModuleId>("dashboard");
  const [credentials, setCredentials] = useState({ username: "", password: "" });
  const [properties, setProperties] = useState<Propriedade[]>([]);
  const [permissions, setPermissions] = useState(emptyPermissions);
  const [selectedPropertyId, setSelectedPropertyId] = useState("");
  const [harvest, setHarvest] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { theme, toggleTheme } = useTheme();

  const selectedProperty = useMemo(
    () => properties.find((item) => String(item.id) === selectedPropertyId) ?? null,
    [properties, selectedPropertyId],
  );
  const identity = useMemo(() => getUserIdentity(), [authenticated]);
  const navigation = useMemo(
    () => NAVIGATION_ITEMS.filter((item) => !item.requiresProperty || properties.length > 0),
    [properties.length],
  );
  const roleLabel = permissions.superusuario
    ? "Superusuário"
    : selectedProperty?.papel_usuario === "administrador"
      ? "Administrador"
      : selectedProperty?.papel_usuario === "gestor"
        ? "Gestor"
        : selectedProperty?.papel_usuario === "operador"
          ? "Operador"
          : selectedProperty?.papel_usuario === "leitura"
            ? "Somente leitura"
            : properties.length > 1
              ? "Múltiplos acessos"
              : "Usuário";

  const load = useCallback(async (term = "") => {
    setLoading(true);
    setError("");
    try {
      const [data, profile] = await Promise.all([
        listarPropriedades(term),
        obterPermissoesUsuario(),
      ]);
      setProperties(data);
      setPermissions(profile);
      setSelectedPropertyId((current) => data.some((item) => String(item.id) === current) ? current : "");
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authenticated) void load();
  }, [authenticated, load]);

  useEffect(() => {
    const active = navigation.some((item) => item.id === activeModule);
    if (!active) setActiveModule("dashboard");
  }, [activeModule, navigation]);

  async function submitLogin(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await autenticar(credentials.username, credentials.password);
      setAuthenticated(true);
      setActiveModule("dashboard");
    } catch {
      setError("Usuário ou senha inválidos.");
    }
  }

  async function saveProperty(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (editingId) await atualizarPropriedade(editingId, form);
      else await criarPropriedade(form);
      setForm(emptyForm);
      setEditingId(null);
      await load(search);
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
    setEditingId(item.id);
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
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function removeProperty(item: Propriedade) {
    if (!item.pode_excluir) {
      setError("Somente administradores podem excluir propriedades.");
      return;
    }
    if (!window.confirm(`Excluir a propriedade "${item.nome}"?`)) return;
    setError("");
    try {
      await excluirPropriedade(item.id);
      await load(search);
    } catch (failure) {
      setError(errorMessage(failure));
    }
  }

  function logout() {
    sair();
    setAuthenticated(false);
    setPermissions(emptyPermissions);
    setProperties([]);
    setSelectedPropertyId("");
    setActiveModule("dashboard");
  }

  if (!authenticated) {
    return (
      <main className="login enterprise-login">
        <form className="card enterprise-login__card" onSubmit={submitLogin}>
          <span className="enterprise-login__mark" aria-hidden="true">A</span>
          <div><span className="kicker">ERP agrícola</span><h1>AGRO-AI-PRO</h1></div>
          <p>Entre para acessar propriedades, produção, operações, mercado e gestão financeira.</p>
          <label>Usuário<input autoComplete="username" value={credentials.username} onChange={(event) => setCredentials({ ...credentials, username: event.target.value })} required /></label>
          <label>Senha<input autoComplete="current-password" type="password" value={credentials.password} onChange={(event) => setCredentials({ ...credentials, password: event.target.value })} required /></label>
          {error && <p className="erro">{error}</p>}
          <button type="submit">Entrar</button>
        </form>
      </main>
    );
  }

  const propertiesContent = (
    <section className="enterprise-properties">
      <PageHeader
        eyebrow="Estrutura rural"
        title="Propriedades"
        description="Cadastros e geometrias dentro do escopo autorizado do usuário."
      />
      {error && <AlertCard title="Não foi possível concluir" tone="danger"><p>{error}</p></AlertCard>}
      <div className="enterprise-properties__layout">
        <PermissionGuard
          allowed={permissions.pode_criar_propriedade || editingId !== null}
          fallback={<AlertCard title="Acesso de consulta" tone="info"><p>Seu perfil permite consultar as propriedades autorizadas sem alterar o cadastro.</p></AlertCard>}
        >
          <SectionCard title={editingId ? "Editar propriedade" : "Nova propriedade"} className="enterprise-properties__form-card">
            <form className="formulario" onSubmit={saveProperty}>
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
                <button disabled={loading} type="submit">Salvar</button>
                {editingId && <button className="secundario" type="button" onClick={() => { setEditingId(null); setForm(emptyForm); }}>Cancelar</button>}
              </div>
            </form>
          </SectionCard>
        </PermissionGuard>

        <div className="enterprise-properties__content">
          <form className="busca" onSubmit={(event) => { event.preventDefault(); void load(search); }}>
            <SearchInput aria-label="Buscar propriedades" placeholder="Buscar por nome, município ou proprietário" value={search} onChange={(event) => setSearch(event.target.value)} />
            <button type="submit">Buscar</button>
            {search && <button className="secundario" type="button" onClick={() => { setSearch(""); void load(); }}>Limpar</button>}
          </form>
          {loading && properties.length === 0 ? <LoadingState label="Carregando propriedades..." /> : properties.length === 0 ? (
            <EmptyState title="Nenhuma propriedade autorizada" description="Confirme os vínculos de acesso ou cadastre a primeira propriedade, quando permitido." />
          ) : (
            <div className="lista">
              {properties.map((item) => (
                <article className={`card item ${selectedProperty?.id === item.id ? "ativo" : ""}`} key={item.id} onClick={() => setSelectedPropertyId(String(item.id))}>
                  <div>
                    <h3>{item.nome}</h3>
                    <p>{item.municipio}/{item.uf} · {item.area_hectares} ha declarados</p>
                    <p className="metadado-geografico">Perfil: {item.papel_usuario ?? "superusuário"}</p>
                    {item.area_calculada_hectares && <p className="metadado-geografico">{item.area_calculada_hectares} ha calculados{item.divergencia_area_percentual && ` · diferença ${item.divergencia_area_percentual}%`}</p>}
                  </div>
                  {(item.pode_editar || item.pode_excluir) && (
                    <div className="acoes">
                      {item.pode_editar && <button className="secundario" onClick={(event) => { event.stopPropagation(); editProperty(item); }}>Editar</button>}
                      {item.pode_excluir && <button className="perigo" onClick={(event) => { event.stopPropagation(); void removeProperty(item); }}>Excluir</button>}
                    </div>
                  )}
                </article>
              ))}
            </div>
          )}
          {selectedProperty?.latitude && selectedProperty.longitude && (
            <MapaPropriedade latitude={Number(selectedProperty.latitude)} longitude={Number(selectedProperty.longitude)} nome={selectedProperty.nome} geometria={selectedProperty.geometria_geojson} />
          )}
        </div>
      </div>
    </section>
  );

  return (
    <AppShell
      items={navigation}
      activeModule={activeModule}
      onNavigate={setActiveModule}
      properties={properties}
      selectedPropertyId={selectedPropertyId}
      onSelectedPropertyChange={setSelectedPropertyId}
      safra={harvest}
      onSafraChange={setHarvest}
      userLabel={identity.label}
      roleLabel={roleLabel}
      theme={theme}
      onToggleTheme={toggleTheme}
      onLogout={logout}
      statusSlot={<AplicativoStatus />}
    >
      {error && activeModule !== "propriedades" && <AlertCard title="Atenção" tone="danger"><p>{error}</p></AlertCard>}
      <ModuleRenderer
        module={activeModule}
        properties={properties}
        selectedProperty={selectedProperty}
        safra={harvest}
        propertiesContent={propertiesContent}
      />
    </AppShell>
  );
}
