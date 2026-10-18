import { useEffect, useState } from "react";
import { Caminhao, Motorista, listarCaminhoes, listarMotoristas } from "../api/transportes";

export default function SelecionarTransporte({ placa, motorista, alterar, disabled = false }: {
  placa: string; motorista: string; alterar: (dados: { placa: string; motorista: string }) => void; disabled?: boolean;
}) {
  const [caminhoes, setCaminhoes] = useState<Caminhao[]>([]);
  const [motoristas, setMotoristas] = useState<Motorista[]>([]);
  const [estado, setEstado] = useState("Carregando cadastros…");
  const [revisao, setRevisao] = useState(0);
  useEffect(() => {
    let ativo = true;
    setEstado("Carregando cadastros…");
    void Promise.all([listarCaminhoes(), listarMotoristas()]).then(([c, m]) => {
      if (ativo) { setCaminhoes(c.filter(i => i.ativo)); setMotoristas(m.filter(i => i.ativo)); setEstado(""); }
    }).catch(() => { if (ativo) setEstado("Não foi possível carregar os cadastros de transporte. Verifique seu acesso e tente atualizar."); });
    return () => { ativo = false; };
  }, [revisao]);
  return <div className="linha">
    <label>Placa do veículo<select value={placa} disabled={disabled || !!estado} onChange={e => alterar({ placa: e.target.value, motorista })}>
      <option value="">Sem placa</option>
      {placa && !caminhoes.some(c => c.placa === placa) && <option value={placa}>{placa} (registro atual)</option>}
      {caminhoes.map(c => <option key={c.id} value={c.placa}>{c.placa} · {c.veiculo}</option>)}
    </select></label>
    <label>Nome do motorista<select value={motorista} disabled={disabled || !!estado} onChange={e => alterar({ placa, motorista: e.target.value })}>
      <option value="">Selecione o motorista</option>
      {motorista && !motoristas.some(m => m.nome === motorista) && <option value={motorista}>{motorista} (registro atual)</option>}
      {motoristas.map(m => <option key={m.id} value={m.nome}>{m.apelido ? `${m.apelido} · ${m.nome}` : m.nome}</option>)}
    </select></label>
    <small>{estado || "Cadastre caminhões e motoristas em Transportes → Motoristas e caminhões. A escolha do motorista é independente da placa."}</small>
    <button type="button" className="secundario" disabled={disabled} onClick={() => setRevisao(r => r + 1)}>Atualizar placas e motoristas</button>
  </div>;
}
