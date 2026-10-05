import AnexosLancamento from "../../components/AnexosLancamento";
import ComprovanteLancamento from "../../components/ComprovanteLancamento";
import ProducaoTerceiros from "./ProducaoTerceiros";
import FormularioValidado from "../../components/FormularioValidado";
import ResumoConsulta, { noPeriodo, ordenarConsulta, OrdemConsulta, totalConsulta } from "../../components/ResumoConsulta";
import { useConferirDuplicidades } from "../../components/ConferirDuplicidades";
import { formatarPercentual } from "../../utils/numeros";
import FiltrosFavoritos from "../../components/FiltrosFavoritos";
import FiltrosRapidos, { correspondeFiltrosRapidos, filtrosRapidosVazios, restaurarConsultaFavorita } from "../../components/FiltrosRapidos";
import { useAlteracoesNaoSalvas } from "../../components/AlteracoesNaoSalvas";
import { BotaoAcao } from "../../components/AcoesContext";
import axios from "axios";
import { Fragment, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import PainelFormulario from "../../components/PainelFormulario";

import {
  ArmazemGraos,
  atualizarCargaColhida,
  CADPro,
  CargaColhida,
  CargaColhidaInput,
  carregarContextoCargas,
  criarCargaColhida,
  excluirCargaColhida,
  carregarPreviaExclusaoCarga,
  PreviaExclusaoCarga,
} from "../../api/cargasColhidas";
import { Propriedade, rotuloPropriedade } from "../../api/propriedades";
import { Talhao } from "../../api/talhoes";
import { aplicarGrupoNaCarga, GrupoPropriedades, listarGruposPropriedades } from "../../api/gruposPropriedades";
import { areaEmAlqueires } from "../../utils/areas";


function dataLocalISO() {
  const agora = new Date();
  const ano = agora.getFullYear();
  const mes = String(agora.getMonth() + 1).padStart(2, "0");
  const dia = String(agora.getDate()).padStart(2, "0");
  return `${ano}-${mes}-${dia}`;
}

function novaChaveRegistro() {
  return globalThis.crypto?.randomUUID?.()
    ?? `carga-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function novaCarga(): CargaColhidaInput {
  return {
    chave_registro: novaChaveRegistro(),
    propriedade: "",
    cad_pro: "",
    cultura: "Soja",
    safra: "",
    armazem: "",
    data_colheita: dataLocalISO(),
    placa: "",
    motorista: "",
    peso_bruto_kg: "",
    umidade_percentual: "",
    impureza_percentual: "",
    defeitos_percentual: "",
    ph: "",
    destinado_semente: false,
    local_colheita: "",
    observacoes: "",
    talhoes_selecionados: [],
    propriedades_selecionadas: [],
    cadpros_por_propriedade: {},
    tolerancia_impureza_percentual: "0.00",
    desconto_impureza_por_ponto: "1.000",
    tolerancia_defeitos_percentual: "0.00",
    desconto_defeitos_por_ponto: "1.000",
    ph_minimo: "0.00",
    desconto_ph_por_ponto: "0.000",
    motivo_correcao: "",
  };
}

const descontosSojaMilho = [
  0, 0, 0, 0, 0, 0, 1, 1.75, 2.5, 3.25, 4, 4.75, 5.5, 6.25, 7,
  7.75, 8.5, 9.25, 10, 10.75, 11.5, 12.25, 13, 13.75, 14.5, 15.25,
  16, 16.75, 17.5, 18.25, 19, 19.75, 20.5, 21.25, 22, 22.75, 23.5, 24.25,
];
const descontosTrigo = [
  0, 0, 0, 0, 1, 1.75, 2.5, 3.25, 4, 4.75, 5.5, 6.25, 7, 7.75, 8.5,
  9.25, 10, 10.75, 11.5, 12.25, 13, 13.75, 14.5, 15.25, 16, 16.75, 17.5,
  18.25, 19, 19.75, 20.5, 21.25, 22, 22.75, 23.5, 24.25, 25, 25.75,
];

function mensagemErro(falha: unknown) {
  if (axios.isAxiosError(falha)) {
    if (!falha.response) return "Não foi possível conectar ao servidor. Aguarde e tente novamente; confira a lista antes de repetir a exclusão.";
    const dados = falha.response?.data;
    if (typeof dados?.detail === "string") return dados.detail;
    if (dados && typeof dados === "object") {
      return Object.values(dados).flat(2).join(" ");
    }
  }
  return "Não foi possível concluir a operação com a carga colhida.";
}

function numero(valor: string | number | null | undefined) {
  const convertido = Number(valor);
  return Number.isFinite(convertido) ? convertido : 0;
}

function objeto(valor: unknown): Record<string, unknown> {
  return valor && typeof valor === "object" && !Array.isArray(valor)
    ? valor as Record<string, unknown>
    : {};
}

function texto(valor: unknown) {
  return valor === null || valor === undefined ? "" : String(valor);
}

function talhoesDoContexto(item: CargaColhida) {
  const talhoes = objeto(item.contexto_colheita).talhoes;
  if (!Array.isArray(talhoes)) return [];
  return talhoes
    .map((talhao) => Number(objeto(talhao).id))
    .filter((id) => Number.isInteger(id) && id > 0);
}

function propriedadesDoContexto(item: CargaColhida) {
  const propriedades = objeto(item.contexto_colheita).propriedades;
  if (!Array.isArray(propriedades)) return [item.propriedade];
  const ids = propriedades
    .map((propriedade) => Number(objeto(propriedade).id))
    .filter((id) => Number.isInteger(id) && id > 0);
  return ids.length ? ids : [item.propriedade];
}

function cadprosDoContexto(item: CargaColhida) {
  return Object.fromEntries(
    rateiosDoContexto(item)
      .map((rateio) => [texto(rateio.propriedade_id), texto(rateio.cad_pro_id)])
      .filter(([, cadpro]) => Boolean(cadpro)),
  );
}

function rateiosDoContexto(item: CargaColhida) {
  const rateios = objeto(item.contexto_colheita).rateio_producao;
  return Array.isArray(rateios) ? rateios.map(objeto) : [];
}

function produtoresDaCarga(item: CargaColhida) {
  const rateios = rateiosDoContexto(item);
  return rateios.length ? rateios.map((parcela) => ({
    propriedadeId: texto(parcela.propriedade_id),
    nome: texto(parcela.propriedade_nome) || `Propriedade #${texto(parcela.propriedade_id)}`,
    cadpro: texto(parcela.cad_pro_numero),
    peso: numero(texto(parcela.peso_liquido_kg)),
    sacas: numero(texto(parcela.sacas_60kg)),
  })) : [{
    propriedadeId: String(item.propriedade),
    nome: item.propriedade_nome,
    cadpro: item.cad_pro_codigo,
    peso: numero(item.peso_liquido_kg),
    sacas: numero(item.sacas_60kg),
  }];
}

