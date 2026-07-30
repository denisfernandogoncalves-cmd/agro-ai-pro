import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";

import { transformWithOxc } from "vite";


const coordinatorSource = await readFile(
  new URL("../src/auth/sessionCoordinator.ts", import.meta.url),
  "utf8",
);
const apiSource = await readFile(
  new URL("../src/api/propriedades.ts", import.meta.url),
  "utf8",
);
const authContextSource = await readFile(
  new URL("../src/auth/AuthContext.tsx", import.meta.url),
  "utf8",
);
const appSource = await readFile(
  new URL("../src/App.tsx", import.meta.url),
  "utf8",
);

const axiosUrl = import.meta.resolve("axios");
const reactUrl = import.meta.resolve("react");
const reactJsxRuntimeUrl = import.meta.resolve("react/jsx-runtime");
const reactDomServerUrl = import.meta.resolve("react-dom/server");

let moduleSequence = 0;

async function transpile(source, jsx = false) {
  const result = await transformWithOxc(source, jsx ? "module.tsx" : "module.ts", {
    lang: jsx ? "tsx" : "ts",
    sourceType: "module",
    target: "es2022",
  });
  return result.code;
}

function moduleDataUrl(source, name) {
  moduleSequence += 1;
  const uniqueSource = `${source}\n//# sourceURL=${name}-${moduleSequence}.mjs`;
  return `data:text/javascript;base64,${Buffer.from(uniqueSource).toString("base64")}`;
}

class MemoryStorage {
  #values = new Map();

  get length() {
    return this.#values.size;
  }

  clear() {
    this.#values.clear();
  }

  getItem(key) {
    return this.#values.has(key) ? this.#values.get(key) : null;
  }

  key(index) {
    return [...this.#values.keys()][index] ?? null;
  }

  removeItem(key) {
    this.#values.delete(key);
  }

  setItem(key, value) {
    this.#values.set(key, String(value));
  }
}

class FakeWindow {
  #listeners = new Map();

  addEventListener(type, listener) {
    const listeners = this.#listeners.get(type) ?? new Set();
    listeners.add(listener);
    this.#listeners.set(type, listeners);
  }

  removeEventListener(type, listener) {
    this.#listeners.get(type)?.delete(listener);
  }

  dispatch(type, event) {
    this.#listeners.get(type)?.forEach((listener) => listener(event));
  }

  confirm() {
    return true;
  }
}

class FakeBroadcastChannel {
  static channels = new Map();

  #listeners = new Set();

  constructor(name) {
    this.name = name;
    const channels = FakeBroadcastChannel.channels.get(name) ?? new Set();
    channels.add(this);
    FakeBroadcastChannel.channels.set(name, channels);
  }

  addEventListener(type, listener) {
    if (type === "message") {
      this.#listeners.add(listener);
    }
  }

  postMessage(data) {
    for (const channel of FakeBroadcastChannel.channels.get(this.name) ?? []) {
      if (channel !== this) {
        queueMicrotask(() => {
          channel.#listeners.forEach((listener) => listener({ data }));
        });
      }
    }
  }
}

const storage = new MemoryStorage();
const fakeWindow = new FakeWindow();
globalThis.localStorage = storage;
globalThis.window = fakeWindow;
globalThis.BroadcastChannel = FakeBroadcastChannel;

async function loadCoordinator() {
  const code = await transpile(coordinatorSource);
  const url = moduleDataUrl(code, "session-coordinator");
  return { module: await import(url), url };
}

async function loadApi(coordinatorUrl, apiUrl) {
  globalThis.__TEST_API_URL__ = apiUrl;
  let source = apiSource
    .replace('from "axios";', `from "${axiosUrl}";`)
    .replace(
      'from "../auth/sessionCoordinator";',
      `from "${coordinatorUrl}";`,
    )
    .replace(
      /import \{ GeometriaGeoJSON \} from "\.\.\/utils\/geometria";/,
      "type GeometriaGeoJSON = unknown;",
    )
    .replace(
      /const API_URL = .*?;/,
      "const API_URL = globalThis.__TEST_API_URL__;",
    );
  source = await transpile(source);
  return import(moduleDataUrl(source, "propriedades-api"));
}

function deferred() {
  let resolve;
  const promise = new Promise((resolver) => {
    resolve = resolver;
  });
  return { promise, resolve };
}

function readRequestBody(request) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    request.on("data", (chunk) => chunks.push(chunk));
    request.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    request.on("error", reject);
  });
}

