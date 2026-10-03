import { BotaoAcao } from "../../components/AcoesContext";
import { useEffect, useRef, useState } from "react";
import axios from "axios";
import {
  confirmarImportacao, consultarLote, listarLinhas, listarLotes, loteElegivel, previewPlanilha,
  type LinhaImportacao, type LoteImportacao, type Pagina,
} from "../../api/importacoes";

function mensagemErro(erro: unknown): string {
  if (axios.isAxiosError(erro)) {
    const dados = erro.response?.data;
    const linhas = Array.isArray(dados?.linhas_rejeitadas)
      ? dados.linhas_rejeitadas.map((l: { planilha: string; linha_origem: number; erros: string[] }) =>
        `${l.planilha}!${l.linha_origem}: ${l.erros.join("; ")}`).join("\n") : "";
    return [dados?.detail || "Não foi possível concluir a operação.", linhas].filter(Boolean).join("\n");
  }
  return "Não foi possível concluir a operação. Verifique a conexão e tente novamente.";
}

export default function ImportacoesPage() {
  const [lotes, setLotes] = useState<Pagina<LoteImportacao> | null>(null);
  const [pagina, setPagina] = useState(1);
  const [lote, setLote] = useState<LoteImportacao | null>(null);
  const [linhas, setLinhas] = useState<Pagina<LinhaImportacao> | null>(null);
  const [paginaLinhas, setPaginaLinhas] = useState(1);
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [aceite, setAceite] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [revisao, setRevisao] = useState(0);
  const enviando = useRef(false);
  useEffect(() => {
    let atual = true;
    listarLotes(pagina).then(d => { if (atual) setLotes(d); })
      .catch(e => { if (atual) setErro(mensagemErro(e)); });
    return () => { atual = false; };
  }, [pagina, revisao]);
  useEffect(() => {
    let atual = true;
    setLinhas(null);
    if (lote) listarLinhas(lote.id, paginaLinhas).then(d => { if (atual) setLinhas(d); })
      .catch(e => { if (atual) setErro(mensagemErro(e)); });
    return () => { atual = false; };
  }, [lote, paginaLinhas]);

  function selecionar(item: LoteImportacao) {
    setLote(item); setPaginaLinhas(1); setAceite(false); setErro(""); setSucesso("");
  }
  async function enviar(confirmacao: boolean) {
    if (enviando.current || (confirmacao && (!lote || !aceite || !loteElegivel(lote))) || (!confirmacao && !arquivo)) return;
    enviando.current = true; setOcupado(true); setErro(""); setSucesso("");
    try {
      if (confirmacao && lote) {
        const nomeChave = `importacao-confirmacao-${lote.id}`;
        let chave = sessionStorage.getItem(nomeChave);
        if (!chave) { chave = crypto.randomUUID(); sessionStorage.setItem(nomeChave, chave); }
        try {
          const resultado = await confirmarImportacao(lote.id, chave);
          setSucesso(`Importação confirmada: ${resultado.total_movimentacoes_criadas} movimentações. ${resultado.replay_idempotente ? "Resultado recuperado sem duplicação." : ""}`);
        } catch (falha) {
          // Sem resposta conclusiva, manter a chave para recuperar o mesmo resultado.
          if (axios.isAxiosError(falha) && falha.response?.status === 409) sessionStorage.removeItem(nomeChave);
          throw falha;
        }
        setAceite(false);
        setLote(await consultarLote(lote.id));
      } else if (arquivo) {
        selecionar((await previewPlanilha(arquivo)).lote);
        setSucesso("Prévia criada. Revise as linhas antes de confirmar.");
      }
      setRevisao(v => v + 1);
    } catch (falha) { setErro(mensagemErro(falha)); }
    finally { enviando.current = false; setOcupado(false); }
  }

  return <section className="card">
    <h2>Importações de planilhas</h2>
    <p>Envie uma planilha XLSX de até 10 MB. A prévia permite revisar os dados; a confirmação registra as movimentações de grãos.</p>
    <label>Planilha<input type="file" accept=".xlsx" disabled={ocupado} onChange={e => setArquivo(e.target.files?.[0] || null)} /></label>
    <BotaoAcao acao="cadastrar" disabled={ocupado || !arquivo || arquivo.size > 10 * 1024 * 1024} onClick={() => void enviar(false)}>Gerar prévia</BotaoAcao>
    {arquivo && arquivo.size > 10 * 1024 * 1024 && <p className="erro" role="alert">O arquivo excede 10 MB.</p>}
    {ocupado && <p role="status">Processando…</p>}
    {erro && <p className="erro" role="alert" style={{ whiteSpace: "pre-wrap" }}>{erro}</p>}
    {sucesso && <p role="status">{sucesso}</p>}
    <h3>Lotes importados</h3>
    {!lotes ? <p>Carregando lotes…</p> : <>
      {!lotes.results.length && <p>Nenhuma planilha importada.</p>}
      <div className="tabela-responsiva"><table><thead><tr><th>Arquivo</th><th>Status</th><th>Linhas</th><th>Erros</th><th>Revisão</th></tr></thead>
        <tbody>{lotes.results.map(item => <tr key={item.id}><td>{item.arquivo_nome}</td><td>{item.status}</td><td>{item.total_linhas}</td><td>{item.total_erros}</td><td><button disabled={ocupado} onClick={() => selecionar(item)}>Revisar lote {item.id}</button></td></tr>)}</tbody></table></div>
      <button disabled={ocupado || !lotes.previous} onClick={() => setPagina(p => p - 1)}>Lotes anteriores</button>
      <button disabled={ocupado || !lotes.next} onClick={() => setPagina(p => p + 1)}>Próximos lotes</button>
    </>}
    {lote && <>
      <h3>Lote {lote.id} — {lote.arquivo_nome}</h3>
      <p>{lote.total_linhas} linhas · {lote.total_erros} erros · {lote.total_advertencias} advertências · {lote.status}</p>
      {!linhas ? <p>Carregando linhas…</p> : <>
        <div className="tabela-responsiva"><table><thead><tr><th>Origem</th><th>Propriedade / lote</th><th>Dados</th><th>Validação</th></tr></thead>
          <tbody>{linhas.results.map(linha => <tr key={linha.id}><td>{linha.planilha}!{linha.linha_origem}</td><td>{linha.propriedade_nome || "Sem associação"}<br />{linha.lote_graos_codigo || "Sem lote de grãos"}</td><td><details><summary>Ver dados da linha</summary><pre>{JSON.stringify(linha.dados_normalizados, null, 2)}</pre></details></td><td>{linha.status}<br />{[...linha.erros, ...linha.advertencias].join("; ")}</td></tr>)}</tbody></table></div>
        <p>Página {paginaLinhas} · {linhas.count} linhas</p>
        <button disabled={ocupado || !linhas.previous} onClick={() => setPaginaLinhas(p => p - 1)}>Linhas anteriores</button>
        <button disabled={ocupado || !linhas.next} onClick={() => setPaginaLinhas(p => p + 1)}>Próximas linhas</button>
      </>}
      {loteElegivel(lote) ? <>
        <label><input type="checkbox" checked={aceite} disabled={ocupado || !linhas} onChange={e => setAceite(e.target.checked)} /> Revisei o lote e autorizo registrar suas movimentações nos saldos.</label>
        <BotaoAcao acao="cadastrar" disabled={ocupado || !aceite || !linhas} onClick={() => void enviar(true)}>Confirmar importação</BotaoAcao>
      </> : <p>{lote.status === "confirmado" ? "Este lote já foi confirmado." : !lote.pode_confirmar ? "A confirmação exige permissão específica do usuário." : "Este lote possui pendências que impedem a confirmação."}</p>}
    </>}
  </section>;
}
