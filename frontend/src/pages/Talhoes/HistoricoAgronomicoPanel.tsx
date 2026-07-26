import { FormEvent } from "react";

import {
  HistoricoAgronomico,
  HistoricoAgronomicoInput,
} from "../../api/talhoes";


type Props = {
  edicao: boolean;
  formulario: HistoricoAgronomicoInput;
  historicos: HistoricoAgronomico[];
  onCancelar: () => void;
  onChange: (formulario: HistoricoAgronomicoInput) => void;
  onEditar: (historico: HistoricoAgronomico) => void;
  onRemover: (historico: HistoricoAgronomico) => void;
  onSubmit: (evento: FormEvent) => void;
};

export default function HistoricoAgronomicoPanel({
  edicao,
  formulario,
  historicos,
  onCancelar,
  onChange,
  onEditar,
  onRemover,
  onSubmit,
}: Props) {
  return (
    <section className="card historico">
      <h2>Histórico agronômico</h2>
      <form className="historico-form" onSubmit={onSubmit}>
        <div className="linha">
          <label>
            Data
            <input
              required
              type="date"
              value={formulario.data_referencia}
              onChange={(e) =>
                onChange({ ...formulario, data_referencia: e.target.value })
              }
            />
          </label>
          <label>
            Safra
            <input
              value={formulario.safra}
              onChange={(e) =>
                onChange({ ...formulario, safra: e.target.value })
              }
            />
          </label>
        </div>
        <label>
          Cultura
          <input
            value={formulario.cultura}
            onChange={(e) =>
              onChange({ ...formulario, cultura: e.target.value })
            }
          />
        </label>
        <div className="linha">
          <label>
            Produtividade esperada
            <input
              min="0"
              step="0.01"
              type="number"
              value={formulario.produtividade_esperada}
              onChange={(e) =>
                onChange({
                  ...formulario,
                  produtividade_esperada: e.target.value,
                })
              }
            />
          </label>
          <label>
            Produtividade realizada
            <input
              min="0"
              step="0.01"
              type="number"
              value={formulario.produtividade_realizada}
              onChange={(e) =>
                onChange({
                  ...formulario,
                  produtividade_realizada: e.target.value,
                })
              }
            />
          </label>
        </div>
        <label>
          Observações
          <textarea
            value={formulario.observacoes}
            onChange={(e) =>
              onChange({ ...formulario, observacoes: e.target.value })
            }
          />
        </label>
        <div className="acoes">
          <button type="submit">
            {edicao ? "Atualizar histórico" : "Registrar histórico"}
          </button>
          {edicao && (
            <button className="secundario" type="button" onClick={onCancelar}>
              Cancelar
            </button>
          )}
        </div>
      </form>

      <div className="historico-lista">
        {historicos.length === 0 ? (
          <p className="vazio">Nenhum histórico registrado.</p>
        ) : (
          historicos.map((historico) => (
            <article key={historico.id}>
              <div>
                <strong>
                  {new Date(
                    `${historico.data_referencia}T00:00:00`,
                  ).toLocaleDateString("pt-BR")}
                </strong>
                <p>
                  {[historico.cultura, historico.safra]
                    .filter(Boolean)
                    .join(" · ") || "Registro agronômico"}
                </p>
                <small>
                  Esperada: {historico.produtividade_esperada ?? "—"} ·
                  Realizada: {historico.produtividade_realizada ?? "—"}
                </small>
              </div>
              <div className="acoes">
                <button
                  className="secundario"
                  onClick={() => onEditar(historico)}
                >
                  Editar
                </button>
                <button className="perigo" onClick={() => onRemover(historico)}>
                  Excluir
                </button>
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
