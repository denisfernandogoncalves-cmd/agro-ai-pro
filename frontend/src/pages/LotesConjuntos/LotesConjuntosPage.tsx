import axios from "axios";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  adicionarCargaLote,
  baixarRelatorioLotesConjuntos,
  carregarCadastrosLoteConjunto,
  confirmarLoteConjunto,
  criarLoteConjunto,
  listarLotesConjuntos,
  obterLoteConjunto,
  colocarLoteEmConferencia,
  ratearLoteManual,
  ratearLotePorArea,
  type CadastrosLoteConjunto,
  type LoteConjunto,
  type MetodoRateio,
} from "../../api/lotesConjuntos";
import type { Propriedade } from "../../api/propriedades";
import {
  AlertCard,
  Badge,
  DataTable,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  PermissionGuard,
  ResponsiveGrid,
  SectionCard,
  StatCard,
} from "../../components/shared/ui";

import "./lotes-conjuntos.css";


type ParticipanteDraft = {
  propriedade: number;
  areaCadastrada: string;
  areaColhida: string;
  cadpro: string;
  talhoes: number[];
  justificativaExcesso: string;
  quantidadeManual: string;
  unidadeManual: "kg" | "toneladas" | "sacas";
};

const etapas = [
  "Informações básicas",
  "Propriedades",
  "Áreas colhidas",
  "CAD/PRO",
  "Cargas e viagens",
  "Qualidade",
  "Armazenagem",
  "Rateio opcional",
  "Conferência",
  "Confirmação",
];

const cadastrosVazios: CadastrosLoteConjunto = {
  culturas: [],
  safras: [],
  cadpros: [],
  locais: [],
  talhoes: [],
  motoristas: [],
  veiculos: [],
  parceiros: [],
};

const numero = (valor: string | number | null | undefined, casas = 2) => Number(valor || 0).toLocaleString("pt-BR", { maximumFractionDigits: casas });
const hoje = new Date().toISOString().slice(0, 10);

function mensagemErro(erro: unknown) {
  if (axios.isAxiosError(erro)) {
    const dados = erro.response?.data;
    if (erro.response?.status === 403) return "Seu perfil não permite executar esta ação em todas as propriedades selecionadas.";
    if (erro.response?.status === 404) return "O lote não foi encontrado ou contém propriedade fora do seu acesso.";
    if (typeof dados?.detail === "string") return dados.detail;
    if (dados && typeof dados === "object") return Object.values(dados).flat(Infinity).join(" ");
  }
  return "Não foi possível concluir a operação.";
}

