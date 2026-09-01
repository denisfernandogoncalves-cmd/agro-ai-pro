import { DadosEntrega } from "../../api/vendas";

type Props = { dados: DadosEntrega; alterar: (dados: DadosEntrega) => void; destinoPadrao?: string; destinoObrigatorio?: boolean };

export default function CamposTransporteVenda({ dados, alterar, destinoPadrao, destinoObrigatorio = false }: Props) {
  return <>
    <label>Destino<input required={destinoObrigatorio} maxLength={160} placeholder={destinoPadrao || "Empresa / destino da carga"} value={dados.destino} onChange={e => alterar({ ...dados, destino: e.target.value })} /></label>
    <div className="linha"><label>Placa<input maxLength={12} placeholder="ABC1D23" value={dados.placa} onChange={e => alterar({ ...dados, placa: e.target.value.toUpperCase() })} /></label><label>Motorista<input maxLength={160} value={dados.motorista} onChange={e => alterar({ ...dados, motorista: e.target.value })} /></label></div>
    <div className="linha"><label>Nº nota produtor<input maxLength={80} value={dados.nota_produtor} onChange={e => alterar({ ...dados, nota_produtor: e.target.value })} /></label><label>Nº nota empresa<input maxLength={80} value={dados.nota_empresa} onChange={e => alterar({ ...dados, nota_empresa: e.target.value })} /></label></div>
  </>;
}
