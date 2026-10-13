import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { formatarDataHora, idadeDoDado } from "../../utils/datas";

import {
  atualizarPrevisoes,
  listarPrevisoes,
  PrevisaoClima,
} from "../../api/clima";
import { Propriedade, rotuloPropriedade } from "../../api/propriedades";
const MapaPropriedade = lazy(() => import("../../components/MapaPropriedade"));
const SatelitePublico = lazy(() => import("../../components/SatelitePublico"));


type Props = {
  propriedades: Propriedade[];
};

function mensagemDoErro(erro: unknown) {
  if (axios.isAxiosError(erro)) {
    const detalhe = erro.response?.data?.detail;
    if (typeof detalhe === "string") {
      return detalhe;
    }
  }
  return "Não foi possível consultar a previsão do tempo.";
}

function formatarData(data: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
    timeZone: "UTC",
  }).format(new Date(`${data}T00:00:00Z`));
}

export default function ClimaPage({ propriedades }: Props) {
  const [propriedadeId, setPropriedadeId] = useState<number | null>(
    propriedades[0]?.id ?? null,
  );
  const [previsoes, setPrevisoes] = useState<PrevisaoClima[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [mostrarHistorico, setMostrarHistorico] = useState(false);
  const hoje = new Date().toLocaleDateString("sv-SE", {timeZone:"America/Sao_Paulo"});
  const fimPrevisao = new Date(`${hoje}T12:00:00Z`);
  fimPrevisao.setUTCDate(fimPrevisao.getUTCDate()+6);
  const ate = fimPrevisao.toISOString().slice(0,10);
  const previsoesVisiveis = previsoes.filter(p => mostrarHistorico || (p.data >= hoje && p.data <= ate));
  const propriedadeAtual = useRef(propriedadeId);
  const localizacao = propriedades.find(item => item.id === propriedadeId);
  propriedadeAtual.current = propriedadeId;
  const propriedade = useMemo(
    () => propriedades.find((item) => item.id === propriedadeId) ?? null,
    [propriedadeId, propriedades],
  );

  useEffect(() => {
    if (!propriedadeId && propriedades[0]) {
      setPropriedadeId(propriedades[0].id);
    }
  }, [propriedadeId, propriedades]);

  useEffect(() => {
    let ativo = true;
    setErro("");
    setPrevisoes([]);
    if (!propriedadeId) {
      setPrevisoes([]);
      return () => {
        ativo = false;
      };
    }
    listarPrevisoes(propriedadeId)
      .then((dados) => {
        if (ativo) {
          setPrevisoes(dados);
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
  }, [propriedadeId]);

  async function atualizar() {
    if (!propriedadeId) {
      return;
    }
    const selecionada = propriedadeId;
    setCarregando(true);
    setErro("");
    try {
      const dados = await atualizarPrevisoes(selecionada);
      if (propriedadeAtual.current === selecionada) setPrevisoes(dados);
    } catch (falha) {
      if (propriedadeAtual.current === selecionada) setErro(`${mensagemDoErro(falha)} Última tentativa nesta sessão: ${new Date().toLocaleString("pt-BR")}. A previsão armazenada foi preservada.`);
    } finally {
      setCarregando(false);
    }
  }

  if (propriedades.length === 0) {
    return (
      <section className="card vazio">
        Cadastre uma propriedade antes de consultar o clima.
      </section>
    );
  }

  return (
    <section className="modulo-clima">
      <section className="card clima-controles">
        <label>
          Propriedade
          <select
            value={propriedadeId ?? ""}
            onChange={(evento) => setPropriedadeId(Number(evento.target.value))}
          >
            {propriedades.map((item) => (
              <option key={item.id} value={item.id}>
                {rotuloPropriedade(item)} — {item.municipio}/{item.uf}
              </option>
            ))}
          </select>
        </label>
        <button
          disabled={
            carregando ||
            !propriedade?.latitude ||
            !propriedade?.longitude
          }
          onClick={() => void atualizar()}
          type="button"
        >
          {carregando ? "Atualizando..." : "Atualizar previsão"}
        </button>
      </section>

      {propriedade && (!propriedade.latitude || !propriedade.longitude) && (
        <p className="erro card" role="alert">
          Esta propriedade precisa de latitude e longitude. Envie um KML ou
          informe as coordenadas no cadastro.
        </p>
      )}
      {erro && <p className="erro card" role="alert">{erro}</p>}

      <label><input type="checkbox" checked={mostrarHistorico} onChange={e => setMostrarHistorico(e.target.checked)}/> Incluir previsões históricas armazenadas</label>
      <p>Consulta: {formatarData(hoje)} a {formatarData(ate)}{mostrarHistorico ? " · incluindo histórico registrado" : " · próximos sete dias"}.</p>
      {previsoesVisiveis.length === 0 ? (
        <section className="card vazio">
          Nenhuma previsão armazenada para o período consultado desta propriedade.
        </section>
      ) : (
        <section className="previsoes-grade" aria-label={mostrarHistorico ? "Previsões armazenadas e histórico" : "Previsão de sete dias"}>
          {previsoesVisiveis.map((previsao) => (
            <article className="card previsao-card" key={previsao.id}>
              <span className="kicker">{formatarData(previsao.data)}</span>
              <h3>{previsao.condicao || "Condição variável"}</h3>
              <p className="temperaturas">
                {previsao.temperatura_min ?? "—"} °C /{" "}
                {previsao.temperatura_max ?? "—"} °C
              </p>
              <dl>
                <div>
                  <dt>Chuva</dt>
                  <dd>{previsao.chuva_mm ?? "—"} mm</dd>
                </div>
                <div>
                  <dt>Probabilidade</dt>
                  <dd>{previsao.probabilidade_chuva ?? "—"}%</dd>
                </div>
                <div>
                  <dt>Umidade média</dt>
                  <dd>{previsao.umidade ?? "—"}%</dd>
                </div>
                <div>
                  <dt>Vento máximo</dt>
                  <dd>{previsao.vento_kmh ?? "—"} km/h</dd>
                </div>
              </dl>
              {previsao.alerta_agricola && (
                <p className="alerta-clima">{previsao.alerta_agricola}</p>
              )}
              <small>Fonte: {previsao.fonte} · Registro: {formatarDataHora(previsao.atualizado_em)} · {idadeDoDado(previsao.atualizado_em)}</small>
            </article>
          ))}
        </section>
      )}
      <article className="card"><h2>Localização da propriedade</h2>{localizacao?.latitude != null && localizacao.longitude != null ? <Suspense fallback={<p role="status">Carregando mapa…</p>}><MapaPropriedade latitude={Number(localizacao.latitude)} longitude={Number(localizacao.longitude)} nome={localizacao.nome} geometria={localizacao.geometria_geojson} /></Suspense> : <p className="vazio">Selecione uma propriedade com coordenadas cadastradas para visualizar o mapa.</p>}<p className="executivo-nota">Mapa das coordenadas cadastradas. Radar meteorológico permanece sem fonte integrada autorizada para o ERP.</p></article>
      {localizacao?.latitude != null && localizacao.longitude != null && <Suspense fallback={<p role="status">Carregando satélite…</p>}><SatelitePublico key={localizacao.id} latitude={Number(localizacao.latitude)} longitude={Number(localizacao.longitude)} nome={localizacao.nome}/></Suspense>}
    </section>
  );
}
