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
  type PapelPropriedade,
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
  FilterBar,
  PageHeader,
  PermissionGuard,
  SearchInput,
} from "./components/shared/ui";
import { useTheme } from "./hooks/useTheme";
import { getUserIdentity } from "./utils/session";

import "./styles.css";

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

const ROLE_LABELS: Record<PapelPropriedade, string> = {
  administrador: "Administrador",
  gestor: "Gestor",
  operador: "Operador",
  leitura: "Somente leitura",
};

function mensagemDoErro(erro: unknown) {
  if (axios.isAxiosError(erro)) {
    const dados = erro.response?.data;
    if (erro.response?.status === 403 && !dados?.detail) {
      return "Seu perfil não permite concluir esta operação.";
    }
    if (erro.response?.status === 404 && !dados?.detail) {
      return "Registro não encontrado ou fora das propriedades autorizadas.";
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
  const [selectedPropertyId, setSelectedPropertyId] = useState("");
  const [safra, setSafra] = useState("");
  const [edicaoId, setEdicaoId] = useState<number | null>(null);
  const [pendingDelete, setPendingDelete] = useState<Propriedade | null>(null);
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
      setSelectedPropertyId((current) =>
        current && dados.some((item) => String(item.id) === current) ? current : "",
      );
    } catch (falha) {
      setErro(mensagemDoErro(falha));
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    if (autenticado) {
      void carregar();
    }
  }, [autenticado, carregar]);

  const selectedProperty = useMemo(
    () => propriedades.find((item) => String(item.id) === selectedPropertyId) ?? null,
    [propriedades, selectedPropertyId],
  );

  const visibleNavigation = useMemo(
    () => NAVIGATION_ITEMS.filter((item) =>
      !item.requiresProperty || permissoes.superusuario || propriedades.length > 0,
    ),
    [permissoes.superusuario, propriedades.length],
  );

  useEffect(() => {
    if (!visibleNavigation.some((item) => item.id === modulo)) {
      setModulo("dashboard");
    }
  }, [modulo, visibleNavigation]);

  const roleLabel = useMemo(() => {
    if (permissoes.superusuario) return "Superusuário";
    if (selectedProperty?.papel_usuario) return ROLE_LABELS[selectedProperty.papel_usuario];
    const roles = new Set(propriedades.map((item) => item.papel_usuario).filter(Boolean));
    if (roles.size === 1) return ROLE_LABELS[[...roles][0] as PapelPropriedade];
    if (roles.size > 1) return "Múltiplos perfis";
    return "Sem propriedade";
  }, [permissoes.superusuario, propriedades, selectedProperty]);

  const userIdentity = useMemo(() => getUserIdentity(), [autenticado]);

  const mapFeatures = useMemo<AgriculturalMapFeature[]>(() => {
    const scope = selectedProperty ? [selectedProperty] : propriedades;
    return scope.map((item) => ({
      id: item.id,
      kind: "propriedade" as const,
      name: item.nome,
      subtitle: `${item.municipio}/${item.uf} · ${item.area_hectares} ha`,
      latitude: item.latitude === null ? null : Number(item.latitude),
      longitude: item.longitude === null ? null : Number(item.longitude),
      geometry: item.geometria_geojson,
    }));
  }, [propriedades, selectedProperty]);

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
      if (edicaoId) {
        await atualizarPropriedade(edicaoId, formulario);
      } else {
        await criarPropriedade(formulario);
      }
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
    setSelectedPropertyId(String(item.id));
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
  }

  function solicitarExclusao(item: Propriedade) {
    if (!item.pode_excluir) {
      setErro("Somente administradores podem excluir propriedades.");
      return;
    }
    setPendingDelete(item);
  }

  async function confirmarExclusao() {
    if (!pendingDelete) return;
    setErro("");
    try {
      await excluirPropriedade(pendingDelete.id);
      if (selectedPropertyId === String(pendingDelete.id)) setSelectedPropertyId("");
      setPendingDelete(null);
      await carregar(busca);
    } catch (falha) {
      setErro(mensagemDoErro(falha));
      setPendingDelete(null);
    }
  }

  function encerrarSessao() {
    sair();
    setAutenticado(false);
    setPermissoes(permissoesVazias);
    setPropriedades([]);
    setSelectedPropertyId("");
    setModulo("dashboard");
  }

  if (!autenticado) {
    return (
      <main className="login">
        <form className="card login-card" onSubmit={enviarLogin}>
          <span className="kicker">ERP agrícola</span>
          <h1>AGRO-AI-PRO</h1>
          <p>Entre para acessar as propriedades e módulos autorizados.</p>
          <label>
            Usuário
            <input
              autoComplete="username"
              value={credenciais.username}
              onChange={(evento) => setCredenciais({ ...credenciais, username: evento.target.value })}
              required
            />
          </label>
          <label>
            Senha
            <input
              autoComplete="current-password"
              type="password"
              value={credenciais.password}
              onChange={(evento) => setCredenciais({ ...credenciais, password: evento.target.value })}
              required
            />
          </label>
          {erro && <p className="erro">{erro}</p>}
          <button type="submit">Entrar</button>
          <button className="secundario" type="button" onClick={toggleTheme}>Usar tema {theme === "dark" ? "claro" : "escuro"}</button>
        </form>
      </main>
    );
  }

  const propertiesContent = (
    <section className="properties-page">
      <PageHeader
        eyebrow="Estrutura rural"
        title="Propriedades"
        description="Cadastros, permissões, área declarada, geometrias e localização."
      />

      {erro && <p className="erro card">{erro}</p>}

      <section className="grade">
        <PermissionGuard
          allowed={permissoes.pode_criar_propriedade || edicaoId !== null}
          fallback={<EmptyState title="Consulta autorizada" description="Seu perfil permite consultar as propriedades vinculadas, sem criar ou editar cadastros." />}
        >
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
              {edicaoId && (
                <button className="secundario" type="button" onClick={() => { setEdicaoId(null); setFormulario(formularioVazio); }}>Cancelar</button>
              )}
            </div>
          </form>
        </PermissionGuard>

        <section className="conteudo">
          <form onSubmit={(event) => { event.preventDefault(); void carregar(busca); }}>
            <FilterBar>
              <SearchInput aria-label="Buscar propriedades" placeholder="Buscar por nome, município ou proprietário" value={busca} onChange={(event) => setBusca(event.target.value)} />
              <button type="submit">Buscar</button>
            </FilterBar>
          </form>

          {carregando && propriedades.length === 0 ? (
            <div className="card vazio">Carregando propriedades...</div>
          ) : propriedades.length === 0 ? (
            <EmptyState title="Nenhuma propriedade autorizada" description="Solicite um vínculo ativo ou cadastre a primeira propriedade, conforme seu perfil." />
          ) : (
            <div className="lista">
              {propriedades.map((item) => (
                <article className={`card item ${selectedProperty?.id === item.id ? "ativo" : ""}`} key={item.id} onClick={() => setSelectedPropertyId(String(item.id))}>
                  <div>
                    <h3>{item.nome}</h3>
                    <p>{item.municipio}/{item.uf} · {item.area_hectares} ha declarados</p>
                    <p className="metadado-geografico">Perfil: {item.papel_usuario ? ROLE_LABELS[item.papel_usuario] : "Superusuário"}</p>
                    {item.area_calculada_hectares && (
                      <p className="metadado-geografico">
                        {item.area_calculada_hectares} ha calculados
                        {item.divergencia_area_percentual && ` · diferença ${item.divergencia_area_percentual}%`}
                      </p>
                    )}
                  </div>
                  {(item.pode_editar || item.pode_excluir) && (
                    <div className="acoes">
                      {item.pode_editar && <button className="secundario" onClick={(event) => { event.stopPropagation(); editar(item); }}>Editar</button>}
                      {item.pode_excluir && <button className="perigo" onClick={(event) => { event.stopPropagation(); solicitarExclusao(item); }}>Excluir</button>}
                    </div>
                  )}
                </article>
              ))}
            </div>
          )}

          <AgriculturalMap features={mapFeatures} emptyMessage="Cadastre coordenadas ou importe KML para visualizar as propriedades." />
        </section>
      </section>
    </section>
  );

  return (
    <>
      <AppShell
        items={visibleNavigation}
        activeModule={modulo}
        onNavigate={setModulo}
        properties={propriedades}
        selectedPropertyId={selectedPropertyId}
        onSelectedPropertyChange={setSelectedPropertyId}
        safra={safra}
        onSafraChange={setSafra}
        userLabel={userIdentity.label}
        roleLabel={roleLabel}
        theme={theme}
        onToggleTheme={toggleTheme}
        onLogout={encerrarSessao}
        statusSlot={<AplicativoStatus />}
      >
        <ModuleRenderer
          module={modulo}
          properties={propriedades}
          selectedProperty={selectedProperty}
          safra={safra}
          propertiesContent={propertiesContent}
        />
      </AppShell>
      <ConfirmDialog
        open={pendingDelete !== null}
        title="Excluir propriedade"
        description={`Confirma a exclusão de ${pendingDelete?.nome ?? "esta propriedade"}? A API continuará protegendo vínculos existentes.`}
        confirmLabel="Excluir"
        onCancel={() => setPendingDelete(null)}
        onConfirm={() => void confirmarExclusao()}
      />
    </>
  );
}
