import { coordenadasParaMapa } from "./utils/coordenadas";
import CoordenadasInput from "./components/CoordenadasInput";
import MarcaAgro from "./components/MarcaAgro";
import IdentidadeModulo, { tituloModulo } from "./components/IdentidadeModulo";
import ExportacaoConferenciaImportacoes from "./components/ExportacaoConferenciaImportacoes";
import MatrizPermissoes from "./components/MatrizPermissoes";
import { AcoesContext, autorizado, BotaoAcao, DestinoConsulta, useDestinoConsulta } from "./components/AcoesContext";
import { nomeModulo } from "./components/gruposModulos";
import { FormEvent, lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import type { Pagina, UsuarioAtual } from "./api/usuarios";
import NavegacaoModulos from "./components/NavegacaoModulos";
import PainelFormulario from "./components/PainelFormulario";
import { ProtecaoAlteracoes, useAlteracoesNaoSalvas, useConfirmarSaida } from "./components/AlteracoesNaoSalvas";
import { ConfirmacoesCompactas } from "./components/ConfirmacaoCompacta";
import AvisoSessao from "./components/AvisoSessao";
import VersaoAplicativo from "./components/VersaoAplicativo";

import {
  api,
  atualizarPropriedade,
  arquivarPropriedade,
  criarPropriedade,
  excluirPropriedade,
  listarPropriedades,
  Propriedade,
  PropriedadeInput,
} from "./api/propriedades";
import { useAuth } from "./auth/AuthContext";
import AplicativoStatus from "./components/AplicativoStatus";

import "./styles.css";
import "./premium.css";
import ImprimirA4 from "./components/ImprimirA4";
import PropriedadesImpressao from "./components/PropriedadesImpressao";

const PainelPage = lazy(() => import("./pages/Painel/PainelPage"));

const HistoricoPage = lazy(() => import("./pages/Historico/HistoricoPage"));
const BackupPage = lazy(() => import("./pages/Backup/BackupPage"));
const UsuariosPage = lazy(() => import("./pages/Usuarios/UsuariosPage"));
const MapaPropriedade = lazy(() => import("./components/MapaPropriedade"));
const CargasColhidasPage = lazy(() => import("./pages/CargasColhidas/CargasColhidasPage"));
const CadastrosAgricolasPage = lazy(() => import("./pages/CadastrosAgricolas/CadastrosAgricolasPage"));
const ProducaoSaldosPage = lazy(() => import("./pages/ProducaoSaldos/ProducaoSaldosPage"));
const TransferenciasSaldoPage = lazy(() => import("./pages/TransferenciasSaldo/TransferenciasSaldoPage"));
const VendasPage = lazy(() => import("./pages/Vendas/VendasPage"));
const CavacoPage = lazy(() => import("./pages/Cavaco/CavacoPage"));
const EstoquePage = lazy(() => import("./pages/Estoque/EstoquePage"));
const FaturamentoInsumos = lazy(() => import("./pages/Estoque/FaturamentoInsumos"));
const FinanceiroPage = lazy(() => import("./pages/Financeiro/FinanceiroModulo"));
const TransportesPage = lazy(() => import("./pages/Transportes/TransportesPage"));
const MaquinasPage = lazy(() => import("./pages/Maquinas/MaquinasPage"));
const OperacoesPage = lazy(() => import("./pages/Operacoes/OperacoesPage"));
const RelatoriosPage = lazy(() => import("./pages/Relatorios/RelatoriosPage"));
const AjudaModulo = lazy(() => import("./components/AjudaModulo"));
const ImportacoesPage = lazy(() => import("./pages/Importacoes/ImportacoesPage"));
const InsightsPage = lazy(() => import("./pages/Insights/InsightsPage"));
const TalhoesPage = lazy(() => import("./pages/Talhoes/TalhoesPage"));
const GruposColheitaPage = lazy(() => import("./pages/Talhoes/GruposPropriedadesPanel"));

const areaEmAlqueires = (valor: string | number | null | undefined) =>
  (Number(valor || 0) / 2.42).toLocaleString("pt-BR", { minimumFractionDigits: 4, maximumFractionDigits: 4 });
const valorAlqueiresParaFormulario = (valor: string | number | null | undefined) =>
  valor === null || valor === undefined || valor === "" ? "" : String(Number((Number(valor) / 2.42).toFixed(4)));


const formularioVazio: PropriedadeInput = {
  formato_coordenadas: "gms", latitude_gms: "", longitude_gms: "", converter_coordenadas: "false",
  cad_pro_identificacao: "",
  tipo_imovel: "",
  apelido: "",
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
    <main className="login login-premium">
      <section className="login-institucional" aria-label="Apresentação do AGRO AI PRO">
        <MarcaAgro />
        <div className="login-manifesto"><span className="kicker">Gestão agrícola inteligente</span><h2>Do campo ao mercado.<br />Cada decisão, mais clara.</h2><p>Inteligência que impulsiona o agro</p><div className="login-pilares"><span>Produção</span><span>Gestão</span><span>Inteligência</span></div></div>
        <small>AGRO AI PRO · Tecnologia a serviço da sua operação</small>
      </section>
      <form className="card" onSubmit={submitLogin}>
        <MarcaAgro />
        <div><span className="kicker">Bem-vindo à sua gestão</span><h1>Acesse sua conta</h1><p>Entre para acompanhar sua operação agrícola.</p></div>
        <label>
          Usuário
          <input
            autoComplete="username"
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
            autoComplete="current-password"
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
        <VersaoAplicativo />
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
  const [mostrarArquivadas, setMostrarArquivadas] = useState(false);
  const [propriedades, setPropriedades] = useState<Propriedade[]>([]);
  const [selecionada, setSelecionada] = useState<Propriedade | null>(null);
  const coordenadasSelecionadas = selecionada ? coordenadasParaMapa(selecionada) : null;
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
      const dados = await listarPropriedades(termo, mostrarArquivadas);
      setPropriedades(dados);
      setSelecionada((atual) =>
        dados.find((item) => item.id === atual?.id) ?? null
      );
    } catch (falha) {
      setErro(mensagemDoErro(falha));
    } finally {
      setCarregando(false);
    }
  }, [mostrarArquivadas]);

  useEffect(() => {
    if (acesso && acesso.modulos.length > 0) void carregar(busca);
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
      cad_pro_identificacao: item.cad_pro_identificacao ?? "",
      tipo_imovel: item.tipo_imovel ?? "",
      apelido: item.apelido ?? "",
      nome: item.nome,
      proprietario: item.proprietario,
      municipio: item.municipio,
      uf: item.uf,
      area_hectares: valorAlqueiresParaFormulario(item.area_hectares),
      formato_coordenadas: item.formato_coordenadas ?? "decimal",
      latitude_gms: item.latitude_gms ?? "", longitude_gms: item.longitude_gms ?? "", converter_coordenadas: "false",
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

  async function alterarArquivo(item: Propriedade) {
    if (travaPropriedade.current) return;
    const restaurar = Boolean(item.arquivada_em);
    if (!window.confirm(restaurar ? `Restaurar a propriedade "${item.nome}" na lista?` : `Arquivar a propriedade "${item.nome}"? Cargas, saldos, áreas e demais históricos serão preservados.`)) return;
    travaPropriedade.current = true; setSalvando(true); setErro("");
    try {
      await arquivarPropriedade(item.id, restaurar);
      await carregar(busca);
    } catch (falha) { setErro(mensagemDoErro(falha)); }
    finally { travaPropriedade.current = false; setSalvando(false); }
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
    <main className="pagina agro-premium" data-modulo={modulo} id="conteudo-principal">
      <a className="agro-skip nao-imprimir" href="#modulo-atual">Ir para o conteúdo</a>
      <header>
        <div className="cabecalho-identidade">
          <span className="marca-aplicativo" aria-hidden="true">AG</span>
          <div>
            <span className="kicker">AGRO-AI-PRO · Gestão rural</span>
            <h1>
            {tituloModulo(modulo)}
            </h1>
            <IdentidadeModulo modulo={modulo} />
          </div>
        </div>
        <div className="cabecalho-acoes">
          <AplicativoStatus />
          <VersaoAplicativo />
          <ImprimirA4 />
          <button className="secundario" onClick={() => { void encerrarSessao(); }}>Sair</button>
        </div>
      </header>

      <DestinoPropriedade destino={destino} aplicar={(termo, id) => {setBusca(termo); void carregar(termo); if (id) setSelecionada(propriedades.find(item => item.id === id) ?? null);}} />
      <NavegacaoModulos acesso={acesso} modulo={modulo} onResultado={async (item, termo) => {
        if (!(await confirmarSaida())) return;
        setDestino({ modulo: item.modulo, filtros: { search: termo, tipo: item.tipo }, registro: /^\d+$/.test(item.id) ? Number(item.id) : undefined, chave: Date.now() });
        setModulo(item.modulo);
      }} onSelecionar={async id => {if (id !== modulo && !(await confirmarSaida())) return; if (id !== modulo && modulo === "propriedades") {setFormulario(formularioVazio); setEdicaoId(null);} setDestino(undefined); setModulo(id);}} />
      <AvisoSessao />
      <div id="modulo-atual" tabIndex={-1} />
      {modulo !== "financeiro" && acesso && autorizado(acesso, modulo, "consultar") && <AjudaModulo modulo={modulo} />}

      {!acesso ? (
        <section className="card"><p role={erroAcesso ? "alert" : "status"}>{erroAcesso ? "Não foi possível verificar seus acessos." : "Carregando acessos..."}</p>{erroAcesso && <button onClick={() => void atualizarAcesso()}>Tentar novamente</button>}</section>
      ) : !autorizado(acesso, modulo, "consultar") ? (
        <section className="card"><p>Nenhum item permitido. Solicite acesso ao administrador.</p></section>
      ) : modulo === "inicio" ? (
        <div className="inicio-dashboard"><PainelPage propriedades={propriedades} abrir={async alvo => {if (!(await confirmarSaida())) return; setDestino({...alvo, chave:Date.now()}); setModulo(alvo.modulo);}} /></div>
      ) : modulo === "historico" ? (
        <HistoricoPage />
      ) : modulo === "backup" ? (
        <BackupPage />
      ) : modulo === "faturamento-insumos" ? (
        <FaturamentoInsumos />
      ) : modulo === "usuarios" ? (
        <><MatrizPermissoes /><UsuariosPage usuarioAtualId={acesso.id} onAtualizado={() => void atualizarAcesso()} /></>
      ) : modulo === "grupos-colheita" ? (
        <GruposColheitaPage propriedades={propriedades} />
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
      ) : modulo === "financeiro" ? (
        <FinanceiroPage propriedades={propriedades} />
      ) : modulo === "cavaco" ? (<CavacoPage />
      ) : modulo === "estoque" ? (
        <EstoquePage propriedades={propriedades} />
      ) : modulo === "operacoes" ? (
        <OperacoesPage />
      ) : modulo === "transportes" ? (
        <TransportesPage />
      ) : modulo === "maquinas" ? (
        <MaquinasPage propriedades={propriedades} />
      ) : modulo === "importacoes" ? (
        <><ExportacaoConferenciaImportacoes /><ImportacoesPage /></>
      ) : modulo === "relatorios" ? (
        <RelatoriosPage propriedades={propriedades} abrir={(alvo,filtros={})=>{void confirmarSaida().then(ok=>{if(!ok)return;setDestino({modulo:alvo,filtros,chave:Date.now()});setModulo(alvo);});}} />
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
          <label>Apelido<input maxLength={100} value={formulario.apelido ?? ""} onChange={e => setFormulario({ ...formulario, apelido: e.target.value })} placeholder="Nome pelo qual a propriedade é conhecida" /></label>
          <label>Proprietário<input value={formulario.proprietario} onChange={(e) => setFormulario({ ...formulario, proprietario: e.target.value })} /></label>
          <label>BP C.Vale<input inputMode="numeric" pattern="[0-9]*" maxLength={40} value={formulario.bp_cvale ?? ""} onChange={e => setFormulario({ ...formulario, bp_cvale: e.target.value })} /><small>Opcional. Usado como BEP somente no faturamento da C.Vale.</small></label>
          <div className="linha">
            <label>Município<input required value={formulario.municipio} onChange={(e) => setFormulario({ ...formulario, municipio: e.target.value })} /></label>
            <label>UF<input maxLength={2} value={formulario.uf} onChange={(e) => setFormulario({ ...formulario, uf: e.target.value.toUpperCase() })} /></label>
          </div>
          <label>Área (alqueires paulistas)<input required min="0.0001" step="0.0001" type="number" value={formulario.area_hectares} onChange={(e) => setFormulario({ ...formulario, area_hectares: e.target.value })} /></label>
          <label>Número CAD/PRO<input placeholder="Ex.: 123.456-7" value={formulario.cad_pro_numero} onChange={(e) => setFormulario({ ...formulario, cad_pro_numero: e.target.value })} /></label>
          <label>Identificação do CAD/PRO<input maxLength={100} list="cad-pro-identificacoes" placeholder="Principal ou Secundário" value={formulario.cad_pro_identificacao ?? ""} onChange={e => setFormulario({ ...formulario, cad_pro_identificacao: e.target.value })} /></label>
          <datalist id="cad-pro-identificacoes"><option value="Principal" /><option value="Secundário" /></datalist>
          <label>Tipo do imóvel<select value={formulario.tipo_imovel ?? ""} onChange={e => setFormulario({ ...formulario, tipo_imovel: e.target.value as PropriedadeInput["tipo_imovel"] })}><option value="">Não informado</option><option value="arrendado">Imóvel arrendado</option><option value="proprio">Imóvel próprio</option></select></label>
          <div className="linha">
            <CoordenadasInput dados={formulario} alterar={setFormulario} />
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

          <label className="opcao-checkbox nao-imprimir"><input type="checkbox" checked={mostrarArquivadas} disabled={salvando} onChange={e => setMostrarArquivadas(e.target.checked)} />Mostrar propriedades arquivadas</label>

          {carregando && propriedades.length === 0 ? (
            <p role="status">Carregando propriedades...</p>
          ) : propriedades.length === 0 ? (
            <div className="card vazio">Nenhuma propriedade cadastrada.</div>
          ) : (
            <div className="lista propriedades-lista">
              {propriedades.map((item) => (
                <article className={`card item ${selecionada?.id === item.id ? "ativo" : ""}`} key={item.id} onClick={() => setSelecionada(atual => atual?.id === item.id ? null : item)}>
                  <div>
                    <h3><button type="button" className="nome-propriedade-mapa" aria-expanded={selecionada?.id === item.id} aria-controls={`mapa-propriedade-${item.id}`} title="Ver localização no mapa" onClick={e => { e.stopPropagation(); setSelecionada(atual => atual?.id === item.id ? null : item); }}>{item.nome}</button></h3>
                    {item.arquivada_em && <p><strong>Arquivada</strong> — histórico preservado</p>}
                    {!!item.apelidos?.length && <p><strong>Apelido:</strong> {item.apelidos.join(" / ")}</p>}
                    <p>{item.municipio}/{item.uf} · {areaEmAlqueires(item.area_hectares)} alq. declarados</p>
                    <p>CAD/PRO: {item.cad_pro_numeros.length ? item.cad_pro_numeros.join(", ") : "não informado"}</p>
                    {item.cad_pro_identificacao && <p>Identificação do CAD/PRO: {item.cad_pro_identificacao}</p>}
                    <p>{item.tipo_imovel === "arrendado" ? "Imóvel arrendado" : item.tipo_imovel === "proprio" ? "Imóvel próprio" : "Tipo do imóvel não informado"}</p>
                    {item.area_calculada_hectares && (
                      <p className="metadado-geografico">
                        {areaEmAlqueires(item.area_calculada_hectares)} alq. calculados
                        {item.divergencia_area_percentual &&
                          ` · diferença ${item.divergencia_area_percentual}%`}
                      </p>
                    )}
                  </div>
                  <div className="acoes">
                    {!item.arquivada_em && <BotaoAcao acao="editar" disabled={salvando} className="secundario" onClick={(e) => { e.stopPropagation(); editar(item); }}>Editar</BotaoAcao>}
                    {!item.arquivada_em && <BotaoAcao acao="excluir" disabled={salvando} className="perigo" onClick={(e) => { e.stopPropagation(); void excluir(item); }}>Excluir</BotaoAcao>}
                    <BotaoAcao acao={item.arquivada_em ? "editar" : "excluir"} disabled={salvando} className="secundario" onClick={e => { e.stopPropagation(); void alterarArquivo(item); }}>{item.arquivada_em ? "Restaurar" : "Arquivar"}</BotaoAcao>
                  </div>
                  {selecionada?.id === item.id && <section id={`mapa-propriedade-${item.id}`} className="propriedade-mapa-inline nao-imprimir" aria-label={`Localização de ${item.nome}`} onClick={e => e.stopPropagation()}>
                    {coordenadasSelecionadas ? <Suspense fallback={<p role="status">Carregando mapa...</p>}>
                      <MapaPropriedade latitude={coordenadasSelecionadas.latitude} longitude={coordenadasSelecionadas.longitude} nome={item.nome} geometria={item.geometria_geojson} />
                    </Suspense> : <p role="status">Esta propriedade não possui coordenadas válidas cadastradas. Use Editar para informar latitude e longitude.</p>}
                  </section>}
                </article>
              ))}
            </div>
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
