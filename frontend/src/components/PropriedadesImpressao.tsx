import { Propriedade } from "../api/propriedades";
import { useState } from "react";

const alqueires = (hectares: number) =>
  (hectares / 2.42).toLocaleString("pt-BR", {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  });

type Props = { propriedades: Propriedade[]; carregando: boolean };

export type FiltrosImpressaoPropriedades = { proprietario: string; nome: string; cadpro: string; municipio: string };
const filtrosVazios: FiltrosImpressaoPropriedades = { proprietario: "", nome: "", cadpro: "", municipio: "" };
export function filtrarPropriedadesImpressao(propriedades: Propriedade[], filtros: FiltrosImpressaoPropriedades) {
  return propriedades.filter(item =>
    (!filtros.proprietario || item.proprietario === filtros.proprietario) &&
    (!filtros.nome || String(item.id) === filtros.nome) &&
    (!filtros.cadpro || item.cad_pro_numeros.includes(filtros.cadpro)) &&
    (!filtros.municipio || `${item.municipio}/${item.uf}` === filtros.municipio)
  );
}

const opcoes = (valores: string[]) => [...new Set(valores.filter(Boolean))].sort((a, b) => a.localeCompare(b, "pt-BR"));

export default function PropriedadesImpressao({ propriedades: disponiveis, carregando }: Props) {
  const [filtros, setFiltros] = useState(filtrosVazios);
  const propriedades = filtrarPropriedadesImpressao(disponiveis, filtros);
  const contexto = [filtros.proprietario && `Proprietário: ${filtros.proprietario}`, filtros.nome && `Propriedade: ${disponiveis.find(p => String(p.id) === filtros.nome)?.nome || "não encontrada"}`, filtros.cadpro && `CAD/PRO: ${filtros.cadpro}`, filtros.municipio && `Município: ${filtros.municipio}`].filter(Boolean).join(" · ");
  const totalDeclarado = propriedades.reduce((total, item) => total + Number(item.area_hectares), 0);
  const calculoCompleto = propriedades.every((item) => item.area_calculada_hectares !== null);
  const totalCalculado = propriedades.reduce(
    (total, item) => total + Number(item.area_calculada_hectares ?? 0),
    0,
  );

  return (<>
    <section className="card filtros-impressao-propriedades nao-imprimir" aria-label="Filtrar propriedades para impressão">
      <div><h2>Impressão de propriedades</h2><p>Combine os filtros abaixo. A impressão usará apenas os registros selecionados da consulta atual.</p></div>
      <div className="filtros-impressao-campos">
        <label>Proprietário<select disabled={carregando} value={filtros.proprietario} onChange={e => setFiltros({ ...filtros, proprietario: e.target.value })}><option value="">Todos os proprietários</option>{opcoes(disponiveis.map(p => p.proprietario)).map(valor => <option key={valor}>{valor}</option>)}</select></label>
        <label>Nome da propriedade<select disabled={carregando} value={filtros.nome} onChange={e => setFiltros({ ...filtros, nome: e.target.value })}><option value="">Todas as propriedades</option>{disponiveis.map(p => <option key={p.id} value={p.id}>{p.nome}</option>)}</select></label>
        <label>CAD/PRO<select disabled={carregando} value={filtros.cadpro} onChange={e => setFiltros({ ...filtros, cadpro: e.target.value })}><option value="">Todos os CAD/PROs</option>{opcoes(disponiveis.flatMap(p => p.cad_pro_numeros)).map(valor => <option key={valor}>{valor}</option>)}</select></label>
        <label>Município/UF<select disabled={carregando} value={filtros.municipio} onChange={e => setFiltros({ ...filtros, municipio: e.target.value })}><option value="">Todos os municípios</option>{opcoes(disponiveis.map(p => `${p.municipio}/${p.uf}`)).map(valor => <option key={valor}>{valor}</option>)}</select></label>
      </div>
      <p role="status">{carregando ? "Carregando propriedades..." : `${propriedades.length} de ${disponiveis.length} propriedades selecionadas para impressão.`}</p>
      {!carregando && <p aria-live="polite">Área total selecionada (declarada): <strong>{alqueires(totalDeclarado)} alq. paulistas</strong></p>}
      <div className="acoes"><button type="button" disabled={carregando || !propriedades.length} onClick={() => window.print()}>Imprimir seleção</button><button type="button" className="secundario" onClick={() => setFiltros(filtrosVazios)}>Limpar seleção</button></div>
    </section>
    <section className="controle-planilha-propriedades somente-impressao" hidden={carregando}>
      <h2 className="titulo-impressao-propriedades">Propriedades</h2>
      {contexto && <p className="nota-impressao-propriedades">{contexto}</p>}
      <p className="nota-impressao-propriedades">Área total selecionada (declarada): <strong>{alqueires(totalDeclarado)} alq. paulistas</strong></p>
      <table className="tabela-impressao-propriedades">
        <thead>
          <tr>
            <th>Propriedade</th>
            <th>CAD/PRO</th>
            <th>Proprietário</th>
            <th>Município/UF</th>
            <th>Área declarada (alq.)</th>
            <th>Área calculada (alq.)</th>
          </tr>
        </thead>
        <tbody>
          {propriedades.length ? propriedades.map((item) => (
            <tr key={item.id}>
              <td>{item.nome}</td>
              <td>{item.cad_pro_numeros.join(", ") || "—"}</td>
              <td>{item.proprietario || "—"}</td>
              <td>{item.municipio}/{item.uf}</td>
              <td>{alqueires(Number(item.area_hectares))}</td>
              <td>{item.area_calculada_hectares === null ? "—" : alqueires(Number(item.area_calculada_hectares))}</td>
            </tr>
          )) : (
            <tr><td colSpan={6}>Nenhuma propriedade na consulta.</td></tr>
          )}
        </tbody>
        <tfoot>
          <tr>
            <th colSpan={4}>TOTAL <small>{propriedades.length} propriedade{propriedades.length === 1 ? "" : "s"}</small></th>
            <td>{alqueires(totalDeclarado)}</td>
            <td>{calculoCompleto ? alqueires(totalCalculado) : "—"}</td>
          </tr>
        </tfoot>
      </table>
      {!calculoCompleto && <p className="nota-impressao-propriedades">Total calculado indisponível: há propriedades sem área calculada.</p>}
    </section></>
  );
}
