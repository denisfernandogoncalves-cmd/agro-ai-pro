import axios from "axios";
import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  ArmazemGraos,
  CargaColhida,
  CargaColhidaInput,
  carregarContextoCargas,
  criarCargaColhida,
  GrupoColheita,
} from "../../api/cargasColhidas";
import { Propriedade } from "../../api/propriedades";


function dataLocalISO() {
  const agora = new Date();
  const ano = agora.getFullYear();
  const mes = String(agora.getMonth() + 1).padStart(2, "0");
  const dia = String(agora.getDate()).padStart(2, "0");
  return `${ano}-${mes}-${dia}`;
}

const hoje = dataLocalISO();
const cargaVazia: CargaColhidaInput = {
  grupo_colheita: "",
  armazem: "",
  data_colheita: hoje,
  placa: "",
  peso_bruto_kg: "",
  umidade_percentual: "",
  impureza_percentual: "",
  defeitos_percentual: "",
  ph: "",
  destinado_semente: false,
  local_colheita: "",
  observacoes: "",
};

function mensagemErro(falha: unknown) {
  if (axios.isAxiosError(falha)) {
    const dados = falha.response?.data;
    if (typeof dados?.detail === "string") return dados.detail;
    if (dados && typeof dados === "object") {
      return Object.values(dados).flat(2).join(" ");
    }
  }
  return "Não foi possível concluir o registro da colheita.";
}

function numero(valor: string | number) {
  const convertido = Number(valor);
  return Number.isFinite(convertido) ? convertido : 0;
}

function resumoCalculado(carga: CargaColhidaInput, grupo?: GrupoColheita) {
  if (!grupo) return { percentual: 0, descontoKg: 0, liquido: 0, sacas: 0 };
  const bruto = numero(carga.peso_bruto_kg);
  const parcelas = [
    [carga.umidade_percentual, grupo.tolerancia_umidade_percentual, grupo.desconto_umidade_por_ponto],
    [carga.impureza_percentual, grupo.tolerancia_impureza_percentual, grupo.desconto_impureza_por_ponto],
    [carga.defeitos_percentual, grupo.tolerancia_defeitos_percentual, grupo.desconto_defeitos_por_ponto],
  ];
  const percentual = parcelas.reduce(
    (total, [medicao, tolerancia, taxa]) =>
      total + Math.max(0, numero(medicao) - numero(tolerancia)) * numero(taxa),
    0,
  );
  const descontoKg = bruto * percentual / 100;
  const liquido = Math.max(0, bruto - descontoKg);
  return { percentual, descontoKg, liquido, sacas: liquido / 60 };
}

type Props = { propriedades: Propriedade[] };

