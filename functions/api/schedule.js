export async function onRequest(context) {
  const { request, env } = context;

  const headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Dinnerly-Secret",
    "Content-Type": "application/json",
  };

  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers });
  }

  if (request.method === "GET") {
    try {
      const data = await env.DINNERLY_KV.get("schedule");
      const schedule = data ? JSON.parse(data) : {};
      return new Response(JSON.stringify(schedule), { status: 200, headers });
    } catch (e) {
      return new Response(JSON.stringify({ error: "Failed to load schedule" }), { status: 500, headers });
    }
  }

  if (request.method === "POST") {
    const secret = request.headers.get("X-Dinnerly-Secret");
    if (!secret || secret !== env.DINNERLY_SECRET) {
      return new Response(JSON.stringify({ error: "Unauthorized" }), { status: 401, headers });
    }
    try {
      const body = await request.json();
      const schedule = (body && typeof body === "object" && !Array.isArray(body)) ? body : {};
      await env.DINNERLY_KV.put("schedule", JSON.stringify(schedule));
      return new Response(JSON.stringify({ ok: true }), { status: 200, headers });
    } catch (e) {
      return new Response(JSON.stringify({ error: "Failed to save schedule" }), { status: 500, headers });
    }
  }

  return new Response(JSON.stringify({ error: "Method not allowed" }), { status: 405, headers });
}
