import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";

import {
  atualizarPrevisoes,
  listarAlertasClimaticos,
  listarPrevisoes,
  listarPrevisoesHorarias,
  obterStatusClima,
  type AlertaClimatico,
  type PrevisaoClima,
  type PrevisaoHoraria,
  type StatusClima,
} from "../../api/clima";
import type { Propriedade } from "../../api/propriedades";


type Props = {
  propriedades: Propriedade[];
};

function mensagemDoErro(erro: unknown) {
  if (axios.isAxiosError(erro)) {
    const detalhe = erro.response?.data?.detail;
    if (typeof detalhe === "string") return detalhe;
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

function formatarDataHora(data: string | null | undefined) {
  if (!data) return "Não disponível";
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(data));
}

function valorAtual(status: StatusClima | null, campo: string, sufixo = "") {
  const valor = status?.atual?.[campo];
  return valor === undefined || valor === null ? "—" : `${valor}${sufixo}`;
}

export default function ClimaPage({ propriedades }: Props) {
  const [propriedadeId, setPropriedadeId] = useState<number | null>(
    propriedades[0]?.id ?? null,
  );
  const [previsoes, setPrevisoes] = useState<PrevisaoClima[]>([]);
  const [horarias, setHorarias] = useState<PrevisaoHoraria[]>([]);
  const [alertas, setAlertas] = useState<AlertaClimatico[]>([]);
  const [statusClima, setStatusClima] = useState<StatusClima | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [atualizando, setAtualizando] = useState(false);
  const [erro, setErro] = useState("");

  const propriedade = useMemo(
    () => propriedades.find((item) => item.id === propriedadeId) ?? null,
    [propriedadeId, propriedades],
  );

  useEffect(() => {
    if (!propriedadeId && propriedades[0]) {
      setPropriedadeId(propriedades[0].id);
    }
  }, [propriedadeId, propriedades]);

  const carregar = useCallback(async () => {
    if (!propriedadeId) {
      setPrevisoes([]);
      setHorarias([]);
      setAlertas([]);
      setStatusClima(null);
      return;
    }
    setCarregando(true);
    setErro("");
    try {
      const [diarias, horas, avisos, estado] = await Promise.all([
        listarPrevisoes(propriedadeId),
        listarPrevisoesHorarias(propriedadeId),
        listarAlertasClimaticos(propriedadeId),
        obterStatusClima(propriedadeId),
      ]);
      setPrevisoes(diarias);
      setHorarias(horas);
      setAlertas(avisos);
      setStatusClima(estado);
    } catch (falha) {
      setErro(mensagemDoErro(falha));
    } finally {
      setCarregando(false);
    }
  }, [propriedadeId]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  async function atualizar() {
    if (!propriedadeId) return;
    setAtualizando(true);
    setErro("");
    try {
      await atualizarPrevisoes(propriedadeId);
      await carregar();
    } catch (falha) {
      setErro(mensagemDoErro(falha));
    } finally {
      setAtualizando(false);
    }
  }

  if (propriedades.length === 0) {
    return (
      <section className="card vazio">
        Cadastre uma propriedade antes de consultar o clima.
      </section>
    );
  }

  const semLocalizacao = Boolean(
    propriedade
    && !propriedade.latitude
    && !propriedade.longitude
    && !propriedade.geometria_geojson,
  );
  const proximasHoras = horarias
    .filter((item) => new Date(item.data_hora).getTime() >= Date.now())
    .slice(0, 12);

  return (
    <section className="modulo-clima clima-enterprise">
      <section className="card clima-controles">
        <div>
          <span className="kicker">Atualização automática</span>
          <h2>Clima da propriedade</h2>
          <p className="muted">
            Frequência padrão de 3 horas, com cache e preservação da última previsão válida.
          </p>
        </div>
        <label>
          Propriedade
          <select
            value={propriedadeId ?? ""}
            onChange={(evento) => setPropriedadeId(Number(evento.target.value))}
          >
            {propriedades.map((item) => (
              <option key={item.id} value={item.id}>
                {item.nome} — {item.municipio}/{item.uf}
              </option>
            ))}
          </select>
        </label>
        <button
          disabled={atualizando || semLocalizacao}
          onClick={() => void atualizar()}
          type="button"
        >
          {atualizando ? "Atualizando..." : "Atualizar previsão"}
        </button>
      </section>

      {semLocalizacao && (
        <p className="erro card">
          Esta propriedade precisa de latitude e longitude. Envie um KML ou
          informe as coordenadas no cadastro. O sistema não inventa coordenadas.
        </p>
      )}
      {erro && <p className="erro card">{erro}</p>}

      <section className="clima-status-grid" aria-label="Estado da atualização climática">
        <article className="card clima-atual-card">
          <span className="kicker">Agora</span>
          <h3>{String(statusClima?.atual?.condicao ?? "Condição não disponível")}</h3>
          <strong className="clima-temperatura-atual">
            {valorAtual(statusClima, "temperatura", " °C")}
          </strong>
          <dl>
            <div><dt>Sensação</dt><dd>{valorAtual(statusClima, "sensacao_termica", " °C")}</dd></div>
            <div><dt>Umidade</dt><dd>{valorAtual(statusClima, "umidade", "%")}</dd></div>
            <div><dt>Vento</dt><dd>{valorAtual(statusClima, "vento_kmh", " km/h")}</dd></div>
            <div><dt>Rajadas</dt><dd>{valorAtual(statusClima, "rajada_vento_kmh", " km/h")}</dd></div>
            <div><dt>Pressão</dt><dd>{valorAtual(statusClima, "pressao_hpa", " hPa")}</dd></div>
            <div><dt>Nuvens</dt><dd>{valorAtual(statusClima, "cobertura_nuvens", "%")}</dd></div>
          </dl>
        </article>

        <article className="card clima-operacao-card">
          <span className="kicker">Operação agrícola</span>
          <h3>Próxima hora</h3>
          {statusClima?.proxima_hora ? (
            <>
              <p><strong>Pulverização:</strong> {statusClima.proxima_hora.condicao_pulverizacao || "—"}</p>
              <p><strong>Colheita:</strong> {statusClima.proxima_hora.condicao_colheita || "—"}</p>
              <p><strong>Chuva:</strong> {statusClima.proxima_hora.probabilidade_chuva ?? "—"}%</p>
              <p><strong>Risco de deriva:</strong> {statusClima.proxima_hora.risco_deriva ? "Sim" : "Não"}</p>
            </>
          ) : <p className="muted">Sem previsão horária armazenada.</p>}
        </article>

        <article className={`card clima-sincronizacao ${statusClima?.configuracao.desatualizado ? "is-stale" : ""}`}>
          <span className="kicker">Sincronização</span>
          <h3>{statusClima?.configuracao.status ?? (carregando ? "Carregando" : "Pendente")}</h3>
          <p><strong>Última:</strong> {formatarDataHora(statusClima?.configuracao.ultima_atualizacao)}</p>
          <p><strong>Próxima:</strong> {formatarDataHora(statusClima?.configuracao.proxima_atualizacao)}</p>
          <p><strong>Origem:</strong> {statusClima?.configuracao.origem_coordenadas || "Não definida"}</p>
          <p><strong>Alertas ativos:</strong> {statusClima?.alertas_ativos ?? 0}</p>
          {statusClima?.configuracao.desatualizado && <p className="alerta-clima">Dados marcados como desatualizados.</p>}
        </article>
      </section>

      {alertas.length > 0 && (
        <section className="card">
          <div className="clima-section-heading">
            <div><span className="kicker">Notificações internas</span><h2>Alertas ativos</h2></div>
            <span>{alertas.length}</span>
          </div>
          <div className="clima-alertas-lista">
            {alertas.map((alerta) => (
              <article key={alerta.id} className={`alerta-clima alerta-clima--${alerta.nivel}`}>
                <strong>{alerta.titulo}</strong>
                <p>{alerta.descricao}</p>
                <small>{formatarDataHora(alerta.inicio)}</small>
              </article>
            ))}
          </div>
        </section>
      )}

      <section className="card clima-horaria-section">
        <div className="clima-section-heading">
          <div><span className="kicker">Próximas horas</span><h2>Previsão horária</h2></div>
          {carregando && <span>Atualizando dados...</span>}
        </div>
        {proximasHoras.length === 0 ? (
          <p className="vazio">Nenhuma previsão horária armazenada para esta propriedade.</p>
        ) : (
          <div className="clima-horaria-lista">
            {proximasHoras.map((hora) => (
              <article key={hora.id}>
                <strong>{new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit" }).format(new Date(hora.data_hora))}</strong>
                <span>{hora.temperatura ?? "—"} °C</span>
                <small>{hora.probabilidade_chuva ?? "—"}% chuva</small>
                <small>{hora.vento_kmh ?? "—"} km/h</small>
                <span className={`clima-condicao clima-condicao--${hora.condicao_pulverizacao || "atencao"}`}>
                  Pulverização {hora.condicao_pulverizacao || "indefinida"}
                </span>
              </article>
            ))}
          </div>
        )}
      </section>

      {previsoes.length === 0 ? (
        <section className="card vazio">
          Nenhuma previsão armazenada para esta propriedade.
        </section>
      ) : (
        <section className="previsoes-grade" aria-label="Previsão de sete dias">
          {previsoes.map((previsao) => (
            <article className="card previsao-card" key={previsao.id}>
              <span className="kicker">{formatarData(previsao.data)}</span>
              <h3>{previsao.condicao || "Condição variável"}</h3>
              <p className="temperaturas">
                {previsao.temperatura_min ?? "—"} °C / {previsao.temperatura_max ?? "—"} °C
              </p>
              <dl>
                <div><dt>Chuva</dt><dd>{previsao.chuva_mm ?? "—"} mm</dd></div>
                <div><dt>Probabilidade</dt><dd>{previsao.probabilidade_chuva ?? "—"}%</dd></div>
                <div><dt>Umidade média</dt><dd>{previsao.umidade ?? "—"}%</dd></div>
                <div><dt>Vento máximo</dt><dd>{previsao.vento_kmh ?? "—"} km/h</dd></div>
                <div><dt>Evapotranspiração</dt><dd>{previsao.evapotranspiracao_mm ?? "—"} mm</dd></div>
                <div><dt>Colheita</dt><dd>{previsao.condicao_colheita || "—"}</dd></div>
              </dl>
              {previsao.alerta_agricola && (
                <p className="alerta-clima">{previsao.alerta_agricola}</p>
              )}
              <small>Fonte: {previsao.fonte}</small>
            </article>
          ))}
        </section>
      )}
    </section>
  );
}
