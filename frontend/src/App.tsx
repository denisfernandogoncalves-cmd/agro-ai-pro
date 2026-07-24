import { useEffect, useState } from "react";

import { buscarPropriedade } from "./api/propriedades";
import MapaPropriedade from "./components/MapaPropriedade";


export default function App() {

  const [propriedade, setPropriedade] = useState<any>(null);


  useEffect(() => {

    buscarPropriedade()
      .then((dados) => {

        console.log("Dados da propriedade:", dados);

        console.log(
          "Arquivo KML:",
          dados.arquivo_kml
        );

        setPropriedade(dados);

      })
      .catch((erro) => {

        console.error(
          "Erro ao buscar propriedade:",
          erro
        );

      });

  }, []);



  if (!propriedade) {

    return (
      <h2>
        Carregando propriedade...
      </h2>
    );

  }



  return (

    <div>

      <h1>
        {propriedade.nome}
      </h1>


      <MapaPropriedade

        latitude={
          Number(propriedade.latitude)
        }

        longitude={
          Number(propriedade.longitude)
        }

        nome={
          propriedade.nome
        }

        kml={
          propriedade.arquivo_kml
        }

      />


    </div>

  );

}