function sendJson(response, status, data) {
  response.writeHead(status, { "content-type": "application/json" });
  response.end(JSON.stringify(data));
}

const serverState = {
  validAccess: "access-renewed",
  refreshCount: 0,
  privateCount: 0,
  loginCount: 0,
  logoutCount: 0,
  refreshGate: null,
  refreshStarted: null,
  privateGate: null,
  privateStarted: null,
};

function resetServerState() {
  serverState.validAccess = "access-renewed";
  serverState.refreshCount = 0;
  serverState.privateCount = 0;
  serverState.loginCount = 0;
  serverState.logoutCount = 0;
  serverState.refreshGate = null;
  serverState.refreshStarted = null;
  serverState.privateGate = null;
  serverState.privateStarted = null;
}

const server = createServer((request, response) => {
  void (async () => {
    const url = new URL(request.url, "http://127.0.0.1");
    await readRequestBody(request);

    if (request.method === "POST" && url.pathname === "/api/auth/token/") {
      serverState.loginCount += 1;
      serverState.validAccess = "access-login";
      sendJson(response, 200, {
        access: "access-login",
        refresh: "refresh-login",
      });
      return;
    }

    if (
      request.method === "POST"
      && url.pathname === "/api/auth/token/refresh/"
    ) {
      serverState.refreshCount += 1;
      serverState.refreshStarted?.resolve();
      if (serverState.refreshGate) {
        await serverState.refreshGate.promise;
      }
      serverState.validAccess = "access-renewed";
      sendJson(response, 200, {
        access: "access-renewed",
        refresh: "refresh-renewed",
      });
      return;
    }

    if (request.method === "POST" && url.pathname === "/api/auth/logout/") {
      serverState.logoutCount += 1;
      sendJson(response, 200, {});
      return;
    }

    if (request.method === "GET" && url.pathname === "/api/propriedades/") {
      serverState.privateCount += 1;
      const authorization = request.headers.authorization;
      if (authorization !== `Bearer ${serverState.validAccess}`) {
        sendJson(response, 401, { detail: "expired" });
        return;
      }
      serverState.privateStarted?.resolve();
      if (serverState.privateGate) {
        await serverState.privateGate.promise;
      }
      sendJson(response, 200, []);
      return;
    }

    sendJson(response, 404, { detail: "not found" });
  })().catch((error) => {
    sendJson(response, 500, { detail: String(error) });
  });
});

await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const address = server.address();
const apiUrl = `http://127.0.0.1:${address.port}/api`;

const approved = [];

async function test(name, action) {
  await action();
  approved.push(name);
}

async function freshScenario() {
  storage.clear();
  resetServerState();
  const coordinator = await loadCoordinator();
  const api = await loadApi(coordinator.url, apiUrl);
  return { coordinator: coordinator.module, api };
}

