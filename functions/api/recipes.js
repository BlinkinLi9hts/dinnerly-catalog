export async function onRequest(context) {
  const { request, env } = context;

  // CORS headers
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
      const data = await env.DINNERLY_KV.get("recipes");
      const recipes = data ? JSON.parse(data) : [];
      return new Response(JSON.stringify(recipes), { status: 200, headers });
    } catch (e) {
      return new Response(JSON.stringify({ error: "Failed to load recipes" }), { status: 500, headers });
    }
  }

  if (request.method === "POST") {
    const secret = request.headers.get("X-Dinnerly-Secret");
    if (!secret || secret !== env.DINNERLY_SECRET) {
      return new Response(JSON.stringify({ error: "Unauthorized" }), { status: 401, headers });
    }
    try {
      const body = await request.json();
      const recipes = Array.isArray(body) ? body : [];
      await env.DINNERLY_KV.put("recipes", JSON.stringify(recipes));
      return new Response(JSON.stringify({ ok: true, count: recipes.length }), { status: 200, headers });
    } catch (e) {
      return new Response(JSON.stringify({ error: "Failed to save recipes" }), { status: 500, headers });
    }
  }

  return new Response(JSON.stringify({ error: "Method not allowed" }), { status: 405, headers });
}
