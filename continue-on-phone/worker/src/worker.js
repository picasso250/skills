const SESSION_TTL_SECONDS = 24 * 60 * 60;

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

function makeSessionId() {
  return crypto.randomUUID().replace(/-/g, "");
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

function createSession(sessionId) {
  const createdAt = nowIso();
  return {
    session_id: sessionId,
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

async function handleCreateSession(request, env) {
  const body = await request.json().catch(() => ({}));
  const requestedSessionId = typeof body.session_id === "string" ? body.session_id.trim() : "";
  if (requestedSessionId) {
    return json({ ok: false, error: "custom_session_id_disabled" }, 400);
  }

  const sessionId = makeSessionId();
  const session = createSession(sessionId);
  await saveSession(env, session);
  const origin = new URL(request.url).origin;
  return json({
    ok: true,
    session_id: sessionId,
    session_url: `${origin}/s/${sessionId}`,
  });
}

async function handleGetSession(env, sessionId) {
  const session = await loadSession(env, sessionId);
  if (!session) {
    return json({ ok: false, error: "session_not_found" }, 404);
  }
  return json(session);
}

async function handleAppendMessage(request, env, sessionId) {
  const body = await request.json().catch(() => null);
  if (!body || typeof body.text !== "string" || !body.text.trim()) {
    return json({ ok: false, error: "invalid_text" }, 400);
  }

  let session = await loadSession(env, sessionId);
  if (!session) {
    session = createSession(sessionId);
  }

  session.messages.push({
    id: makeMessageId(),
    role: body.role === "user" ? "user" : "agent",
    text: body.text.trim(),
    ts: nowIso(),
  });
  withUpdatedAt(session);
  await saveSession(env, session);
  return json({ ok: true, session });
}

async function handleGetMessages(url, env, sessionId) {
  const session = await loadSession(env, sessionId);
  if (!session) {
    return json({ ok: false, error: "session_not_found" }, 404);
  }

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

  return json({
    ok: true,
    session_id: sessionId,
    messages,
  });
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

    const sessionPageMatch = url.pathname.match(/^\/s\/([a-zA-Z0-9_-]+)$/);
    if (sessionPageMatch && request.method === "GET") {
      return env.ASSETS.fetch(
        assetRequest(request, "/index.html", `?session_id=${encodeURIComponent(sessionPageMatch[1])}`)
      );
    }

    const sessionMatch = url.pathname.match(/^\/api\/sessions\/([a-zA-Z0-9_-]+)$/);
    if (sessionMatch && request.method === "GET") {
      return handleGetSession(env, sessionMatch[1]);
    }

    const messagesMatch = url.pathname.match(/^\/api\/sessions\/([a-zA-Z0-9_-]+)\/messages$/);
    if (messagesMatch && request.method === "GET") {
      return handleGetMessages(url, env, messagesMatch[1]);
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