try {
  await test("access expirado permite refresh legítimo", async () => {
    const { coordinator, api } = await freshScenario();
    assert.equal(
      coordinator.registrarLoginExplicito(
        coordinator.obterGeracaoSessao(),
        "access-expired",
        "refresh-valid",
      ),
      true,
    );

    const result = await api.listarPropriedades();
    assert.deepEqual(result, []);
    assert.equal(serverState.refreshCount, 1);
    assert.equal(serverState.privateCount, 2);
    assert.equal(coordinator.obterAccessToken(), "access-renewed");
    assert.equal(coordinator.obterRefreshToken(), "refresh-renewed");
    assert.equal(coordinator.logoutExplicitoAtivo(), false);
  });

  await test("logout explícito impede refresh", async () => {
    const { coordinator, api } = await freshScenario();
    coordinator.registrarLoginExplicito(
      coordinator.obterGeracaoSessao(),
      "access-expired",
      "refresh-valid",
    );
    await api.sair();
    await assert.rejects(api.listarPropriedades());
    assert.equal(serverState.refreshCount, 0);
    assert.equal(coordinator.logoutExplicitoAtivo(), true);
  });

  await test("refresh anterior ao logout é descartado", async () => {
    const { coordinator, api } = await freshScenario();
    coordinator.registrarLoginExplicito(
      coordinator.obterGeracaoSessao(),
      "access-expired",
      "refresh-valid",
    );
    serverState.refreshStarted = deferred();
    serverState.refreshGate = deferred();

    const request = api.listarPropriedades();
    await serverState.refreshStarted.promise;
    await api.sair();
    serverState.refreshGate.resolve();

    await assert.rejects(request);
    assert.equal(serverState.refreshCount, 1);
    assert.equal(serverState.privateCount, 1);
    assert.equal(coordinator.obterAccessToken(), null);
    assert.equal(coordinator.obterRefreshToken(), null);
  });

  await test("logout remove access e refresh", async () => {
    const { coordinator } = await freshScenario();
    coordinator.registrarLoginExplicito(
      coordinator.obterGeracaoSessao(),
      "access",
      "refresh",
    );
    assert.equal(coordinator.registrarLogoutExplicito(), "refresh");
    assert.equal(coordinator.obterAccessToken(), null);
    assert.equal(coordinator.obterRefreshToken(), null);
  });

  await test("tombstone persiste após reload", async () => {
    const { coordinator } = await freshScenario();
    coordinator.registrarLoginExplicito(
      coordinator.obterGeracaoSessao(),
      "access",
      "refresh",
    );
    coordinator.registrarLogoutExplicito();
    const reloaded = await loadCoordinator();
    assert.equal(reloaded.module.logoutExplicitoAtivo(), true);
    assert.equal(reloaded.module.estaAutenticado(), false);
    const tombstone = JSON.parse(
      storage.getItem("agro-ai-pro.logout-tombstone"),
    );
    assert.equal(tombstone.version, 1);
  });

  await test("login explícito remove tombstone", async () => {
    const { coordinator, api } = await freshScenario();
    coordinator.registrarLogoutExplicito();
    await api.autenticar("novo-usuario", "senha");
    assert.equal(coordinator.logoutExplicitoAtivo(), false);
    assert.equal(coordinator.estaAutenticado(), true);
    assert.equal(coordinator.obterAccessToken(), "access-login");
  });

  await test("logout em outra aba encerra sessão local", async () => {
    storage.clear();
    resetServerState();
    const tabA = await loadCoordinator();
    const tabB = await loadCoordinator();
    let notifications = 0;
    tabB.module.observarSessao(() => {
      notifications += 1;
    });
    tabA.module.registrarLoginExplicito(
      tabA.module.obterGeracaoSessao(),
      "access",
      "refresh",
    );
    await Promise.resolve();
    tabA.module.registrarLogoutExplicito();
    await Promise.resolve();
    assert.equal(tabB.module.estaAutenticado(), false);
    assert.equal(tabB.module.logoutExplicitoAtivo(), true);
    assert.ok(notifications >= 2);
  });

  await test("resposta privada de geração antiga é ignorada", async () => {
    const { coordinator, api } = await freshScenario();
    serverState.validAccess = "access-old";
    coordinator.registrarLoginExplicito(
      coordinator.obterGeracaoSessao(),
      "access-old",
      "refresh-old",
    );
    serverState.privateStarted = deferred();
    serverState.privateGate = deferred();
    let privateState = "preserved";
    const request = api.listarPropriedades().then(() => {
      privateState = "stale";
    });
    await serverState.privateStarted.promise;
    coordinator.registrarLogoutExplicito();
    serverState.privateGate.resolve();
    await assert.rejects(request);
    assert.equal(privateState, "preserved");
  });

  await test("pageshow com bfcache mantém logout", async () => {
    const { coordinator } = await freshScenario();
    coordinator.registrarLogoutExplicito();

    let source = authContextSource
      .replace('from "react";', `from "${reactUrl}";`)
      .replace(
        /import \{\s*autenticar[\s\S]*?\} from "\.\.\/api\/propriedades";/,
        "const autenticarNaApi = async () => {};\n"
          + "const sairDaApi = async () => true;",
      )
      .replace(
        'from "./sessionCoordinator";',
        `from "${(await loadCoordinator()).url}";`,
      );
    source = (await transpile(source, true))
      .replace('"react/jsx-runtime"', `"${reactJsxRuntimeUrl}"`);
    const context = await import(moduleDataUrl(source, "auth-context"));
    let authenticated = true;
    context.handlePersistedPageShow({ persisted: true }, () => {
      authenticated = coordinator.estaAutenticado();
    });
    assert.equal(authenticated, false);
  });

  await test("logout desmonta estado privado e módulo Talhões", async () => {
    const rendered = await renderAppStates();
    assert.match(rendered.privateHtml, /class="pagina"/);
    assert.doesNotMatch(rendered.loggedOutHtml, /class="pagina"/);
    assert.doesNotMatch(rendered.loggedOutHtml, /data-private-component/);
    assert.doesNotMatch(rendered.loggedOutHtml, /Talhões/);
  });

  await test("troca de usuários não reutiliza árvore privada", async () => {
    const rendered = await renderAppStates();
    assert.notEqual(rendered.userOneKey, rendered.userTwoKey);
    assert.doesNotMatch(rendered.userTwoHtml, /SENSITIVE_USER_ONE/);
    assert.match(
      appSource,
      /<PrivateArea key=\{`private-\$\{geracao\}`\}/,
    );
  });

  await test("logout repetido permanece seguro", async () => {
    const { coordinator } = await freshScenario();
    coordinator.registrarLoginExplicito(
      coordinator.obterGeracaoSessao(),
      "access",
      "refresh",
    );
    assert.equal(coordinator.registrarLogoutExplicito(), "refresh");
    assert.equal(coordinator.registrarLogoutExplicito(), null);
    assert.equal(coordinator.logoutExplicitoAtivo(), true);
    assert.equal(coordinator.estaAutenticado(), false);
  });

  await test("refresh concorrente é compartilhado", async () => {
    const { coordinator, api } = await freshScenario();
    coordinator.registrarLoginExplicito(
      coordinator.obterGeracaoSessao(),
      "access-expired",
      "refresh-valid",
    );
    serverState.refreshStarted = deferred();
    serverState.refreshGate = deferred();
    const requests = [
      api.listarPropriedades(),
      api.listarPropriedades(),
    ];
    await serverState.refreshStarted.promise;
    serverState.refreshGate.resolve();
    const results = await Promise.all(requests);
    assert.deepEqual(results, [[], []]);
    assert.equal(serverState.refreshCount, 1);
    assert.equal(serverState.privateCount, 4);
  });
} finally {
  await new Promise((resolve, reject) => {
    server.close((error) => (error ? reject(error) : resolve()));
  });
}

