const SESSION_TTL_SECONDS = 24 * 60 * 60;
const EXCHANGE_TTL_SECONDS = 30 * 60;
const COOKIE_SESSION_NAME = "cop_session_id";
const COOKIE_TOKEN_NAME = "cop_session_token";

function json(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "access-control-allow-origin": "*",
      "access-control-allow-methods": "GET,POST,OPTIONS",
      "access-control-allow-headers": "content-type",
      ...extraHeaders,
    },
  });
}

function withCookieHeaders(response, cookieHeaders) {
  for (const value of cookieHeaders) {
    response.headers.append("set-cookie", value);
  }
  return response;
}

function makeSessionId() {
  return crypto.randomUUID().replace(/-/g, "");
}

function makeAppToken() {
  return crypto.randomUUID().replace(/-/g, "") + crypto.randomUUID().replace(/-/g, "");
}

function randomBase62(length) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  const values = crypto.getRandomValues(new Uint8Array(length));
  let output = "";
  for (const value of values) {
    output += alphabet[value % alphabet.length];
  }
  return output;
}

function makeExchangeToken() {
  return randomBase62(16);
}

function nowIso() {
  return new Date().toISOString();
}

function makeMessageId() {
  return crypto.randomUUID().replace(/-/g, "");
}

async function loadSession(env, sessionId) {
  const raw = await env.SESSIONS.get(sessionId);
  if (!raw) {
    return null;
  }
  return JSON.parse(raw);
}

async function saveSession(env, session) {
  await env.SESSIONS.put(session.session_id, JSON.stringify(session), {
    expirationTtl: SESSION_TTL_SECONDS,
  });
}

async function loadExchange(env, exchangeToken) {
  const raw = await env.SESSIONS.get(`exchange:${exchangeToken}`);
  if (!raw) {
    return null;
  }
  return JSON.parse(raw);
}

async function saveExchange(env, exchangeToken, exchange) {
  await env.SESSIONS.put(`exchange:${exchangeToken}`, JSON.stringify(exchange), {
    expirationTtl: EXCHANGE_TTL_SECONDS,
  });
}

async function deleteExchange(env, exchangeToken) {
  await env.SESSIONS.delete(`exchange:${exchangeToken}`);
}

function createSession(sessionId) {
  const createdAt = nowIso();
  return {
    session_id: sessionId,
    app_token: makeAppToken(),
    created_at: createdAt,
    updated_at: createdAt,
    messages: [],
  };
}

function withUpdatedAt(session) {
  session.updated_at = nowIso();
  return session;
}

function assetRequest(request, path, search = "") {
  const url = new URL(request.url);
  url.pathname = path;
  url.search = search;
  return new Request(url.toString(), request);
}

function parseCookies(request) {
  const header = request.headers.get("cookie") || "";
  const cookies = {};
  for (const part of header.split(";")) {
    const trimmed = part.trim();
    if (!trimmed) {
      continue;
    }
    const separator = trimmed.indexOf("=");
    if (separator < 0) {
      continue;
    }
    const key = trimmed.slice(0, separator).trim();
    const value = trimmed.slice(separator + 1).trim();
    cookies[key] = value;
  }
  return cookies;
}

function buildAuthCookieHeaders(session) {
  const base = [
    "Path=/",
    "HttpOnly",
    "Secure",
    "SameSite=Lax",
    `Max-Age=${SESSION_TTL_SECONDS}`,
  ];
  return [
    `${COOKIE_SESSION_NAME}=${session.session_id}; ${base.join("; ")}`,
    `${COOKIE_TOKEN_NAME}=${session.app_token}; ${base.join("; ")}`,
  ];
}

function buildClearCookieHeaders() {
  const base = [
    "Path=/",
    "HttpOnly",
    "Secure",
    "SameSite=Lax",
    "Max-Age=0",
  ];
  return [
    `${COOKIE_SESSION_NAME}=; ${base.join("; ")}`,
    `${COOKIE_TOKEN_NAME}=; ${base.join("; ")}`,
  ];
}

async function requireSessionAuth(request, env, sessionId) {
  const cookies = parseCookies(request);
  const cookieSessionId = cookies[COOKIE_SESSION_NAME];
  const cookieToken = cookies[COOKIE_TOKEN_NAME];

  if (!cookieSessionId || !cookieToken) {
    return { ok: false, response: json({ ok: false, error: "auth_required" }, 401) };
  }

  if (cookieSessionId !== sessionId) {
    return { ok: false, response: json({ ok: false, error: "session_mismatch" }, 403) };
  }

  const session = await loadSession(env, sessionId);
  if (!session) {
    return {
      ok: false,
      response: withCookieHeaders(
        json({ ok: false, error: "session_not_found" }, 404),
        buildClearCookieHeaders()
      ),
    };
  }

  if (session.app_token !== cookieToken) {
    return {
      ok: false,
      response: withCookieHeaders(
        json({ ok: false, error: "invalid_token" }, 403),
        buildClearCookieHeaders()
      ),
    };
  }

  return { ok: true, session };
}

