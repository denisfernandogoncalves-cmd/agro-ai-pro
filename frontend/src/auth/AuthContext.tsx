import {
  createContext,
  PropsWithChildren,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  autenticar as autenticarNaApi,
  sair as sairDaApi,
} from "../api/propriedades";
import {
  estaAutenticado,
  obterGeracaoSessao,
  observarSessao,
} from "./sessionCoordinator";

type AuthContextValue = {
  autenticado: boolean;
  geracao: string;
  autenticar: (username: string, password: string) => Promise<void>;
  sair: () => Promise<boolean>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function handlePersistedPageShow(
  event: Pick<PageTransitionEvent, "persisted">,
  revalidate: () => void,
) {
  if (event.persisted) {
    revalidate();
  }
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [sessao, setSessao] = useState(() => ({
    autenticado: estaAutenticado(),
    geracao: obterGeracaoSessao(),
  }));

  useEffect(() => {
    const revalidarSessao = () => {
      setSessao({
        autenticado: estaAutenticado(),
        geracao: obterGeracaoSessao(),
      });
    };
    const deixarDeObservar = observarSessao(revalidarSessao);
    const observarPageShow = (event: PageTransitionEvent) =>
      handlePersistedPageShow(event, revalidarSessao);
    window.addEventListener("pageshow", observarPageShow);
    return () => {
      deixarDeObservar();
      window.removeEventListener("pageshow", observarPageShow);
    };
  }, []);

  const valor = useMemo<AuthContextValue>(() => ({
    autenticado: sessao.autenticado,
    geracao: sessao.geracao,
    autenticar: autenticarNaApi,
    sair: sairDaApi,
  }), [sessao]);

  return (
    <AuthContext.Provider value={valor}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const contexto = useContext(AuthContext);
  if (!contexto) {
    throw new Error("useAuth deve ser usado dentro de AuthProvider.");
  }
  return contexto;
}
