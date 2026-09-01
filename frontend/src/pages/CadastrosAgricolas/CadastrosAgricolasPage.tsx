import { FormEvent, useCallback, useEffect, useState } from "react";
import axios from "axios";

import {
  ArmazemGraos,
  atualizarArmazemGraos,
  carregarCadastrosAgricolas,
  criarArmazemGraos,
  excluirArmazemGraos,
} from "../../api/cadastrosAgricolas";
import {
  atualizarFornecedor,
  criarFornecedor,
  excluirFornecedor,
  ParceiroFinanceiro,
} from "../../api/financeiro";
import {
  atualizarLocal,
  atualizarProduto,
  criarLocal,
  criarProduto,
  excluirLocal,
  excluirProduto,
  LocalEstoque,
  ProdutoEstoque,
} from "../../api/estoque";
import { Propriedade } from "../../api/propriedades";
import ContratosComerciais from "./ContratosComerciais";


const armazemVazio = { nome: "", capacidade_kg: "" };
const localVazio = { nome: "", propriedade: "", descricao: "" };
const produtoVazio = {
  nome: "",
  categoria: "insumo" as ProdutoEstoque["categoria"],
  unidade: "kg" as ProdutoEstoque["unidade"],
  fabricante: "",
  estoque_minimo: "0",
};
const fornecedorVazio = {
  nome: "",
  documento: "",
  email: "",
  telefone: "",
};

const nomesCategorias: Record<ProdutoEstoque["categoria"], string> = {
  insumo: "Insumo",
  herbicida: "Herbicida",
  fungicida: "Fungicida",
  fertilizante: "Fertilizante",
  semente: "Semente",
  outro: "Outro",
};

const nomesUnidades: Record<ProdutoEstoque["unidade"], string> = {
  kg: "Quilograma",
  l: "Litro",
  un: "Unidade",
  sc: "Saca",
  t: "Tonelada",
};

function mensagemErro(falha: unknown) {
  if (axios.isAxiosError(falha)) {
    const dados = falha.response?.data;
    if (typeof dados?.detail === "string") return dados.detail;
    if (dados && typeof dados === "object") {
      return Object.values(dados).flat().join(" ");
    }
  }
  return "Não foi possível concluir o cadastro agrícola.";
}

function numero(valor: string) {
  return Number(valor).toLocaleString("pt-BR", { maximumFractionDigits: 3 });
}

type Props = { propriedades: Propriedade[] };

