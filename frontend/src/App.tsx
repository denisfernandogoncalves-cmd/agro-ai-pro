import { AcoesContext, autorizado, BotaoAcao, DestinoConsulta, useDestinoConsulta } from "./components/AcoesContext";
import { nomeModulo } from "./components/gruposModulos";
import { FormEvent, lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import type { Pagina, UsuarioAtual } from "./api/usuarios";
import NavegacaoModulos from "./components/NavegacaoModulos";
import PainelFormulario from "./components/PainelFormulario";
import { ProtecaoAlteracoes, useAlteracoesNaoSalvas, useConfirmarSaida } from "./components/AlteracoesNaoSalvas";
import { ConfirmacoesCompactas } from "./components/ConfirmacaoCompacta";

import {
  api,
  atualizarPropriedade,
  criarPropriedade,
  excluirPropriedade,
  listarPropriedades,
  Propriedade,
  PropriedadeInput,
} from "./api/propriedades";
import { useAuth } from "./auth/AuthContext";
import AplicativoStatus from "./components/AplicativoStatus";

import "./styles.css";
import ImprimirA4 from "./components/ImprimirA4";
import PropriedadesImpressao from "./components/PropriedadesImpressao";

const PainelPage = lazy(() => import("./pages/Painel/PainelPage"));
const HistoricoPage = lazy(() => import("./pages/Historico/HistoricoPage"));
const UsuariosPage = lazy(() => import("./pages/Usuarios/UsuariosPage"));
const MapaPropriedade = lazy(() => import("./components/MapaPropriedade"));
const ClimaPage = lazy(() => import("./pages/Clima/ClimaPage"));
const CargasColhidasPage = lazy(() => import("./pages/CargasColhidas/CargasColhidasPage"));
const CadastrosAgricolasPage = lazy(() => import("./pages/CadastrosAgricolas/CadastrosAgricolasPage"));
const ProducaoSaldosPage = lazy(() => import("./pages/ProducaoSaldos/ProducaoSaldosPage"));
const TransferenciasSaldoPage = lazy(() => import("./pages/TransferenciasSaldo/TransferenciasSaldoPage"));
const VendasPage = lazy(() => import("./pages/Vendas/VendasPage"));
const EstoquePage = lazy(() => import("./pages/Estoque/EstoquePage"));
const FaturamentoInsumos = lazy(() => import("./pages/Estoque/FaturamentoInsumos"));
const FinanceiroPage = lazy(() => import("./pages/Financeiro/FinanceiroPage"));
const MercadoPage = lazy(() => import("./pages/Mercado/MercadoPage"));
const MaquinasPage = lazy(() => import("./pages/Maquinas/MaquinasPage"));
const OperacoesPage = lazy(() => import("./pages/Operacoes/OperacoesPage"));
const RelatoriosPage = lazy(() => import("./pages/Relatorios/RelatoriosPage"));
const ImportacoesPage = lazy(() => import("./pages/Importacoes/ImportacoesPage"));
const InsightsPage = lazy(() => import("./pages/Insights/InsightsPage"));
const TalhoesPage = lazy(() => import("./pages/Talhoes/TalhoesPage"));

const areaEmAlqueires = (valor: string | number | null | undefined) =>
  (Number(valor || 0) / 2.42).toLocaleString("pt-BR", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
const valorAlqueiresParaFormulario = (valor: string | number | null | undefined) =>
  valor === null || valor === undefined || valor === "" ? "" : String(Number((Number(valor) / 2.42).toFixed(4)));


const formularioVazio: PropriedadeInput = {
  bp_cvale: "",
  nome: "",
  proprietario: "",
  municipio: "",
  uf: "",
  area_hectares: "",
  latitude: "",
  longitude: "",
  observacoes: "",
  cad_pro_numero: "",
  arquivo_kml: null,
};

function mensagemDoErro(erro: unknown) {
  if (axios.isAxiosError(erro)) {
    const dados = erro.response?.data;
    if (typeof dados?.detail === "string") {
      return dados.detail;
    }
    if (dados && typeof dados === "object") {
      return Object.values(dados).flat().join(" ");
    }
  }
  return "Não foi possível concluir a operação.";
}

type LoginProps = {
  authenticate: (username: string, password: string) => Promise<void>;
};

function Login({ authenticate }: LoginProps) {
  const [credentials, setCredentials] = useState({
    username: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [entrando, setEntrando] = useState(false);
  const travaLogin = useRef(false);

  async function submitLogin(event: FormEvent) {
    event.preventDefault();
    if (travaLogin.current) return;
    travaLogin.current = true; setEntrando(true);
    setError("");
    try {
      await authenticate(credentials.username, credentials.password);
      setCredentials({ username: "", password: "" });
    } catch {
      setError("Usuário ou senha inválidos.");
    } finally { travaLogin.current = false; setEntrando(false); }
  }

  return (
    <main className="login">
      <form className="card" onSubmit={submitLogin}>
        <h1>AGRO-AI-PRO</h1>
        <p>Acesse o módulo de propriedades.</p>
        <label>
          Usuário
          <input
            value={credentials.username}
            onChange={(event) =>
              setCredentials({
                ...credentials,
                username: event.target.value,
              })
            }
            required
          />
        </label>
        <label>
          Senha
          <input
            type="password"
            value={credentials.password}
            onChange={(event) =>
              setCredentials({
                ...credentials,
                password: event.target.value,
              })
            }
            required
          />
        </label>
        {error && <p className="erro" role="alert">{error}</p>}
        <button disabled={entrando} type="submit">{entrando ? "Entrando..." : "Entrar"}</button>
      </form>
    </main>
  );
}

type PrivateAreaProps = {
  sair: () => Promise<boolean>;
};

function DestinoPropriedade({ destino, aplicar }: {destino?: DestinoConsulta; aplicar: (termo:string, id?:number) => void}) {
  useDestinoConsulta("propriedades", (filtros, id) => aplicar(String(filtros.search || ""), id));
  return destino ? <p className="card destino-aviso nao-imprimir">Consulta aberta a partir do painel{destino.registro ? ` · registro #${destino.registro}` : ""}. Confira o registro indicado abaixo.</p> : null;
}

function PrivateArea({ sair }: PrivateAreaProps) {
  const confirmarSaida = useConfirmarSaida();
  const [acesso, setAcesso] = useState<UsuarioAtual | null>(null);
  const [erroAcesso, setErroAcesso] = useState(false);
  const [modulo, setModulo] = useState<Pagina>("inicio");
  const [destino, setDestino] = useState<DestinoConsulta>();
  const atualizarAcesso = useCallback(async () => {
    try {
      const { data } = await api.get<UsuarioAtual>("/auth/me/");
      setAcesso(data); setErroAcesso(false);
      setModulo(atual => autorizado(data, atual, "consultar") ? atual : "inicio");
    } catch { setAcesso(null); setErroAcesso(true); }
  }, []);
  useEffect(() => {
    let ativo = true;
    const atualizar = () => { if (ativo) void atualizarAcesso(); };
    atualizar();
    window.addEventListener("focus", atualizar);
    const intervalo = window.setInterval(atualizar, 30000);
    return () => { ativo = false; window.removeEventListener("focus", atualizar); window.clearInterval(intervalo); };
  }, [atualizarAcesso]);
  const [propriedades, setPropriedades] = useState<Propriedade[]>([]);
  const [selecionada, setSelecionada] = useState<Propriedade | null>(null);
  const [edicaoId, setEdicaoId] = useState<number | null>(null);
  const [formulario, setFormulario] = useState(formularioVazio);
  const [busca, setBusca] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);
  const travaPropriedade = useRef(false);
  const protecaoPropriedade = useAlteracoesNaoSalvas(formulario, "Propriedade", edicaoId, modulo === "propriedades");

  const carregar = useCallback(async (termo = "") => {
    setCarregando(true);
    setErro("");
    try {
      const dados = await listarPropriedades(termo);
      setPropriedades(dados);
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
    if (acesso && acesso.modulos.some(item => item !== "mercado")) void carregar();
    else { setPropriedades([]); setSelecionada(null); }
  }, [carregar, acesso?.modulos.join(",")]);

  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    if (travaPropriedade.current) return;
    travaPropriedade.current = true; setSalvando(true);
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
    } finally { travaPropriedade.current = false; setSalvando(false); }
  }

  async function editar(item: Propriedade) {
    if (!(await protecaoPropriedade.confirmarDescarte())) return;
    setEdicaoId(item.id);
    setFormulario({
      bp_cvale: item.bp_cvale ?? "",
      nome: item.nome,
      proprietario: item.proprietario,
      municipio: item.municipio,
      uf: item.uf,
      area_hectares: valorAlqueiresParaFormulario(item.area_hectares),
      latitude: item.latitude ?? "",
      longitude: item.longitude ?? "",
      observacoes: item.observacoes,
      cad_pro_numero: item.cad_pro_numeros[0] ?? "",
      arquivo_kml: null,
    });
  }

  async function excluir(item: Propriedade) {
    if (travaPropriedade.current) return;
    if (!window.confirm(`Excluir a propriedade "${item.nome}"?`)) {
      return;
    }
    setErro("");
    travaPropriedade.current = true; setSalvando(true);
    try {
      await excluirPropriedade(item.id);
      await carregar(busca);
    } catch (falha) {
      setErro(mensagemDoErro(falha));
    } finally { travaPropriedade.current = false; setSalvando(false); }
  }

  async function encerrarSessao() {
    if (!(await confirmarSaida())) return;
    setErro("");
    setModulo("inicio");
    setPropriedades([]);
    setSelecionada(null);
    setEdicaoId(null);
    setFormulario(formularioVazio);
    setBusca("");
    setCarregando(false);
    await sair();
  }

  return (
    <AcoesContext.Provider value={{acesso, modulo, destino}}><Suspense fallback={<main className="pagina"><section className="card" role="status">Carregando tela...</section></main>}>
    <main className="pagina">
      <header>
        <div className="cabecalho-identidade">
          <span className="marca-aplicativo" aria-hidden="true">AG</span>
          <div>
            <span className="kicker">AGRO-AI-PRO · Gestão rural</span>
            <h1>
            {modulo === "inicio" ? "Painel inicial" : modulo === "historico" ? "Histórico de alterações" : modulo === "usuarios" ? "Usuários" : nomeModulo(modulo)}
            </h1>
          </div>
        </div>
        <div className="cabecalho-acoes">
          <AplicativoStatus />
          <ImprimirA4 />
          <button className="secundario" onClick={() => { void encerrarSessao(); }}>Sair</button>
        </div>
      </header>

      <DestinoPropriedade destino={destino} aplicar={(termo, id) => {setBusca(termo); void carregar(termo); if (id) setSelecionada(propriedades.find(item => item.id === id) ?? null);}} />
      <NavegacaoModulos acesso={acesso} modulo={modulo} onSelecionar={async id => {if (id !== modulo && !(await confirmarSaida())) return; if (id !== modulo && modulo === "propriedades") {setFormulario(formularioVazio); setEdicaoId(null);} setDestino(undefined); setModulo(id);}} />

      {!acesso ? (
        <section className="card"><p role={erroAcesso ? "alert" : "status"}>{erroAcesso ? "Não foi possível verificar seus acessos." : "Carregando acessos..."}</p>{erroAcesso && <button onClick={() => void atualizarAcesso()}>Tentar novamente</button>}</section>
      ) : !autorizado(acesso, modulo, "consultar") ? (
        <section className="card"><p>Nenhum item permitido. Solicite acesso ao administrador.</p></section>
      ) : modulo === "inicio" ? (
        <PainelPage propriedades={propriedades} abrir={async alvo => {if (!(await confirmarSaida())) return; setDestino({...alvo, chave:Date.now()}); setModulo(alvo.modulo);}} />
      ) : modulo === "historico" ? (
        <HistoricoPage />
      ) : modulo === "faturamento-insumos" ? (
        <FaturamentoInsumos />
      ) : modulo === "usuarios" ? (
        <UsuariosPage usuarioAtualId={acesso.id} onAtualizado={() => void atualizarAcesso()} />
      ) : modulo === "talhoes" ? (
        <TalhoesPage />
      ) : modulo === "cadastros-agricolas" ? (
        <CadastrosAgricolasPage propriedades={propriedades} />
      ) : modulo === "cargas" ? (
        <CargasColhidasPage propriedades={propriedades} />
      ) : modulo === "producao-saldos" ? (
        <ProducaoSaldosPage propriedades={propriedades} />
      ) : modulo === "transferencias" ? (
        <TransferenciasSaldoPage />
      ) : modulo === "vendas" ? (
        <VendasPage />
      ) : modulo === "clima" ? (
        <ClimaPage propriedades={propriedades} />
      ) : modulo === "mercado" ? (
        <MercadoPage />
      ) : modulo === "financeiro" ? (
        <FinanceiroPage propriedades={propriedades} />
      ) : modulo === "estoque" ? (
        <EstoquePage propriedades={propriedades} />
      ) : modulo === "operacoes" ? (
        <OperacoesPage />
      ) : modulo === "maquinas" ? (
        <MaquinasPage propriedades={propriedades} />
      ) : modulo === "importacoes" ? (
        <ImportacoesPage />
      ) : modulo === "relatorios" ? (
        <RelatoriosPage propriedades={propriedades} />
      ) : modulo === "insights" ? (
        <InsightsPage propriedades={propriedades} />
      ) : (
        <>
          {erro && <p className="erro card" role="alert">{erro}</p>}

          <section className="grade modulo-propriedades">
        <PropriedadesImpressao propriedades={propriedades} carregando={carregando} />
        <PainelFormulario titulo={edicaoId ? "Editar propriedade" : "Nova propriedade"} edicao={edicaoId}>
        <form className="card formulario" onSubmit={salvar}>
          <fieldset className="campos-formulario" disabled={salvando}>
          <h2>{edicaoId ? "Editar propriedade" : "Nova propriedade"}</h2>
          <label>Nome<input required value={formulario.nome} onChange={(e) => setFormulario({ ...formulario, nome: e.target.value })} /></label>
          <label>Proprietário<input value={formulario.proprietario} onChange={(e) => setFormulario({ ...formulario, proprietario: e.target.value })} /></label>
          <label>BP C.Vale<input inputMode="numeric" pattern="[0-9]*" maxLength={40} value={formulario.bp_cvale ?? ""} onChange={e => setFormulario({ ...formulario, bp_cvale: e.target.value })} /><small>Opcional. Usado como BEP somente no faturamento da C.Vale.</small></label>
          <div className="linha">
            <label>Município<input required value={formulario.municipio} onChange={(e) => setFormulario({ ...formulario, municipio: e.target.value })} /></label>
            <label>UF<input maxLength={2} value={formulario.uf} onChange={(e) => setFormulario({ ...formulario, uf: e.target.value.toUpperCase() })} /></label>
          </div>
          <label>Área (alqueires paulistas)<input required min="0.01" step="0.01" type="number" value={formulario.area_hectares} onChange={(e) => setFormulario({ ...formulario, area_hectares: e.target.value })} /></label>
          <label>Número CAD/PRO<input placeholder="Ex.: 123.456-7" value={formulario.cad_pro_numero} onChange={(e) => setFormulario({ ...formulario, cad_pro_numero: e.target.value })} /></label>
          <div className="linha">
            <label>Latitude<input step="any" type="number" value={formulario.latitude} onChange={(e) => setFormulario({ ...formulario, latitude: e.target.value })} /></label>
            <label>Longitude<input step="any" type="number" value={formulario.longitude} onChange={(e) => setFormulario({ ...formulario, longitude: e.target.value })} /></label>
          </div>
          <label>KML (até 5 MB)<input accept=".kml" type="file" onChange={(e) => setFormulario({ ...formulario, arquivo_kml: e.target.files?.[0] ?? null })} /></label>
          <label>Observações<textarea value={formulario.observacoes} onChange={(e) => setFormulario({ ...formulario, observacoes: e.target.value })} /></label>
          <div className="acoes">
            <button disabled={carregando || salvando} type="submit">{salvando ? "Salvando..." : "Salvar"}</button>
            {edicaoId && <button className="secundario" type="button" onClick={() => { setEdicaoId(null); setFormulario(formularioVazio); }}>Cancelar</button>}
          </div>
          </fieldset>
        </form>
        </PainelFormulario>

        <section className="conteudo">
          <form className="busca" onSubmit={(e) => { e.preventDefault(); void carregar(busca); }}>
            <input aria-label="Buscar propriedades" placeholder="Buscar por nome, município ou proprietário" value={busca} onChange={(e) => setBusca(e.target.value)} />
            <button type="submit">Buscar</button>
          </form>

          {carregando && propriedades.length === 0 ? (
            <p role="status">Carregando propriedades...</p>
          ) : propriedades.length === 0 ? (
            <div className="card vazio">Nenhuma propriedade cadastrada.</div>
          ) : (
            <div className="lista propriedades-lista">
              {propriedades.map((item) => (
                <article className={`card item ${selecionada?.id === item.id ? "ativo" : ""}`} key={item.id} onClick={() => setSelecionada(item)}>
                  <div>
                    <h3>{item.nome}</h3>
                    <p>{item.municipio}/{item.uf} · {areaEmAlqueires(item.area_hectares)} alq. declarados</p>
                    <p>CAD/PRO: {item.cad_pro_numeros.length ? item.cad_pro_numeros.join(", ") : "não informado"}</p>
                    {item.area_calculada_hectares && (
                      <p className="metadado-geografico">
                        {areaEmAlqueires(item.area_calculada_hectares)} alq. calculados
                        {item.divergencia_area_percentual &&
                          ` · diferença ${item.divergencia_area_percentual}%`}
                      </p>
                    )}
                  </div>
                  <div className="acoes">
                    <BotaoAcao acao="editar" disabled={salvando} className="secundario" onClick={(e) => { e.stopPropagation(); editar(item); }}>Editar</BotaoAcao>
                    <BotaoAcao acao="excluir" disabled={salvando} className="perigo" onClick={(e) => { e.stopPropagation(); void excluir(item); }}>Excluir</BotaoAcao>
                  </div>
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
        </>
      )}
    </main>
    </Suspense></AcoesContext.Provider>
  );
}

export default function App() {
  const {
    autenticado,
    autenticar,
    geracao,
    sair,
  } = useAuth();

  if (!autenticado) {
    return <Login key={`login-${geracao}`} authenticate={autenticar} />;
  }

  return <ConfirmacoesCompactas key={`confirmacoes-${geracao}`}><ProtecaoAlteracoes><PrivateArea key={`private-${geracao}`} sair={sair} /></ProtecaoAlteracoes></ConfirmacoesCompactas>;
}
