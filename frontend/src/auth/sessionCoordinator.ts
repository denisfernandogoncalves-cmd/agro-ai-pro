const ACCESS_TOKEN_KEY = "agro-ai-pro.access-token";
const REFRESH_TOKEN_KEY = "agro-ai-pro.refresh-token";
const SESSION_GENERATION_KEY = "agro-ai-pro.session-generation";
const LOGOUT_TOMBSTONE_KEY = "agro-ai-pro.logout-tombstone";
const LOGOUT_TOMBSTONE_VERSION = 1;
const SESSION_CHANNEL = "agro-ai-pro.session";

type SessionListener = () => void;

type LogoutTombstone = {
  version: typeof LOGOUT_TOMBSTONE_VERSION;
  generation: string;
  createdAt: number;
};

export type SessionSnapshot = {
  generation: string;
  logoutActive: boolean;
  access: string | null;
  refresh: string | null;
};

const listeners = new Set<SessionListener>();
let channel: BroadcastChannel | null = null;

function storageDisponivel() {
  return typeof localStorage !== "undefined";
}

function lerGeracao() {
  if (!storageDisponivel()) {
    return "sem-storage";
  }
  return localStorage.getItem(SESSION_GENERATION_KEY) ?? "inicial";
}

function lerTombstone() {
  if (!storageDisponivel()) {
    return null;
  }
  const stored = localStorage.getItem(LOGOUT_TOMBSTONE_KEY);
  if (!stored) {
    return null;
  }
  try {
    const tombstone = JSON.parse(stored) as Partial<LogoutTombstone>;
    if (
      tombstone.version === LOGOUT_TOMBSTONE_VERSION
      && typeof tombstone.generation === "string"
      && typeof tombstone.createdAt === "number"
    ) {
      return tombstone as LogoutTombstone;
    }
  } catch {
    // An invalid tombstone remains blocking until an explicit login replaces it.
  }
  return {
    version: LOGOUT_TOMBSTONE_VERSION,
    generation: "invalid",
    createdAt: 0,
  } satisfies LogoutTombstone;
}

function notificarAlteracao() {
  listeners.forEach((listener) => listener());
}

function obterCanal() {
  if (
    channel === null
    && typeof BroadcastChannel !== "undefined"
  ) {
    channel = new BroadcastChannel(SESSION_CHANNEL);
    channel.addEventListener("message", notificarAlteracao);
  }
  return channel;
}

function publicarAlteracao(action: "login" | "logout" | "refresh" | "invalidated") {
  obterCanal()?.postMessage({
    type: "session-changed",
    action,
    generation: lerGeracao(),
  });
  notificarAlteracao();
}

function criarGeracao() {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`;
}

function removerTokenSeIgual(chave: string, valor: string) {
  if (localStorage.getItem(chave) === valor) {
    localStorage.removeItem(chave);
  }
}

export function obterAccessToken() {
  return storageDisponivel() ? localStorage.getItem(ACCESS_TOKEN_KEY) : null;
}

export function obterRefreshToken() {
  return storageDisponivel() ? localStorage.getItem(REFRESH_TOKEN_KEY) : null;
}

export function obterGeracaoSessao() {
  return lerGeracao();
}

export function logoutExplicitoAtivo() {
  return lerTombstone() !== null;
}

export function capturarSessao(): SessionSnapshot {
  return {
    generation: lerGeracao(),
    logoutActive: logoutExplicitoAtivo(),
    access: obterAccessToken(),
    refresh: obterRefreshToken(),
  };
}

export function geracaoSessaoValida(generation: string) {
  return (
    !logoutExplicitoAtivo()
    && lerGeracao() === generation
    && Boolean(obterAccessToken() && obterRefreshToken())
  );
}

export function estaAutenticado() {
  return geracaoSessaoValida(lerGeracao());
}

export function registrarLoginExplicito(
  expectedGeneration: string,
  access: string,
  refresh: string,
) {
  if (!storageDisponivel() || lerGeracao() !== expectedGeneration) {
    return false;
  }

  const nextGeneration = criarGeracao();
  localStorage.setItem(SESSION_GENERATION_KEY, nextGeneration);
  localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  localStorage.setItem(ACCESS_TOKEN_KEY, access);
  localStorage.removeItem(LOGOUT_TOMBSTONE_KEY);

  if (lerGeracao() !== nextGeneration || logoutExplicitoAtivo()) {
    removerTokenSeIgual(REFRESH_TOKEN_KEY, refresh);
    removerTokenSeIgual(ACCESS_TOKEN_KEY, access);
    publicarAlteracao("invalidated");
    return false;
  }

  publicarAlteracao("login");
  return true;
}

export function atualizarSessao(
  expectedGeneration: string,
  expectedRefresh: string,
  access: string,
  refresh: string,
) {
  if (
    !storageDisponivel()
    || logoutExplicitoAtivo()
    || lerGeracao() !== expectedGeneration
    || localStorage.getItem(REFRESH_TOKEN_KEY) !== expectedRefresh
  ) {
    return false;
  }

  localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  localStorage.setItem(ACCESS_TOKEN_KEY, access);

  if (logoutExplicitoAtivo() || lerGeracao() !== expectedGeneration) {
    removerTokenSeIgual(REFRESH_TOKEN_KEY, refresh);
    removerTokenSeIgual(ACCESS_TOKEN_KEY, access);
    publicarAlteracao("invalidated");
    return false;
  }

  publicarAlteracao("refresh");
  return true;
}

export function registrarLogoutExplicito() {
  if (!storageDisponivel()) {
    return null;
  }

  const refresh = obterRefreshToken();
  const generation = criarGeracao();
  const tombstone: LogoutTombstone = {
    version: LOGOUT_TOMBSTONE_VERSION,
    generation,
    createdAt: Date.now(),
  };

  localStorage.setItem(LOGOUT_TOMBSTONE_KEY, JSON.stringify(tombstone));
  localStorage.setItem(SESSION_GENERATION_KEY, generation);
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  publicarAlteracao("logout");
  return refresh;
}

export function invalidarSessao(expectedGeneration: string) {
  if (!storageDisponivel() || lerGeracao() !== expectedGeneration) {
    return false;
  }

  localStorage.setItem(SESSION_GENERATION_KEY, criarGeracao());
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  publicarAlteracao("invalidated");
  return true;
}

export function observarSessao(listener: SessionListener) {
  listeners.add(listener);
  obterCanal();

  const observarStorage = (evento: StorageEvent) => {
    if (
      evento.key === ACCESS_TOKEN_KEY
      || evento.key === REFRESH_TOKEN_KEY
      || evento.key === SESSION_GENERATION_KEY
      || evento.key === LOGOUT_TOMBSTONE_KEY
      || evento.key === null
    ) {
      listener();
    }
  };

  if (typeof window !== "undefined") {
    window.addEventListener("storage", observarStorage);
  }

  return () => {
    listeners.delete(listener);
    if (typeof window !== "undefined") {
      window.removeEventListener("storage", observarStorage);
    }
  };
}
