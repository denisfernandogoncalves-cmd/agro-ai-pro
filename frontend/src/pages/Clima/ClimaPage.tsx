import { useEffect, useMemo, useState } from "react";
import axios from "axios";

import {
  atualizarPrevisoes,
  listarPrevisoes,
  PrevisaoClima,
} from "../../api/clima";
import { Propriedade } from "../../api/propriedades";


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
    setCarregando(true);
    setErro("");
    try {
      setPrevisoes(await atualizarPrevisoes(propriedadeId));
    } catch (falha) {
      setErro(mensagemDoErro(falha));
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
                {item.nome} — {item.municipio}/{item.uf}
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
        <p className="erro card">
          Esta propriedade precisa de latitude e longitude. Envie um KML ou
          informe as coordenadas no cadastro.
        </p>
      )}
      {erro && <p className="erro card">{erro}</p>}

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
              <small>Fonte: {previsao.fonte}</small>
            </article>
          ))}
        </section>
      )}
    </section>
  );
}