export function numeroPlanilhaCarga(valor: string | number) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  });
}

export function dataPlanilhaCarga(valor?: string) {
  const [ano, mes, dia] = (valor || "").slice(0, 10).split("-");
  return ano && mes && dia ? `${dia}/${mes}/${ano}` : "—";
}

export function identificacaoCargaColhida(
  item: CargaColhida,
  propriedades: Pick<Propriedade, "id" | "proprietario">[],
) {
  return produtoresDaCarga(item).map(produtor => {
    const proprietario = propriedades.find(
      propriedade => propriedade.id === Number(produtor.propriedadeId),
    )?.proprietario?.trim();
    return [produtor.nome, produtor.cadpro, proprietario].filter(Boolean).join(" - ");
  }).join(" · ");
}

export function TabelaImpressaoCargas({
  cargas,
  propriedades,
}: {
  cargas: CargaColhida[];
  propriedades: Pick<Propriedade, "id" | "proprietario">[];
}) {
  const totais = cargas.reduce((acumulado, item) => ({
    bruto: acumulado.bruto + numero(item.peso_bruto_kg),
    liquido: acumulado.liquido + numero(item.peso_liquido_kg),
    sacas: acumulado.sacas + numero(item.sacas_60kg),
  }), { bruto: 0, liquido: 0, sacas: 0 });
  return <div className="tabela-responsiva"><table className="tabela-relatorio tabela-controle cargas-planilha">
    <caption>Cargas colhidas e totais das linhas impressas</caption>
    <thead><tr><th>Data</th><th>Placa / motorista</th><th className="coluna-carga-origem">Propriedade / CAD-PRO / proprietário</th><th>Produto / safra</th><th>Armazenagem</th><th>Status</th><th>Peso bruto (kg)</th><th>Peso líquido (kg)</th><th>Sacas de 60 kg</th></tr></thead>
    <tbody>{cargas.length ? cargas.map(item => <tr key={`carga-impressao-${item.id}`}><td>{dataPlanilhaCarga(item.data_colheita)}</td><td>{item.placa || "—"}<small>{item.motorista || "—"}</small></td><td>{identificacaoCargaColhida(item, propriedades)}</td><td>{item.cultura}<small>{item.safra}</small></td><td>{item.armazem_nome}</td><td>{item.status}</td><td>{numeroPlanilhaCarga(item.peso_bruto_kg)}</td><td><strong>{numeroPlanilhaCarga(item.peso_liquido_kg)}</strong></td><td>{numeroPlanilhaCarga(item.sacas_60kg)}</td></tr>) : <tr><td colSpan={9}>Nenhuma carga encontrada para os filtros informados.</td></tr>}</tbody>
    {cargas.length > 0 && <tfoot><tr><td><strong>TOTAL</strong><small>Total das linhas impressas</small></td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td><strong>{numeroPlanilhaCarga(totais.bruto)}</strong></td><td><strong>{numeroPlanilhaCarga(totais.liquido)}</strong></td><td><strong>{numeroPlanilhaCarga(totais.sacas)}</strong></td></tr></tfoot>}
  </table></div>;
}

