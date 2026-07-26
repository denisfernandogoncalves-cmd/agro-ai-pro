import { FormEvent } from "react";

import { Propriedade } from "../../api/propriedades";
import { FiltrosTalhao, Talhao } from "../../api/talhoes";


type Props = {
  carregando: boolean;
  filtros: FiltrosTalhao;
  pagina: number;
  propriedades: Propriedade[];
  selecionado: Talhao | null;
  talhoes: Talhao[];
  total: number;
  onAplicarFiltros: (evento: FormEvent) => void;
  onEditar: (talhao: Talhao) => void;
  onFiltrosChange: (filtros: FiltrosTalhao) => void;
  onPaginaChange: (pagina: number) => void;
  onRemover: (talhao: Talhao) => void;
  onSelecionar: (talhao: Talhao) => void;
};

export default function TalhaoLista({
  carregando,
  filtros,
  pagina,
  propriedades,
  selecionado,
  talhoes,
  total,
  onAplicarFiltros,
  onEditar,
  onFiltrosChange,
  onPaginaChange,
  onRemover,
  onSelecionar,
}: Props) {
  const totalPaginas = Math.max(1, Math.ceil(total / 10));

  return (
    <>
      <form className="card painel-filtros" onSubmit={onAplicarFiltros}>
        <input
          aria-label="Buscar talhões"
          placeholder="Buscar talhão, propriedade, cultura ou solo"
          value={filtros.search}
          onChange={(e) => onFiltrosChange({ ...filtros, search: e.target.value })}
        />
        <select
          aria-label="Filtrar por propriedade"
          value={filtros.propriedade}
          onChange={(e) =>
            onFiltrosChange({ ...filtros, propriedade: e.target.value })
          }
        >
          <option value="">Todas as propriedades</option>
          {propriedades.map((propriedade) => (
            <option key={propriedade.id} value={propriedade.id}>
              {propriedade.nome}
            </option>
          ))}
        </select>
        <input
          aria-label="Filtrar por cultura"
          placeholder="Cultura"
          value={filtros.cultura}
          onChange={(e) => onFiltrosChange({ ...filtros, cultura: e.target.value })}
        />
        <input
          aria-label="Filtrar por safra"
          placeholder="Safra"
          value={filtros.safra}
          onChange={(e) => onFiltrosChange({ ...filtros, safra: e.target.value })}
        />
        <select
          aria-label="Ordenar talhões"
          value={filtros.ordering}
          onChange={(e) =>
            onFiltrosChange({ ...filtros, ordering: e.target.value })
          }
        >
          <option value="nome">Nome</option>
          <option value="-area_hectares">Maior área</option>
          <option value="area_hectares">Menor área</option>
          <option value="-produtividade_realizada">
            Maior produtividade realizada
          </option>
          <option value="-atualizado_em">Atualizados recentemente</option>
        </select>
        <button type="submit">Aplicar</button>
      </form>

      {carregando && talhoes.length === 0 ? (
        <p>Carregando talhões...</p>
      ) : talhoes.length === 0 ? (
        <div className="card vazio">Nenhum talhão encontrado.</div>
      ) : (
        <div className="lista">
          {talhoes.map((talhao) => (
            <article
              className={`card item ${
                selecionado?.id === talhao.id ? "ativo" : ""
              }`}
              key={talhao.id}
              onClick={() => onSelecionar(talhao)}
            >
              <div>
                <h3>{talhao.nome}</h3>
                <p>
                  {talhao.propriedade_nome} · {talhao.area_hectares} ha
                  {talhao.cultura_atual ? ` · ${talhao.cultura_atual}` : ""}
                </p>
              </div>
              <div className="acoes">
                <button
                  className="secundario"
                  onClick={(e) => {
                    e.stopPropagation();
                    onEditar(talhao);
                  }}
                >
                  Editar
                </button>
                <button
                  className="perigo"
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemover(talhao);
                  }}
                >
                  Excluir
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      <div className="paginacao">
        <button
          className="secundario"
          disabled={pagina <= 1}
          onClick={() => onPaginaChange(pagina - 1)}
        >
          Anterior
        </button>
        <span>
          Página {pagina} de {totalPaginas} · {total} registro(s)
        </span>
        <button
          className="secundario"
          disabled={pagina >= totalPaginas}
          onClick={() => onPaginaChange(pagina + 1)}
        >
          Próxima
        </button>
      </div>
    </>
  );
}
