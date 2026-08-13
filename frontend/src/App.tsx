import { FormEvent, useCallback, useEffect, useState } from "react";
import axios from "axios";

import {
  atualizarPropriedade,
  criarPropriedade,
  excluirPropriedade,
  listarPropriedades,
  Propriedade,
  PropriedadeInput,
} from "./api/propriedades";
import { useAuth } from "./auth/AuthContext";
import MapaPropriedade from "./components/MapaPropriedade";
import AplicativoStatus from "./components/AplicativoStatus";
import ClimaPage from "./pages/Clima/ClimaPage";
import CargasColhidasPage from "./pages/CargasColhidas/CargasColhidasPage";
import GruposColheitaPage from "./pages/GruposColheita/GruposColheitaPage";
import ProducaoSaldosPage from "./pages/ProducaoSaldos/ProducaoSaldosPage";
import VendasPage from "./pages/Vendas/VendasPage";
import EstoquePage from "./pages/Estoque/EstoquePage";
import FinanceiroPage from "./pages/Financeiro/FinanceiroPage";
import MercadoPage from "./pages/Mercado/MercadoPage";
import MaquinasPage from "./pages/Maquinas/MaquinasPage";
import OperacoesPage from "./pages/Operacoes/OperacoesPage";
import RelatoriosPage from "./pages/Relatorios/RelatoriosPage";
import InsightsPage from "./pages/Insights/InsightsPage";
import TalhoesPage from "./pages/Talhoes/TalhoesPage";

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

  async function submitLogin(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await authenticate(credentials.username, credentials.password);
      setCredentials({ username: "", password: "" });
    } catch {
      setError("Usuário ou senha inválidos.");
    }
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
        {error && <p className="erro">{error}</p>}
        <button type="submit">Entrar</button>
      </form>
    </main>
  );
}

type PrivateAreaProps = {
  sair: () => Promise<boolean>;
};

