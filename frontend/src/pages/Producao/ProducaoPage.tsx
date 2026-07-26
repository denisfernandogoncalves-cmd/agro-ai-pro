import axios from "axios";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  baixarRelatorioProducao,
  carregarCadastrosProducao,
  carregarPainelProducao,
  confirmarEmbarque,
  confirmarImportacao,
  confirmarRecebimento,
  criarContrato,
  criarEmbarque,
  criarRecebimento,
  enviarImportacao,
  type CadPro,
  type Comprador,
  type ContratoProducao,
  type CulturaProducao,
  type DashboardProducao,
  type EmbarqueProducao,
  type ImportacaoProducao,
  type LocalArmazenagem,
  type RecebimentoProducao,
  type SafraProducao,
  type SaldoGraos,
  type TalhaoResumo,
} from "../../api/producaoIntegrada";
import type { Propriedade } from "../../api/propriedades";
import {
  AlertCard,
  Badge,
  DataTable,
  EmptyState,
  ErrorState,
  FilterBar,
  LoadingState,
  PageHeader,
  PermissionGuard,
  ResponsiveGrid,
  SectionCard,
  StatCard,
} from "../../components/shared/ui";

import "./producao.css";


type Tab = "dashboard" | "recebimentos" | "estoque" | "contratos" | "embarques" | "importacao";
type Cadastros = {
  cadpros: CadPro[];
  culturas: CulturaProducao[];
  safras: SafraProducao[];
  locais: LocalArmazenagem[];
  compradores: Comprador[];
  talhoes: TalhaoResumo[];
};

type Painel = {
  dashboard: DashboardProducao;
  recebimentos: RecebimentoProducao[];
  saldos: SaldoGraos[];
  contratos: ContratoProducao[];
  embarques: EmbarqueProducao[];
  importacoes: ImportacaoProducao[];
};

const emptyCadastros: Cadastros = { cadpros: [], culturas: [], safras: [], locais: [], compradores: [], talhoes: [] };
const number = (value: string | number | null | undefined, digits = 2) => Number(value || 0).toLocaleString("pt-BR", { maximumFractionDigits: digits });
const currency = (value: string | number | null | undefined) => Number(value || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

function errorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    if (error.response?.status === 403) return "Seu perfil não permite executar esta ação.";
    if (error.response?.status === 404) return "O registro não foi encontrado ou não pertence ao seu escopo autorizado.";
    const data = error.response?.data;
    if (typeof data?.detail === "string") return data.detail;
    if (data && typeof data === "object") return Object.values(data).flat().join(" ");
  }
  return "Não foi possível concluir a operação.";
}