export default function LotesConjuntosPage({ properties }: { properties: Propriedade[] }) {
  const [cadastros, setCadastros] = useState(cadastrosVazios);
  const [lotes, setLotes] = useState<LoteConjunto[]>([]);
  const [selecionado, setSelecionado] = useState<LoteConjunto | null>(null);
  const [etapa, setEtapa] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busca, setBusca] = useState("");
  const [municipio, setMunicipio] = useState("");
  const [produtor, setProdutor] = useState("");
  const [filtroCadpro, setFiltroCadpro] = useState("");
  const [participantes, setParticipantes] = useState<ParticipanteDraft[]>([]);
  const [basico, setBasico] = useState({
    descricao: "",
    cultura: "",
    variedade: "",
    safra: "",
    inicio: hoje,
    fim: "",
    local: "",
    cadproResponsavel: "",
    modoRateio: "sem_rateio" as MetodoRateio,
    observacoes: "",
  });
  const [carga, setCarga] = useState({
    motorista: "",
    cavalo: "",
    carreta: "",
    placaCavalo: "",
    placaCarreta: "",
    transportadora: "",
    origem: "",
    destino: "",
    bruto: "",
    tara: "",
    liquido: "",
    umidade: "",
    impureza: "",
    defeitos: "",
    romaneio: "",
    balanca: "",
    notaFiscal: "",
    observacoes: "",
  });
  const [justificativaRateio, setJustificativaRateio] = useState("");

  const canManage = properties.some((item) => item.pode_editar);
  const canOperate = properties.some((item) => item.pode_operar || item.pode_editar);

  const carregar = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [registros, dadosLotes] = await Promise.all([
        carregarCadastrosLoteConjunto(),
        listarLotesConjuntos({ ordering: "-data_inicio_colheita" }),
      ]);
      setCadastros(registros);
      setLotes(dadosLotes);
      setBasico((atual) => ({
        ...atual,
        cultura: atual.cultura || String(registros.culturas[0]?.id || ""),
        safra: atual.safra || String(registros.safras[0]?.id || ""),
        local: atual.local || String(registros.locais[0]?.id || ""),
      }));
    } catch (falha) {
      setError(mensagemErro(falha));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void carregar(); }, [carregar]);

  const propriedadesFiltradas = useMemo(() => properties.filter((propriedade) => {
    const texto = `${propriedade.nome} ${propriedade.municipio} ${propriedade.proprietario}`.toLowerCase();
    const cadpros = cadastros.cadpros.filter((item) => item.propriedade === propriedade.id);
    return (!busca || texto.includes(busca.toLowerCase()))
      && (!municipio || propriedade.municipio.toLowerCase().includes(municipio.toLowerCase()))
      && (!produtor || propriedade.proprietario.toLowerCase().includes(produtor.toLowerCase()))
      && (!filtroCadpro || cadpros.some((item) => `${item.codigo} ${item.titular}`.toLowerCase().includes(filtroCadpro.toLowerCase())));
  }), [busca, cadastros.cadpros, filtroCadpro, municipio, produtor, properties]);

  const areaCadastrada = participantes.reduce((total, item) => total + Number(item.areaCadastrada || 0), 0);
  const areaColhida = participantes.reduce((total, item) => total + Number(item.areaColhida || 0), 0);
  const pesoLiquido = selecionado ? Number(selecionado.peso_liquido_total_kg) : 0;
  const sacas = selecionado ? Number(selecionado.quantidade_sacas) : 0;
  const produtividadeKg = areaColhida > 0 ? pesoLiquido / areaColhida : 0;
  const produtividadeSacas = areaColhida > 0 ? sacas / areaColhida : 0;
  const saldoConjunto = selecionado?.saldos_conjuntos.reduce((total, item) => total + Number(item.quantidade_kg), 0) || 0;

  function alternarPropriedade(propriedade: Propriedade) {
    setParticipantes((atuais) => {
      const existe = atuais.some((item) => item.propriedade === propriedade.id);
      if (existe) return atuais.filter((item) => item.propriedade !== propriedade.id);
      return [...atuais, {
        propriedade: propriedade.id,
        areaCadastrada: String(propriedade.area_hectares || ""),
        areaColhida: String(propriedade.area_hectares || ""),
        cadpro: "",
        talhoes: [],
        justificativaExcesso: "",
        quantidadeManual: "",
        unidadeManual: "kg",
      }];
    });
  }

  function atualizarParticipante(propriedade: number, campo: keyof ParticipanteDraft, valor: string | number[]) {
    setParticipantes((atuais) => atuais.map((item) => item.propriedade === propriedade ? { ...item, [campo]: valor } : item));
  }

  async function executar(acao: () => Promise<unknown>, mensagem: string, recarregarSelecionado = true) {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      await acao();
      setSuccess(mensagem);
      const dadosLotes = await listarLotesConjuntos({ ordering: "-data_inicio_colheita" });
      setLotes(dadosLotes);
      if (recarregarSelecionado && selecionado) setSelecionado(await obterLoteConjunto(selecionado.id));
    } catch (falha) {
      setError(mensagemErro(falha));
    } finally {
      setSaving(false);
    }
  }

  async function salvarRascunho(event: FormEvent) {
    event.preventDefault();
    if (participantes.length < 2) return setError("Selecione ao menos duas propriedades.");
    await executar(async () => {
      const novo = await criarLoteConjunto({
        descricao: basico.descricao,
        cultura: Number(basico.cultura),
        variedade: basico.variedade,
        safra: Number(basico.safra),
        data_inicio_colheita: basico.inicio,
        data_final_colheita: basico.fim || null,
        cadpro_responsavel: basico.cadproResponsavel ? Number(basico.cadproResponsavel) : null,
        local_armazenagem: Number(basico.local),
        modo_rateio: basico.modoRateio,
        observacoes: basico.observacoes,
        participantes: participantes.map((item) => {
          const propriedade = properties.find((registro) => registro.id === item.propriedade)!;
          const talhoes = cadastros.talhoes.filter((talhao) => item.talhoes.includes(talhao.id));
          return {
            propriedade: item.propriedade,
            cadpro: item.cadpro ? Number(item.cadpro) : null,
            area_cadastrada_ha: item.areaCadastrada,
            area_colhida_ha: item.areaColhida,
            justificativa_excesso_area: item.justificativaExcesso,
            talhoes: talhoes.map((talhao) => ({
              talhao: talhao.id,
              area_cadastrada_ha: String((talhao as TalhaoComArea).area_hectares || propriedade.area_hectares),
              area_colhida_ha: item.areaColhida,
            })),
          };
        }),
      });
      setSelecionado(novo);
      setEtapa(4);
    }, "Lote conjunto salvo como rascunho.", false);
  }

  async function salvarCarga(event: FormEvent) {
    event.preventDefault();
    if (!selecionado) return;
    await executar(() => adicionarCargaLote({
      lote: selecionado.id,
      data_hora: new Date().toISOString(),
      motorista: carga.motorista ? Number(carga.motorista) : null,
      veiculo_cavalo: carga.cavalo ? Number(carga.cavalo) : null,
      veiculo_carreta: carga.carreta ? Number(carga.carreta) : null,
      placa_cavalo_informada: carga.placaCavalo,
      placa_carreta_informada: carga.placaCarreta,
      transportadora: carga.transportadora ? Number(carga.transportadora) : null,
      origem: carga.origem,
      destino: carga.destino,
      peso_bruto_kg: carga.bruto,
      tara_kg: carga.tara || "0",
      peso_liquido_kg: carga.liquido,
      umidade_percentual: carga.umidade || "0",
      impureza_percentual: carga.impureza || "0",
      defeitos_percentual: carga.defeitos || "0",
      romaneio: carga.romaneio,
      numero_balanca: carga.balanca,
      nota_fiscal: carga.notaFiscal,
      local_armazenagem: selecionado.local_armazenagem,
      observacoes: carga.observacoes,
    }), "Carga adicionada e totais recalculados.");
  }

  async function aplicarRateioManual() {
    if (!selecionado) return;
    const itens = participantes.filter((item) => item.quantidadeManual).map((item) => ({
      participante: selecionado.participantes.find((registro) => registro.propriedade === item.propriedade)?.id || 0,
      cadpro: Number(item.cadpro),
      quantidade: item.quantidadeManual,
      unidade: item.unidadeManual,
    }));
    await executar(() => ratearLoteManual(selecionado.id, itens, justificativaRateio), "Rateio manual registrado com auditoria.");
  }

  async function abrirLote(lote: LoteConjunto) {
    setLoading(true);
    try {
      const completo = await obterLoteConjunto(lote.id);
      setSelecionado(completo);
      setParticipantes(completo.participantes.map((item) => ({
        propriedade: item.propriedade,
        areaCadastrada: item.area_cadastrada_ha,
        areaColhida: item.area_colhida_ha,
        cadpro: String(item.cadpro || ""),
        talhoes: item.talhoes.map((talhao) => talhao.talhao),
        justificativaExcesso: item.justificativa_excesso_area || "",
        quantidadeManual: item.quantidade_rateada_kg || "",
        unidadeManual: "kg",
      })));
      setEtapa(completo.status === "rascunho" ? 4 : 8);
    } catch (falha) {
      setError(mensagemErro(falha));
    } finally {
      setLoading(false);
    }
  }

  if (loading && lotes.length === 0) return <LoadingState label="Carregando lotes conjuntos..." />;
  if (error && lotes.length === 0 && cadastros.culturas.length === 0) return <ErrorState description={error} onRetry={() => void carregar()} />;

  return (
    <section className="joint-page">
      <PageHeader
        eyebrow="Gestão integrada da produção"
        title="Lotes conjuntos de produção"
        description="Produção de duas ou mais propriedades mantida como conjunta até existir rateio confiável e explicitamente confirmado."
        actions={<div className="joint-export-actions">{(["csv", "xlsx", "pdf"] as const).map((formato) => <button className="secundario" key={formato} type="button" onClick={() => void baixarRelatorioLotesConjuntos(formato)}>Exportar {formato.toUpperCase()}</button>)}</div>}
      />

      {error && <AlertCard title="Não foi possível concluir" tone="danger"><p>{error}</p></AlertCard>}
      {success && <AlertCard title="Operação concluída" tone="success"><p>{success}</p></AlertCard>}

      <nav className="joint-steps" aria-label="Etapas do lote conjunto">
        {etapas.map((rotulo, indice) => <button key={rotulo} type="button" className={etapa === indice ? "is-active" : "secundario"} onClick={() => setEtapa(indice)}><span>{indice + 1}</span>{rotulo}</button>)}
      </nav>

      <ResponsiveGrid className="stat-grid joint-summary">
        <StatCard label="Propriedades selecionadas" value={participantes.length} />
        <StatCard label="Área cadastrada" value={`${numero(areaCadastrada, 4)} ha`} />
        <StatCard label="Área efetivamente colhida" value={`${numero(areaColhida, 4)} ha`} tone="info" />
        <StatCard label="Produção total" value={`${numero(pesoLiquido, 3)} kg`} detail={`${numero(sacas, 3)} sacas`} />
        <StatCard label="Produtividade conjunta" value={`${numero(produtividadeKg, 2)} kg/ha`} detail={`${numero(produtividadeSacas, 2)} sc/ha`} />
        <StatCard label="Saldo conjunto" value={`${numero(saldoConjunto, 3)} kg`} tone={saldoConjunto > 0 ? "warning" : "success"} />
      </ResponsiveGrid>

      {!selecionado && (
        <PermissionGuard allowed={canManage} fallback={<AlertCard title="Acesso de consulta" tone="info"><p>Somente administradores e gestores podem criar lotes conjuntos.</p></AlertCard>}>
          <form onSubmit={salvarRascunho}>
            {etapa === 0 && <SectionCard title="Informações básicas"><div className="joint-form-grid"><Field label="Descrição" value={basico.descricao} onChange={(valor) => setBasico({ ...basico, descricao: valor })} /><Select label="Cultura" value={basico.cultura} onChange={(valor) => setBasico({ ...basico, cultura: valor })} options={cadastros.culturas.map((item) => [item.id, item.nome])} /><Field label="Variedade" value={basico.variedade} onChange={(valor) => setBasico({ ...basico, variedade: valor })} /><Select label="Safra" value={basico.safra} onChange={(valor) => setBasico({ ...basico, safra: valor })} options={cadastros.safras.map((item) => [item.id, item.nome])} /><Field label="Início da colheita" type="date" value={basico.inicio} onChange={(valor) => setBasico({ ...basico, inicio: valor })} /><Field label="Fim da colheita" type="date" value={basico.fim} onChange={(valor) => setBasico({ ...basico, fim: valor })} /></div></SectionCard>}
            {etapa === 1 && <SectionCard title="Seleção de propriedades" description="Somente propriedades autorizadas aparecem."><div className="joint-filters"><Field label="Buscar por nome" value={busca} onChange={setBusca} /><Field label="Município" value={municipio} onChange={setMunicipio} /><Field label="Produtor" value={produtor} onChange={setProdutor} /><Field label="CAD/PRO" value={filtroCadpro} onChange={setFiltroCadpro} /></div><div className="joint-property-grid">{propriedadesFiltradas.map((propriedade) => { const ativo = participantes.some((item) => item.propriedade === propriedade.id); return <button className={`joint-property-card ${ativo ? "is-selected" : ""}`} type="button" key={propriedade.id} onClick={() => alternarPropriedade(propriedade)}><strong>{propriedade.nome}</strong><span>{propriedade.municipio}/{propriedade.uf}</span><small>{propriedade.proprietario || "Produtor não informado"} · {propriedade.area_hectares} ha</small></button>; })}</div></SectionCard>}
            {etapa === 2 && <SectionCard title="Áreas efetivamente colhidas" description="A área cadastrada é apenas sugestão. Excesso exige administrador e justificativa."><ParticipantRows participantes={participantes} properties={properties} onChange={atualizarParticipante} mode="areas" /></SectionCard>}
            {etapa === 3 && <SectionCard title="CAD/PRO e talhões"><ParticipantRows participantes={participantes} properties={properties} cadastros={cadastros} onChange={atualizarParticipante} mode="cadpro" /><div className="joint-form-grid"><Select label="CAD/PRO responsável" value={basico.cadproResponsavel} onChange={(valor) => setBasico({ ...basico, cadproResponsavel: valor })} options={cadastros.cadpros.filter((item) => participantes.some((participante) => participante.propriedade === item.propriedade)).map((item) => [item.id, `${item.codigo} · ${item.titular}`])} optional /><Select label="Local de armazenagem" value={basico.local} onChange={(valor) => setBasico({ ...basico, local: valor })} options={cadastros.locais.map((item) => [item.id, item.nome])} /><Select label="Modo de apuração" value={basico.modoRateio} onChange={(valor) => setBasico({ ...basico, modoRateio: valor as MetodoRateio })} options={[["sem_rateio", "Conjunta sem rateio"], ["area", "Rateio automático pela área"], ["manual", "Rateio manual"]]} /></div><button disabled={saving || participantes.length < 2} type="submit">Salvar como rascunho</button></SectionCard>}
          </form>
        </PermissionGuard>
      )}

      {selecionado && etapa >= 4 && etapa <= 6 && (
        <PermissionGuard allowed={canOperate && ["rascunho", "conferencia"].includes(selecionado.status)} fallback={<AlertCard title="Cargas bloqueadas" tone="info"><p>O lote está confirmado ou seu perfil permite apenas consulta.</p></AlertCard>}>
          <SectionCard title="Adicionar carga e viagem" description={`Lote ${selecionado.codigo} · o total das cargas forma a produção do lote.`}>
            <form className="joint-form-grid" onSubmit={salvarCarga}>
              <Select label="Motorista" value={carga.motorista} onChange={(valor) => setCarga({ ...carga, motorista: valor })} options={cadastros.motoristas.map((item) => [item.id, item.nome])} optional />
              <Select label="Cavalo cadastrado" value={carga.cavalo} onChange={(valor) => setCarga({ ...carga, cavalo: valor })} options={cadastros.veiculos.filter((item) => item.tipo !== "carreta").map((item) => [item.id, item.placa])} optional />
              <Select label="Carreta cadastrada" value={carga.carreta} onChange={(valor) => setCarga({ ...carga, carreta: valor })} options={cadastros.veiculos.filter((item) => item.tipo === "carreta").map((item) => [item.id, item.placa])} optional />
              <Field label="Placa cavalo (legado)" value={carga.placaCavalo} onChange={(valor) => setCarga({ ...carga, placaCavalo: valor })} />
              <Field label="Placa carreta (legado)" value={carga.placaCarreta} onChange={(valor) => setCarga({ ...carga, placaCarreta: valor })} />
              <Select label="Transportadora" value={carga.transportadora} onChange={(valor) => setCarga({ ...carga, transportadora: valor })} options={cadastros.parceiros.map((item) => [item.id, item.nome])} optional />
              <Field label="Origem" value={carga.origem} onChange={(valor) => setCarga({ ...carga, origem: valor })} />
              <Field label="Destino" value={carga.destino} onChange={(valor) => setCarga({ ...carga, destino: valor })} />
              <Field label="Peso bruto (kg)" type="number" value={carga.bruto} onChange={(valor) => setCarga({ ...carga, bruto: valor })} required />
              <Field label="Tara (kg)" type="number" value={carga.tara} onChange={(valor) => setCarga({ ...carga, tara: valor })} />
              <Field label="Peso líquido (kg)" type="number" value={carga.liquido} onChange={(valor) => setCarga({ ...carga, liquido: valor })} required />
              <Field label="Umidade (%)" type="number" value={carga.umidade} onChange={(valor) => setCarga({ ...carga, umidade: valor })} />
              <Field label="Impureza (%)" type="number" value={carga.impureza} onChange={(valor) => setCarga({ ...carga, impureza: valor })} />
              <Field label="Defeitos (%)" type="number" value={carga.defeitos} onChange={(valor) => setCarga({ ...carga, defeitos: valor })} />
              <Field label="Romaneio" value={carga.romaneio} onChange={(valor) => setCarga({ ...carga, romaneio: valor })} />
              <Field label="Número da balança" value={carga.balanca} onChange={(valor) => setCarga({ ...carga, balanca: valor })} />
              <Field label="Nota fiscal" value={carga.notaFiscal} onChange={(valor) => setCarga({ ...carga, notaFiscal: valor })} />
              <button disabled={saving} type="submit">Adicionar carga</button>
            </form>
          </SectionCard>
        </PermissionGuard>
      )}

      {selecionado && etapa === 7 && <SectionCard title="Rateio opcional" description="O padrão é manter a produção conjunta. Nenhum valor individual é inventado."><AlertCard title="Saldo conjunto disponível" tone="info"><p>{numero(saldoConjunto, 3)} kg ainda não distribuídos.</p></AlertCard><div className="joint-rate-actions"><button disabled={!canManage || selecionado.status !== "confirmado" || saving} type="button" onClick={() => void executar(() => ratearLotePorArea(selecionado.id), "Rateio proporcional à área concluído.")}>Ratear pela área</button></div><ParticipantRows participantes={participantes} properties={properties} cadastros={cadastros} onChange={atualizarParticipante} mode="manual" /><label>Justificativa do rateio manual<textarea value={justificativaRateio} onChange={(event) => setJustificativaRateio(event.target.value)} /></label><button disabled={!canManage || selecionado.status !== "confirmado" || saving} type="button" onClick={() => void aplicarRateioManual()}>Confirmar rateio manual</button></SectionCard>}

      {selecionado && etapa >= 8 && <SectionCard title="Conferência e confirmação" description="Lotes confirmados ficam imutáveis; correções posteriores exigem ajuste ou estorno rastreável."><div className="joint-review"><p><strong>{selecionado.codigo}</strong> · {selecionado.cultura_nome} · {selecionado.safra_nome}</p><p>{selecionado.participantes.length} propriedades · {selecionado.quantidade_cargas} cargas · {numero(selecionado.area_total_colhida_ha, 4)} ha</p><p>{numero(selecionado.peso_liquido_total_kg, 3)} kg · {numero(selecionado.produtividade_kg_ha, 2)} kg/ha</p><Badge tone={selecionado.status === "confirmado" ? "success" : selecionado.status === "estornado" ? "danger" : "warning"}>{selecionado.status}</Badge></div>{selecionado.status === "rascunho" && <button disabled={!canManage || saving} type="button" onClick={() => void executar(() => colocarLoteEmConferencia(selecionado.id), "Lote enviado para conferência.")}>Enviar para conferência</button>}{["rascunho", "conferencia"].includes(selecionado.status) && <button disabled={!canManage || saving || selecionado.quantidade_cargas === 0} type="button" onClick={() => void executar(() => confirmarLoteConjunto(selecionado.id), "Lote confirmado e entrada de estoque registrada.")}>Confirmar lote</button>}</SectionCard>}

      <SectionCard title="Lotes cadastrados" description="A consulta respeita todas as propriedades participantes.">
        {lotes.length === 0 ? <EmptyState title="Nenhum lote conjunto cadastrado" /> : <DataTable rows={lotes} getRowKey={(item) => item.id} columns={[
          { key: "codigo", header: "Lote", render: (item) => <button className="link-button" type="button" onClick={() => void abrirLote(item)}><strong>{item.codigo}</strong><small>{item.descricao || "Sem descrição"}</small></button> },
          { key: "contexto", header: "Cultura / safra", render: (item) => `${item.cultura_nome} · ${item.safra_nome}` },
          { key: "propriedades", header: "Propriedades", render: (item) => item.participantes.map((registro) => registro.propriedade_nome).join(", ") },
          { key: "area", header: "Área colhida", align: "right", render: (item) => `${numero(item.area_total_colhida_ha, 4)} ha` },
          { key: "producao", header: "Produção", align: "right", render: (item) => `${numero(item.peso_liquido_total_kg, 3)} kg` },
          { key: "status", header: "Status", render: (item) => <Badge tone={item.status === "confirmado" || item.status === "encerrado" ? "success" : item.status === "estornado" ? "danger" : "warning"}>{item.status}</Badge> },
        ]} />}
      </SectionCard>
    </section>
  );
}

