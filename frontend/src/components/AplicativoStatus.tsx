import { useEffect, useState } from "react";

interface EventoInstalacao extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export default function AplicativoStatus() {
  const [online, setOnline] = useState(typeof navigator === "undefined" ? true : navigator.onLine);
  const [instalacao, setInstalacao] = useState<EventoInstalacao | null>(null);
  useEffect(() => {
    const conectar = () => setOnline(true);
    const desconectar = () => setOnline(false);
    const preparar = (evento: Event) => { evento.preventDefault(); setInstalacao(evento as EventoInstalacao); };
    window.addEventListener("online", conectar);
    window.addEventListener("offline", desconectar);
    window.addEventListener("beforeinstallprompt", preparar);
    return () => {
      window.removeEventListener("online", conectar);
      window.removeEventListener("offline", desconectar);
      window.removeEventListener("beforeinstallprompt", preparar);
    };
  }, []);
  async function instalar() {
    if (!instalacao) return;
    await instalacao.prompt();
    await instalacao.userChoice;
    setInstalacao(null);
  }
  return <div className="status-aplicativo"><span className={online ? "online" : "offline"}>{online ? "Online" : "Offline · consultas dependem de conexão"}</span>{instalacao && <button className="secundario" onClick={() => void instalar()}>Instalar aplicativo</button>}</div>;
}
