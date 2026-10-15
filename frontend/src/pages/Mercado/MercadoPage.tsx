import QuadroCBOT from "../../components/QuadroCBOT";
import { formatarData, formatarDataHora, idadeDoDado } from "../../utils/datas";
import { useEffect, useMemo, useState } from "react";
import axios from "axios";

import {
  atualizarCornBelt,
  atualizarCotacoes,
  carregarPainelMercado,
  ClimaCornBelt,
  CotacaoMercado,
  NoticiaMercado,
  ProdutoMercado,
  ResumoMercado,
} from "../../api/mercado";
import GraficoMercado from "./GraficoMercado";


const produtos: { codigo: ProdutoMercado; nome: string }[] = [
  { codigo: "soja", nome: "Soja" },
  { codigo: "milho", nome: "Milho" },
  { codigo: "trigo", nome: "Trigo" },
  { codigo: "brent", nome: "Petróleo Brent" },
];

function mensagemErro(falha: unknown) {
  if (axios.isAxiosError(falha) && typeof falha.response?.data?.detail === "string") {
    return falha.response.data.detail;
  }
  return "Não foi possível atualizar o painel de mercado.";
}

export default function MercadoPage() {
  const [cotacoes, setCotacoes] = useState<CotacaoMercado[]>([]);
  const [resumos, setResumos] = useState<ResumoMercado[]>([]);
  const [clima, setClima] = useState<ClimaCornBelt[]>([]);
  const [noticias, setNoticias] = useState<NoticiaMercado[]>([]);
  const [produto, setProduto] = useState<ProdutoMercado>("soja");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");

  async function carregar() {
    setCarregando(true);
    setErro("");
    try {
      const dados = await carregarPainelMercado();
      setCotacoes(dados.cotacoes);
      setResumos(dados.resumos);
      setClima(dados.clima);
      setNoticias(dados.noticias);
    } catch (falha) {
      setErro(mensagemErro(falha));
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    void carregar();
  }, []);

  async function atualizar(tipo: "cotacoes" | "clima") {
    setCarregando(true);
    setErro("");
    try {
      if (tipo === "cotacoes") {
        await atualizarCotacoes();
      } else {
        await atualizarCornBelt();
      }
      await carregar();
    } catch (falha) {
      setErro(`${mensagemErro(falha)} Última tentativa nesta sessão: ${new Date().toLocaleString("pt-BR")}. Os dados exibidos permanecem na última consulta concluída.`);
      setCarregando(false);
    }
  }

  const historico = useMemo(
    () => cotacoes.filter((item) => item.produto === produto),
    [cotacoes, produto],
  );
  const climaPorRegiao = useMemo(() => {
    const grupos = new Map<string, ClimaCornBelt[]>();
    for (const item of clima) {
      grupos.set(item.regiao, [...(grupos.get(item.regiao) ?? []), item]);
    }
    return [...grupos.values()];
  }, [clima]);

  return (
    <section className="modulo-mercado">
      <section className="card mercado-controles">
        <div>
          <h2>Mercado agrícola</h2>
          <p>Referências dos futuros de Chicago em US$/bushel via Yahoo Finance / CBOT e dólar USD/BRL pelo Investing, indicadores mensais globais e previsões armazenadas do Corn Belt.</p>
        </div>
        <div className="acoes">
          <button disabled={carregando} onClick={() => void atualizar("cotacoes")}>
            Atualizar cotações
          </button>
          <button
            className="secundario"
            disabled={carregando}
            onClick={() => void atualizar("clima")}
          >
            Atualizar Corn Belt
          </button>
        </div>
      </section>

      {erro && <p className="erro card" role="alert">{erro}</p>}

      <section className="card"><h2>Chicago e dólar — referências gratuitas</h2><QuadroCBOT /></section>
      <h2>Indicadores mensais FRED/FMI</h2>
      <section className="resumos-mercado" aria-label="Resumo dos indicadores mensais FRED/FMI">
        {resumos.map((resumo) => {
          const registro = cotacoes.find(item => item.produto === resumo.produto && item.data === resumo.data);
          return (
          <article className="card" key={resumo.produto}>
            <span className="kicker">{resumo.produto_nome}</span>
            <h3>{Number(resumo.valor).toFixed(2)}</h3>
            <p>{resumo.unidade} · {formatarData(resumo.data)}</p>
            <p className={
              Number(resumo.variacao_percentual ?? 0) >= 0
                ? "variacao-positiva"
                : "variacao-negativa"
            }>
              {resumo.variacao_percentual ?? "—"}%
            </p>
            <small>{resumo.tendencia}</small>
            <p><small>Fonte: {registro?.fonte || "Não informada"} · Registro: {formatarDataHora(registro?.atualizado_em)} · {idadeDoDado(registro?.atualizado_em)}</small></p>
            {resumo.aviso && <p className="aviso">{resumo.aviso}</p>}
          </article>
        );})}
      </section>

      <section>
        <label className="seletor-produto">
          Histórico
          <select
            value={produto}
            onChange={(evento) => setProduto(evento.target.value as ProdutoMercado)}
          >
            {produtos.map((item) => (
              <option key={item.codigo} value={item.codigo}>{item.nome}</option>
            ))}
          </select>
        </label>
        <GraficoMercado cotacoes={historico} />
      </section>

      <section>
        <h2>Clima no Corn Belt</h2>
        <div className="corn-belt-grade">
          {climaPorRegiao.map((previsoes) => {
            const proxima = previsoes[0];
            const chuva = previsoes.reduce(
              (total, item) => total + Number(item.precipitacao_mm),
              0,
            );
            const alertas = previsoes.filter((item) => item.alerta);
            return (
              <article className="card" key={proxima.regiao}>
                <h3>{proxima.regiao_nome}</h3>
                <p><small>Fonte: {proxima.fonte} · Registro: {formatarDataHora(proxima.atualizado_em)} · {idadeDoDado(proxima.atualizado_em)}</small></p>
                <p>Período registrado: {formatarData(proxima.data)} a {formatarData(previsoes[previsoes.length-1].data)} · {previsoes.length} dia(s).</p>
                <p>Precipitação no período: <strong>{chuva.toFixed(1)} mm</strong></p>
                <p>
                  {proxima.temperatura_min} °C a {proxima.temperatura_max} °C no
                  primeiro dia
                </p>
                {alertas.length > 0 && (
                  <p className="alerta-clima">{alertas[0].alerta}</p>
                )}
              </article>
            );
          })}
        </div>
      </section>

      <section>
        <h2>Notícias cadastradas</h2>
        {noticias.length === 0 ? (
          <div className="card vazio">
            Nenhuma notícia ativa. Cadastre fontes verificadas na administração.
          </div>
        ) : (
          <div className="noticias-mercado">
            {noticias.map((noticia) => (
              <article className="card" key={noticia.id}>
                <span className="kicker">{noticia.fonte}</span>
                <h3>{noticia.titulo}</h3>
                <p>{noticia.resumo}</p>
                <a href={noticia.url} rel="noreferrer" target="_blank">
                  Abrir fonte
                </a>
              </article>
            ))}
          </div>
        )}
      </section>

      <p className="aviso-mercado card">
        Dados de referência para apoio gerencial. Não constituem recomendação
        financeira, de compra ou de venda.
      </p>
      <section className="card"><h2>Mercado físico e B3</h2><p className="executivo-nota">Comparativo indisponível: o sistema não possui um feed conectado de preços locais e contratos B3. As cotações CBOT, dólar, Brent e séries históricas acima mantêm suas fontes e unidades originais.</p></section>
    </section>
  );
}