type TalhaoComArea = { id: number; nome: string; propriedade: number; safra: string; area_hectares?: string };

function ParticipantRows({ participantes, properties, cadastros = cadastrosVazios, onChange, mode }: { participantes: ParticipanteDraft[]; properties: Propriedade[]; cadastros?: CadastrosLoteConjunto; onChange: (propriedade: number, campo: keyof ParticipanteDraft, valor: string | number[]) => void; mode: "areas" | "cadpro" | "manual" }) {
  if (participantes.length === 0) return <EmptyState title="Selecione propriedades primeiro" />;
  return <div className="joint-participant-list">{participantes.map((item) => { const propriedade = properties.find((registro) => registro.id === item.propriedade)!; const cadpros = cadastros.cadpros.filter((cadpro) => cadpro.propriedade === item.propriedade); const talhoes = cadastros.talhoes.filter((talhao) => talhao.propriedade === item.propriedade); return <article key={item.propriedade} className="joint-participant-card"><div><strong>{propriedade.nome}</strong><small>{propriedade.municipio}/{propriedade.uf}</small></div>{mode === "areas" && <div className="joint-form-grid"><Field label="Área cadastrada (ha)" type="number" value={item.areaCadastrada} onChange={(valor) => onChange(item.propriedade, "areaCadastrada", valor)} /><Field label="Área colhida (ha)" type="number" value={item.areaColhida} onChange={(valor) => onChange(item.propriedade, "areaColhida", valor)} /><Field label="Justificativa de excesso" value={item.justificativaExcesso} onChange={(valor) => onChange(item.propriedade, "justificativaExcesso", valor)} /></div>}{mode === "cadpro" && <><Select label="CAD/PRO da propriedade" value={item.cadpro} onChange={(valor) => onChange(item.propriedade, "cadpro", valor)} options={cadpros.map((cadpro) => [cadpro.id, `${cadpro.codigo} · ${cadpro.titular}`])} optional /><div className="joint-talhao-list">{talhoes.map((talhao) => <label key={talhao.id}><input type="checkbox" checked={item.talhoes.includes(talhao.id)} onChange={() => onChange(item.propriedade, "talhoes", item.talhoes.includes(talhao.id) ? item.talhoes.filter((id) => id !== talhao.id) : [...item.talhoes, talhao.id])} />{talhao.nome}</label>)}</div></>}{mode === "manual" && <div className="joint-form-grid"><Select label="CAD/PRO" value={item.cadpro} onChange={(valor) => onChange(item.propriedade, "cadpro", valor)} options={cadpros.map((cadpro) => [cadpro.id, cadpro.codigo])} /><Field label="Quantidade" type="number" value={item.quantidadeManual} onChange={(valor) => onChange(item.propriedade, "quantidadeManual", valor)} /><Select label="Unidade" value={item.unidadeManual} onChange={(valor) => onChange(item.propriedade, "unidadeManual", valor)} options={[["kg", "Kg"], ["toneladas", "Toneladas"], ["sacas", "Sacas"]]} /></div>}</article>; })}</div>;
}

function Field({ label, value, onChange, type = "text", required = false }: { label: string; value: string; onChange: (value: string) => void; type?: string; required?: boolean }) {
  return <label>{label}<input type={type} step={type === "number" ? "0.001" : undefined} value={value} required={required} onChange={(event) => onChange(event.target.value)} /></label>;
}

function Select({ label, value, onChange, options, optional = false }: { label: string; value: string; onChange: (value: string) => void; options: Array<[string | number, string]>; optional?: boolean }) {
  return <label>{label}<select value={value} required={!optional} onChange={(event) => onChange(event.target.value)}>{optional && <option value="">Não informado</option>}{!optional && options.length === 0 && <option value="">Nenhuma opção disponível</option>}{options.map(([id, nome]) => <option key={String(id)} value={String(id)}>{nome}</option>)}</select></label>;
}
