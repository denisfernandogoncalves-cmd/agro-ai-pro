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
  return "NÃ£o foi possÃ­vel concluir a operaÃ§Ã£o.";
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
      setError("UsuÃ¡rio ou senha invÃ¡lidos.");
    }
  }

  return (
    <main className="login">
      <form className="card" onSubmit={submitLogin}>
        <h1>AGRO-AI-PRO</h1>
        <p>Acesse o mÃ³dulo de propriedades.</p>
        <label>
          UsuÃ¡rio
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
    "propriedades" | "talhoes" | "cargas" | "clima" | "mercado" | "financeiro" | "estoque" | "operacoes" | "maquinas" | "relatorios" | "insights"
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
 ïMº¶‰ËkºwµçVBÖ„ÆVæwFƒ×³‡ÒÆ6V†öÆFW#Ò$$3C#2"fÇVS×¶6&vçÆ6Òöä6†ævS×²†R’Óâ6WD6&v‡²ââæ6&vÂÆ6¢RçF&vWBçfÇVRçFõWW$66R‚’Ò—ÒóãÂöÆ&VÃà¢ÂöF—cà¢ÆÆ&VÃäÆö6ÂFR6öÆ†V—FÆ–çWBÆ6V†öÆFW#Ò%FÆŒ:6òÂvÆV&÷RöçFòFR÷&–vVÒ"fÇVS×¶6&væÆö6Åö6öÆ†V—FÒöä6†ævS×²†R’Óâ6WD6&v‡²ââæ6&vÂÆö6Åö6öÆ†V—F¢RçF&vWBçfÇVRÒ—ÒóãÂöÆ&VÃà¢ÆÆ&VÃåW6ò''WFò†¶r“Æ–çWB&WV—&VBÖ–ãÒ#ã"7FWÒ#ã"G—SÒ&çVÖ&W""fÇVS×¶6&vçW6õö''WFõö¶wÒöä6†ævS×²†R’Óâ6WD6&v‡²ââæ6&vÂW6õö''WFõö¶s¢RçF&vWBçfÇVRÒ—ÒóãÂöÆ&VÃà¢ÆF—b6Æ74æÖSÒ&Æ–æ†#à¢ÆÆ&VÃåVÖ–FFR‚R“Æ–çWB&WV—&VBÖ–ãÒ#"ÖƒÒ#"7FWÒ#ã"G—SÒ&çVÖ&W""fÇVS×¶6&vçVÖ–FFU÷W&6VçGVÇÒöä6†ævS×²†R’Óâ6WD6&v‡²ââæ6&vÂVÖ–FFU÷W&6VçGVÃ¢RçF&vWBçfÇVRÒ—ÒóãÂöÆ&VÃà¢ÆÆ&VÃä–×W&W¦‚R“Æ–çWB&WV—&VBÖ–ãÒ#"ÖƒÒ#"7FWÒ#ã"G—SÒ&çVÖ&W""fÇVS×¶6&væ–×W&W¦÷W&6VçGVÇÒöä6†ævS×²†R’Óâ6WD6&v‡²ââæ6&vÂ–×W&W¦÷W&6VçGVÃ¢RçF&vWBçfÇVRÒ—ÒóãÂöÆ&VÃà¢ÆÆ&VÃäFVfV—F÷2‚R“Æ–çWB&WV—&VBÖ–ãÒ#"ÖƒÒ#"7FWÒ#ã"G—SÒ&çVÖ&W""fÇVS×¶6&væFVfV—F÷5÷W&6VçGVÇÒöä6†ævS×²†R’Óâ6WD6&v‡²ââæ6&vÂFVfV—F÷5÷W&6VçGVÃ¢RçF&vWBçfÇVRÒ—ÒóãÂöÆ&VÃà¢ÂöF—cà¢ÆF—b6Æ74æÖSÒ&Æ–æ†#à¢ÆÆ&VÃåƒÆ–çWBÖ–ãÒ#"ÖƒÒ#"7FWÒ#ã"G—SÒ&çVÖ&W""fÇVS×¶6&vç‡Òöä6†ævS×²†R’Óâ6WD6&v‡²ââæ6&vÂƒ¢RçF&vWBçfÇVRÒ—ÒóãÂöÆ&VÃà¢ÆÆ&VÂ6Æ74æÖSÒ&÷6òÖ6†V6¶&÷‚#ãÆ–çWBG—SÒ&6†V6¶&÷‚"6†V6¶VC×¶6&væFW7F–æFõ÷6VÖVçFWÒöä6†ævS×²†R’Óâ6WD6&v‡²ââæ6&vÂFW7F–æFõ÷6VÖVçFS¢RçF&vWBæ6†V6¶VBÒ—ÒóâFW7F–æF6VÖVçFSÂöÆ&VÃà¢ÂöF—cà¢ÆÆ&VÃäö'6W'f:|;VW3ÇFW‡F&VfÇVS×¶6&væö'6W'f6öW7Òöä6†ævS×²†R’Óâ6WD6&v‡²ââæ6&vÂö'6W'f6öW3¢RçF&vWBçfÇVRÒ—ÒóãÂöÆ&VÃà¢ÆF—b6Æ74æÖSÒ'&W7VÖò×W6ò"&–ÖÆ—fSÒ'öÆ—FR#à¢Ç7ãäFW66öçFòÇ7G&öæsç¶6Æ7VÆòçW&6VçGVÂçFôf—†VBƒ2—ÒSÂ÷7G&öæsãÂ÷7ãà¢Ç7ãåW6òÌ:×V–FòÇ7G&öæsç¶6Æ7VÆòæÆ—V–FòçFôÆö6ÆU7G&–ær‚'BÔ%""Â²Ö†–×VÔg&7F–öäF–v—G3¢2Ò—Ò¶sÂ÷7G&öæsãÂ÷7ãà¢Ç7ãä6öçfW'<:6òÇ7G&öæsç¶6Æ7VÆòç662çFôÆö6ÆU7G&–ær‚'BÔ%""Â²Ö†–×VÔg&7F–öäF–v—G3¢2Ò—Ò663Â÷7G&öæsãÂ÷7ãà¢ÂöF—cà¢Æ'WGFöâF—6&ÆVC×¶6'&VvæFòÇÂ6Æ7VÆòçW&6VçGVÂãÒÒG—SÒ'7V&Ö—B#å&Vv—7G&"R7&VF—F"6ÆFóÂö'WGFöãà¢Âöf÷&Óà ¢Ç6V7F–öâ6Æ74æÖSÒ&6öçFWVFò#à¢ÆF—b6Æ74æÖSÒ'–æVÂÖf–ÇG&÷2#à¢Æ–çWB&–ÖÆ&VÃÒ$'W66"6&v2"Æ6V†öÆFW#Ò$'W66"Æ6Â&÷&–VFFRÂw'WòÂ4Bõ$ò÷RÆö6Â"fÇVS×¶'W66Òöä6†ævS×²†R’Óâ6WD'W66†RçF&vWBçfÇVR—Òóà¢Æ'WGFöâG—SÒ&'WGFöâ"öä6Æ–6³×²‚’Óâfö–B6'&Vv"‚—ÓäGVÆ—¦#Âö'WGFöãà¢ÂöF—cà¢ÆF—b6Æ74æÖSÒ&Æ—7F6&v2ÖÆ—7F#à¢¶6&v4f–ÇG&F2æÆVæwF‚ÓÓÒòÆF—b6Æ74æÖSÒ&6&Bf¦–ò#äæVæ‡VÖ6&v6öÆ†–F&Vv—7G&FãÂöF—câ¢6&v4f–ÇG&F2æÖ‚†—FVÒ’Óâ€¢Æ'F–6ÆR6Æ74æÖSÒ&6&B6&vÖ—FVÒ"¶W“×¶—FVÒæ–GÓà¢ÆF—b6Æ74æÖSÒ&6&vÖ—FVÒ×F÷ò#ãÆF—cãÇ7â6Æ74æÖSÒ&¶–6¶W"#ç¶—FVÒæFFö6öÆ†V—FÒ+r¶—FVÒçÆ6ÓÂ÷7ããÆƒ3ç¶—FVÒç&÷&–VFFUöæöÖWÓÂöƒ3ãÇç¶—FVÒæw'Wõö6öÆ†V—FöæöÖWÒ+r4Bõ$ò¶—FVÒæ6E÷&õö6öF–v÷Ò+r¶—FVÒæ&Ö¦VÕöæöÖWÓÂ÷ãÂöF—cãÇ7G&öæsç¶çVÖW&ò†—FVÒç665óc¶r’çFôÆö6ÆU7G&–ær‚'BÔ%""Â²Ö†–×VÔg&7F–öäF–v—G3¢2Ò—Ò63Â÷7G&öæsãÂöF—cà¢ÆF—b6Æ74æÖSÒ&6&vÖÖWG&–62#ãÇ7ãä''WFòÇ7G&öæsç¶çVÖW&ò†—FVÒçW6õö''WFõö¶r’çFôÆö6ÆU7G&–ær‚'BÔ%""—Ò¶sÂ÷7G&öæsãÂ÷7ããÇ7ãäFW66öçFòÇ7G&öæsç¶—FVÒæFW66öçFõ÷F÷FÅ÷W&6VçGVÇÒSÂ÷7G&öæsãÂ÷7ããÇ7ãäÌ:×V–FòÇ7G&öæsç¶çVÖW&ò†—FVÒçW6õöÆ—V–Fõö¶r’çFôÆö6ÆU7G&–ær‚'BÔ%""—Ò¶sÂ÷7G&öæsãÂ÷7ããÂöF—cà¢Ç6ÖÆÃåVÖ–FFR¶—FVÒçVÖ–FFU÷W&6VçGVÇÒR+r–×W&W¦¶—FVÒæ–×W&W¦÷W&6VçGVÇÒR+rFVfV—F÷2¶—FVÒæFVfV—F÷5÷W&6VçGVÇÒW¶—FVÒç‚ò+r‚G¶—FVÒç‡Ö¢"'×¶—FVÒæFW7F–æFõ÷6VÖVçFRò"+r6VÖVçFR"¢"'Ò+rÖ÷f–ÖVçFò7¶—FVÒæÖ÷f–ÖVçF6÷ÓÂ÷6ÖÆÃà¢Âö'F–6ÆSà¢’—Ğ¢ÂöF—cà¢Â÷6V7F–öãà¢Â÷6V7F–öãà¢Â÷6V7F–öãà¢“°§Ğ 