async function handleCreateSession(request, env) {
  const sessionId = makeSessionId();
  const session = createSession(sessionId);
  await saveSession(env, session);
  const exchangeToken = makeExchangeToken();
  await saveExchange(env, exchangeToken, {
    session_id: sessionId,
    created_at: nowIso(),
  });
  const origin = new URL(request.url).origin;
  return json({
    ok: true,
    session_id: sessionId,
    app_token: session.app_token,
    session_url: `${origin}/s/${sessionId}`,
    exchange_url: `${origin}/n/${exchangeToken}`,
  });
}

async function handleExchange(env, exchangeToken) {
  const exchange = await loadExchange(env, exchangeToken);
  if (!exchange) {
    return json({ ok: false, error: "exchange_not_found" }, 404);
  }
  await deleteExchange(env, exchangeToken);

  const session = await loadSession(env, exchange.session_id);
  if (!session) {
    return json({ ok: false, error: "session_not_found" }, 404);
  }

  return withCookieHeaders(new Response(null, {
    status: 302,
    headers: {
      location: `/s/${session.session_id}`,
      "cache-control": "no-store",
    },
  }), buildAuthCookieHeaders(session));
}

async function handleGetSession(request, env, sessionId) {
  const auth = await requireSessionAuth(request, env, sessionId);
  if (!auth.ok) {
    return auth.response;
  }
  return withCookieHeaders(json(auth.session), buildAuthCookieHeaders(auth.session));
}

async function handleAppendMessage(request, env, sessionId) {
  const auth = await requireSessionAuth(request, env, sessionId);
  if (!auth.ok) {
    return auth.response;
  }

  const body = await request.json().catch(() => null);
  if (!body || typeof body.text !== "string" || !body.text.trim()) {
    return json({ ok: false, error: "invalid_text" }, 400);
  }

  const session = auth.session;

  session.messages.push({
    id: makeMessageId(),
    role: body.role === "user" ? "user" : "agent",
    text: body.text.trim(),
    ts: nowIso(),
  });
  withUpdatedAt(session);
  await saveSession(env, session);
  return withCookieHeaders(json({ ok: true, session }), buildAuthCookieHeaders(session));
}

async function handleGetMessages(request, url, env, sessionId) {
  const auth = await requireSessionAuth(request, env, sessionId);
  if (!auth.ok) {
    return auth.response;
  }
  const session = auth.session;

  const since = url.searchParams.get("since");
  const role = url.searchParams.get("role");
  let messages = session.messages || [];

  if (since) {
    const sinceMs = Date.parse(since);
    if (!Number.isNaN(sinceMs)) {
      messages = messages.filter((message) => Date.parse(message.ts) > sinceMs);
    }
  }

  if (role) {
    messages = messages.filter((message) => message.role === role);
  }

  return withCookieHeaders(
    json({
      ok: true,
      session_id: sessionId,
      messages,
    }),
    buildAuthCookieHeaders(session)
  );
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "access-control-allow-origin": "*",
          "access-control-allow-methods": "GET,POST,OPTIONS",
          "access-control-allow-headers": "content-type",
        },
      });
    }

    if (url.pathname === "/api/sessions" && request.method === "POST") {
      return handleCreateSession(request, env);
    }

    const exchangeMatch = url.pathname.match(/^\/n\/([a-zA-Z0-9]+)$/);
    if (exchangeMatch && request.method === "GET") {
      return handleExchange(env, exchangeMatch[1]);
    }

    const sessionPageMatch = url.pathname.match(/^\/s\/([a-zA-Z0-9_-]+)$/);
    if (sessionPageMatch && request.method === "GET") {
      return env.ASSETS.fetch(assetRequest(request, "/"));
    }

    const sessionMatch = url.pathname.match(/^\/api\/sessions\/([a-zA-Z0-9_-]+)$/);
    if (sessionMatch && request.method === "GET") {
      return handleGetSession(request, env, sessionMatch[1]);
    }

    const messagesMatch = url.pathname.match(/^\/api\/sessions\/([a-zA-Z0-9_-]+)\/messages$/);
    if (messagesMatch && request.method === "GET") {
      return handleGetMessages(request, url, env, messagesMatch[1]);
    }
    if (messagesMatch && request.method === "POST") {
      return handleAppendMessage(request, env, messagesMatch[1]);
    }

    if (request.method === "GET" || request.method === "HEAD") {
      return env.ASSETS.fetch(request);
    }

    return json({ ok: false, error: "not_found" }, 404);
  },
};
