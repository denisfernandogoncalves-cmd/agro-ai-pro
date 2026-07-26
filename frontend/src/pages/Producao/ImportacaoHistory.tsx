import { useCallback, useEffect, useState } from "react";

import { confirmarImportacao, type ImportacaoPlanilha } from "../../api/producaoIntegrada";
import { api } from "../../api/propriedades";
import type { Propriedade } from "../../api/propriedades";
import {
  AlertCard,
  Badge,
  DataTable,
  EmptyState,
  ErrorState,
  LoadingState,
  PermissionGuard,
  SectionCard,
} from "../../components/shared/ui";

function tone(status: ImportacaoPlanilha["status"]) {
  if (status === "importada") return "success" as const;
  if (status === "validada") return "info" as const;
  if (status === "erro") return "danger" as const;
  return "warning" as const;
}

export default function ImportacaoHistory({
  selectedProperty,
  canManage,
}: {
  selectedProperty: Propriedade | null;
  canManage: boolean;
}) {
  const [items, setItems] = useState<ImportacaoPlanilha[]>([]);
  const [selected, setSelected] = useState<ImportacaoPlanilha | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get<ImportacaoPlanilha[]>("/producao/importacoes/", {
        params: { propriedade: selectedProperty?.id || undefined },
      });
      setItems(response.data);
      setSelected((current) =>
        response.data.find((item) => item.id === current?.id) ?? response.data[0] ?? null
      );
    } catch {
      setError("Não foi possível carregar as importações analisadas.");
    } finally {
      setLoading(false);
    }
  }, [selectedProperty?.id]);

  useEffect(() => { void load(); }, [load]);

  async function confirm() {
    if (!selected) return;
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const updated = await confirmarImportacao(selected.id);
      setSuccess(`${updated.linhas_importadas} linha(s) importada(s) com sucesso.`);
      await load();
    } catch {
      setError("A confirmação foi bloqueada. Corrija as inconsistências e valide novamente.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <SectionCard
      title="Revisão das importações"
      description="Nenhuma linha é aplicada antes da confirmação explícita."
      actions={<button className="secundario" type="button" disabled={loading} onClick={() => void load()}>Atualizar histórico</button>}
    >
      {loading && items.length === 0 ? <LoadingState label="Carregando importações..." /> : null}
      {error && <ErrorState description={error} onRetry={() => void load()} />}
      {success && <AlertCard title="Importação concluída" tone="success"><p>{success}</p></AlertCard>}
      {!loading && items.length === 0 ? (
        <EmptyState title="Nenhuma planilha analisada" description="Envie um CSV ou XLSX no assistente de importação acima." />
      ) : (
        <div className="import-review-layout">
          <DataTable<ImportacaoPlanilha>
            rows={items}
            getRowKey={(item) => item.id}
            columns={[
              { key: "file", header: "Arquivo", render: (item) => <button className="link-button" type="button" onClick={() => setSelected(item)}>{item.nome_original}</button> },
              { key: "type", header: "Tipo", render: (item) => item.tipo },
              { key: "lines", header: "Linhas", align: "right", render: (item) => item.total_linhas },
              { key: "errors", header: "Inconsistências", align: "right", render: (item) => item.inconsistencias.length },
              { key: "status", header: "Status", render: (item) => <Badge tone={tone(item.status)}>{item.status}</Badge> },
            ]}
          />

          {selected && (
            <div className="import-preview">
              <div className="import-preview__header">
                <div>
                  <h3>{selected.nome_original}</h3>
                  <p>{selected.total_linhas} linha(s) analisada(s) · CAD/PRO {selected.cadpro_codigo || "a mapear"}</p>
                </div>
                <Badge tone={tone(selected.status)}>{selected.status}</Badge>
              </div>

              {selected.inconsistencias.length > 0 && (
                <AlertCard title="Inconsistências encontradas" tone="danger">
                  <ul>
                    {selected.inconsistencias.slice(0, 20).map((item, index) => (
                      <li key={`${item.linha}-${item.campo}-${index}`}>Linha {item.linha}{item.campo ? ` · ${item.campo}` : ""}: {item.mensagem}</li>
                    ))}
                  </ul>
                </AlertCard>
              )}

              <div className="import-mapping">
                <h4>Mapeamento detectado</h4>
                {Object.keys(selected.mapeamento).length ? (
                  <dl>{Object.entries(selected.mapeamento).map(([target, source]) => <div key={target}><dt>{target}</dt><dd>{source}</dd></div>)}</dl>
                ) : <p>Nenhum mapeamento confirmado.</p>}
              </div>

              <div className="import-preview__table">
                <h4>Pré-visualização</h4>
                {selected.previa.length ? (
                  <div className="data-table-wrap">
                    <table className="data-table">
                      <thead><tr>{Object.keys(selected.previa[0]).map((key) => <th key={key}>{key}</th>)}</tr></thead>
                      <tbody>{selected.previa.slice(0, 10).map((row, index) => <tr key={index}>{Object.keys(selected.previa[0]).map((key) => <td key={key}>{String(row[key] ?? "")}</td>)}</tr>)}</tbody>
                    </table>
                  </div>
                ) : <EmptyState title="Sem pré-visualização" />}
              </div>

              <PermissionGuard allowed={canManage}>
                {selected.status === "validada" && selected.inconsistencias.length === 0 && (
                  <button type="button" disabled={saving} onClick={() => void confirm()}>{saving ? "Importando..." : "Confirmar importação"}</button>
                )}
              </PermissionGuard>
            </div>
          )}
        </div>
      )}
    </SectionCard>
  );
}