function PrivateArea({ sair }: PrivateAreaProps) {
  const [modulo, setModulo] = useState<
    "propriedades" | "talhoes" | "grupos-colheita" | "cargas" | "producao-saldos" | "vendas" | "clima" | "mercado" | "financeiro" | "estoque" | "operacoes" | "maquinas" | "relatorios" | "insights"
  >("propriedades");
  const [propriedades, setPropriedades] = useState<Propriedade[]>([]);
  const [selecionada, setSelecionada] = useState<Propriedade | null>(null);
  const [edicaoId, setEdicaoId] = useState<number | null>(null);
  const [formulario, setFormulario] = useState(formularioVazio);
  const [busca, setBusca] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");

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
    void carregar();
  }, [carregar]);

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

  async function excluir(item: Propriedade) {
    if (!window.confirm(`Excluir a propriedade "${item.nome}"?`)) {
      return;
    }
    setErro("");
    try {
      await excluirPropriedade(item.id);
      await carregar(busca);
    } catch (falha) {
      setErro(mensagemDoErro(falha));
    }
  }

  async function encerrarSessao() {
    setErro("");
    setModulo("propriedades");
    setPropriedades([]);
    setSelecionada(null);
    setEdicaoId(null);
    setFormulario(formularioVazio);
    setBusca("");
    setCarregando(false);
    await sair();
  }

  return (
    <main className="pagina">
      <header>
        <div>
          <span className="kicker">Gestão rural</span>
          <h1>
            {modulo === "propriedades"
              ? "Propriedades"
              : modulo === "talhoes"
                ? "Talhões"
                : modulo === "grupos-colheita"
                  ? "Grupos de colheita"
                : modulo === "cargas"
                  ? "Cargas colhidas"
                : modulo === "producao-saldos"
                  ? "Produção e saldos"
                : modulo === "vendas"
                  ? "Vendas"
                : modulo === "clima"
                  ? "Clima"
                  : modulo === "mercado"
                    ? "Mercado"
                    : modulo === "financeiro"
                      ? "Financeiro"
                      : modulo === "estoque"
                        ? "Estoque"
                        : modulo === "operacoes" ? "Operações" : modulo === "maquinas" ? "Máquinas" : modulo === "relatorios" ? "Relatórios" : "Assistente"}
          </h1>
        </div>
        <div className="cabecalho-acoes">
          <AplicativoStatus />
          <button className="secundario" onClick={() => { void encerrarSessao(); }}>Sair</button>
        </div>
      </header>

      <nav className="navegacao-modulos" aria-label="Módulos agrícolas">
        <button
          className={modulo === "propriedades" ? "" : "secundario"}
          onClick={() => setModulo("propriedades")}
        >
          Propriedades
        </button>
        <button
          className={modulo === "talhoes" ? "" : "secundario"}
          onClick={() => setModulo("talhoes")}
        >
          Talhões
        </button>
        <button
          className={modulo === "grupos-colheita" ? "" : "secundario"}
          onClick={() => setModulo("grupos-colheita")}
        >
          Grupos de colheita
        </button>
        <button
          className={modulo === "cargas" ? "" : "secundario"}
          onClick={() => setModulo("cargas")}
        >
          Cargas colhidas
        </button>
        <button
          className={modulo === "producao-saldos" ? "" : "secundario"}
          onClick={() => setModulo("producao-saldos")}
        >
          Produção e saldos
        </button>
        <button
          className={modulo === "vendas" ? "" : "secundario"}
          onClick={() => setModulo("vendas")}
        >
          Vendas
        </button>
        <button
          className={modulo === "clima" ? "" : "secundario"}
          onClick={() => setModulo("clima")}
        >
          Clima
        </button>
        <button
          className={modulo === "mercado" ? "" : "secundario"}
          onClick={() => setModulo("mercado")}
        >
          Mercado
        </button>
        <button
          className={modulo === "financeiro" ? "" : "secundario"}
          onClick={() => setModulo("financeiro")}
        >
          Financeiro
        </button>
        <button
          className={modulo === "estoque" ? "" : "secundario"}
          onClick={() => setModulo("estoque")}
        >
          Estoque
        </button>
        <button
          className={modulo === "operacoes" ? "" : "secundario"}
          onClick={() => setModulo("operacoes")}
        >
          Operações
        </button>
        <button className={modulo === "maquinas" ? "" : "secundario"} onClick={() => setModulo("maquinas")}>Máquinas</button>
        <button className={modulo === "relatorios" ? "" : "secundario"} onClick={() => setModulo("relatorios")}>Relatórios</button>
        <button className={modulo === "insights" ? "" : "secundario"} onClick={() => setModulo("insights")}>Assistente</button>
      </nav>

      {modulo === "talhoes" ? (
        <TalhoesPage />
      ) : modulo === "grupos-colheita" ? (
        <GruposColheitaPage propriedades={propriedades} />
      ) : modulo === "cargas" ? (
        <CargasColhidasPage propriedades={propriedades} />
      ) : modulo === "producao-saldos" ? (
        <ProducaoSaldosPage propriedades={propriedades} />
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
      ) : modulo === "relatorios" ? (
        <RelatoriosPage propriedades={propriedades} />
      ) : modulo === "insights" ? (
        <InsightsPage propriedades={propriedades} />
      ) : (
        <>
          {erro && <p className="erro card">{erro}</p>}

          <section className="grade">
        <form className="card formulario" onSubmit={salvar}>
          <h2>{edicaoId ? "Editar propriedade" : "Nova propriedade"}</h2>
          <label>Nome<input required value={formulario.nome} onChange={(e) => setFormulario({ ...formulario, nome: e.target.value })} /></label>
          <label>Proprietário<input value={formulario.proprietario} onChange={(e) => setFormulario({ ...formulario, proprietario: e.target.value })} /></label>
          <div className="linha">
            <label>Município<input required value={formulario.municipio} onChange={(e) => setFormulario({ ...formulario, municipio: e.target.value })} /></label>
            <label>UF<input maxLength={2} value={formulario.uf} onChange={(e) => setFormulario({ ...formulario, uf: e.target.value.toUpperCase() })} /></label>
          </div>
          <label>Área (ha)<input required min="0.01" step="0.01" type="number" value={formulario.area_hectares} onChange={(e) => setFormulario({ ...formulario, area_hectares: e.target.value })} /></label>
          <div className="linha">
            <label>Latitude<input step="any" type="number" value={formulario.latitude} onChange={(e) => setFormulario({ ...formulario, latitude: e.target.value })} /></label>
            <label>Longitude<input step="any" type="number" value={formulario.longitude} onChange={(e) => setFormulario({ ...formulario, longitude: e.target.value })} /></label>
          </div>
          <label>KML (até 5 MB)<input accept=".kml" type="file" onChange={(e) => setFormulario({ ...formulario, arquivo_kml: e.target.files?.[0] ?? null })} /></label>
          <label>Observações<textarea value={formulario.observacoes} onChange={(e) => setFormulario({ ...formulario, observacoes: e.target.value })} /></label>
          <div className="acoes">
            <button disabled={carregando} type="submit">Salvar</button>
            {edicaoId && <button className="secundario" type="button" onClick={() => { setEdicaoId(null); setFormulario(formularioVazio); }}>Cancelar</button>}
          </div>
        </form>

        <section className="conteudo">
          <form className="busca" onSubmit={(e) => { e.preventDefault(); void carregar(busca); }}>
            <input aria-label="Buscar propriedades" placeholder="Buscar por nome, município ou proprietário" value={busca} onChange={(e) => setBusca(e.target.value)} />
            <button type="submit">Buscar</button>
          </form>

          {carregando && propriedades.length === 0 ? (
            <p>Carregando propriedades...</p>
          ) : propriedades.length === 0 ? (
            <div className="card vazio">Nenhuma propriedade cadastrada.</div>
          ) : (
            <div className="lista">
              {propriedades.map((item) => (
                <article className={`card item ${selecionada?.id === item.id ? "ativo" : ""}`} key={item.id} onClick={() => setSelecionada(item)}>
                  <div>
                    <h3>{item.nome}</h3>
                    <p>{item.municipio}/{item.uf} · {item.area_hectares} ha declarados</p>
                    {item.area_calculada_hectares && (
                      <p className="metadado-geografico">
                        {item.area_calculada_hectares} ha calculados
                        {item.divergencia_area_percentual &&
                          ` · diferença ${item.divergencia_area_percentual}%`}
                      </p>
                    )}
                  </div>
                  <div className="acoes">
                    <button className="secundario" onClick={(e) => { e.stopPropagation(); editar(item); }}>Editar</button>
                    <button className="perigo" onClick={(e) => { e.stopPropagation(); void excluir(item); }}>Excluir</button>
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

  return <PrivateArea key={`private-${geracao}`} sair={sair} />;
}
