const ACCESS_TOKEN_KEY = "agro-ai-pro.access-token";

export type UserIdentity = {
  label: string;
  identifier: string | null;
};

function decodePayload(token: string) {
  const payload = token.split(".")[1];
  if (!payload) return null;
  try {
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
    return JSON.parse(window.atob(padded)) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export function getUserIdentity(): UserIdentity {
  if (typeof window === "undefined") {
    return { label: "Usuário autenticado", identifier: null };
  }
  const token = window.localStorage.getItem(ACCESS_TOKEN_KEY);
  const payload = token ? decodePayload(token) : null;
  const preferred = payload?.username ?? payload?.name ?? payload?.email;
  const identifier = payload?.user_id ?? payload?.sub ?? null;
  return {
    label: typeof preferred === "string" && preferred.trim()
      ? preferred
      : identifier !== null
        ? `Usuário #${String(identifier)}`
        : "Usuário autenticado",
    identifier: identifier === null ? null : String(identifier),
  };
}
