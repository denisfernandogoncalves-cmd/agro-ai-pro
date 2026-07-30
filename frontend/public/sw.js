const CACHE_PREFIX = "agro-ai-pro-";
const CACHE = `${CACHE_PREFIX}v2`;
const SHELL = ["/", "/manifest.webmanifest", "/agro-ai-icon.svg"];

const matchFromCache = async (request) => {
  try {
    return await caches.match(request);
  } catch {
    return undefined;
  }
};

const putInCache = async (request, response) => {
  try {
    const cache = await caches.open(CACHE);
    await cache.put(request, response);
  } catch {
    // Cache failures must not prevent the original response from reaching the browser.
  }
};

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(SHELL))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE)
          .map((key) => caches.delete(key)),
      ))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;

  if (request.mode === "navigate") {
    const networkResult = fetch(request).then((response) => ({
      response,
      cacheCopy: response.clone(),
    }));

    event.waitUntil(
      networkResult
        .then(({ cacheCopy }) => putInCache("/", cacheCopy))
        .catch(() => undefined),
    );
    event.respondWith(
      networkResult
        .then(({ response }) => response)
        .catch(() => matchFromCache("/")),
    );
    return;
  }

  const assetResult = matchFromCache(request).then((cached) => {
    if (cached) return { response: cached, cacheCopy: undefined };

    return fetch(request).then((response) => ({
      response,
      cacheCopy: response.ok ? response.clone() : undefined,
    }));
  });

  event.waitUntil(
    assetResult
      .then(({ cacheCopy }) => (cacheCopy ? putInCache(request, cacheCopy) : undefined))
      .catch(() => undefined),
  );
  event.respondWith(assetResult.then(({ response }) => response));
});
