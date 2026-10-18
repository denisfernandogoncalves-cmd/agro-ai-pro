import { Pagina } from "../api/usuarios";
import { nomeModulo } from "./gruposModulos";

const identidade: Partial<Record<Pagina, [string, string]>> = {
  transportes: ["Transportes", "Fretes, despesas, salário e comissão por motorista e caminhão"],
  inicio: ["Painel Geral", "Visão completa do seu negócio, do campo ao mercado"],
  cargas: ["Produção e Colheita", "Da pesagem aos descontos: acompanhe cada carga colhida"],
  "producao-saldos": ["Estoque e CAD/PRO", "Saldos físicos, comprometidos e disponíveis com rastreabilidade"],
  cavaco: ["Cavaco", "Pesagem, pagamentos e romaneios individuais em duas vias"],
  estoque: ["Estoque", "Insumos, armazenagem e movimentações sob controle"],
  propriedades: ["Propriedades", "Fazendas, áreas e informações geográficas em um só lugar"],
  talhoes: ["Talhões", "Mapas, culturas e desempenho de cada área produtiva"],
  relatorios: ["Relatórios", "Transforme registros em análises e exportações completas"],
  insights: ["Assistente AGRO AI", "Análises explicáveis com evidências dos seus dados"],
  vendas: ["Vendas", "Contratos, entregas e reservas com segurança de estoque"],
  financeiro: ["Financeiro", "Compromissos, recebimentos e conferência financeira"],
  transferencias: ["Transferências", "Movimentações entre saldos com origem e destino auditáveis"],
  importacoes: ["Importações", "Revise e confira seus arquivos antes da confirmação"],
  maquinas: ["Máquinas", "Equipamentos, manutenção e custos da operação"],
  operacoes: ["Operações", "Planejamento e execução das atividades agrícolas"],
  usuarios: ["Usuários e permissões", "Administre acessos respeitando os controles do sistema"],
  historico: ["Histórico de alterações", "Rastreabilidade e auditoria dos registros"],
  backup: ["Backup em Excel", "Consulte e exporte os registros autorizados"],
};
export function tituloModulo(modulo: Pagina) { return identidade[modulo]?.[0] ?? nomeModulo(modulo as Parameters<typeof nomeModulo>[0]); }
export default function IdentidadeModulo({ modulo }: { modulo: Pagina }) {
  return <p className="cabecalho-panorama">{identidade[modulo]?.[1] ?? "Gestão integrada para uma operação agrícola eficiente"}</p>;
}