export default function ProducaoPage({
  properties,
  selectedProperty,
  safra,
}: {
  properties: Propriedade[];
  selectedProperty: Propriedade | null;
  safra: string;
}) {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [cadastros, setCadastros] = useState<Cadastros>(emptyCadastros);
  const [painel, setPainel] = useState<Painel | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [receipt, setReceipt] = useState({ cadpro: "", talhao: "", cultura: "", safra: "", local: "", romaneio: "", placa: "", bruto: "", tara: "", liquido: "", umidade: "", impureza: "", defeitos: "" });
  const [contract, setContract] = useState({ cadpro: "", cultura: "", safra: "", comprador: "", numero: "", data: new Date().toISOString().slice(0, 10), limite: "", quantidade: "", preco: "", tolerancia: "0" });
  const [shipment, setShipment] = useState({ cadpro: "", cultura: "", safra: "", local: "", comprador: "", contrato: "", romaneio: "", placa: "", destino: "", notaProdutor: "", notaEmpresa: "", quantidade: "", preco: "" });
  const [importType, setImportType] = useState<ImportacaoProducao["tipo"]>("recebimentos");
  const [importCadPro, setImportCadPro] = useState("");
  const [importFile, setImportFile] = useState<File | null>(null);

  const canOperate = selectedProperty?.pode_operar ?? properties.some((item) => item.pode_operar);
  const canManage = selectedProperty?.pode_editar ?? properties.some((item) => item.pode_editar);
  const selectedHarvestId = useMemo(
    () => String(cadastros.safras.find((item) => item.nome === safra)?.id ?? ""),
    [cadastros.safras, safra],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const registrations = await carregarCadastrosProducao(selectedProperty?.id);
      setCadastros(registrations);
      const harvestId = String(registrations.safras.find((item) => item.nome === safra)?.id ?? "");
      setPainel(await carregarPainelProducao(selectedProperty?.id, harvestId));
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setLoading(false);
    }
  }, [safra, selectedProperty?.id]);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    const cadpro = cadastros.cadpros[0]?.id ? String(cadastros.cadpros[0].id) : "";
    const cultura = cadastros.culturas[0]?.id ? String(cadastros.culturas[0].id) : "";
    const harvest = selectedHarvestId || (cadastros.safras[0]?.id ? String(cadastros.safras[0].id) : "");
    const local = cadastros.locais[0]?.id ? String(cadastros.locais[0].id) : "";
    setReceipt((current) => ({ ...current, cadpro: current.cadpro || cadpro, cultura: current.cultura || cultura, safra: current.safra || harvest, local: current.local || local }));
    setContract((current) => ({ ...current, cadpro: current.cadpro || cadpro, cultura: current.cultura || cultura, safra: current.safra || harvest }));
    setShipment((current) => ({ ...current, cadpro: current.cadpro || cadpro, cultura: current.cultura || cultura, safra: current.safra || harvest, local: current.local || local }));
    setImportCadPro((current) => current || cadpro);
  }, [cadastros, selectedHarvestId]);

  async function execute(action: () => Promise<unknown>, message: string) {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      await action();
      setSuccess(message);
      await load();
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setSaving(false);
    }
  }

  async function submitReceipt(event: FormEvent) {
    event.preventDefault();
    if (!selectedProperty) return setError("Selecione uma propriedade para registrar o recebimento.");
    await execute(
      () => criarRecebimento({
        propriedade: selectedProperty.id,
        cadpro: Number(receipt.cadpro),
        talhao: receipt.talhao ? Number(receipt.talhao) : null,
        cultura: Number(receipt.cultura),
        safra: Number(receipt.safra),
        local_armazenagem: Number(receipt.local),
        romaneio: receipt.romaneio,
        placa_informada: receipt.placa,
        peso_bruto_kg: receipt.bruto,
        tara_kg: receipt.tara || "0",
        peso_liquido_kg: receipt.liquido,
        umidade_percentual: receipt.umidade || "0",
        impureza_percentual: receipt.impureza || "0",
        defeitos_percentual: receipt.defeitos || "0",
      }),
      "Recebimento salvo como rascunho. Confirme após revisar os dados.",
    );
  }

  async function submitContract(event: FormEvent) {
    event.preventDefault();
    if (!selectedProperty) return setError("Selecione uma propriedade para cadastrar o contrato.");
    await execute(
      () => criarContrato({
        propriedade: selectedProperty.id,
        cadpro: Number(contract.cadpro),
        cultura: Number(contract.cultura),
        safra: Number(contract.safra),
        comprador: Number(contract.comprador),
        numero: contract.numero,
        data_contrato: contract.data,
        data_limite: contract.limite || null,
        quantidade_kg: contract.quantidade,
        preco_saca: contract.preco,
        tolerancia_percentual: contract.tolerancia || "0",
      }),
      "Contrato cadastrado.",
    );
  }

  async function submitShipment(event: FormEvent) {
    event.preventDefault();
    if (!selectedProperty) return setError("Selecione uma propriedade para registrar o embarque.");
    await execute(
      () => criarEmbarque({
        propriedade: selectedProperty.id,
        cadpro: Number(shipment.cadpro),
        cultura: Number(shipment.cultura),
        safra: Number(shipment.safra),
        local_armazenagem: Number(shipment.local),
        comprador: Number(shipment.comprador),
        contrato: shipment.contrato ? Number(shipment.contrato) : null,
        romaneio: shipment.romaneio,
        placa_informada: shipment.placa,
        destino: shipment.destino,
        nota_produtor: shipment.notaProdutor,
        nota_empresa: shipment.notaEmpresa,
        quantidade_kg: shipment.quantidade,
        preco_saca: shipment.preco,
      }),
      "Embarque salvo como rascunho. A baixa e o financeiro ocorrerão somente após confirmação.",
    );
  }

  async function submitImport(event: FormEvent) {
    event.preventDefault();
    if (!selectedProperty || !importFile) return setError("Selecione a propriedade, o CAD/PRO e a planilha.");
    await execute(
      () => enviarImportacao({ tipo: importType, propriedade: selectedProperty.id, cadpro: Number(importCadPro), arquivo: importFile }),
      "Planilha enviada para pré-validação. Revise a prévia antes de confirmar.",
    );
    setImportFile(null);
  }

  if (loading && !painel) return <LoadingState label="Carregando Gestão da Produção..." />;
  if (!painel && error) return <ErrorState description={error} onRetry={() => void load()} />;
  if (!painel) return <EmptyState title="Nenhum dado disponível" description="Cadastre a estrutura produtiva para iniciar." />;

  const tabs: Array<{ id: Tab; label: string }> = [
    { id: "dashboard", label: "Visão executiva" },
    { id: "recebimentos", label: "Recebimentos" },
    { id: "estoque", label: "Estoque de grãos" },
    { id: "contratos", label: "Contratos" },
    { id: "embarques", label: "Embarques" },
    { id: "importacao", label: "Importar planilhas" },
  ];

  return (
    <section className="production-page">
      <PageHeader
        eyebrow="Gestão integrada"
        title="Produção agrícola"
        description={`Recebimento, qualidade, estoque, contratos e comercialização${selectedProperty ? ` · ${selectedProperty.nome}` : " · propriedades autorizadas"}.`}
        actions={<button type="button" disabled={loading} onClick={() => void load()}>{loading ? "Atualizando..." : "Atualizar"}</button>}
      />

      {error && <AlertCard title="Não foi possível concluir" tone="danger"><p>{error}</p></AlertCard>}
      {success && <AlertCard title="Operação concluída" tone="success"><p>{success}</p></AlertCard>}

      <nav className="production-tabs" aria-label="Áreas da Gestão da Produção">
        {tabs.map((item) => <button key={item.id} type="button" className={tab === item.id ? "is-active" : "secundario"} onClick={() => setTab(item.id)}>{item.label}</button>)}
      </nav>

      {tab === "dashboard" && (
        <>
          <ResponsiveGrid className="stat-grid production-stat-grid">
            <StatCard label="Produção recebida" value={`${number(painel.dashboard.producao.peso_liquido_kg, 3)} kg`} detail={`${number(painel.dashboard.producao.sacas, 3)} sacas`} tone="success" />
            <StatCard label="Estoque disponível" value={`${number(painel.dashboard.estoque.disponivel_kg, 3)} kg`} detail={`${painel.dashboard.estoque.posicoes} posições`} />
            <StatCard label="Cargas" value={painel.dashboard.producao.cargas} />
            <StatCard label="Embarques" value={painel.dashboard.embarques.total} detail={`${number(painel.dashboard.embarques.quantidade_kg, 3)} kg`} />
            <StatCard label="Receita de embarques" value={currency(painel.dashboard.embarques.valor_total)} tone="info" />
            <StatCard label="Contratos abertos" value={painel.dashboard.contratos.abertos} />
            {painel.dashboard.qualidade.umidade_media !== null && <StatCard label="Umidade média" value={`${number(painel.dashboard.qualidade.umidade_media, 3)}%`} />}
            {painel.dashboard.qualidade.impureza_media !== null && <StatCard label="Impureza média" value={`${number(painel.dashboard.qualidade.impureza_media, 3)}%`} />}
          </ResponsiveGrid>
          <div className="production-columns">
            <SectionCard title="Produção por CAD/PRO" description="Somente cargas confirmadas.">
              <DataTable rows={painel.dashboard.por_cadpro} getRowKey={(row) => row.cadpro_id} columns={[
                { key: "cadpro", header: "CAD/PRO", render: (row) => row.cadpro__codigo },
                { key: "kg", header: "Kg", align: "right", render: (row) => number(row.peso_kg, 3) },
                { key: "sacas", header: "Sacas", align: "right", render: (row) => number(row.sacas, 3) },
              ]} />
            </SectionCard>
            <SectionCard title="Relatórios" description="Arquivos gerados localmente pelo backend.">
              <div className="production-export-actions">
                {(["csv", "xlsx", "pdf"] as const).map((format) => <button key={format} className="secundario" type="button" onClick={() => void baixarRelatorioProducao(format, selectedProperty?.id, selectedHarvestId)}>Exportar {format.toUpperCase()}</button>)}
              </div>
            </SectionCard>
          </div>
        </>
      )}

      {tab === "recebimentos" && (
        <div className="production-workspace">
          <PermissionGuard allowed={canOperate && Boolean(selectedProperty)} fallback={<AlertCard title="Consulta disponível" tone="info"><p>Seu perfil pode consultar recebimentos, mas não registrar novas cargas.</p></AlertCard>}>
            <SectionCard title="Novo recebimento" description="O estoque só é atualizado após confirmação.">
              <form className="production-form" onSubmit={submitReceipt}>
                <Select label="CAD/PRO" value={receipt.cadpro} onChange={(value) => setReceipt({ ...receipt, cadpro: value })} options={cadastros.cadpros.map((item) => [item.id, `${item.codigo} · ${item.titular}`])} />
                <Select label="Talhão" value={receipt.talhao} onChange={(value) => setReceipt({ ...receipt, talhao: value })} options={cadastros.talhoes.map((item) => [item.id, item.nome])} optional />
                <Select label="Cultura" value={receipt.cultura} onChange={(value) => setReceipt({ ...receipt, cultura: value })} options={cadastros.culturas.map((item) => [item.id, item.nome])} />
                <Select label="Safra" value={receipt.safra} onChange={(value) => setReceipt({ ...receipt, safra: value })} options={cadastros.safras.map((item) => [item.id, item.nome])} />
                <Select label="Local" value={receipt.local} onChange={(value) => setReceipt({ ...receipt, local: value })} options={cadastros.locais.map((item) => [item.id, item.nome])} />
                <Field label="Romaneio" value={receipt.romaneio} onChange={(value) => setReceipt({ ...receipt, romaneio: value })} />
                <Field label="Placa" value={receipt.placa} onChange={(value) => setReceipt({ ...receipt, placa: value })} />
                <Field label="Peso bruto (kg)" type="number" value={receipt.bruto} onChange={(value) => setReceipt({ ...receipt, bruto: value })} required />
                <Field label="Tara (kg)" type="number" value={receipt.tara} onChange={(value) => setReceipt({ ...receipt, tara: value })} />
                <Field label="Peso líquido (kg)" type="number" value={receipt.liquido} onChange={(value) => setReceipt({ ...receipt, liquido: value })} required />
                <Field label="Umidade (%)" type="number" value={receipt.umidade} onChange={(value) => setReceipt({ ...receipt, umidade: value })} />
                <Field label="Impureza (%)" type="number" value={receipt.impureza} onChange={(value) => setReceipt({ ...receipt, impureza: value })} />
                <Field label="Defeitos (%)" type="number" value={receipt.defeitos} onChange={(value) => setReceipt({ ...receipt, defeitos: value })} />
                <button disabled={saving} type="submit">Salvar rascunho</button>
              </form>
            </SectionCard>
          </PermissionGuard>
          <SectionCard title="Cargas recebidas" description="Confirme somente após revisar balança, qualidade e destino.">
            <DataTable rows={painel.recebimentos} getRowKey={(row) => row.id} columns={[
              { key: "data", header: "Data", render: (row) => new Date(row.data).toLocaleDateString("pt-BR") },
              { key: "origem", header: "Origem", render: (row) => <><strong>{row.cadpro_codigo}</strong><small>{row.talhao_nome || "Sem talhão"}</small></> },
              { key: "produto", header: "Cultura / safra", render: (row) => `${row.cultura_nome} · ${row.safra_nome}` },
              { key: "peso", header: "Peso líquido", align: "right", render: (row) => `${number(row.peso_liquido_kg, 3)} kg` },
              { key: "qualidade", header: "Qualidade", render: (row) => `U ${number(row.umidade_percentual, 2)}% · I ${number(row.impureza_percentual, 2)}%` },
              { key: "status", header: "Status", render: (row) => <Badge tone={row.status === "confirmado" ? "success" : row.status === "estornado" ? "danger" : "warning"}>{row.status}</Badge> },
              { key: "acoes", header: "", render: (row) => row.status === "rascunho" && canOperate ? <button disabled={saving} type="button" onClick={() => void execute(() => confirmarRecebimento(row.id), "Recebimento confirmado e estoque atualizado.")}>Confirmar</button> : null },
            ]} />
          </SectionCard>
        </div>
      )}

      {tab === "estoque" && (
        <SectionCard title="Posição de estoque de grãos" description="Saldo por propriedade, CAD/PRO, talhão, cultura, safra e local.">
          <FilterBar><span>{painel.saldos.length} posição(ões)</span></FilterBar>
          <DataTable rows={painel.saldos} getRowKey={(row) => row.id} columns={[
            { key: "cadpro", header: "CAD/PRO", render: (row) => row.cadpro_codigo },
            { key: "origem", header: "Talhão", render: (row) => row.talhao_nome || "Geral" },
            { key: "produto", header: "Cultura / safra", render: (row) => `${row.cultura_nome} · ${row.safra_nome}` },
            { key: "local", header: "Armazenagem", render: (row) => row.local_nome },
            { key: "kg", header: "Kg", align: "right", render: (row) => number(row.quantidade_kg, 3) },
            { key: "sacas", header: "Sacas", align: "right", render: (row) => number(row.quantidade_sacas, 3) },
          ]} />
        </SectionCard>
      )}

      {tab === "contratos" && (
        <div className="production-workspace">
          <PermissionGuard allowed={canManage && Boolean(selectedProperty)} fallback={<AlertCard title="Somente consulta" tone="info"><p>Contratos podem ser alterados apenas por administradores e gestores.</p></AlertCard>}>
            <SectionCard title="Novo contrato">
              <form className="production-form" onSubmit={submitContract}>
                <Select label="CAD/PRO" value={contract.cadpro} onChange={(value) => setContract({ ...contract, cadpro: value })} options={cadastros.cadpros.map((item) => [item.id, item.codigo])} />
                <Select label="Cultura" value={contract.cultura} onChange={(value) => setContract({ ...contract, cultura: value })} options={cadastros.culturas.map((item) => [item.id, item.nome])} />
                <Select label="Safra" value={contract.safra} onChange={(value) => setContract({ ...contract, safra: value })} options={cadastros.safras.map((item) => [item.id, item.nome])} />
                <Select label="Comprador" value={contract.comprador} onChange={(value) => setContract({ ...contract, comprador: value })} options={cadastros.compradores.map((item) => [item.id, item.nome])} />
                <Field label="Número" value={contract.numero} onChange={(value) => setContract({ ...contract, numero: value })} required />
                <Field label="Data" type="date" value={contract.data} onChange={(value) => setContract({ ...contract, data: value })} required />
                <Field label="Data limite" type="date" value={contract.limite} onChange={(value) => setContract({ ...contract, limite: value })} />
                <Field label="Quantidade (kg)" type="number" value={contract.quantidade} onChange={(value) => setContract({ ...contract, quantidade: value })} required />
                <Field label="Preço por saca" type="number" value={contract.preco} onChange={(value) => setContract({ ...contract, preco: value })} required />
                <Field label="Tolerância (%)" type="number" value={contract.tolerancia} onChange={(value) => setContract({ ...contract, tolerancia: value })} />
                <button disabled={saving} type="submit">Cadastrar contrato</button>
              </form>
            </SectionCard>
          </PermissionGuard>
          <SectionCard title="Contratos">
            <DataTable rows={painel.contratos} getRowKey={(row) => row.id} columns={[
              { key: "numero", header: "Contrato", render: (row) => <><strong>{row.numero}</strong><small>{row.comprador_nome}</small></> },
              { key: "contexto", header: "Contexto", render: (row) => `${row.cadpro_codigo} · ${row.cultura_nome} · ${row.safra_nome}` },
              { key: "quantidade", header: "Contratado", align: "right", render: (row) => `${number(row.quantidade_kg, 3)} kg` },
              { key: "saldo", header: "Saldo", align: "right", render: (row) => `${number(row.saldo_contrato_kg, 3)} kg` },
              { key: "preco", header: "Preço/sc", align: "right", render: (row) => currency(row.preco_saca) },
              { key: "status", header: "Status", render: (row) => <Badge tone={row.status === "aberto" ? "success" : "neutral"}>{row.status}</Badge> },
            ]} />
          </SectionCard>
        </div>
      )}

      {tab === "embarques" && (
        <div className="production-workspace">
          <PermissionGuard allowed={canOperate && Boolean(selectedProperty)} fallback={<AlertCard title="Somente consulta" tone="info"><p>Seu perfil não permite registrar embarques.</p></AlertCard>}>
            <SectionCard title="Novo embarque" description="Estoque e Financeiro são atualizados somente na confirmação.">
              <form className="production-form" onSubmit={submitShipment}>
                <Select label="CAD/PRO" value={shipment.cadpro} onChange={(value) => setShipment({ ...shipment, cadpro: value })} options={cadastros.cadpros.map((item) => [item.id, item.codigo])} />
                <Select label="Cultura" value={shipment.cultura} onChange={(value) => setShipment({ ...shipment, cultura: value })} options={cadastros.culturas.map((item) => [item.id, item.nome])} />
                <Select label="Safra" value={shipment.safra} onChange={(value) => setShipment({ ...shipment, safra: value })} options={cadastros.safras.map((item) => [item.id, item.nome])} />
                <Select label="Local" value={shipment.local} onChange={(value) => setShipment({ ...shipment, local: value })} options={cadastros.locais.map((item) => [item.id, item.nome])} />
                <Select label="Comprador" value={shipment.comprador} onChange={(value) => setShipment({ ...shipment, comprador: value })} options={cadastros.compradores.map((item) => [item.id, item.nome])} />
                <Select label="Contrato" value={shipment.contrato} onChange={(value) => setShipment({ ...shipment, contrato: value })} options={painel.contratos.filter((item) => item.status === "aberto").map((item) => [item.id, `${item.numero} · ${item.comprador_nome}`])} optional />
                <Field label="Romaneio" value={shipment.romaneio} onChange={(value) => setShipment({ ...shipment, romaneio: value })} required />
                <Field label="Placa" value={shipment.placa} onChange={(value) => setShipment({ ...shipment, placa: value })} />
                <Field label="Destino" value={shipment.destino} onChange={(value) => setShipment({ ...shipment, destino: value })} />
                <Field label="Nota do produtor" value={shipment.notaProdutor} onChange={(value) => setShipment({ ...shipment, notaProdutor: value })} />
                <Field label="Nota da empresa" value={shipment.notaEmpresa} onChange={(value) => setShipment({ ...shipment, notaEmpresa: value })} />
                <Field label="Quantidade (kg)" type="number" value={shipment.quantidade} onChange={(value) => setShipment({ ...shipment, quantidade: value })} required />
                <Field label="Preço por saca" type="number" value={shipment.preco} onChange={(value) => setShipment({ ...shipment, preco: value })} required />
                <button disabled={saving} type="submit">Salvar rascunho</button>
              </form>
            </SectionCard>
          </PermissionGuard>
          <SectionCard title="Embarques">
            <DataTable rows={painel.embarques} getRowKey={(row) => row.id} columns={[
              { key: "romaneio", header: "Romaneio", render: (row) => <><strong>{row.romaneio}</strong><small>{row.comprador_nome}</small></> },
              { key: "contexto", header: "Contexto", render: (row) => `${row.cadpro_codigo} · ${row.cultura_nome} · ${row.safra_nome}` },
              { key: "quantidade", header: "Quantidade", align: "right", render: (row) => `${number(row.quantidade_kg, 3)} kg` },
              { key: "valor", header: "Valor", align: "right", render: (row) => currency(row.valor_total) },
              { key: "status", header: "Status", render: (row) => <Badge tone={row.status === "confirmado" ? "success" : row.status === "estornado" ? "danger" : "warning"}>{row.status}</Badge> },
              { key: "acoes", header: "", render: (row) => row.status === "rascunho" && canOperate ? <button disabled={saving} type="button" onClick={() => void execute(() => confirmarEmbarque(row.id), "Embarque confirmado, estoque baixado e receita criada.")}>Confirmar</button> : null },
            ]} />
          </SectionCard>
        </div>
      )}

      {tab === "importacao" && (
        <div className="production-workspace">
          <PermissionGuard allowed={canManage && Boolean(selectedProperty)} fallback={<AlertCard title="Importação restrita" tone="info"><p>Somente administradores e gestores podem importar planilhas.</p></AlertCard>}>
            <SectionCard title="Assistente de importação" description="CSV, XLSX ou XLSM até 10 MB. Nenhum registro é criado antes da confirmação.">
              <form className="production-form production-import-form" onSubmit={submitImport}>
                <Select label="Tipo" value={importType} onChange={(value) => setImportType(value as ImportacaoProducao["tipo"])} options={[["recebimentos", "Recebimentos"], ["movimentacoes", "Movimentações"], ["embarques", "Embarques"]]} />
                <Select label="CAD/PRO" value={importCadPro} onChange={setImportCadPro} options={cadastros.cadpros.map((item) => [item.id, item.codigo])} />
                <label>Planilha<input accept=".csv,.xlsx,.xlsm" type="file" onChange={(event) => setImportFile(event.target.files?.[0] ?? null)} required /></label>
                <button disabled={saving} type="submit">Enviar e pré-validar</button>
              </form>
            </SectionCard>
          </PermissionGuard>
          <SectionCard title="Importações">
            {painel.importacoes.length === 0 ? <EmptyState title="Nenhuma planilha enviada" /> : (
              <div className="production-import-list">
                {painel.importacoes.map((item) => (
                  <article key={item.id} className="production-import-card">
                    <div><strong>{item.nome_original}</strong><small>{item.tipo} · {item.total_linhas} linha(s)</small></div>
                    <Badge tone={item.status === "importada" ? "success" : item.inconsistencias.length ? "danger" : "warning"}>{item.status}</Badge>
                    {item.inconsistencias.length > 0 && <ul>{item.inconsistencias.slice(0, 5).map((issue, index) => <li key={`${issue.linha}-${index}`}>Linha {issue.linha}: {issue.mensagem}</li>)}</ul>}
                    {item.status === "validada" && canManage && <button disabled={saving} type="button" onClick={() => void execute(() => confirmarImportacao(item.id), "Importação confirmada.")}>Confirmar importação</button>}
                  </article>
                ))}
              </div>
            )}
          </SectionCard>
        </div>
      )}
    </section>
  );
}

function Field({ label, value, onChange, type = "text", required = false }: { label: string; value: string; onChange: (value: string) => void; type?: string; required?: boolean }) {
  return <label>{label}<input type={type} value={value} step={type === "number" ? "0.001" : undefined} required={required} onChange={(event) => onChange(event.target.value)} /></label>;
}

function Select({ label, value, onChange, options, optional = false }: { label: string; value: string; onChange: (value: string) => void; options: Array<[string | number, string]>; optional?: boolean }) {
  return (
    <label>{label}<select value={value} required={!optional} onChange={(event) => onChange(event.target.value)}>
      {optional && <option value="">Não informado</option>}
      {!optional && options.length === 0 && <option value="">Nenhuma opção disponível</option>}
      {options.map(([id, name]) => <option key={String(id)} value={String(id)}>{name}</option>)}
    </select></label>
  );
}
