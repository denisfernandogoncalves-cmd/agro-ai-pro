import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import type { Propriedade } from "../../api/propriedades";
import {
  baixarRelatorio,
  carregarProducaoIntegrada,
  confirmarEmbarque,
  confirmarImportacao,
  confirmarRecebimento,
  criarContrato,
  criarEmbarque,
  criarRecebimento,
  enviarImportacao,
  type ContratoInput,
  type ContratoProducao,
  type EmbarqueInput,
  type EmbarqueProducao,
  type ImportacaoPlanilha,
  type RecebimentoInput,
  type RecebimentoProducao,
  type SaldoGraos,
} from "../../api/producaoIntegrada";
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


type TabId = "visao" | "recebimentos" | "estoque" | "contratos" | "embarques" | "importacao";
type PanelData = Awaited<ReturnType<typeof carregarProducaoIntegrada>>;

const number = (value: string | number | null | undefined, digits = 2) =>
  Number(value || 0).toLocaleString("pt-BR", { maximumFractionDigits: digits });
const currency = (value: string | number) =>
  Number(value || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const today = () => new Date().toISOString().slice(0, 10);

const emptyReceipt = (): Omit<RecebimentoInput, "propriedade" | "cadpro" | "cultura" | "safra" | "local_armazenagem"> => ({
  romaneio: "",
  peso_bruto_kg: "",
  tara_kg: "",
  peso_liquido_kg: "",
  umidade_percentual: "0",
  impureza_percentual: "0",
  defeitos_percentual: "0",
});

const emptyContract = (): Omit<ContratoInput, "propriedade" | "cadpro" | "cultura" | "safra" | "comprador"> => ({
  numero: "",
  data_contrato: today(),
  data_limite: null,
  quantidade_kg: "",
  preco_saca: "",
  tolerancia_percentual: "0",
});

const emptyShipment = (): Omit<EmbarqueInput, "propriedade" | "cadpro" | "cultura" | "safra" | "local_armazenagem" | "comprador"> => ({
  contrato: null,
  destino: "",
  romaneio: "",
  nota_produtor: "",
  nota_empresa: "",
  quantidade_kg: "",
  preco_saca: "",
});

function statusTone(status: string) {
  if (status === "confirmado" || status === "importada" || status === "concluido") return "success" as const;
  if (status === "estornado" || status === "cancelado" || status === "erro") return "danger" as const;
  if (status === "validada") return "info" as const;
  return "warning" as const;
}

export default function ProducaoPage({
  properties,
  selectedProperty,
  shellSafra,
  canOperate,
  canManage,
}: {
  properties: Propriedade[];
  selectedProperty: Propriedade | null;
  shellSafra: string;
  canOperate: boolean;
  canManage: boolean;
}) {
  const [tab, setTab] = useState<TabId>("visao");
  const [data, setData] = useState<PanelData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [harvestId, setHarvestId] = useState("");
  const [receipt, setReceipt] = useState(emptyReceipt());
  const [receiptContext, setReceiptContext] = useState({ cadpro: "", cultura: "", safra: "", local: "" });
  const [contract, setContract] = useState(emptyContract());
  const [contractContext, setContractContext] = useState({ cadpro: "", cultura: "", safra: "", comprador: "" });
  const [shipment, setShipment] = useState(emptyShipment());
  const [shipmentContext, setShipmentContext] = useState({ cadpro: "", cultura: "", safra: "", local: "", comprador: "" });
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importType, setImportType] = useState<ImportacaoPlanilha["tipo"]>("recebimentos");
  const [importCadpro, setImportCadpro] = useState("");
  const propertyId = selectedProperty ? String(selectedProperty.id) : "";

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await carregarProducaoIntegrada(propertyId, harvestId);
      setData(result);
      if (!harvestId && shellSafra) {
        const matched = result.safras.find((item) => item.nome === shellSafra);
        if (matched) setHarvestId(String(matched.id));
      }
    } catch {
      setError("Não foi possível carregar a Gestão Integrada da Produção.");
    } finally {
      setLoading(false);
    }
  }, [harvestId, propertyId, shellSafra]);

  useEffect(() => { void load(); }, [load]);

  const availableCadpros = useMemo(
    () => data?.cadpros.filter((item) => !selectedProperty || item.propriedade === selectedProperty.id) ?? [],
    [data?.cadpros, selectedProperty],
  );
  const availableLocations = useMemo(
    () => data?.locais.filter((item) => item.propriedade === null || !selectedProperty || item.propriedade === selectedProperty.id) ?? [],
    [data?.locais, selectedProperty],
  );

  async function act(action: () => Promise<unknown>, message: string) {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      await action();
      setSuccess(message);
      await load();
    } catch {
      setError("A operação não pôde ser concluída. Verifique os dados e suas permissões.");
    } finally {
      setSaving(false);
    }
  }

  async function submitReceipt(event: FormEvent) {
    event.preventDefault();
    if (!selectedProperty) { setError("Selecione uma propriedade no cabeçalho."); return; }
    await act(
      () => criarRecebimento({
        propriedade: selectedProperty.id,
        cadpro: Number(receiptContext.cadpro),
        cultura: Number(receiptContext.cultura),
        safra: Number(receiptContext.safra),
        local_armazenagem: Number(receiptContext.local),
        ...receipt,
      }),
      "Recebimento salvo como rascunho.",
    );
    setReceipt(emptyReceipt());
  }

  async function submitContract(event: FormEvent) {
    event.preventDefault();
    if (!selectedProperty) { setError("Selecione uma propriedade no cabeçalho."); return; }
    await act(
      () => criarContrato({
        propriedade: selectedProperty.id,
        cadpro: Number(contractContext.cadpro),
        cultura: Number(contractContext.cultura),
        safra: Number(contractContext.safra),
        comprador: Number(contractContext.comprador),
        ...contract,
      }),
      "Contrato cadastrado.",
    );
    setContract(emptyContract());
  }

  async function submitShipment(event: FormEvent) {
    event.preventDefault();
    if (!selectedProperty) { setError("Selecione uma propriedade no cabeçalho."); return; }
    await act(
      () => criarEmbarque({
        propriedade: selectedProperty.id,
        cadpro: Number(shipmentContext.cadpro),
        cultura: Number(shipmentContext.cultura),
        safra: Number(shipmentContext.safra),
        local_armazenagem: Number(shipmentContext.local),
        comprador: Number(shipmentContext.comprador),
        ...shipment,
      }),
      "Embarque salvo como rascunho.",
    );
    setShipment(emptyShipment());
  }

  async function submitImport(event: FormEvent) {
    event.preventDefault();
    if (!selectedProperty || !importFile) { setError("Selecione a propriedade e o arquivo."); return; }
    await act(
      () => enviarImportacao({
        arquivo: importFile,
        tipo: importType,
        propriedade: selectedProperty.id,
        cadpro: importCadpro ? Number(importCadpro) : undefined,
      }),
      "Planilha analisada. Revise a pré-visualização antes de confirmar.",
    );
    setImportFile(null);
  }

  if (loading && !data) return <LoadingState label="Consolidando produção, estoque e comercialização..." />;
  if (!data) return <ErrorState description={error} onRetry={() => void load()} />;

  const tabs: Array<{ id: TabId; label: string }> = [
    { id: "visao", label: "Visão geral" },
    { id: "recebimentos", label: "Recebimentos" },
    { id: "estoque", label: "Estoque" },
    { id: "contratos", label: "Contratos" },
    { id: "embarques", label: "Embarques" },
    { id: "importacao", label: "Importação" },
  ];

  return (
    <section className="production-page">
      <PageHeader
        eyebrow="Gestão integrada"
        title="Produção agrícola"
        description="Recebimentos, qualidade, estoque de grãos, contratos, embarques e receitas em um único fluxo auditável."
        actions={<button type="button" disabled={loading} onClick={() => void load()}>{loading ? "Atualizando..." : "Atualizar"}</button>}
      />

      {error && <AlertCard title="Atenção" tone="danger"><p>{error}</p></AlertCard>}
      {success && <AlertCard title="Operação concluída" tone="success"><p>{success}</p></AlertCard>}

      <FilterBar>
        <label>Safra
          <select value={harvestId} onChange={(event) => setHarvestId(event.target.value)}>
            <option value="">Todas</option>
            {data.safras.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}
          </select>
        </label>
        <div className="production-export-actions">
          <button className="secundario" type="button" onClick={() => void baixarRelatorio("csv", propertyId, harvestId)}>CSV</button>
          <button className="secundario" type="button" onClick={() => void baixarRelatorio("xlsx", propertyId, harvestId)}>Excel</button>
          <button className="secundario" type="button" onClick={() => void baixarRelatorio("pdf", propertyId, harvestId)}>PDF</button>
        </div>
      </FilterBar>

      <nav className="production-tabs" aria-label="Áreas da produção">
        {tabs.map((item) => <button key={item.id} type="button" className={tab === item.id ? "is-active" : "secundario"} onClick={() => setTab(item.id)}>{item.label}</button>)}
      </nav>

      {tab === "visao" && (
        <>
          <ResponsiveGrid className="stat-grid">
            <StatCard label="Produção total" value={`${number(data.dashboard.producao.peso_liquido_kg, 0)} kg`} detail={`${number(data.dashboard.producao.sacas)} sacas`} />
            <StatCard label="Cargas recebidas" value={data.dashboard.producao.cargas} />
            <StatCard label="Estoque disponível" value={`${number(data.dashboard.estoque.disponivel_kg, 0)} kg`} tone="success" />
            <StatCard label="Embarques" value={data.dashboard.embarques.total} detail={`${number(data.dashboard.embarques.quantidade_kg, 0)} kg`} />
            <StatCard label="Receita registrada" value={currency(data.dashboard.embarques.valor_total)} tone="info" />
            <StatCard label="Contratos abertos" value={data.dashboard.contratos.abertos} tone={data.dashboard.contratos.abertos ? "warning" : "neutral"} />
          </ResponsiveGrid>
          <ResponsiveGrid className="production-quality-grid">
            <StatCard label="Umidade média" value={data.dashboard.qualidade.umidade_media === null ? "—" : `${number(data.dashboard.qualidade.umidade_media)}%`} />
            <StatCard label="Impureza média" value={data.dashboard.qualidade.impureza_media === null ? "—" : `${number(data.dashboard.qualidade.impureza_media)}%`} />
            <StatCard label="Defeitos médios" value={data.dashboard.qualidade.defeitos_media === null ? "—" : `${number(data.dashboard.qualidade.defeitos_media)}%`} />
          </ResponsiveGrid>
          <ResponsiveGrid className="production-summary-grid">
            <SectionCard title="Produção por propriedade">
              {data.dashboard.por_propriedade.length ? data.dashboard.por_propriedade.map((item) => <div className="production-ranking" key={item.propriedade_id}><span>{item.propriedade__nome}</span><strong>{number(item.peso_kg, 0)} kg</strong></div>) : <EmptyState title="Sem produção confirmada" />}
            </SectionCard>
            <SectionCard title="Produção por CAD/PRO">
              {data.dashboard.por_cadpro.length ? data.dashboard.por_cadpro.map((item) => <div className="production-ranking" key={item.cadpro_id}><span>{item.cadpro__codigo}</span><strong>{number(item.peso_kg, 0)} kg</strong></div>) : <EmptyState title="Sem produção por CAD/PRO" />}
            </SectionCard>
            <SectionCard title="Produtividade por talhão">
              {data.dashboard.por_talhao.length ? data.dashboard.por_talhao.map((item) => <div className="production-ranking" key={item.talhao_id}><span>{item.talhao__nome}</span><strong>{number(item.peso_kg, 0)} kg</strong></div>) : <EmptyState title="Sem recebimentos vinculados a talhões" />}
            </SectionCard>
          </ResponsiveGrid>
        </>
      )}

      {tab === "recebimentos" && (
        <div className="production-workspace">
          <PermissionGuard allowed={canOperate} fallback={<AlertCard title="Consulta habilitada" tone="info"><p>Seu perfil pode consultar recebimentos, mas não registrar cargas.</p></AlertCard>}>
            <SectionCard title="Novo recebimento" description="O estoque somente será creditado após a confirmação.">
              <form className="production-form" onSubmit={submitReceipt}>
                <label>CAD/PRO<select required value={receiptContext.cadpro} onChange={(event) => setReceiptContext({ ...receiptContext, cadpro: event.target.value })}><option value="">Selecione</option>{availableCadpros.map((item) => <option key={item.id} value={item.id}>{item.codigo}</option>)}</select></label>
                <label>Cultura<select required value={receiptContext.cultura} onChange={(event) => setReceiptContext({ ...receiptContext, cultura: event.target.value })}><option value="">Selecione</option>{data.culturas.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
                <label>Safra<select required value={receiptContext.safra} onChange={(event) => setReceiptContext({ ...receiptContext, safra: event.target.value })}><option value="">Selecione</option>{data.safras.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
                <label>Armazenagem<select required value={receiptContext.local} onChange={(event) => setReceiptContext({ ...receiptContext, local: event.target.value })}><option value="">Selecione</option>{availableLocations.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
                <label>Romaneio<input value={receipt.romaneio} onChange={(event) => setReceipt({ ...receipt, romaneio: event.target.value })} /></label>
                <label>Peso bruto (kg)<input required type="number" min="0.001" step="0.001" value={receipt.peso_bruto_kg} onChange={(event) => setReceipt({ ...receipt, peso_bruto_kg: event.target.value })} /></label>
                <label>Tara (kg)<input required type="number" min="0" step="0.001" value={receipt.tara_kg} onChange={(event) => setReceipt({ ...receipt, tara_kg: event.target.value })} /></label>
                <label>Peso líquido (kg)<input required type="number" min="0.001" step="0.001" value={receipt.peso_liquido_kg} onChange={(event) => setReceipt({ ...receipt, peso_liquido_kg: event.target.value })} /></label>
                <label>Umidade (%)<input type="number" min="0" max="100" step="0.01" value={receipt.umidade_percentual} onChange={(event) => setReceipt({ ...receipt, umidade_percentual: event.target.value })} /></label>
                <label>Impureza (%)<input type="number" min="0" max="100" step="0.01" value={receipt.impureza_percentual} onChange={(event) => setReceipt({ ...receipt, impureza_percentual: event.target.value })} /></label>
                <label>Defeitos (%)<input type="number" min="0" max="100" step="0.01" value={receipt.defeitos_percentual} onChange={(event) => setReceipt({ ...receipt, defeitos_percentual: event.target.value })} /></label>
                <button disabled={saving} type="submit">Salvar rascunho</button>
              </form>
            </SectionCard>
          </PermissionGuard>
          <SectionCard title="Cargas registradas">
            <DataTable<RecebimentoProducao>
              rows={data.recebimentos}
              getRowKey={(item) => item.id}
              columns={[
                { key: "date", header: "Data", render: (item) => new Date(item.data).toLocaleDateString("pt-BR") },
                { key: "context", header: "Origem", render: (item) => <><strong>{item.cadpro_codigo}</strong><small>{item.cultura_nome} · {item.safra_nome}</small></> },
                { key: "weight", header: "Peso líquido", align: "right", render: (item) => `${number(item.peso_liquido_kg, 0)} kg` },
                { key: "quality", header: "Qualidade", render: (item) => `${number(item.umidade_percentual)}% U · ${number(item.impureza_percentual)}% I` },
                { key: "status", header: "Status", render: (item) => <Badge tone={statusTone(item.status)}>{item.status}</Badge> },
                { key: "actions", header: "Ações", render: (item) => item.status === "rascunho" && canOperate ? <button type="button" disabled={saving} onClick={() => void act(() => confirmarRecebimento(item.id), "Recebimento confirmado e estoque atualizado.")}>Confirmar</button> : null },
              ]}
            />
          </SectionCard>
        </div>
      )}

      {tab === "estoque" && (
        <SectionCard title="Estoque de grãos" description="Saldos por propriedade, CAD/PRO, cultura, safra, talhão e local de armazenagem.">
          <DataTable<SaldoGraos>
            rows={data.saldos}
            getRowKey={(item) => item.id}
            columns={[
              { key: "cadpro", header: "CAD/PRO", render: (item) => item.cadpro_codigo },
              { key: "crop", header: "Cultura / safra", render: (item) => `${item.cultura_nome} · ${item.safra_nome}` },
              { key: "field", header: "Talhão", render: (item) => item.talhao_nome || "Não informado" },
              { key: "location", header: "Armazenagem", render: (item) => item.local_nome },
              { key: "kg", header: "Quilogramas", align: "right", render: (item) => number(item.quantidade_kg, 0) },
              { key: "bags", header: "Sacas", align: "right", render: (item) => number(item.quantidade_sacas) },
            ]}
          />
        </SectionCard>
      )}

      {tab === "contratos" && (
        <div className="production-workspace">
          <PermissionGuard allowed={canManage} fallback={<AlertCard title="Consulta habilitada" tone="info"><p>Contratos são administrados por gestores e administradores.</p></AlertCard>}>
            <SectionCard title="Novo contrato">
              <form className="production-form" onSubmit={submitContract}>
                <label>CAD/PRO<select required value={contractContext.cadpro} onChange={(event) => setContractContext({ ...contractContext, cadpro: event.target.value })}><option value="">Selecione</option>{availableCadpros.map((item) => <option key={item.id} value={item.id}>{item.codigo}</option>)}</select></label>
                <label>Cultura<select required value={contractContext.cultura} onChange={(event) => setContractContext({ ...contractContext, cultura: event.target.value })}><option value="">Selecione</option>{data.culturas.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
                <label>Safra<select required value={contractContext.safra} onChange={(event) => setContractContext({ ...contractContext, safra: event.target.value })}><option value="">Selecione</option>{data.safras.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
                <label>Comprador<select required value={contractContext.comprador} onChange={(event) => setContractContext({ ...contractContext, comprador: event.target.value })}><option value="">Selecione</option>{data.parceiros.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
                <label>Número<input required value={contract.numero} onChange={(event) => setContract({ ...contract, numero: event.target.value })} /></label>
                <label>Data<input required type="date" value={contract.data_contrato} onChange={(event) => setContract({ ...contract, data_contrato: event.target.value })} /></label>
                <label>Limite<input type="date" value={contract.data_limite ?? ""} onChange={(event) => setContract({ ...contract, data_limite: event.target.value || null })} /></label>
                <label>Quantidade (kg)<input required type="number" min="0.001" step="0.001" value={contract.quantidade_kg} onChange={(event) => setContract({ ...contract, quantidade_kg: event.target.value })} /></label>
                <label>Preço por saca<input required type="number" min="0.01" step="0.01" value={contract.preco_saca} onChange={(event) => setContract({ ...contract, preco_saca: event.target.value })} /></label>
                <label>Tolerância (%)<input type="number" min="0" max="100" step="0.01" value={contract.tolerancia_percentual} onChange={(event) => setContract({ ...contract, tolerancia_percentual: event.target.value })} /></label>
                <button disabled={saving} type="submit">Cadastrar contrato</button>
              </form>
            </SectionCard>
          </PermissionGuard>
          <SectionCard title="Contratos">
            <DataTable<ContratoProducao>
              rows={data.contratos}
              getRowKey={(item) => item.id}
              columns={[
                { key: "number", header: "Contrato", render: (item) => <><strong>{item.numero}</strong><small>{item.comprador_nome}</small></> },
                { key: "context", header: "Contexto", render: (item) => `${item.cadpro_codigo} · ${item.cultura_nome} · ${item.safra_nome}` },
                { key: "quantity", header: "Contratado", align: "right", render: (item) => `${number(item.quantidade_kg, 0)} kg` },
                { key: "balance", header: "Saldo", align: "right", render: (item) => `${number(item.saldo_contrato_kg, 0)} kg` },
                { key: "price", header: "Preço/sc", align: "right", render: (item) => currency(item.preco_saca) },
                { key: "status", header: "Status", render: (item) => <Badge tone={statusTone(item.status)}>{item.status}</Badge> },
              ]}
            />
          </SectionCard>
        </div>
      )}

      {tab === "embarques" && (
        <div className="production-workspace">
          <PermissionGuard allowed={canOperate} fallback={<AlertCard title="Consulta habilitada" tone="info"><p>Seu perfil não permite registrar embarques.</p></AlertCard>}>
            <SectionCard title="Novo embarque" description="A confirmação baixa o estoque e cria a conta a receber.">
              <form className="production-form" onSubmit={submitShipment}>
                <label>CAD/PRO<select required value={shipmentContext.cadpro} onChange={(event) => setShipmentContext({ ...shipmentContext, cadpro: event.target.value })}><option value="">Selecione</option>{availableCadpros.map((item) => <option key={item.id} value={item.id}>{item.codigo}</option>)}</select></label>
                <label>Cultura<select required value={shipmentContext.cultura} onChange={(event) => setShipmentContext({ ...shipmentContext, cultura: event.target.value })}><option value="">Selecione</option>{data.culturas.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
                <label>Safra<select required value={shipmentContext.safra} onChange={(event) => setShipmentContext({ ...shipmentContext, safra: event.target.value })}><option value="">Selecione</option>{data.safras.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
                <label>Armazenagem<select required value={shipmentContext.local} onChange={(event) => setShipmentContext({ ...shipmentContext, local: event.target.value })}><option value="">Selecione</option>{availableLocations.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
                <label>Comprador<select required value={shipmentContext.comprador} onChange={(event) => setShipmentContext({ ...shipmentContext, comprador: event.target.value })}><option value="">Selecione</option>{data.parceiros.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
                <label>Contrato<select value={shipment.contrato ?? ""} onChange={(event) => setShipment({ ...shipment, contrato: event.target.value ? Number(event.target.value) : null })}><option value="">Sem contrato</option>{data.contratos.filter((item) => !shipmentContext.cadpro || item.cadpro === Number(shipmentContext.cadpro)).map((item) => <option key={item.id} value={item.id}>{item.numero}</option>)}</select></label>
                <label>Romaneio<input required value={shipment.romaneio} onChange={(event) => setShipment({ ...shipment, romaneio: event.target.value })} /></label>
                <label>Destino<input value={shipment.destino} onChange={(event) => setShipment({ ...shipment, destino: event.target.value })} /></label>
                <label>Nota do produtor<input value={shipment.nota_produtor} onChange={(event) => setShipment({ ...shipment, nota_produtor: event.target.value })} /></label>
                <label>Nota da empresa<input value={shipment.nota_empresa} onChange={(event) => setShipment({ ...shipment, nota_empresa: event.target.value })} /></label>
                <label>Quantidade (kg)<input required type="number" min="0.001" step="0.001" value={shipment.quantidade_kg} onChange={(event) => setShipment({ ...shipment, quantidade_kg: event.target.value })} /></label>
                <label>Preço por saca<input required type="number" min="0.01" step="0.01" value={shipment.preco_saca} onChange={(event) => setShipment({ ...shipment, preco_saca: event.target.value })} /></label>
                <button disabled={saving} type="submit">Salvar rascunho</button>
              </form>
            </SectionCard>
          </PermissionGuard>
          <SectionCard title="Embarques">
            <DataTable<EmbarqueProducao>
              rows={data.embarques}
              getRowKey={(item) => item.id}
              columns={[
                { key: "date", header: "Data", render: (item) => new Date(item.data).toLocaleDateString("pt-BR") },
                { key: "document", header: "Romaneio / comprador", render: (item) => <><strong>{item.romaneio}</strong><small>{item.comprador_nome}</small></> },
                { key: "context", header: "Contexto", render: (item) => `${item.cadpro_codigo} · ${item.cultura_nome}` },
                { key: "quantity", header: "Quantidade", align: "right", render: (item) => `${number(item.quantidade_kg, 0)} kg` },
                { key: "value", header: "Valor", align: "right", render: (item) => currency(item.valor_total) },
                { key: "status", header: "Status", render: (item) => <Badge tone={statusTone(item.status)}>{item.status}</Badge> },
                { key: "actions", header: "Ações", render: (item) => item.status === "rascunho" && canOperate ? <button type="button" disabled={saving} onClick={() => void act(() => confirmarEmbarque(item.id), "Embarque confirmado, estoque baixado e Financeiro atualizado.")}>Confirmar</button> : null },
              ]}
            />
          </SectionCard>
        </div>
      )}

      {tab === "importacao" && (
        <div className="production-workspace">
          <PermissionGuard allowed={canManage} fallback={<AlertCard title="Acesso restrito" tone="info"><p>A importação de dados legados exige perfil gestor ou administrador.</p></AlertCard>}>
            <SectionCard title="Assistente de importação" description="Detecta colunas, apresenta prévia e somente importa após confirmação.">
              <form className="production-form production-form--import" onSubmit={submitImport}>
                <label>Tipo<select value={importType} onChange={(event) => setImportType(event.target.value as ImportacaoPlanilha["tipo"])}><option value="recebimentos">Recebimentos</option><option value="movimentacoes">Movimentações</option><option value="embarques">Embarques</option></select></label>
                <label>CAD/PRO padrão<select value={importCadpro} onChange={(event) => setImportCadpro(event.target.value)}><option value="">Identificar na planilha</option>{availableCadpros.map((item) => <option key={item.id} value={item.id}>{item.codigo}</option>)}</select></label>
                <label>Arquivo CSV/XLSX<input required accept=".csv,.xlsx,.xlsm" type="file" onChange={(event) => setImportFile(event.target.files?.[0] ?? null)} /></label>
                <button disabled={saving || !importFile} type="submit">Analisar planilha</button>
              </form>
            </SectionCard>
          </PermissionGuard>
          <SectionCard title="Importações analisadas">
            {data && (
              <EmptyState title="Histórico sob demanda" description="As importações aparecem após o envio. Atualize esta tela para acompanhar validações e confirmação." />
            )}
          </SectionCard>
        </div>
      )}
    </section>
  );
}