export default function CargasColhidasPage({ propriedades }: Props) {
  const [armazens, setArmazens] = useState<ArmazemGraos[]>([]);
  const [grupos, setGrupos] = useState<GrupoColheita[]>([]);
  const [cargas, setCargas] = useState<CargaColhida[]>([]);
  const [carga, setCarga] = useState<CargaColhidaInput>(cargaVazia);
  const [busca, setBusca] = useState("");
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function carregar() {
    setCarregando(true);
    setErro("");
    try {
      const dados = await carregarContextoCargas(propriedades);
      setArmazens(dados.armazens);
      setGrupos(dados.grupos);
      setCargas(dados.cargas);
    } catch (falha) {
      setErro(mensagemErro(falha));
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    void carregar();
  }, [propriedades]);

  const grupoSelecionado = grupos.find((item) => String(item.id) === carga.grupo_colheita);
  const armazensDisponiveis = armazens.filter(
    (item) => !grupoSelecionado || item.propriedade === grupoSelecionado.propriedade,
  );
  const calculo = useMemo(
    () => resumoCalculado(carga, grupoSelecionado),
    [carga, grupoSelecionado],
  );
  const cargasFiltradas = cargas.filter((item) => {
    const termo = busca.trim().toLowerCase();
    return !termo || [
      item.placa,
      item.propriedade_nome,
      item.grupo_colheita_nome,
      item.cad_pro_codigo,
      item.local_colheita,
    ].some((valor) => valor.toLowerCase().includes(termo));
  });

  async function salvarCarga(evento: FormEvent) {
    evento.preventDefault();
    setErro("");
    setSucesso("");
    try {
      const criada = await criarCargaColhida(carga);
      setCarga(cargaVazia);
      setSucesso(
        `Carga registrada: ${criada.peso_liquido_kg} kg líquidos (${criada.sacas_60kg} sacas).`,
      );
      await carregar();
    } catch (falha) {
      setErro(mensagemErro(falha));
    }
  }

  return (
    <section className="modulo-cargas">
      {erro && <p className="erro card" role="alert">{erro}</p>}
      {sucesso && <p className="sucesso card">{sucesso}</p>}

      <div className="cargas-cabecalho">
        <div>
          <span className="kicker">Produção recebida</span>
          <h2>Cargas colhidas</h2>
          <p>Registro manual com descontos auditáveis e crédito automático no saldo do CAD/PRO.</p>
        </div>
        <span className="kicker">Configuração disponível em Grupos de colheita</span>
      </div>

      <section className="grade cargas-grade">
        <form className="card formulario" onSubmit={salvarCarga}>
          <h3>Registrar carga manual</h3>
          <label>Grupo de colheita<select required value={carga.grupo_colheita} onChange={(e) => { const selecionado = grupos.find((item) => String(item.id) === e.target.value); setCarga({ ...carga, grupo_colheita: e.target.value, armazem: selecionado?.armazem_padrao ? String(selecionado.armazem_padrao) : "" }); }}><option value="">Selecione</option>{grupos.map((item) => <option key={item.id} value={item.id}>{item.nome} · {item.propriedade_nome} · {item.cultura} {item.safra}</option>)}</select></label>
          <label>Armazenagem<select required value={carga.armazem} onChange={(e) => setCarga({ ...carga, armazem: e.target.value })}><option value="">Selecione</option>{armazensDisponiveis.map((item) => <option key={item.id} value={item.id}>{item.nome} · ocupação {numero(item.ocupacao_kg).toLocaleString("pt-BR")} kg</option>)}</select></label>
          <div className="linha">
            <label>Data<input required type="date" value={carga.data_colheita} onChange={(e) => setCarga({ ...carga, data_colheita: e.target.value })} /></label>
            <label>Placa<input required maxLength={8} placeholder="ABC1D23" value={carga.placa} onChange={(e) => setCarga({ ...carga, placa: e.target.value.toUpperCase() })} /></label>
          </div>
          <label>Local de colheita<input placeholder="Talhão, gleba ou ponto de origem" value={carga.local_colheita} onChange={(e) => setCarga({ ...carga, local_colheita: e.target.value })} /></label>
          <label>Peso bruto (kg)<input required min="0.001" step="0.001" type="number" value={carga.peso_bruto_kg} onChange={(e) => setCarga({ ...carga, peso_bruto_kg: e.target.value })} /></label>
          <div className="linha">
            <label>Umidade (%)<input required min="0" max="100" step="0.01" type="number" value={carga.umidade_percentual} onChange={(e) => setCarga({ ...carga, umidade_percentual: e.target.value })} /></label>
            <label>Impureza (%)<input required min="0" max="100" step="0.01" type="number" value={carga.impureza_percentual} onChange={(e) => setCarga({ ...carga, impureza_percentual: e.target.value })} /></label>
            <label>Defeitos (%)<input required min="0" max="100" step="0.01" type="number" value={carga.defeitos_percentual} onChange={(e) => setCarga({ ...carga, defeitos_percentual: e.target.value })} /></label>
          </div>
          <div className="linha">
            <label>PH<input min="0" max="100" step="0.01" type="number" value={carga.ph} onChange={(e) => setCarga({ ...carga, ph: e.target.value })} /></label>
            <label className="opcao-checkbox"><input type="checkbox" checked={carga.destinado_semente} onChange={(e) => setCarga({ ...carga, destinado_semente: e.target.checked })} /> Destinada a semente</label>
          </div>
          <label>Observações<textarea value={carga.observacoes} onChange={(e) => setCarga({ ...carga, observacoes: e.target.value })} /></label>
          <div className="resumo-peso" aria-live="polite">
            <span>Desconto <strong>{calculo.percentual.toFixed(3)}%</strong></span>
            <span>Peso líquido <strong>{calculo.liquido.toLocaleString("pt-BR", { maximumFractionDigits: 3 })} kg</strong></span>
            <span>Conversão <strong>{calculo.sacas.toLocaleString("pt-BR", { maximumFractionDigits: 3 })} sacas</strong></span>
          </div>
          <button disabled={carregando || calculo.percentual >= 100} type="submit">Registrar e creditar saldo</button>
        </form>

        <section className="conteudo">
          <div className="painel-filtros">
            <input aria-label="Buscar cargas" placeholder="Buscar placa, propriedade, grupo, CAD/PRO ou local" value={busca} onChange={(e) => setBusca(e.target.value)} />
            <button type="button" onClick={() => void carregar()}>Atualizar</button>
          </div>
          <div className="lista cargas-lista">
            {cargasFiltradas.length === 0 ? <div className="card vazio">Nenhuma carga colhida registrada.</div> : cargasFiltradas.map((item) => (
              <article className="card carga-item" key={item.id}>
                <div className="carga-item-topo"><div><span className="kicker">{item.data_colheita} · {item.placa}</span><h3>{item.propriedade_nome}</h3><p>{item.grupo_colheita_nome} · CAD/PRO {item.cad_pro_codigo} · {item.armazem_nome}</p></div><strong>{numero(item.sacas_60kg).toLocaleString("pt-BR", { maximumFractionDigits: 3 })} sc</strong></div>
                <div className="carga-metricas"><span>Bruto <strong>{numero(item.peso_bruto_kg).toLocaleString("pt-BR")} kg</strong></span><span>Desconto <strong>{item.desconto_total_percentual}%</strong></span><span>Líquido <strong>{numero(item.peso_liquido_kg).toLocaleString("pt-BR")} kg</strong></span></div>
                <small>Umidade {item.umidade_percentual}% · Impureza {item.impureza_percentual}% · Defeitos {item.defeitos_percentual}%{item.ph ? ` · PH ${item.ph}` : ""}{item.destinado_semente ? " · Semente" : ""} · movimento #{item.movimentacao}</small>
              </article>
            ))}
          </div>
        </section>
      </section>
    </section>
  );
}
