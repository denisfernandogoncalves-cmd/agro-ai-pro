import axios from "axios";
import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  ArmazemGraos,
  atualizarCargaColhida,
  CADPro,
  CargaColhida,
  CargaColhidaInput,
  carregarContextoCargas,
  criarCargaColhida,
  excluirCargaColhida,
} from "../../api/cargasColhidas";
import { Propriedade } from "../../api/propriedades";
import { Talhao } from "../../api/talhoes";


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
    tolerancia_impureza_percentual: "100.00",
    desconto_impureza_por_ponto: "0.000",
    tolerancia_defeitos_percentual: "100.00",
    desconto_defeitos_por_ponto: "0.000",
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

function resumoCalculado(carga: CargaColhidaInput) {
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
  const percentual = descontoUmidade + descontoImpureza + descontoDefeitos + descontoPh;
  const descontoKg = bruto * percentual / 100;
  const liquido = Math.max(0, bruto - descontoKg);
  return { percentual, liquido, sacas: liquido / 60 };
}

type Props = { propriedades: Propriedade[] };

export default function CargasColhidasPage({ propriedades }: Props) {
  const [armazens, setArmazens] = useState<ArmazemGraos[]>([]);
  const [cadpros, setCadpros] = useState<CADPro[]>([]);
  const [cargas, setCargas] = useState<CargaColhida[]>([]);
  const [talhoes, setTalhoes] = useState<Talhao[]>([]);
  const [carga, setCarga] = useState<CargaColhidaInput>(() => novaCarga());
  const [edicaoId, setEdicaoId] = useState<number | null>(null);
  const [busca, setBusca] = useState("");
  const [mostrarHistorico, setMostrarHistorico] = useState(false);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [carregando, setCarregando] = useState(false);

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
  const propriedadeSelecionada = propriedades.find((item) => item.id === propriedadeId);
  const cadprosDisponiveis = cadpros.filter((item) =>
    item.propriedades.includes(propriedadeId)
      && (item.ativo || item.id === carga.cad_pro)
  );
  const cadproSelecionado = cadpros.find((item) => item.id === carga.cad_pro);
  const armazensDisponiveis = armazens.filter((item) =>
    item.propriedade === propriedadeId
      && (item.ativo || String(item.id) === carga.armazem)
  );
  const talhoesDisponiveis = talhoes.filter((item) =>
    item.propriedade === propriedadeId
  );
  const areaTotalTalhoes = talhoesDisponiveis
    .filter((item) => carga.talhoes_selecionados.includes(item.id))
    .reduce((total, item) => total + numero(item.area_hectares), 0);
  const calculo = useMemo(() => resumoCalculado(carga), [carga]);

  const cargasFiltradas = cargas.filter((item) => {
    if (!mostrarHistorico && item.status !== "ativa") return false;
    const termo = busca.trim().toLowerCase();
    return !termo || [
      item.placa,
      item.motorista,
      item.propriedade_nome,
      item.cad_pro_codigo,
      item.cultura,
      item.safra,
      item.armazem_nome,
      item.local_colheita,
    ].some((valor) => texto(valor).toLowerCase().includes(termo));
  });
  const cargasDoControle = cargas.filter((item) => {
    if (!propriedadeId || !carga.safra.trim()) return false;
    return item.status === "ativa"
      && item.propriedade === propriedadeId
      && item.safra.toLowerCase() === carga.safra.trim().toLowerCase()
      && item.cultura.toLowerCase() === carga.cultura.toLowerCase();
  });
  const producaoTotalKg = cargasDoControle.reduce(
    (total, item) => total + numero(item.peso_liquido_kg), 0,
  );
  const producaoTotalSacas = cargasDoControle.reduce(
    (total, item) => total + numero(item.sacas_60kg), 0,
  );
  const sementeTotalSacas = cargasDoControle
    .filter((item) => item.destinado_semente)
    .reduce((total, item) => total + numero(item.sacas_60kg), 0);
  const areaPropriedade = numero(propriedadeSelecionada?.area_hectares);
  const mediaSacasHectare = areaPropriedade > 0
    ? producaoTotalSacas / areaPropriedade
    : 0;

  function alterarPropriedade(valor: string) {
    const id = numero(valor);
    const opcoesCadpro = cadpros.filter((item) =>
      item.ativo && item.propriedades.includes(id)
    );
    const opcoesArmazem = armazens.filter((item) =>
      item.ativo && item.propriedade === id
    );
    setCarga({
      ...carga,
      propriedade: valor,
      cad_pro: opcoesCadpro.length === 1 ? opcoesCadpro[0].id : "",
      armazem: opcoesArmazem.length === 1 ? String(opcoesArmazem[0].id) : "",
      talhoes_selecionados: [],
    });
  }

  function cancelarEdicao() {
    setEdicaoId(null);
    setCarga(novaCarga());
  }

  function editar(item: CargaColhida) {
    const contexto = objeto(item.contexto_colheita);
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
      motivo_correcao: "",
      ...regrasDaCarga(item),
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function salvarCarga(evento: FormEvent) {
    evento.preventDefault();
    setErro("");
    setSucesso("");
    if (!carga.propriedade) {
      setErro("Selecione a propriedade da carga.");
      return;
    }
    if (!carga.cad_pro) {
      setErro("Selecione o CAD/PRO da propriedade.");
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
    setCarregando(true);
    try {
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
    }
  }

  async function excluir(item: CargaColhida) {
    if (!window.confirm(
      `Cancelar a carga #${item.id} de ${item.data_colheita}? O saldo será estornado e o histórico permanecerá auditável.`,
    )) return;
    setErro("");
    setSucesso("");
    setCarregando(true);
    try {
      await excluirCargaColhida(
        item.id,
        "Cancelamento solicitado pelo usuário na tela de cargas colhidas.",
      );
      if (edicaoId === item.id) cancelarEdicao();
      setSucesso(`Carga #${item.id} cancelada e saldo estornado.`);
      await carregar();
    } catch (falha) {
      setErro(mensagemErro(falha));
      setCarregando(false);
    }
  }

  return (
    <section className="modulo-cargas">
      {erro && <p className="erro card" role="alert">{erro}</p>}
      {sucesso && <p className="sucesso card" role="status">{sucesso}</p>}

      <div className="cargas-cabecalho">
        <div>
          <span className="kicker">Produção recebida</span>
          <h2>Cargas colhidas</h2>
          <p>Registro direto por propriedade, CAD/PRO, cultura, safra e armazenagem.</p>
        </div>
        <span className="kicker">{mostrarHistorico ? "Exibindo ativas e histórico" : "Exibindo cargas ativas"}</span>
      </div>

      <section className="grade cargas-grade">
        <form className="card formulario" onSubmit={salvarCarga}>
          <h3>{edicaoId ? `Editar carga #${edicaoId}` : "Registrar carga manual"}</h3>
          {edicaoId && <p className="aviso-contexto">Ao salvar, a carga original será estornada e preservada; uma versão corrigida será criada.</p>}
          <label>Propriedade<select required value={carga.propriedade} onChange={(e) => alterarPropriedade(e.target.value)}><option value="">Selecione</option>{propriedades.map((item) => <option key={item.id} value={item.id}>{item.nome} · {item.area_hectares} ha</option>)}</select></label>
          <label>CAD/PRO<select required disabled={!propriedadeId} value={carga.cad_pro} onChange={(e) => setCarga({ ...carga, cad_pro: e.target.value })}><option value="">Selecione</option>{cadprosDisponiveis.map((item) => <option key={item.id} value={item.id}>{item.codigo} · {item.descricao}</option>)}</select></label>
          {propriedadeId > 0 && cadprosDisponiveis.length === 0 && <p className="aviso-contexto">A propriedade não possui CAD/PRO ativo. Informe o número no cadastro da propriedade.</p>}
          <div className="linha"><label>Tipo de grão<select required value={carga.cultura} onChange={(e) => setCarga({ ...carga, cultura: e.target.value })}><option>Soja</option><option>Milho</option><option>Trigo</option></select></label><label>Safra<input required placeholder="2026/2027" value={carga.safra} onChange={(e) => setCarga({ ...carga, safra: e.target.value })} /></label></div>
          <label>Armazenagem<select required disabled={!propriedadeId} value={carga.armazem} onChange={(e) => setCarga({ ...carga, armazem: e.target.value })}><option value="">Selecione</option>{armazensDisponiveis.map((item) => <option key={item.id} value={item.id}>{item.nome} · ocupação {numero(item.ocupacao_kg).toLocaleString("pt-BR")} kg</option>)}</select></label>
          {propriedadeId > 0 && armazensDisponiveis.length === 0 && <p className="aviso-contexto">Nenhuma armazenagem ativa pertence à propriedade selecionada.</p>}
          <fieldset disabled={!propriedadeId}>
            <legend>Talhões da propriedade (opcional)</legend>
            {talhoesDisponiveis.length === 0 ? <span>Nenhum talhão disponível.</span> : talhoesDisponiveis.map((item) => <label className="opcao-checkbox" key={item.id}><input type="checkbox" checked={carga.talhoes_selecionados.includes(item.id)} onChange={(e) => setCarga({ ...carga, talhoes_selecionados: e.target.checked ? [...carga.talhoes_selecionados, item.id] : carga.talhoes_selecionados.filter((id) => id !== item.id) })} /> {item.nome} · {item.area_hectares} ha</label>)}
          </fieldset>
          <div className="resumo-peso"><span>Área da propriedade <strong>{areaPropriedade.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} ha</strong></span><span>Área dos talhões <strong>{areaTotalTalhoes.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} ha</strong></span><span>CAD/PRO <strong>{cadproSelecionado?.codigo || "não informado"}</strong></span></div>
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
            <label>Quebrados (%)<input required min="0" max="100" step="0.01" type="number" value={carga.defeitos_percentual} onChange={(e) => setCarga({ ...carga, defeitos_percentual: e.target.value })} /></label>
          </div>
          <div className="linha">
            <label>PH<input required={numero(carga.desconto_ph_por_ponto) > 0} min="0" max="100" step="0.01" type="number" value={carga.ph} onChange={(e) => setCarga({ ...carga, ph: e.target.value })} /></label>
            <label className="opcao-checkbox"><input type="checkbox" checked={carga.destinado_semente} onChange={(e) => setCarga({ ...carga, destinado_semente: e.target.checked })} /> Destinada a semente</label>
          </div>
          <details className="configuracao-descontos">
            <summary>Regras opcionais de impureza, quebrados e PH</summary>
            <p>A umidade segue automaticamente a tabela oficial da cultura.</p>
            <div className="regras-desconto">
              <fieldset><legend>Impureza</legend><label>Tolerância (%)<input min="0" max="100" step="0.01" type="number" value={carga.tolerancia_impureza_percentual ?? ""} onChange={(e) => setCarga({ ...carga, tolerancia_impureza_percentual: e.target.value })} /></label><label>Desconto/ponto (%)<input min="0" max="100" step="0.001" type="number" value={carga.desconto_impureza_por_ponto ?? ""} onChange={(e) => setCarga({ ...carga, desconto_impureza_por_ponto: e.target.value })} /></label></fieldset>
              <fieldset><legend>Quebrados</legend><label>Tolerância (%)<input min="0" max="100" step="0.01" type="number" value={carga.tolerancia_defeitos_percentual ?? ""} onChange={(e) => setCarga({ ...carga, tolerancia_defeitos_percentual: e.target.value })} /></label><label>Desconto/ponto (%)<input min="0" max="100" step="0.001" type="number" value={carga.desconto_defeitos_por_ponto ?? ""} onChange={(e) => setCarga({ ...carga, desconto_defeitos_por_ponto: e.target.value })} /></label></fieldset>
              <fieldset><legend>PH</legend><label>PH mínimo<input min="0" max="100" step="0.01" type="number" value={carga.ph_minimo ?? ""} onChange={(e) => setCarga({ ...carga, ph_minimo: e.target.value })} /></label><label>Desconto/ponto abaixo (%)<input min="0" max="100" step="0.001" type="number" value={carga.desconto_ph_por_ponto ?? ""} onChange={(e) => setCarga({ ...carga, desconto_ph_por_ponto: e.target.value })} /></label></fieldset>
            </div>
          </details>
          <label>Observações<textarea value={carga.observacoes} onChange={(e) => setCarga({ ...carga, observacoes: e.target.value })} /></label>
          {edicaoId && <label>Motivo da correção<input required maxLength={500} placeholder="Ex.: correção do peso informado" value={carga.motivo_correcao ?? ""} onChange={(e) => setCarga({ ...carga, motivo_correcao: e.target.value })} /></label>}
          <div className="resumo-peso" aria-live="polite">
            <span>Desconto estimado <strong>{calculo.percentual.toFixed(3)}%</strong></span>
            <span>Peso líquido estimado <strong>{calculo.liquido.toLocaleString("pt-BR", { maximumFractionDigits: 3 })} kg</strong></span>
            <span>Conversão estimada <strong>{calculo.sacas.toLocaleString("pt-BR", { maximumFractionDigits: 3 })} sacas</strong></span>
          </div>
          <small>O cálculo definitivo e o snapshot auditável são gravados pelo servidor.</small>
          <div className="acoes"><button disabled={carregando || calculo.percentual >= 100} type="submit">{edicaoId ? "Salvar alterações" : "Registrar e creditar saldo"}</button>{edicaoId && <button className="secundario" type="button" onClick={cancelarEdicao}>Cancelar</button>}</div>
        </form>

        <section className="conteudo">
          <section className="card controle-planilha">
            <div className="controle-planilha-titulo"><div><span className="kicker">Controle de estoque por propriedade</span><h3>{propriedadeSelecionada?.nome || "Selecione uma propriedade"}</h3><p>Área {areaPropriedade.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} ha · cultura {propriedadeSelecionada ? carga.cultura : "—"} · safra {propriedadeSelecionada ? carga.safra || "informe no formulário" : "—"}</p></div><div className="controle-planilha-total"><span>Produção total</span><strong>{producaoTotalSacas.toLocaleString("pt-BR", { maximumFractionDigits: 3 })} sc</strong><small>{producaoTotalKg.toLocaleString("pt-BR", { maximumFractionDigits: 3 })} kg</small></div></div>
            <div className="resumo-controle"><span>Média de produção<strong>{mediaSacasHectare.toLocaleString("pt-BR", { maximumFractionDigits: 3 })} sc/ha</strong></span><span>Destinada a semente<strong>{sementeTotalSacas.toLocaleString("pt-BR", { maximumFractionDigits: 3 })} sc</strong></span><span>CAD/PRO<strong>{cadproSelecionado?.codigo || "—"}</strong></span><span>Área declarada<strong>{areaPropriedade.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} ha</strong></span></div>
            <div className="tabela-responsiva"><table className="tabela-relatorio tabela-controle"><thead><tr><th>Data</th><th>Placa / motorista</th><th>Peso bruto</th><th>Umidade</th><th>Impureza</th><th>Quebrados</th><th>PH</th><th>Semente</th><th>Silo de armazenagem</th><th>Peso líquido</th><th>Sacas 60 kg</th></tr></thead><tbody>{cargasDoControle.length ? cargasDoControle.map((item) => <tr key={`controle-${item.id}`}><td>{item.data_colheita}</td><td>{item.placa || "—"}<small>{item.motorista || "—"}</small></td><td>{numero(item.peso_bruto_kg).toLocaleString("pt-BR")} kg</td><td>{item.umidade_percentual}%</td><td>{item.impureza_percentual}%</td><td>{item.defeitos_percentual}%</td><td>{item.ph || "—"}</td><td>{item.destinado_semente ? `${numero(item.sacas_60kg).toLocaleString("pt-BR")} sc` : "Não"}</td><td>{item.armazem_nome}</td><td>{numero(item.peso_liquido_kg).toLocaleString("pt-BR")} kg</td><td>{numero(item.sacas_60kg).toLocaleString("pt-BR", { maximumFractionDigits: 3 })}</td></tr>) : <tr><td colSpan={11}>Nenhuma carga ativa corresponde à propriedade, safra e cultura selecionadas.</td></tr>}</tbody></table></div>
          </section>
          <div className="painel-filtros">
            <input aria-label="Buscar cargas" placeholder="Buscar placa, propriedade, CAD/PRO, cultura, safra ou local" value={busca} onChange={(e) => setBusca(e.target.value)} />
            <label className="opcao-checkbox"><input type="checkbox" checked={mostrarHistorico} onChange={(e) => setMostrarHistorico(e.target.checked)} /> Mostrar histórico</label>
            <button disabled={carregando} type="button" onClick={() => void carregar()}>Atualizar</button>
          </div>
          <div className="lista cargas-lista">
            {carregando && cargas.length === 0 ? <div className="card vazio">Carregando cargas colhidas...</div> : cargasFiltradas.length === 0 ? <div className="card vazio">Nenhuma carga colhida {mostrarHistorico ? "encontrada" : "ativa"}.</div> : cargasFiltradas.map((item) => (
              <article className={`card carga-item ${item.status !== "ativa" ? "inativo" : ""}`} key={item.id}>
                <div className="carga-item-topo"><div><span className="kicker">Carga #{item.id} · {item.data_colheita} · {item.placa || "sem placa"}{item.motorista ? ` · ${item.motorista}` : ""}</span><h3>{item.propriedade_nome}</h3><p>CAD/PRO {item.cad_pro_codigo} · {item.cultura} · {item.safra} · {item.armazem_nome}</p></div><div><span className="kicker">{item.status === "ativa" ? "Ativa" : item.status === "substituida" ? "Substituída" : "Cancelada"}</span><strong>{numero(item.sacas_60kg).toLocaleString("pt-BR", { maximumFractionDigits: 3 })} sc</strong></div></div>
                <div className="carga-metricas"><span>Bruto <strong>{numero(item.peso_bruto_kg).toLocaleString("pt-BR")} kg</strong></span><span>Desconto <strong>{item.desconto_total_percentual}%</strong></span><span>Líquido <strong>{numero(item.peso_liquido_kg).toLocaleString("pt-BR")} kg</strong></span></div>
                <small>Umidade {item.umidade_percentual}% · Impureza {item.impureza_percentual}% · Quebrados {item.defeitos_percentual}%{item.ph ? ` · PH ${item.ph}` : ""}{item.destinado_semente ? " · Semente" : ""} · movimento #{item.movimentacao}{item.substituida_por ? ` · substituída pela carga #${item.substituida_por}` : ""}</small>
                {item.status !== "ativa" && item.motivo_cancelamento && <small>Motivo: {item.motivo_cancelamento}</small>}
                {item.status === "ativa" && <div className="acoes carga-item-acoes"><button disabled={carregando} className="secundario" type="button" onClick={() => editar(item)}>Editar</button><button disabled={carregando} className="perigo" type="button" onClick={() => void excluir(item)}>Excluir</button></div>}
              </article>
            ))}
          </div>
        </section>
      </section>
    </section>
  );
}
