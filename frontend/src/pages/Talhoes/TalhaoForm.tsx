import { FormEvent } from "react";

import { Propriedade } from "../../api/propriedades";
import { TalhaoInput } from "../../api/talhoes";


type Props = {
  carregando: boolean;
  edicao: boolean;
  formulario: TalhaoInput;
  propriedades: Propriedade[];
  onCancelar: () => void;
  onChange: (formulario: TalhaoInput) => void;
  onSubmit: (evento: FormEvent) => void;
};

export default function TalhaoForm({
  carregando,
  edicao,
  formulario,
  propriedades,
  onCancelar,
  onChange,
  onSubmit,
}: Props) {
  return (
    <form className="card formulario" onSubmit={onSubmit}>
      <h2>{edicao ? "Editar talhão" : "Novo talhão"}</h2>
      <label>
        Propriedade
        <select
          required
          value={formulario.propriedade}
          onChange={(e) =>
            onChange({ ...formulario, propriedade: e.target.value })
          }
        >
          <option value="">Selecione</option>
          {propriedades.map((propriedade) => (
            <option key={propriedade.id} value={propriedade.id}>
              {propriedade.nome}
            </option>
          ))}
        </select>
      </label>
      <label>
        Nome
        <input
          required
          value={formulario.nome}
          onChange={(e) => onChange({ ...formulario, nome: e.target.value })}
        />
      </label>
      <label>
        Área (ha)
        <input
          required
          min="0.01"
          step="0.01"
          type="number"
          value={formulario.area_hectares}
          onChange={(e) =>
            onChange({ ...formulario, area_hectares: e.target.value })
          }
        />
      </label>
      <div className="linha">
        <label>
          Cultura
          <input
            value={formulario.cultura_atual}
            onChange={(e) =>
              onChange({ ...formulario, cultura_atual: e.target.value })
            }
          />
        </label>
        <label>
          Safra
          <input
            value={formulario.safra}
            onChange={(e) => onChange({ ...formulario, safra: e.target.value })}
          />
        </label>
      </div>
      <label>
        Tipo de solo
        <input
          value={formulario.tipo_solo}
          onChange={(e) =>
            onChange({ ...formulario, tipo_solo: e.target.value })
          }
        />
      </label>
      <div className="linha">
        <label>
          Altitude média (m)
          <input
            step="0.01"
            type="number"
            value={formulario.altitude_media}
            onChange={(e) =>
              onChange({ ...formulario, altitude_media: e.target.value })
            }
          />
        </label>
        <label>
          Declividade média
          <input
            step="0.01"
            type="number"
            value={formulario.declividade_media}
            onChange={(e) =>
              onChange({ ...formulario, declividade_media: e.target.value })
            }
          />
        </label>
      </div>
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
        KML (até 5 MB)
        <input
          accept=".kml"
          type="file"
          onChange={(e) =>
            onChange({
              ...formulario,
              arquivo_kml: e.target.files?.[0] ?? null,
            })
          }
        />
      </label>
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
        <button disabled={carregando} type="submit">
          Salvar
        </button>
        {edicao && (
          <button className="secundario" type="button" onClick={onCancelar}>
            Cancelar
          </button>
        )}
      </div>
    </form>
  );
}
