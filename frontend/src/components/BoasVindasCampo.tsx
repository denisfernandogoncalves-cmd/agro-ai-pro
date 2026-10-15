import { useState } from "react";
import { Icon } from "./ModuloIcon";

const foto = "https://images.unsplash.com/photo-1557445796-184d83fc49b9";
export default function BoasVindasCampo() {
  const [indisponivel, setIndisponivel] = useState(false);
  return <figure className="boas-vindas-campo nao-imprimir">
    {!indisponivel && <img src={`${foto}?auto=format&fit=crop&w=720&q=70`} srcSet={`${foto}?auto=format&fit=crop&w=360&q=70 360w, ${foto}?auto=format&fit=crop&w=720&q=70 720w`} sizes="(max-width: 640px) 100vw, 300px" width="720" height="360" loading="lazy" decoding="async" alt="Paisagem ilustrativa de campos agrícolas vista do alto; não representa uma propriedade cadastrada" onError={() => setIndisponivel(true)} />}
    {indisponivel && <div className="foto-indisponivel"><Icon name="leaf" /><span>Fotografia ilustrativa indisponível</span></div>}
    <figcaption>Imagem ilustrativa · <a href="https://unsplash.com/photos/hdD1ZP1PzqI" target="_blank" rel="noreferrer">Ivan Bandura / Unsplash</a></figcaption>
  </figure>;
}
