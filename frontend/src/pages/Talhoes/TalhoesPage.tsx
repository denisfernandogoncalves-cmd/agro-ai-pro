import { FormEvent, useCallback, useEffect, useState } from "react";
import axios from "axios";

import { listarPropriedades, Propriedade } from "../../api/propriedades";
import {
  atualizarHistorico,
  atualizarTalhao,
  criarHistorico,
  criarTalhao,
  excluirHistorico,
  excluirTalhao,
  FiltrosTalhao,
  HistoricoAgronomico,
  HistoricoAgronomicoInput,
  listarHistoricos,
  listarTalhoes,
  Talhao,
  TalhaoInput,
} from "../../api/talhoes";
import MapaTalhao from "../../components/MapaTalhao";
import HistoricoAgronomicoPanel from "./HistoricoAgronomicoPanel";
import TalhaoForm from "./TalhaoForm";
import TalhaoLista from "./TalhaoLista";


const formularioVazio: TalhaoInput = {
  propriedade: "",
  nome: "",
  area_hectares: "",
  cultura_atual: "",
  safra: "",
  tipo_solo: "",
  altitude_media: "",
  declividade_media: "",
  produtividade_esperada: "",
  produtividade_realizada: "",
  observacoes: "",
  arquivo_kml: null,
};

const filtrosVazios: FiltrosTalhao = {
  search: "",
  propriedade: "",
  cultura: "",
  safra: "",
  ordering: "nome",
};

function hoje() {
  return new Date().toISOString().slice(0, 10);
}

function historicoVazio(talhao?: Talhao | null): HistoricoAgronomicoInput {
  return {
    talhao: talhao?.id ?? 0,
    data_referencia: hoje(),
    cultura: talhao?.cultura_atual ?? "",
    safra: talhao?.safra ?? "",
    produtividade_esperada: talhao?.produtividade_esperada ?? "",
    produtividade_realizada: talhao?.produtividade_realizada ?? "",
    observacoes: "",
  };
}

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

