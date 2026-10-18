export const dynamic = "force-dynamic";

export function GET() {
  const api = new URL(process.env.CORRIDOR_API_URL ?? "http://127.0.0.1:8000");
  return Response.redirect(new URL("/docs", api.origin));
}
