import type { Finding, GraphEdge, StreamEvent } from "./types";
export function parse<T>(text: unknown, fallback: T): T {
  try {
    return typeof text === "string" ? JSON.parse(text) : fallback;
  } catch {
    return fallback;
  }
}
export function acceptEvent(cursor: number, id: string, event: StreamEvent) {
  const next = Number(id);
  return Number.isSafeInteger(next) && next > cursor
    ? { cursor: next, event }
    : null;
}
export function transferIds(finding?: Finding): Set<string> {
  const ids = new Set<string>();
  const walk = (value: unknown, key = "") => {
    if (
      typeof value === "string" &&
      ["transfers", "edge_ids", "transfer_id"].includes(key)
    )
      ids.add(value);
    else if (Array.isArray(value)) value.forEach((v) => walk(v, key));
    else if (value && typeof value === "object")
      Object.entries(value).forEach(([k, v]) => walk(v, k));
  };
  if (finding) walk(parse(finding.result_json, []));
  return ids;
}
export function exactEdge(edge: GraphEdge, ids: Set<string>) {
  return typeof edge.properties.id === "string" && ids.has(edge.properties.id);
}
export const toolNames: Record<string, string> = {
  min_freeze_set: "Measure freeze impact and the exact cut",
  simulate_freeze: "Compare a proposed freeze",
  prior_cases: "Review account history",
  shared_identifiers: "Trace shared identifiers",
  circular_flows: "Follow circular transfers",
  fan_in: "Inspect incoming transfers",
  ajo_payout_pattern: "Review pool payouts",
  link_to_known_bad: "Check historical connections",
  corridor_context: "Retrieve corridor policies",
  precedents: "Find current precedents",
  who_knows: "Identify relevant expertise",
  guardrail: "Apply deterministic guardrail",
  collector_rank: "Rank transfer collectors",
  connected_cluster: "Explore connected accounts",
  ring_communities: "Explore account communities",
  seed_history: "Historical review",
};
export const label = (tool: string) =>
  toolNames[tool] ?? tool.replaceAll("_", " ");
export const date = (ts: unknown) =>
  typeof ts === "number"
    ? new Date(ts * 1000).toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "Unavailable";
export const money = (amount: unknown, currency: unknown = "USD") =>
  typeof amount === "number"
    ? new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: typeof currency === "string" ? currency : "USD",
        maximumFractionDigits: 2,
      }).format(amount)
    : "No transfer";
export function message(status: number) {
  return status === 409
    ? "An investigation is already running. Open account history to follow it."
    : status === 429
      ? "Four investigations are already running. Wait for one to finish, then retry."
      : status === 404
        ? "This case could not be found. Return to the review queue."
        : "The service is unavailable. Check the local API and retry.";
}
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch("/api" + path, { cache: "no-store", ...init });
  if (!response.ok) throw new Error(message(response.status));
  return response.json();
}