export function cargaCorrespondeBusca(item: CargaColhida, busca: string) {
  const termo = busca.trim().toLocaleLowerCase("pt-BR");
  const numeroBusca = termo.match(/^(?:carga\s*)?#?(\d+)$/);
  if (numeroBusca && item.id === Number(numeroBusca[1])) return true;
  if (numeroBusca && /^(?:carga|#)/.test(termo)) return false;
  return !termo || [
    item.placa, item.motorista, item.propriedade_nome, item.cad_pro_codigo,
    item.cultura, item.safra, item.armazem_nome, item.local_colheita,
    ...produtoresDaCarga(item).flatMap((produtor) => [produtor.nome, produtor.cadpro]),
  ].some((valor) => texto(valor).toLocaleLowerCase("pt-BR").includes(termo));
}

export function CartaoCargaColhida({ item, carregando, onEditar, onExcluir }: {
  item: CargaColhida;
  carregando: boolean;
  onEditar: (item: CargaColhida) => void;
  onExcluir: (item: CargaColhida) => void;
}) {
  const produtores = produtoresDaCarga(item);
  const compartilhada = produtores.length > 1;
  const formatar = (valor: number) => valor.toLocaleString("pt-BR", { maximumFractionDigits: 3 });
  return (
    <article className={`card carga-item ${item.status !== "ativa" ? "inativo" : ""}`} aria-label={`Carga #${item.id}`}>
      <div className="carga-item-topo">
        <div>
          <span className="kicker">Carga #{item.id} · {dataPlanilhaCarga(item.data_colheita)} · {item.placa || "sem placa"}{item.motorista ? ` · ${item.motorista}` : ""}</span>
          <h3>{compartilhada ? `Carga compartilhada · ${produtores.length} propriedades` : produtores[0].nome}</h3>
          <p>{!compartilhada && `CAD/PRO ${produtores[0].cadpro} · `}{item.cultura} · {item.safra} · {item.armazem_nome}</p>
        </div>
        <div className="carga-item-total">
          <span className="kicker">{item.status === "ativa" ? "Ativa" : item.status === "substituida" ? "Substituída" : "Cancelada"}</span>
          <small>Total da carga</small>
          <strong>{formatar(numero(item.sacas_60kg))} sc</strong>
        </div>
      </div>
      {compartilhada && <section className="carga-rateios" aria-label="Distribuição da carga por propriedade e CAD/PRO">
        <h4>Distribuição por propriedade e CAD/PRO</h4>
        <ul>{produtores.map((produtor) => <li key={produtor.propriedadeId}>
          <div><strong>{produtor.nome}</strong><span>CAD/PRO {produtor.cadpro || "não informado"}</span></div>
          <div><strong>{formatar(produtor.peso)} kg</strong><span>{formatar(produtor.sacas)} sc</span></div>
        </li>)}</ul>
      </section>}
      <div className="carga-metricas"><span>Bruto total <strong>{formatar(numero(item.peso_bruto_kg))} kg</strong></span><span>Desconto <strong>{formatarPercentual(item.desconto_total_percentual)}</strong></span><span>Líquido total <strong>{formatar(numero(item.peso_liquido_kg))} kg</strong></span></div>
      <details className="detalhes-listagem"><summary>Análises e histórico da carga</summary><div className="carga-analises" aria-label="Análise e rastreabilidade da carga">
        <span>Umidade <strong>{formatarPercentual(item.umidade_percentual)}</strong></span>
        <span>Impureza <strong>{formatarPercentual(item.impureza_percentual)}</strong></span>
        <span>Avariados <strong>{formatarPercentual(item.defeitos_percentual)}</strong></span>
        {item.ph && <span>PH <strong>{formatarPercentual(item.ph).slice(0,-1)}</strong></span>}
        {item.destinado_semente && <span>Semente</span>}
        <span>Movimento principal #{item.movimentacao}</span>
        {item.substituida_por && <span>Substituída pela carga #{item.substituida_por}</span>}
      </div>{item.observacoes&&<p>{item.observacoes}</p>}</details>
      <AnexosLancamento entidade="carga" registro={item.id} />
      <ComprovanteLancamento dados={{titulo:`Carga #${item.id}`,campos:[["Situação",item.status],["Data",dataPlanilhaCarga(item.data_colheita)],["Propriedades / CAD/PRO",produtores.map(p=>`${p.nome} / ${p.cadpro}: ${formatar(p.peso)} kg`).join("; ")],["Produto / safra",`${item.cultura} / ${item.safra}`],["Armazenagem",item.armazem_nome],["Placa / motorista",`${item.placa||"Sem placa"} / ${item.motorista||"—"}`],["Bruto",`${formatar(numero(item.peso_bruto_kg))} kg`],["Desconto",formatarPercentual(item.desconto_total_percentual)],["Líquido",`${formatar(numero(item.peso_liquido_kg))} kg`],["Sacas",formatar(numero(item.sacas_60kg))],["Umidade / impureza / avariados",`${formatarPercentual(item.umidade_percentual)} / ${formatarPercentual(item.impureza_percentual)} / ${formatarPercentual(item.defeitos_percentual)}`],["Movimento",String(item.movimentacao)],["Observações",item.observacoes||"—"],["Motivo de cancelamento",item.motivo_cancelamento||"—"]]}}/>
      {item.status !== "ativa" && item.motivo_cancelamento && <small>Motivo: {item.motivo_cancelamento}</small>}
      {item.status === "ativa" && <div className="acoes carga-item-acoes"><BotaoAcao acao="editar" disabled={carregando} className="secundario" type="button" onClick={() => onEditar(item)}>Editar</BotaoAcao><BotaoAcao acao="excluir" disabled={carregando} className="perigo" type="button" onClick={() => onExcluir(item)}>Excluir</BotaoAcao></div>}
    </article>
  );
}

function regrasDaCarga(item: CargaColhida) {
  const parcelas = objeto(objeto(item.regra_desconto_aplicada).parcelas);
  const impureza = objeto(parcelas.impureza);
  const defeitos = objeto(parcelas.defeitos);
  const ph = objeto(parcelas.ph);
  return {
    tolerancia_impureza_percentual:
      texto(impureza.tolerancia_percentual) || "100.00",
    desconto_impureza_por_ponto:
      texto(impureza.desconto_por_ponto) || "0.000",
    tolerancia_defeitos_percentual:
      texto(defeitos.tolerancia_percentual) || "100.00",
    desconto_defeitos_por_ponto:
      texto(defeitos.desconto_por_ponto) || "0.000",
    ph_minimo: texto(ph.minimo) || "0.00",
    desconto_ph_por_ponto:
      texto(ph.desconto_por_ponto) || "0.000",
  };
}

export function resumoCalculado(carga: CargaColhidaInput) {
  const bruto = numero(carga.peso_bruto_kg);
  const umidade = numero(carga.umidade_percentual);
  const indiceUmidade = Number.isInteger((umidade - 11.5) * 2)
    ? (umidade - 11.5) * 2
    : -1;
  const tabelaUmidade = carga.cultura.toLowerCase() === "trigo"
    ? descontosTrigo
    : descontosSojaMilho;
  const descontoUmidade = tabelaUmidade[indiceUmidade] ?? 0;
  const descontoImpureza = Math.max(
    0,
    numero(carga.impureza_percentual)
      - numero(carga.tolerancia_impureza_percentual),
  ) * numero(carga.desconto_impureza_por_ponto);
  const descontoDefeitos = Math.max(
    0,
    numero(carga.defeitos_percentual)
      - numero(carga.tolerancia_defeitos_percentual),
  ) * numero(carga.desconto_defeitos_por_ponto);
  const phMedido = carga.ph === "" ? numero(carga.ph_minimo) : numero(carga.ph);
  const descontoPh = Math.max(
    0,
    numero(carga.ph_minimo) - phMedido,
  ) * numero(carga.desconto_ph_por_ponto);
  const arredondar = (valor: number) => Math.round((valor + Number.EPSILON) * 1000) / 1000;
  const umidadeKg = arredondar(bruto * descontoUmidade / 100);
  const pesoAposUmidade = arredondar(bruto - umidadeKg);
  const classificacaoKg = arredondar(pesoAposUmidade * (arredondar(descontoImpureza) + arredondar(descontoDefeitos)) / 100);
  const descontoKg = arredondar(umidadeKg + classificacaoKg + arredondar(bruto * arredondar(descontoPh) / 100));
  const percentual = bruto > 0 ? arredondar(descontoKg * 100 / bruto) : 0;
  const liquido = Math.max(0, arredondar(bruto - descontoKg));
  return { percentual, liquido, sacas: arredondar(liquido / 60) };
}

type Props = { propriedades: Propriedade[] };

export default function CargasColhidasPage({ propriedades }: Props) {
  const [exclusao, setExclusao] = useState<{ item: CargaColhida; previa?: PreviaExclusaoCarga; erro: string; motivo: string; carregando: boolean } | null>(null);

  const [grupos, setGrupos] = useState<GrupoPropriedades[]>([]);
  const [erroGrupos, setErroGrupos] = useState("");
  async function carregarGrupos() {
    try { setGrupos(await listarGruposPropriedades()); setErroGrupos(""); }
    catch { setErroGrupos("Não foi possível carregar os grupos. A seleção manual continua disponível."); }
  }
  useEffect(() => { void carregarGrupos(); }, []);
  const [armazens, setArmazens] = useState<ArmazemGraos[]>([]);
  const [cadpros, setCadpros] = useState<CADPro[]>([]);
  const [cargas, setCargas] = useState<CargaColhida[]>([]);
  const [talhoes, setTalhoes] = useState<Talhao[]>([]);
  const [carga, setCarga] = useState<CargaColhidaInput>(() => novaCarga());
  const [edicaoId, setEdicaoId] = useState<number | null>(null);
  const protecao = useAlteracoesNaoSalvas({...carga, chave_registro: undefined}, "Carga colhida", edicaoId);
  const [filtrosRapidos, setFiltrosRapidos] = useState(filtrosRapidosVazios);
  const [ordem,setOrdem]=useState<OrdemConsulta>("data-desc");
  const [busca, setBusca] = useState("");
  const [mostrarHistorico, setMostrarHistorico] = useState(false);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [carregando, setCarregando] = useState(false);
  const travaCarga = useRef(false);
  const [salvando, setSalvando] = useState(false);

  async function carregar() {
    setCarregando(true);
    setErro("");
    try {
      const dados = await carregarContextoCargas(propriedades);
      setArmazens(dados.armazens);
      setCadpros(dados.cadpros);
      setCargas(dados.cargas);
      setTalhoes(dados.talhoes);
    } catch (falha) {
      setErro(mensagemErro(falha));
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    void carregar();
  }, [propriedades]);

  const propriedadeId = numero(carga.propriedade);
  const propriedadesSelecionadasIds = carga.propriedades_selecionadas;
  const propriedadesSelecionadas = propriedades.filter((item) =>
    propriedadesSelecionadasIds.includes(item.id)
  );
  const armazensDisponiveis = armazens.filter((item) =>
    item.ativo || String(item.id) === carga.armazem
  );
  const talhoesDisponiveis = talhoes.filter((item) =>
    propriedadesSelecionadasIds.includes(item.propriedade)
  );
  const areaTotalTalhoes = talhoesDisponiveis
    .filter((item) => carga.talhoes_selecionados.includes(item.id))
    .reduce((total, item) => total + numero(item.area_hectares), 0);
  const calculo = useMemo(() => resumoCalculado(carga), [carga]);

  const cargasFiltradas = ordenarConsulta(cargas.filter((item) => {
    if (!mostrarHistorico && item.status !== "ativa") return false;
    return noPeriodo(item.data_colheita,filtrosRapidos.data_inicio,filtrosRapidos.data_fim) && cargaCorrespondeBusca(item, busca) && correspondeFiltrosRapidos(filtrosRapidos, item.cultura, item.safra, propriedadesDoContexto(item));
  }),ordem,item=>({data:item.data_colheita,propriedade:produtoresDaCarga(item).map(p=>p.nome).join(" / "),quantidade:Number(item.peso_liquido_kg),id:item.id}));
  const propriedadesImpressao = [...new Set(cargasFiltradas.flatMap(
    item => produtoresDaCarga(item).map(produtor => produtor.nome),
  ))];
  const cadprosImpressao = [...new Set(cargasFiltradas.flatMap(
    item => produtoresDaCarga(item).map(produtor => produtor.cadpro).filter(Boolean),
  ))];
  const culturasImpressao = [...new Set(cargasFiltradas.map(item => item.cultura))];
  const safrasImpressao = [...new Set(cargasFiltradas.map(item => item.safra))];
  const pesoLiquidoImpressao = cargasFiltradas.reduce(
    (total, item) => total + numero(item.peso_liquido_kg), 0,
  );
  const areaTotalSelecionada = propriedadesSelecionadas.reduce(
    (total, item) => total + numero(item.area_hectares), 0,
  );
  const previaRateio = propriedadesSelecionadas.map((item, indice) => {
    const area = numero(item.area_hectares);
    const proporcao = areaTotalSelecionada > 0 ? area / areaTotalSelecionada : 0;
    const cadprosAtivos = cadpros.filter((cadpro) =>
      cadpro.ativo && cadpro.propriedades.includes(item.id)
    );
    const cadproId = carga.cadpros_por_propriedade[String(item.id)] || "";
    const cadpro = cadprosAtivos.find((opcao) => opcao.id === cadproId);
    return {
      ...item,
      proporcao,
      peso: indice === propriedadesSelecionadas.length - 1
        ? calculo.liquido - propriedadesSelecionadas.slice(0, -1).reduce(
          (total, anterior) => total + Math.round(
            calculo.liquido * numero(anterior.area_hectares) / areaTotalSelecionada * 1000,
          ) / 1000,
          0,
        )
        : Math.round(calculo.liquido * proporcao * 1000) / 1000,
      cadpro,
      cadproAmbiguo: !cadpro,
    };
  });

  function alternarPropriedadeRateio(id: number, marcada: boolean) {
    const ids = marcada
      ? [...new Set([...propriedadesSelecionadasIds, id])]
      : propriedadesSelecionadasIds.filter((item) => item !== id);
    const cadprosEscolhidos = { ...carga.cadpros_por_propriedade };
    if (marcada) {
      const opcoes = cadpros.filter((item) =>
        item.ativo && item.propriedades.includes(id)
      );
      cadprosEscolhidos[String(id)] = opcoes.length === 1 ? opcoes[0].id : "";
    } else {
      delete cadprosEscolhidos[String(id)];
    }
    const propriedadePrincipal = ids.includes(propriedadeId)
      ? propriedadeId
      : ids[0] || 0;
    const propriedadesMantidas = new Set(ids);
    setCarga({
      ...carga,
      propriedade: propriedadePrincipal ? String(propriedadePrincipal) : "",
      cad_pro: propriedadePrincipal
        ? cadprosEscolhidos[String(propriedadePrincipal)] || ""
        : "",
      propriedades_selecionadas: ids,
      cadpros_por_propriedade: cadprosEscolhidos,
      talhoes_selecionados: carga.talhoes_selecionados.filter((talhaoId) => {
        const talhao = talhoes.find((item) => item.id === talhaoId);
        return talhao ? propriedadesMantidas.has(talhao.propriedade) : false;
      }),
    });
  }

  function alterarCadproDaPropriedade(id: number, cadproId: string) {
    setCarga({
      ...carga,
      cad_pro: id === propriedadeId ? cadproId : carga.cad_pro,
      cadpros_por_propriedade: {
        ...carga.cadpros_por_propriedade,
        [String(id)]: cadproId,
      },
    });
  }

  function cancelarEdicao() {
    setEdicaoId(null);
    const nova = novaCarga(); setCarga(nova); protecao.marcarSalvo({...nova,chave_registro:undefined});
  }

  async function editar(item: CargaColhida) {
    if (!(await protecao.confirmarDescarte())) return;
    const contexto = objeto(item.contexto_colheita);
    const propriedadesDaCarga = propriedadesDoContexto(item);
    setErro("");
    setSucesso("");
    setEdicaoId(item.id);
    setCarga({
      chave_registro: "",
      propriedade: String(item.propriedade),
      cad_pro: item.cad_pro,
      cultura: item.cultura || texto(contexto.cultura) || "Soja",
      safra: item.safra || texto(contexto.safra),
      armazem: String(item.armazem),
      data_colheita: item.data_colheita,
      placa: item.placa,
      motorista: item.motorista,
      peso_bruto_kg: item.peso_bruto_kg,
      umidade_percentual: item.umidade_percentual,
      impureza_percentual: item.impureza_percentual,
      defeitos_percentual: item.defeitos_percentual,
      ph: item.ph ?? "",
      destinado_semente: item.destinado_semente,
      local_colheita: item.local_colheita,
      observacoes: item.observacoes,
      talhoes_selecionados: talhoesDoContexto(item),
      propriedades_selecionadas: propriedadesDaCarga,
      cadpros_por_propriedade: cadprosDoContexto(item),
      motivo_correcao: "",
      ...regrasDaCarga(item),
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const conferirDuplicidades = useConferirDuplicidades();
  async function salvarCarga(evento: FormEvent) {
    evento.preventDefault();
    if (travaCarga.current) return;
    setErro("");
    setSucesso("");
    if (carga.propriedades_selecionadas.length === 0) {
      setErro("Selecione ao menos uma propriedade para a carga.");
      return;
    }
    if (!carga.cad_pro) {
      setErro("Selecione o CAD/PRO de cada propriedade marcada.");
      return;
    }
    if (previaRateio.some((item) => item.cadproAmbiguo)) {
      setErro("Selecione um CAD/PRO ativo para cada propriedade marcada.");
      return;
    }
    if (!carga.placa.trim() && !carga.motorista.trim()) {
      setErro("Informe a placa do veículo ou o nome do motorista.");
      return;
    }
    if (edicaoId && !carga.motivo_correcao?.trim()) {
      setErro("Informe o motivo da correção para manter a auditoria da carga.");
      return;
    }
    travaCarga.current = true; setSalvando(true);
    setCarregando(true);
    try {
      if (!(await conferirDuplicidades("carga", {data:carga.data_colheita,quantidade:Number(carga.peso_bruto_kg.replace(",",".")),propriedade:Number(carga.propriedade),cultura:carga.cultura,safra:carga.safra,placa:carga.placa,...(edicaoId?{excluir_id:edicaoId}:{})}))) {setCarregando(false);return;}
      const salva = edicaoId
        ? await atualizarCargaColhida(edicaoId, carga)
        : await criarCargaColhida(carga);
      setSucesso(
        edicaoId
          ? `Carga retificada com sucesso. A versão corrigida é a carga #${salva.id}.`
          : `Carga registrada: ${salva.peso_liquido_kg} kg líquidos (${salva.sacas_60kg} sacas).`,
      );
      cancelarEdicao();
      await carregar();
    } catch (falha) {
      setErro(mensagemErro(falha));
      setCarregando(false);
    } finally { travaCarga.current = false; setSalvando(false); }
  }

  async function prepararExclusao(item: CargaColhida) {
    setExclusao({ item, motivo: "", erro: "", carregando: true });
    try { const previa = await carregarPreviaExclusaoCarga(item.id); setExclusao(atual => atual?.item.id === item.id ? { ...atual, previa, carregando: false } : atual); }
    catch (falha) { setExclusao(atual => atual?.item.id === item.id ? { ...atual, erro: mensagemErro(falha), carregando: false } : atual); }
  }

  async function excluir(item: CargaColhida) {
    if (travaCarga.current || !exclusao?.previa?.pode_excluir || !exclusao.motivo.trim()) return;
    if (!window.confirm(
      `Cancelar a carga #${item.id} de ${dataPlanilhaCarga(item.data_colheita)}? O saldo será estornado e o histórico permanecerá auditável.`,
    )) return;
    setErro("");
    setSucesso("");
    travaCarga.current = true; setSalvando(true);
    setCarregando(true);
    try {
      await excluirCargaColhida(
        item.id,
        exclusao.motivo.trim(),
      );
      if (edicaoId === item.id) cancelarEdicao();
      setExclusao(null);
      setSucesso(`Carga #${item.id} cancelada e saldo estornado.`);
      await carregar();
    } catch (falha) {
      setErro(mensagemErro(falha));
      setExclusao(atual => atual ? { ...atual, erro: mensagemErro(falha) } : atual);
      setCarregando(false);
    } finally { travaCarga.current = false; setSalvando(false); }
  }

  return (
    <section className="modulo-cargas">
      <FiltrosFavoritos contexto="cargas" filtros={{search:busca, mostrarHistorico, ...filtrosRapidos}} aplicar={valores => {const consulta=restaurarConsultaFavorita(valores);setBusca(consulta.busca);setMostrarHistorico(consulta.mostrarHistorico);setFiltrosRapidos(consulta.filtros);}} />
      {erro && <p className="erro card" role="alert">{erro}</p>}
      {sucesso && <p className="sucesso card" role="status">{sucesso}</p>}
      {(carregando || salvando) && <p role="status">{salvando ? "Salvando carga..." : "Atualizando cargas colhidas..."}</p>}

      <ProducaoTerceiros armazens={armazens} atualizarArmazens={carregar} />
      <section className="card controle-planilha controle-planilha-impressao controle-planilha-cargas somente-impressao" hidden={carregando}>
        <h2 className="somente-impressao titulo-impressao-planilha">Cargas colhidas</h2>
        <div className="controle-planilha-titulo"><div><span className="kicker">Controle de entrada de produção</span><h3>{propriedadesImpressao.join(" · ") || "Todas as propriedades"}</h3><p>CAD/PRO {cadprosImpressao.join(", ") || "—"} · {culturasImpressao.join(", ") || "todas as culturas"} · safra {safrasImpressao.join(", ") || "todas"}</p></div><div className="controle-planilha-total"><span>Entrada líquida</span><strong>{numeroPlanilhaCarga(pesoLiquidoImpressao)} kg</strong><small>{numeroPlanilhaCarga(pesoLiquidoImpressao / 60)} sacas de 60 kg</small></div></div>
        <TabelaImpressaoCargas cargas={cargasFiltradas} propriedades={propriedades} />
      </section>

      <div className="cargas-cabecalho">
        <div>
          <span className="kicker">Produção recebida</span>
          <h2>Cargas colhidas</h2>
          <p>Registro por propriedades, seus CAD/PROs, cultura, safra e armazenagem.</p>
        </div>
        <span className="kicker">{mostrarHistorico ? "Exibindo ativas e histórico" : "Exibindo cargas ativas"}</span>
      </div>

      <section className="grade cargas-grade">
        <PainelFormulario titulo={edicaoId ? `Editar carga #${edicaoId}` : "Registrar carga manual"} edicao={edicaoId}>
        <FormularioValidado className="card formulario formulario-carga-horizontal" onSubmit={salvarCarga}>
          <h3>{edicaoId ? `Editar carga #${edicaoId}` : "Registrar carga manual"}</h3>
          {edicaoId && <><p className="aviso-contexto">Ao salvar, a carga original será estornada e preservada; uma versão corrigida será criada.</p><div className="comparacao-edicao"><span>Líquido atual da carga <strong>{numero(cargas.find(c => c.id === edicaoId)?.peso_liquido_kg || 0).toLocaleString("pt-BR")} kg</strong></span><span>Novo crédito líquido <strong>{calculo.liquido.toLocaleString("pt-BR")} kg</strong></span></div><small>Prévia do crédito da carga. Saldos finais de cada posição e bloqueios são validados ao salvar.</small></>}
          <label>Usar grupo de colheita
            <select value="" disabled={carregando} onChange={e => {
              const grupo = grupos.find(g => String(g.id) === e.target.value);
              if (!grupo) return;
              try {
                const preenchida = aplicarGrupoNaCarga(carga, grupo);
                if (grupo.membros.some(m => !propriedades.some(p => p.id === m.propriedade))) throw new Error("Atualize as propriedades antes de usar este grupo.");
                setCarga(preenchida); setErroGrupos("");
              } catch (falha) { setErroGrupos(falha instanceof Error ? falha.message : "Não foi possível aplicar o grupo."); }
            }}>
              <option value="">Selecione para preencher as propriedades</option>
              {grupos.filter(g => g.ativo).map(g => <option key={g.id} value={g.id}>{g.nome}</option>)}
            </select>
          </label>
          <button type="button" onClick={() => void carregarGrupos()}>Atualizar grupos</button>
          {erroGrupos && <p className="erro" role="alert">{erroGrupos}</p>}
          <p>Cadastre grupos em Talhões. Após aplicar, confira as propriedades abaixo; você pode ajustar a seleção e os CAD/PROs antes de salvar.</p>
          <fieldset>
            <legend>Escolha as propriedades</legend>
            {propriedades.map((item) => {
              const selecionada = propriedadesSelecionadasIds.includes(item.id);
              const opcoesCadpro = cadpros.filter((cadpro) =>
                cadpro.ativo && cadpro.propriedades.includes(item.id)
              );
              return <div key={`rateio-${item.id}`}>
                <label className="opcao-checkbox"><input type="checkbox" checked={selecionada} onChange={(e) => alternarPropriedadeRateio(item.id, e.target.checked)} /> {rotuloPropriedade(item)} · {areaEmAlqueires(item.area_hectares)} alq.</label>
                {selecionada && <label>CAD/PRO de {item.nome}<select required value={carga.cadpros_por_propriedade[String(item.id)] || ""} onChange={(e) => alterarCadproDaPropriedade(item.id, e.target.value)}><option value="">Selecione</option>{opcoesCadpro.map((cadpro) => <option key={cadpro.id} value={cadpro.id}>{cadpro.codigo} · {cadpro.descricao}</option>)}</select></label>}
                {selecionada && opcoesCadpro.length === 0 && <p className="aviso-contexto">Esta propriedade não possui CAD/PRO ativo.</p>}
              </div>;
            })}
          </fieldset>
          <div className="linha"><label>Tipo de grão<select required value={carga.cultura} onChange={(e) => setCarga({ ...carga, cultura: e.target.value })}><option>Soja</option><option>Milho</option><option>Trigo</option></select></label><label>Safra<input required placeholder="2026/2027" value={carga.safra} onChange={(e) => setCarga({ ...carga, safra: e.target.value })} /></label></div>
          <label>Armazenagem<select required value={carga.armazem} onChange={(e) => setCarga({ ...carga, armazem: e.target.value })}><option value="">Selecione</option>{armazensDisponiveis.map((item) => <option key={item.id} value={item.id}>{item.nome} · ocupação {numero(item.ocupacao_kg).toLocaleString("pt-BR")} kg</option>)}</select></label>
          {armazensDisponiveis.length === 0 && <p className="aviso-contexto">Nenhuma armazenagem ativa cadastrada.</p>}
          <fieldset disabled={propriedadesSelecionadasIds.length === 0}>
            <legend>Talhões das propriedades (opcional)</legend>
            {talhoesDisponiveis.length === 0 ? <span>Nenhum talhão disponível.</span> : talhoesDisponiveis.map((item) => <label className="opcao-checkbox" key={item.id}><input type="checkbox" checked={carga.talhoes_selecionados.includes(item.id)} onChange={(e) => setCarga({ ...carga, talhoes_selecionados: e.target.checked ? [...carga.talhoes_selecionados, item.id] : carga.talhoes_selecionados.filter((id) => id !== item.id) })} /> {item.nome} · {areaEmAlqueires(item.area_hectares)} alq.</label>)}
          </fieldset>
          <div className="resumo-peso"><span>Área total selecionada <strong>{areaEmAlqueires(areaTotalSelecionada)} alq.</strong></span><span>Área dos talhões <strong>{areaEmAlqueires(areaTotalTalhoes)} alq.</strong></span><span>Propriedades <strong>{propriedadesSelecionadas.length}</strong></span></div>
          <div className="linha">
            <label>Data<input required type="date" value={carga.data_colheita} onChange={(e) => setCarga({ ...carga, data_colheita: e.target.value })} /></label>
            <label>Placa do veículo<input maxLength={8} placeholder="ABC1D23" value={carga.placa} onChange={(e) => setCarga({ ...carga, placa: e.target.value.toUpperCase() })} /></label>
          </div>
          <label>Nome do motorista<input maxLength={120} placeholder="Obrigatório quando não houver placa" value={carga.motorista} onChange={(e) => setCarga({ ...carga, motorista: e.target.value })} /></label>
          <label>Local de colheita<input placeholder="Talhão, gleba ou ponto de origem" value={carga.local_colheita} onChange={(e) => setCarga({ ...carga, local_colheita: e.target.value })} /></label>
          <label>Peso bruto (kg)<input required min="0.001" step="0.001" type="number" value={carga.peso_bruto_kg} onChange={(e) => setCarga({ ...carga, peso_bruto_kg: e.target.value })} /></label>
          <div className="linha">
            <label>Umidade (%)<input required min="11.5" max="30" step="0.5" type="number" value={carga.umidade_percentual} onChange={(e) => setCarga({ ...carga, umidade_percentual: e.target.value })} /></label>
            <label>Impureza (%)<input required min="0" max="100" step="0.01" type="number" value={carga.impureza_percentual} onChange={(e) => setCarga({ ...carga, impureza_percentual: e.target.value })} /></label>
            <label>Avariados (%)<input required min="0" max="100" step="0.01" type="number" value={carga.defeitos_percentual} onChange={(e) => setCarga({ ...carga, defeitos_percentual: e.target.value })} /></label>
          </div>
          <div className="linha">
            <label>PH<input required={numero(carga.desconto_ph_por_ponto) > 0} min="0" max="100" step="0.01" type="number" value={carga.ph} onChange={(e) => setCarga({ ...carga, ph: e.target.value })} /></label>
            <label className="opcao-checkbox"><input type="checkbox" checked={carga.destinado_semente} onChange={(e) => setCarga({ ...carga, destinado_semente: e.target.checked })} /> Destinada a semente</label>
          </div>
          <details className="configuracao-descontos">
            <summary>Regras opcionais de impureza, avariados e PH</summary>
            <p>Primeiro descontamos a umidade pela tabela da cultura. Depois, impureza e avariados são somados e descontados sobre o peso restante. Por padrão, os percentuais informados são descontados integralmente.</p>
            <div className="regras-desconto">
              <fieldset><legend>Impureza</legend><label>Tolerância (%)<input min="0" max="100" step="0.01" type="number" value={carga.tolerancia_impureza_percentual ?? ""} onChange={(e) => setCarga({ ...carga, tolerancia_impureza_percentual: e.target.value })} /></label><label>Desconto/ponto (%)<input min="0" max="100" step="0.001" type="number" value={carga.desconto_impureza_por_ponto ?? ""} onChange={(e) => setCarga({ ...carga, desconto_impureza_por_ponto: e.target.value })} /></label></fieldset>
              <fieldset><legend>Avariados</legend><label>Tolerância (%)<input min="0" max="100" step="0.01" type="number" value={carga.tolerancia_defeitos_percentual ?? ""} onChange={(e) => setCarga({ ...carga, tolerancia_defeitos_percentual: e.target.value })} /></label><label>Desconto/ponto (%)<input min="0" max="100" step="0.001" type="number" value={carga.desconto_defeitos_por_ponto ?? ""} onChange={(e) => setCarga({ ...carga, desconto_defeitos_por_ponto: e.target.value })} /></label></fieldset>
              <fieldset><legend>PH</legend><label>PH mínimo<input min="0" max="100" step="0.01" type="number" value={carga.ph_minimo ?? ""} onChange={(e) => setCarga({ ...carga, ph_minimo: e.target.value })} /></label><label>Desconto/ponto abaixo (%)<input min="0" max="100" step="0.001" type="number" value={carga.desconto_ph_por_ponto ?? ""} onChange={(e) => setCarga({ ...carga, desconto_ph_por_ponto: e.target.value })} /></label></fieldset>
            </div>
          </details>
          <label>Observações<textarea value={carga.observacoes} onChange={(e) => setCarga({ ...carga, observacoes: e.target.value })} /></label>
          {edicaoId && <label>Motivo da correção<input required maxLength={500} placeholder="Ex.: correção do peso informado" value={carga.motivo_correcao ?? ""} onChange={(e) => setCarga({ ...carga, motivo_correcao: e.target.value })} /></label>}
          <div className="resumo-peso" aria-live="polite">
            <span>Desconto estimado <strong>{formatarPercentual(calculo.percentual)}</strong></span>
            <span>Peso líquido estimado <strong>{calculo.liquido.toLocaleString("pt-BR", { maximumFractionDigits: 3 })} kg</strong></span>
            <span>Conversão estimada <strong>{calculo.sacas.toLocaleString("pt-BR", { maximumFractionDigits: 3 })} sacas</strong></span>
          </div>
          {previaRateio.length > 0 && <div className="resumo-peso" aria-label="Prévia do rateio proporcional">{previaRateio.map((item) => <span key={`previa-${item.id}`}>{item.nome}<strong>{item.peso.toLocaleString("pt-BR", { maximumFractionDigits: 3 })} kg · {(item.proporcao * 100).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}% · CAD/PRO {item.cadpro?.codigo || "revisar cadastro"}</strong></span>)}</div>}
          <small>O cálculo definitivo e o snapshot auditável são gravados pelo servidor.</small>
          <div className="acoes"><button disabled={salvando || carregando || calculo.percentual >= 100} type="submit">{salvando ? "Salvando carga..." : edicaoId ? "Salvar alterações" : "Registrar e creditar saldo"}</button>{edicaoId && <button className="secundario" type="button" onClick={async () => {if (await protecao.confirmarDescarte()) cancelarEdicao();}}>Cancelar</button>}</div>
        </FormularioValidado>

        </PainelFormulario>
        <section className="conteudo">
          <div className="painel-filtros">
            <input aria-label="Buscar cargas" placeholder="Número da carga, placa, propriedade ou CAD/PRO" value={busca} onChange={(e) => setBusca(e.target.value)} />
            <label className="opcao-checkbox"><input type="checkbox" checked={mostrarHistorico} onChange={(e) => setMostrarHistorico(e.target.checked)} /> Mostrar histórico</label>
            <button disabled={carregando} type="button" onClick={() => void carregar()}>Atualizar</button>
          </div>
          <FiltrosRapidos valor={filtrosRapidos} alterar={setFiltrosRapidos} culturas={[...new Set(cargas.map(c => c.cultura))].sort()} safras={[...new Set(cargas.map(c => c.safra))].sort()} propriedades={propriedades} busca={busca} limparBusca={() => setBusca("")} quantidade={cargasFiltradas.length} />
          <ResumoConsulta quantidade={cargasFiltradas.length} descricao="Totais apenas das cargas ativas desta consulta; histórico não somado." ordem={ordem} alterar={setOrdem} totais={[{nome:"Bruto ativo",valor:totalConsulta(cargasFiltradas.filter(c=>c.status==="ativa"),c=>c.peso_bruto_kg),unidade:"kg"},{nome:"Líquido ativo",valor:totalConsulta(cargasFiltradas.filter(c=>c.status==="ativa"),c=>c.peso_liquido_kg),unidade:"kg"},{nome:"Sacas ativas",valor:totalConsulta(cargasFiltradas.filter(c=>c.status==="ativa"),c=>c.sacas_60kg),unidade:"sc"}]}/>
          <div className="lista cargas-lista">
            {carregando && cargas.length === 0 ? <div className="card vazio">Carregando cargas colhidas...</div> : cargasFiltradas.length === 0 ? <div className="card vazio">Nenhuma carga colhida {mostrarHistorico ? "encontrada" : "ativa"}.</div> : cargasFiltradas.map((item) => (
              <Fragment key={item.id}><CartaoCargaColhida item={item} carregando={carregando || salvando} onEditar={editar} onExcluir={(selecionada) => void prepararExclusao(selecionada)} />
              {exclusao?.item.id === item.id && <FormularioValidado className="card formulario confirmacao-exclusao-carga" onSubmit={e => { e.preventDefault(); void excluir(item); }}><h3>Excluir carga #{item.id}</h3>
                {exclusao.carregando && <p role="status">Conferindo os saldos antes da exclusão...</p>}
                {exclusao.erro && <p className="erro" role="alert">{exclusao.erro}</p>}
                {exclusao.previa && <><p>A exclusão estorna a entrada e mantém o registro no histórico.</p>
                  {exclusao.previa.impedimentos.map((texto, i) => <p className="erro" role="alert" key={i}>{texto}</p>)}
                  <ul>{exclusao.previa.efeitos.map(efeito => <li key={efeito.posicao}>{efeito.propriedade} · CAD/PRO {efeito.cad_pro} · {efeito.cultura}: saldo {Number(efeito.saldo_anterior_kg).toLocaleString("pt-BR")} kg → {Number(efeito.saldo_posterior_kg).toLocaleString("pt-BR")} kg após excluir; reservado {Number(efeito.comprometido_kg).toLocaleString("pt-BR")} kg.</li>)}</ul>
                  {exclusao.previa.transferencias.length > 0 && <><p>Transferências posteriores ainda ativas. Confira ou exclua a transferência na tela “Transferência de saldo entre CAD/PROs” antes de tentar novamente.</p><ul>{exclusao.previa.transferencias.map(t => <li key={t.movimento_saida}>Transferência #{t.movimento_saida}: {Number(t.quantidade_kg).toLocaleString("pt-BR")} kg para {t.destino}.</li>)}</ul>{exclusao.previa.mais_transferencias && <p>Há outras transferências. Consulte o histórico completo.</p>}</>}
                  {exclusao.previa.pode_excluir && <label>Motivo da exclusão<textarea required maxLength={500} disabled={salvando} value={exclusao.motivo} onChange={e => setExclusao({ ...exclusao, motivo: e.target.value })} /></label>}
                </>}
                <div className="acoes"><BotaoAcao acao="excluir" type="submit" className="perigo" disabled={salvando || !exclusao.previa?.pode_excluir || !exclusao.motivo.trim()} motivoBloqueio={salvando ? "Aguarde o processamento." : exclusao.carregando ? "Conferindo os saldos." : !exclusao.previa?.pode_excluir ? exclusao.previa?.impedimentos[0] || "Confira os saldos para liberar a exclusão." : "Informe o motivo da exclusão."}>Confirmar exclusão</BotaoAcao><button type="button" className="secundario" disabled={salvando} onClick={() => void prepararExclusao(item)}>Conferir novamente</button><button type="button" className="secundario" disabled={salvando} onClick={() => setExclusao(null)}>Cancelar exclusão</button></div>
              </FormularioValidado>}
              </Fragment>
            ))}
          </div>
        </section>
      </section>
    </section>
  );
}
