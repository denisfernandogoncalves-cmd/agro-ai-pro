import { useEffect, useState } from "react";
import { buscarPropriedade } from "./api/propriedades";
import MapaPropriedade from "./components/MapaPropriedade";

export default function App() {
  const [propriedade, setPropriedade] = useState<any>(null);

  useEffect(() => {
    buscarPropriedade().then(setPropriedade);
  }, []);

  if (!propriedade) return <h2>Carregando propriedade...</h2>;

  return (
    <div>
      <h1>{propriedade.nome}</h1>
      <MapaPropriedade
        latitude={Number(propriedade.latitude)}
        longitude={Number(propriedade.longitude)}
        nome={propriedade.nome}
      />
    </div>
  );
}