export default function CadastrosAgricolasPage({ propriedades }: Props) {
  const [armazens, setArmazens] = useState<ArmazemGraos[]>([]);
  const [locais, setLocais] = useState<LocalEstoque[]>([]);
  const [produtos, setProdutos] = useState<ProdutoEstoque[]>([]);
  const [fornecedores, setFornecedores] = useState<ParceiroFinanceiro[]>([]);
  const [armazem, setArmazem] = useState(armazemVazio);
  const [local, setLocal] = useState(localVazio);
  const [produto, setProduto] = useState(produtoVazio);
  const [fornecedor, setFornecedor] = useState(fornecedorVazio);
  const [edicaoArmazem, setEdicaoArmazem] = useState<number | null>(null);
  const [edicaoLocal, setEdicaoLocal] = useState<number | null>(null);
  const [edicaoProduto, setEdicaoProduto] = useState<number | null>(null);
  const [edicaoFornecedor, setEdicaoFornecedor] = useState<number | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [processando, setProcessando] = useState("");
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro("");
    try {
      const dados = await carregarCadastrosAgricolas();
      setArmazens(dados.armazens);
      setLocais(dados.locais);
      setProdutos(dados.produtos);
      setFornecedores(dados.fornecedores);
      if (dados.falhas.length) {
        setErro(
          `Os demais cadastros foram carregados, mas houve falha em: ${dados.falhas.join(", ")}.`,
        );
      }
    } catch (falha) {
      setErro(mensagemErro(falha));
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  async function salvarCadastro(
    evento: FormEvent,
    tipo: string,
    mensagem: string,
    operacao: () => Promise<unknown>,
    limpar: () => void,
  ) {
    evento.preventDefault();
    setProcessando(tipo);
    setErro("");
    setSucesso("");
    try {
      await operacao();
      limpar();
      setSucesso(mensagem);
      await carregar();
    } catch (falha) {
      setErro(mensagemErro(falha));
    } finally {
      setProcessando("");
    }
  }

  async function excluirCadastro(
    tipo: string,
    nome: string,
    operacao: () => Promise<unknown>,
    cancelarEdicao: () => void,
  ) {
    if (!window.confirm(`Excluir ${nome}? Se houver histórico vinculado, o cadastro será desativado.`)) return;
    setProcessando(tipo);
    setErro("");
    setSucesso("");
    try {
      await operacao();
      cancelarEdicao();
      setSucesso(`${nome} excluído ou desativado com segurança.`);
      await carregar();
    } catch (falha) {
      setErro(mensagemErro(falha));
    } finally {
      setProcessando("");
    }
  }

  return (
    <section className="modulo-estoque">
      <div className="cargas-cabecalho">
        <div>
          <span className="kicker">Cadastros centrais</span>
          <h2>Cadastros agrícolas</h2>
          <p>Inclua armazenagens, produtos e fornecedores antes de utilizá-los nas operações.</p>
        </div>
        <span className="kicker">Silos e depósitos permanecem separados</span>
      </div>

      {erro && <p className="erro card" role="alert">{erro}</p>}
      {sucesso && <p className="sucesso card" role="status">{sucesso}</p>}
      <section className="auxiliares-grade" aria-label="Formulários de cadastros agrícolas">
        <ContratosComerciais />
        <section className="card">
          <div><span className="kicker">Produção colhida</span><h3>Silos e armazéns de grãos</h3><p>Destinos independentes de propriedades para as cargas colhidas.</p></div>
          <form className="conteudo" onSubmit={(evento) => void salvarCadastro(
            evento,
            "armazem",
            edicaoArmazem ? "Armazenagem atualizada." : "Armazenagem de grãos cadastrada.",
            () => edicaoArmazem ? atualizarArmazemGraos(edicaoArmazem, armazem) : criarArmazemGraos(armazem),
            () => { setArmazem(armazemVazio); setEdicaoArmazem(null); },
          )}>
            <label>Nome<input required placeholder="Ex.: Silo principal" value={armazem.nome} onChange={(e) => setArmazem({ ...armazem, nome: e.target.value })} /></label>
            <label>Capacidade (kg)<input required min="0.001" step="0.001" type="number" value={armazem.capacidade_kg} onChange={(e) => setArmazem({ ...armazem, capacidade_kg: e.target.value })} /></label>
            <div className="acoes"><button disabled={carregando || Boolean(processando)} type="submit">{edicaoArmazem ? "Salvar armazenagem" : "Cadastrar armazenagem"}</button>{edicaoArmazem && <button className="secundario" type="button" onClick={() => { setArmazem(armazemVazio); setEdicaoArmazem(null); }}>Cancelar</button>}</div>
          </form>
          <div className="lista">
            {armazens.length ? armazens.map((item) => <article className="item" key={item.id}><div><h3>{item.nome}</h3><p>Capacidade {numero(item.capacidade_kg)} kg</p><small>Ocupação atual: {numero(item.ocupacao_kg)} kg</small><div className="acoes"><button className="secundario" type="button" onClick={() => { setEdicaoArmazem(item.id); setArmazem({ nome: item.nome, capacidade_kg: item.capacidade_kg }); }}>Editar</button><button className="perigo" type="button" onClick={() => void excluirCadastro("armazem", item.nome, () => excluirArmazemGraos(item.id), () => { setEdicaoArmazem(null); setArmazem(armazemVazio); })}>Excluir</button></div></div><span className="kicker">{item.ativo ? "Ativo" : "Inativo"}</span></article>) : <p className="vazio">{carregando ? "Carregando armazenagens..." : "Nenhuma armazenagem cadastrada."}</p>}
          </div>
        </section>

        <section className="card">
          <div><span className="kicker">Estoque de insumos</span><h3>Depósitos de insumos</h3><p>Locais usados para guardar produtos e controlar lotes.</p></div>
          <form className="conteudo" onSubmit={(evento) => void salvarCadastro(
            evento,
            "local",
            edicaoLocal ? "Depósito atualizado." : "Depósito de insumos cadastrado.",
            () => edicaoLocal ? atualizarLocal(edicaoLocal, local) : criarLocal(local),
            () => { setLocal(localVazio); setEdicaoLocal(null); },
          )}>
            <label>Nome<input required placeholder="Ex.: Galpão norte" value={local.nome} onChange={(e) => setLocal({ ...local, nome: e.target.value })} /></label>
            <label>Propriedade<select value={local.propriedade} onChange={(e) => setLocal({ ...local, propriedade: e.target.value })}><option value="">Sem propriedade específica</option>{propriedades.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label>
            <label>Descrição<input placeholder="Localização ou finalidade" value={local.descricao} onChange={(e) => setLocal({ ...local, descricao: e.target.value })} /></label>
            <div className="acoes"><button disabled={carregando || Boolean(processando)} type="submit">{edicaoLocal ? "Salvar depósito" : "Cadastrar depósito"}</button>{edicaoLocal && <button className="secundario" type="button" onClick={() => { setLocal(localVazio); setEdicaoLocal(null); }}>Cancelar</button>}</div>
          </form>
          <div className="lista">
            {locais.length ? locais.map((item) => <article className="item" key={item.id}><div><h3>{item.nome}</h3><p>{item.propriedade_nome || "Sem propriedade específica"}</p><small>{item.descricao || "Sem descrição"}</small><div className="acoes"><button className="secundario" type="button" onClick={() => { setEdicaoLocal(item.id); setLocal({ nome: item.nome, propriedade: item.propriedade ? String(item.propriedade) : "", descricao: item.descricao }); }}>Editar</button><button className="perigo" type="button" onClick={() => void excluirCadastro("local", item.nome, () => excluirLocal(item.id), () => { setEdicaoLocal(null); setLocal(localVazio); })}>Excluir</button></div></div><span className="kicker">{item.ativo ? "Ativo" : "Inativo"}</span></article>) : <p className="vazio">{carregando ? "Carregando depósitos..." : "Nenhum depósito cadastrado."}</p>}
          </div>
        </section>

        <section className="card">
          <div><span className="kicker">Catálogo de estoque</span><h3>Produtos agrícolas</h3><p>Insumos, defensivos, fertilizantes e sementes.</p></div>
          <form className="conteudo" onSubmit={(evento) => void salvarCadastro(
            evento,
            "produto",
            edicaoProduto ? "Produto atualizado." : "Produto agrícola cadastrado.",
            () => edicaoProduto ? atualizarProduto(edicaoProduto, produto) : criarProduto(produto),
            () => { setProduto(produtoVazio); setEdicaoProduto(null); },
          )}>
            <label>Nome<input required value={produto.nome} onChange={(e) => setProduto({ ...produto, nome: e.target.value })} /></label>
            <label>Categoria<select value={produto.categoria} onChange={(e) => setProduto({ ...produto, categoria: e.target.value as ProdutoEstoque["categoria"] })}>{Object.entries(nomesCategorias).map(([valor, nome]) => <option key={valor} value={valor}>{nome}</option>)}</select></label>
            <label>Unidade<select value={produto.unidade} onChange={(e) => setProduto({ ...produto, unidade: e.target.value as ProdutoEstoque["unidade"] })}>{Object.entries(nomesUnidades).map(([valor, nome]) => <option key={valor} value={valor}>{nome}</option>)}</select></label>
            <label>Fabricante<input value={produto.fabricante} onChange={(e) => setProduto({ ...produto, fabricante: e.target.value })} /></label>
            <label>Estoque mínimo<input min="0" step="0.001" type="number" value={produto.estoque_minimo} onChange={(e) => setProduto({ ...produto, estoque_minimo: e.target.value })} /></label>
            <div className="acoes"><button disabled={carregando || Boolean(processando)} type="submit">{edicaoProduto ? "Salvar produto" : "Cadastrar produto"}</button>{edicaoProduto && <button className="secundario" type="button" onClick={() => { setProduto(produtoVazio); setEdicaoProduto(null); }}>Cancelar</button>}</div>
          </form>
          <div className="lista">
            {produtos.length ? produtos.map((item) => <article className="item" key={item.id}><div><h3>{item.nome}</h3><p>{nomesCategorias[item.categoria]} · {nomesUnidades[item.unidade]}</p><small>{item.fabricante || "Fabricante não informado"} · mínimo {numero(item.estoque_minimo)}</small><div className="acoes"><button className="secundario" type="button" onClick={() => { setEdicaoProduto(item.id); setProduto({ nome: item.nome, categoria: item.categoria, unidade: item.unidade, fabricante: item.fabricante, estoque_minimo: item.estoque_minimo }); }}>Editar</button><button className="perigo" type="button" onClick={() => void excluirCadastro("produto", item.nome, () => excluirProduto(item.id), () => { setEdicaoProduto(null); setProduto(produtoVazio); })}>Excluir</button></div></div><span className="kicker">{item.ativo ? "Ativo" : "Inativo"}</span></article>) : <p className="vazio">{carregando ? "Carregando produtos..." : "Nenhum produto cadastrado."}</p>}
          </div>
        </section>

        <section className="card">
          <div><span className="kicker">Parceiros comerciais</span><h3>Fornecedores</h3><p>Fornecedores e parceiros que também atuam como clientes.</p></div>
          <form className="conteudo" onSubmit={(evento) => void salvarCadastro(
            evento,
            "fornecedor",
            edicaoFornecedor ? "Fornecedor atualizado." : "Fornecedor cadastrado.",
            () => edicaoFornecedor ? atualizarFornecedor(edicaoFornecedor, fornecedor) : criarFornecedor(fornecedor),
            () => { setFornecedor(fornecedorVazio); setEdicaoFornecedor(null); },
          )}>
            <label>Nome<input required value={fornecedor.nome} onChange={(e) => setFornecedor({ ...fornecedor, nome: e.target.value })} /></label>
            <label>CPF/CNPJ<input maxLength={20} value={fornecedor.documento} onChange={(e) => setFornecedor({ ...fornecedor, documento: e.target.value })} /></label>
            <label>Telefone<input maxLength={30} value={fornecedor.telefone} onChange={(e) => setFornecedor({ ...fornecedor, telefone: e.target.value })} /></label>
            <label>E-mail<input type="email" value={fornecedor.email} onChange={(e) => setFornecedor({ ...fornecedor, email: e.target.value })} /></label>
            <div className="acoes"><button disabled={carregando || Boolean(processando)} type="submit">{edicaoFornecedor ? "Salvar fornecedor" : "Cadastrar fornecedor"}</button>{edicaoFornecedor && <button className="secundario" type="button" onClick={() => { setFornecedor(fornecedorVazio); setEdicaoFornecedor(null); }}>Cancelar</button>}</div>
          </form>
          <div className="lista">
            {fornecedores.length ? fornecedores.map((item) => {
              const contato = [item.documento, item.telefone, item.email].filter(Boolean).join(" · ");
              return <article className="item" key={item.id}><div><h3>{item.nome}</h3><p>{item.tipo === "ambos" ? "Fornecedor e cliente" : "Fornecedor"}</p><small>{contato || "Sem contato informado"}</small><div className="acoes"><button className="secundario" type="button" onClick={() => { setEdicaoFornecedor(item.id); setFornecedor({ nome: item.nome, documento: item.documento || "", telefone: item.telefone, email: item.email }); }}>Editar</button><button className="perigo" type="button" onClick={() => void excluirCadastro("fornecedor", item.nome, () => excluirFornecedor(item.id), () => { setEdicaoFornecedor(null); setFornecedor(fornecedorVazio); })}>Excluir</button></div></div><span className="kicker">{item.ativo ? "Ativo" : "Inativo"}</span></article>;
            }) : <p className="vazio">{carregando ? "Carregando fornecedores..." : "Nenhum fornecedor cadastrado."}</p>}
          </div>
        </section>
      </section>
    </section>
  );
}
