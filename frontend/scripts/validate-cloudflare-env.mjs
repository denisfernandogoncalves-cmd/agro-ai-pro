const rawApiUrl = process.env.VITE_API_URL?.trim();

if (!rawApiUrl) {
  throw new Error("VITE_API_URL é obrigatória no build do Cloudflare Pages.");
}

let apiUrl;
try {
  apiUrl = new URL(rawApiUrl);
} catch {
  throw new Error("VITE_API_URL deve ser uma URL HTTPS absoluta.");
}

if (apiUrl.protocol !== "https:") {
  throw new Error("VITE_API_URL deve usar HTTPS.");
}
if (["localhost", "127.0.0.1"].includes(apiUrl.hostname)) {
  throw new Error("VITE_API_URL não pode apontar para o computador local.");
}
if (!apiUrl.pathname.replace(/\/$/, "").endsWith("/api")) {
  throw new Error("VITE_API_URL deve terminar com /api.");
}

console.log(`API de homologação validada: ${apiUrl.origin}${apiUrl.pathname.replace(/\/$/, "")}`);