export default function TalhoesPage() {
  const [propriedades, setPropriedades] = useState<Propriedade[]>([]);
  const [talhoes, setTalhoes] = useState<Talhao[]>([]);
  const [selecionado, setSelecionado] = useState<Talhao | null>(null);
  const [formulario, setFormulario] = useState<TalhaoInput>(formularioVazio);
  const [edicaoId, setEdicaoId] = useState<number | null>(null);
  const [filtros, setFiltros] = useState<FiltrosTalhao>(filtrosVazios);
  const [filtrosAplicados, setFiltrosAplicados] =
    useState<FiltrosTalhao>(filtrosVazios);
  const [pagina, setPagina] = useState(1);
  const [total, setTotal] = useState(0);
  const [historicos, setHistoricos] = useState<HistoricoAgronomico[]>([]);
  const [historicoEdicaoId, setHistoricoEdicaoId] = useState<number | null>(
    null,
  );
  const [formularioHistorico, setFormularioHistorico] =
    useState<HistoricoAgronomicoInput>(historicoVazio());
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");

  const carregarTalhoes = useCallback(async () => {
    setCarregando(true);
    setErro("");
    try {
      const dados = await listarTalhoes({
        ...filtrosAplicados,
        page: pagina,
        pageSize: 10,
      });
      setTalhoes(dados.results);
      setTotal(dados.count);
      setSelecionado((atual) =>
        dados.results.find((item) => item.id === atual?.id) ??
        dados.results[0] ??
        null
      );
    } catch (falha) {
      setErro(mensagemDoErro(falha));
    } finally {
      setCarregando(false);
    }
  }, [filtrosAplicados, pagina]);

  useEffect(() => {
    let ativo = true;
    listarPropriedades()
      .then((dados) => {
        if (ativo) {
          setPropriedades(dados);
        }
      })
      .catch((falha) => {
        if (ativo) {
          setErro(mensagemDoErro(falha));
        }
      });
    return () => {
      ativo = false;
    };
  }, []);

  useEffect(() => {
    void carregarTalhoes();
  }, [carregarTalhoes]);

  useEffect(() => {
    let ativo = true;
    setHistoricoEdicaoId(null);
    if (!selecionado) {
      setHistoricos([]);
      setFormularioHistorico(historicoVazio());
      return () => {
        ativo = false;
      };
    }
    setFormularioHistorico(historicoVazio(selecionado));
    listarHistoricos(selecionado.id)
      .then((dados) => {
        if (ativo) {
          setHistoricos(dados);
        }
      })
      .catch((falha) => {
        if (ativo) {
          setErro(mensagemDoErro(falha));
        }
      });
    return () => {
      ativo = false;
    };
  }, [selecionado]);

  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    setCarregando(true);
    setErro("");
    try {
      const salvo = edicaoId
        ? await atualizarTalhao(edicaoId, formulario)
        : await criarTalhao(formulario);
      setFormulario(formularioVazio);
      setEdicaoId(null);
      await carregarTalhoes();
      setSelecionado(salvo);
    } catch (falha) {
      setErro(mensagemDoErro(falha));
      setCarregando(false);
    }
  }

  function editar(talhao: Talhao) {
    setEdicaoId(talhao.id);
    setFormulario({
      propriedade: String(talhao.propriedade),
      nome: talhao.nome,
      area_hectares: talhao.area_hectares,
      cultura_atual: talhao.cultura_atual,
      safra: talhao.safra,
      tipo_solo: talhao.tipo_solo,
      altitude_media: talhao.altitude_media ?? "",
      declividade_media: talhao.declividade_media ?? "",
      produtividade_esperada: talhao.produtividade_esperada ?? "",
      produtividade_realizada: talhao.produtividade_realizada ?? "",
      observacoes: talhao.observacoes,
      arquivo_kml: null,
    });
  }

  async function remover(talhao: Talhao) {
    if (!window.confirm(`Excluir o talhão "${talhao.nome}"?`)) {
      return;
    }
    setErro("");
    try {
      await excluirTalhao(talhao.id);
      if (edicaoId === talhao.id) {
        setEdicaoId(null);
        setFormulario(formularioVazio);
      }
      if (talhoes.length === 1 && pagina > 1) {
        setPagina((atual) => atual - 1);
      } else {
        await carregarTalhoes();
      }
    } catch (falha) {
      setErro(mensagemDoErro(falha));
    }
  }

  async function recarregarHistoricos(talhaoId: number) {
    setHistoricos(await listarHistoricos(talhaoId));
  }

  async function salvarHistorico(evento: FormEvent) {
    evento.preventDefault();
    if (!selecionado) {
      return;
    }
    setErro("");
    try {
      const dados = { ...formularioHistorico, talhao: selecionado.id };
      if (historicoEdicaoId) {
        await atualizarHistorico(historicoEdicaoId, dados);
      } else {
        await criarHistorico(dados);
      }
      await recarregarHistoricos(selecionado.id);
      cancelarEdicaoHistorico();
    } catch (falha) {
      setErro(mensagemDoErro(falha));
    }
  }

  function editarHistorico(historico: HistoricoAgronomico) {
    setHistoricoEdicaoId(historico.id);
    setFormularioHistorico({
      talhao: historico.talhao,
      data_referencia: historico.data_referencia,
      cultura: historico.cultura,
      safra: historico.safra,
      produtividade_esperada: historico.produtividade_esperada ?? "",
      produtividade_realizada: historico.produtividade_realizada ?? "",
      observacoes: historico.observacoes,
    });
  }

  function cancelarEdicaoHistorico() {
    setHistoricoEdicaoId(null);
    setFormularioHistorico(historicoVazio(selecionado));
  }

  async function removerHistorico(historico: HistoricoAgronomico) {
    if (!window.confirm("Excluir este registro do histórico agronômico?")) {
      return;
    }
    try {
      await excluirHistorico(historico.id);
      if (historicoEdicaoId === historico.id) {
        cancelarEdicaoHistorico();
      }
      if (selecionado) {
        await recarregarHistoricos(selecionado.id);
      }
    } catch (falha) {
      setErro(mensagemDoErro(falha));
    }
  }

  return (
    <section className="modulo-talhoes">
      {erro && <p className="erro card">{erro}</p>}

      <section className="grade talhoes-grade">
        <TalhaoForm
          carregando={carregando}
          edicao={Boolean(edicaoId)}
          formulario={formulario}
          propriedades={propriedades}
          onCancelar={() => {
            setEdicaoId(null);
            setFormulario(formularioVazio);
          }}
          onChange={setFormulario}
          onSubmit={salvar}
        />

        <section className="conteudo">
          <TalhaoLista
            carregando={carregando}
            filtros={filtros}
            pagina={pagina}
            propriedades={propriedades}
            selecionado={selecionado}
            talhoes={talhoes}
            total={total}
            onAplicarFiltros={(evento) => {
              evento.preventDefault();
              setPagina(1);
              setFiltrosAplicados(filtros);
            }}
            onEditar={editar}
            onFiltrosChange={setFiltros}
            onPaginaChange={setPagina}
            onRemover={(talhao) => void remover(talhao)}
            onSelecionar={setSelecionado}
          />

          {selecionado && (
            <section className="detalhes">
              {selecionado.geometria_geojson &&
                selecionado.latitude_centro &&
                selecionado.longitude_centro && (
                  <MapaTalhao
                    geometria={selecionado.geometria_geojson}
                    latitude={Number(selecionado.latitude_centro)}
                    longitude={Number(selecionado.longitude_centro)}
                    nome={selecionado.nome}
                  />
                )}

              <HistoricoAgronomicoPanel
                edicao={Boolean(historicoEdicaoId)}
                formulario={formularioHistorico}
                historicos={historicos}
                onCancelar={cancelarEdicaoHistorico}
                onChange={setFormularioHistorico}
                onEditar={editarHistorico}
                onRemover={(historico) => void removerHistorico(historico)}
                onSubmit={salvarHistorico}
              />
            </section>
          )}
        </section>
      </section>
    </section>
  );
}
