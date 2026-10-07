import { autorizado } from "./AcoesContext";
import { useEffect, useState } from "react";
import { Pagina, UsuarioAtual } from "../api/usuarios";
import { AREAS_MODULOS, nomeModulo } from "./gruposModulos";

export default function NavegacaoModulos({ acesso, modulo, onSelecionar }: { acesso: UsuarioAtual | null; modulo: Pagina; onSelecionar: (id: Pagina) => void }) {
  const areas = AREAS_MODULOS.filter(area => area.modulos.some(id => autorizado(acesso, id, "consultar")) || (area.nome === "Gestão" && acesso?.is_staff));
  const areaAtual = AREAS_MODULOS.find(area => ["usuarios", "historico", "backup"].includes(modulo) ? area.nome === "Gestão" : area.modulos.some(id => id === modulo))?.nome;
  const [areaSelecionada, setAreaSelecionada] = useState(areaAtual);
  useEffect(() => { setAreaSelecionada(areaAtual); }, [areaAtual]);
  const area = areas.find(item => item.nome === areaSelecionada) ?? areas[0];
  return <nav className="navegacao-modulos navegacao-por-area" aria-label="Módulos agrícolas">
    <div className="navegacao-areas" aria-label="Áreas do sistema">
      {acesso && <button type="button" aria-current={modulo === "inicio" ? "page" : undefined} className={modulo === "inicio" ? "" : "secundario"} onClick={() => onSelecionar("inicio")}>Início</button>}
      {areas.map(item => <button type="button" key={item.nome} aria-pressed={area?.nome === item.nome} className={area?.nome === item.nome ? "" : "secundario"} onClick={() => setAreaSelecionada(item.nome)}>{item.nome}</button>)}
    </div>
    <div className="navegacao-itens" aria-label={area ? `Módulos de ${area.nome}` : "Nenhum módulo permitido"}>
      {area?.modulos.filter(id => autorizado(acesso, id, "consultar")).map(id => <button type="button" key={id} aria-current={modulo === id ? "page" : undefined} className={modulo === id ? "" : "secundario"} onClick={() => onSelecionar(id)}>{nomeModulo(id)}</button>)}
      {area?.nome === "Gestão" && acesso?.is_staff && <button type="button" aria-current={modulo === "usuarios" ? "page" : undefined} className={modulo === "usuarios" ? "" : "secundario"} onClick={() => onSelecionar("usuarios")}>Usuários</button>}
      {area?.nome === "Gestão" && acesso?.is_staff && <button type="button" aria-current={modulo === "historico" ? "page" : undefined} className={modulo === "historico" ? "" : "secundario"} onClick={() => onSelecionar("historico")}>Histórico de alterações</button>}
      {area?.nome === "Gestão" && acesso?.is_staff && <button type="button" aria-current={modulo === "backup" ? "page" : undefined} className={modulo === "backup" ? "" : "secundario"} onClick={() => onSelecionar("backup")}>Backup em Excel</button>}
    </div>
  </nav>;
}
