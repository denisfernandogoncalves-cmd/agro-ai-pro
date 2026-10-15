import { useState } from "react";
import axios from "axios";
import { api } from "../api/propriedades";
import { BotaoAcao } from "./AcoesContext";
import { useAlteracoesNaoSalvas } from "./AlteracoesNaoSalvas";

type Campo = { nome: string; rotulo: string; tipo?: "number" | "date" | "text"; nullable?: boolean; opcional?: boolean };
type Props = { base: string; dados: { id: number; versao_correcao?: string }; campos: Campo[]; atualizar: () => void; horimetro?: boolean; somenteCancelar?: boolean };

export default function CorrecaoHistorico({ base, dados, campos, atualizar, horimetro = false, somenteCancelar = false }: Props) {
  const [modo, setModo] = useState<"corrigir" | "cancelar" | null>(null);
  const [form, setForm] = useState<Record<string, string>>({});
  const [motivo, setMotivo] = useState("");
  const [leitura, setLeitura] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState("");
  const [versaoOriginal, setVersaoOriginal] = useState("");
  const [versaoMaquina, setVersaoMaquina] = useState<unknown>(null);
  const original = dados as unknown as Record<string, unknown>;
  const protecao = useAlteracoesNaoSalvas({ form, motivo, leitura }, "correção do histórico", modo ? `${base}:${dados.id}` : null);
  async function abrir(proximo: "corrigir" | "cancelar") {
    if (!(await protecao.confirmarDescarte())) return;
    const valores = Object.fromEntries(campos.map(c => [c.nome, String(original[c.nome] ?? "")]));
    const atual = String(original.horimetro_atual_maquina ?? "");
    setForm(valores); setMotivo(""); setLeitura(atual); setErro(""); setModo(proximo);
    setVersaoOriginal(dados.versao_correcao ?? ""); setVersaoMaquina(original.versao_maquina_original);
    protecao.marcarSalvo({ form: valores, motivo: "", leitura: atual });
  }
  function fechar() {
    setModo(null); setForm({}); setMotivo(""); setLeitura(""); protecao.marcarSalvo({ form: {}, motivo: "", leitura: "" });
  }
  async function salvar() {
    if (ocupado || !modo) return;
    setOcupado(true); setErro("");
    const payload = {
      motivo_correcao: motivo.trim(), versao_correcao_original: versaoOriginal,
      ...(modo === "corrigir" ? Object.fromEntries(campos.map(c => [c.nome, c.nullable && !form[c.nome] ? null : form[c.nome]])) : {}),
      ...(horimetro ? { horimetro_corrigido: leitura, versao_maquina_original: versaoMaquina } : {}),
    };
    try {
      if (modo === "corrigir") await api.patch(`${base}${dados.id}/corrigir/`, payload);
      else await api.delete(`${base}${dados.id}/cancelar-registro/`, { data: payload });
      fechar(); atualizar();
    } catch (e) {
      setErro(axios.isAxiosError(e) && e.response?.data ? Object.values(e.response.data).flat().join(" ") : "Não foi possível corrigir. Seus dados foram preservados.");
    } finally { setOcupado(false); }
  }
  return <div className="nao-imprimir correcao-historico">
    <div className="acoes">{!somenteCancelar && <BotaoAcao type="button" acao="editar" disabled={ocupado || !dados.versao_correcao} onClick={() => void abrir("corrigir")}>Corrigir</BotaoAcao>}<BotaoAcao type="button" acao="excluir" className="perigo" disabled={ocupado || !dados.versao_correcao} onClick={() => void abrir("cancelar")}>Cancelar registro</BotaoAcao></div>
    {modo && <div className="card formulario">
      <strong>{modo === "corrigir" ? "Corrigir" : "Cancelar"} registro #{dados.id}</strong>
      <p>O original e o motivo serão preservados na auditoria. Confira os efeitos antes de confirmar.</p>
      {erro && <p role="alert" className="erro">{erro}</p>}
      {modo === "corrigir" && campos.map(c => <label key={c.nome}>{c.rotulo}<input type={c.tipo ?? "text"} step={c.tipo === "number" ? "any" : undefined} required={!c.nullable && !c.opcional} value={form[c.nome] ?? ""} disabled={ocupado} onChange={e => setForm({ ...form, [c.nome]: e.target.value })} /></label>)}
      {horimetro && <label>Horímetro atual correto, confirmado (h)<input required min="0" type="number" step="0.1" value={leitura} disabled={ocupado} onChange={e => setLeitura(e.target.value)} /><small>Não pode ficar abaixo das demais leituras mantidas no histórico.</small></label>}
      <label>Motivo<textarea required maxLength={500} value={motivo} disabled={ocupado} onChange={e => setMotivo(e.target.value)} /></label>
      <div className="acoes"><BotaoAcao type="button" acao={modo === "corrigir" ? "editar" : "excluir"} disabled={ocupado || !motivo.trim() || (horimetro && !leitura.trim())} onClick={() => void salvar()}>Confirmar {modo === "corrigir" ? "correção" : "cancelamento"}</BotaoAcao><button type="button" className="secundario" disabled={ocupado} onClick={async () => { if (await protecao.confirmarDescarte()) fechar(); }}>Fechar</button></div>
    </div>}
  </div>;
}