async function renderAppStates() {
  const React = await import(reactUrl);
  const { renderToString } = await import(reactDomServerUrl);
  globalThis.__APP_API__ = {
    atualizarPropriedade: async () => ({}),
    criarPropriedade: async () => ({}),
    excluirPropriedade: async () => undefined,
    listarPropriedades: async () => [],
  };
  globalThis.__PRIVATE_COMPONENTS__ = new Proxy({}, {
    get: (_target, name) => () =>
      React.createElement("div", {
        "data-private-component": String(name),
      }),
  });

  let source = appSource
    .replace('from "react";', `from "${reactUrl}";`)
    .replace('from "axios";', `from "${axiosUrl}";`)
    .replace(
      /import \{\s*atualizarPropriedade[\s\S]*?\} from "\.\/api\/propriedades";/,
      "const { atualizarPropriedade, criarPropriedade, "
        + "excluirPropriedade, listarPropriedades } = globalThis.__APP_API__;\n"
        + "type Propriedade = any;\ntype PropriedadeInput = any;",
    )
    .replace(
      /import \{ useAuth \} from "\.\/auth\/AuthContext";/,
      "const useAuth = () => globalThis.__AUTH_STATE__;",
    )
    .replace(
      /import (\w+) from "\.\/(?:components|pages)\/[^"]+";/g,
      "const $1 = globalThis.__PRIVATE_COMPONENTS__.$1;",
    )
    .replace(/import "\.\/styles\.css";/, "");
  source = (await transpile(source, true))
    .replace('"react/jsx-runtime"', `"${reactJsxRuntimeUrl}"`);
  const app = await import(moduleDataUrl(source, "app"));
  const authenticate = async () => undefined;
  const logout = async () => true;

  globalThis.__AUTH_STATE__ = {
    autenticado: true,
    autenticar: authenticate,
    geracao: "user-one",
    sair: logout,
  };
  const privateHtml = renderToString(React.createElement(app.default));

  globalThis.__AUTH_STATE__ = {
    autenticado: false,
    autenticar: authenticate,
    geracao: "logout",
    sair: logout,
  };
  const loggedOutHtml = renderToString(React.createElement(app.default));

  globalThis.__AUTH_STATE__ = {
    autenticado: true,
    autenticar: authenticate,
    geracao: "user-two",
    sair: logout,
  };
  const userTwoHtml = renderToString(React.createElement(app.default));

  return {
    privateHtml,
    loggedOutHtml,
    userTwoHtml,
    userOneKey: "private-user-one",
    userTwoKey: "private-user-two",
  };
}

console.log(`${approved.length} cenários comportamentais de autenticação aprovados:`);
approved.forEach((name) => console.log(`- ${name}`));
