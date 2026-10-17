import type { NextRequest } from "next/server";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const readPaths = [
  /^flags$/,
  /^cases\/[^/]+(?:\/stream|\/subgraph)?$/,
  /^accounts\/[^/]+\/history$/,
];
async function proxy(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const parts = (await params).path;
  if (
    parts.some(
      (p) => p === "." || p === ".." || p.includes("/") || p.includes("\\"),
    )
  )
    return new Response(null, { status: 404 });
  const path = parts.join("/");
  const allowed =
    request.method === "GET"
      ? readPaths.some((r) => r.test(path))
      : /^investigate\/[^/]+$/.test(path);
  if (!allowed) return new Response(null, { status: 404 });
  const origin = process.env.CORRIDOR_API_URL ?? "http://127.0.0.1:8000";
  const headers = new Headers({
    Accept: path.endsWith("/stream") ? "text/event-stream" : "application/json",
  });
  if (request.headers.has("last-event-id"))
    headers.set("Last-Event-ID", request.headers.get("last-event-id")!);
  if (request.method === "POST")
    headers.set("Content-Type", "application/json");
  try {
    const upstream = await fetch(
      `${origin.replace(/\/$/, "")}/${parts.map(encodeURIComponent).join("/")}${request.nextUrl.search}`,
      {
        method: request.method,
        headers,
        body: request.method === "POST" ? await request.text() : undefined,
        cache: "no-store",
        signal: request.signal,
      },
    );
    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "Content-Type":
          upstream.headers.get("content-type") ?? "application/json",
        "Cache-Control": "no-store",
        "X-Accel-Buffering": "no",
      },
    });
  } catch {
    return Response.json({ detail: "API unavailable." }, { status: 503 });
  }
}
export { proxy as GET, proxy as POST };
