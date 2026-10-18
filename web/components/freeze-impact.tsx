"use client";
import { useEffect, useState } from "react";
import { Button } from "./ui/button";
import type { CaseData } from "@/lib/types";

type Measurement = {
  inflow_volume: number;
  senders_reaching_collector: number;
  cycles_remaining: number;
};
type Step = {
  account: string;
  after: Measurement;
  outside_community_counterparties: string[];
  outside_candidate_counterparties: string[];
};
type Plan = {
  plan_id: string;
  collector: string;
  freeze_ids: string[];
  before: Measurement;
  after: Measurement;
  steps: Step[];
  method: string;
  scope: string;
  scratch_deleted: boolean;
  min_cut?: {
    size: number | null;
    accounts: string[];
    max_flow: number;
    verified?: boolean;
  };
};
type Order = {
  order: { id: string; status: string };
  measurement: {
    before?: string;
    after?: string;
    matched_projection?: boolean;
  } | null;
};

async function jsonResponse(response: Response) {
  const body = await response.json();
  if (!response.ok)
    throw new Error(
      body.detail ?? "Intervention service unavailable. Try again.",
    );
  return body;
}

export function FreezeImpact({ data }: { data: CaseData }) {
  const [plan, setPlan] = useState<Plan | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [token, setToken] = useState("");
  const [confirm, setConfirm] = useState(false);
  const base = `/api/cases/${encodeURIComponent(data.case.id)}`;
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${base}/freeze-impact`, { signal: controller.signal })
      .then(jsonResponse)
      .then((body) => {
        setPlan(body.plan ?? null);
        setOrders(body.orders ?? []);
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => controller.abort();
  }, [base]);
  async function simulate() {
    setBusy(true);
    setError("");
    setConfirm(false);
    const cited = new Set(data.evidence.flatMap((f) => f.cited));
    const account_ids = data.subgraph.nodes
      .filter((n) => n.labels.includes("Account") && cited.has(n.id))
      .map((n) => n.id);
    try {
      setPlan(
        await fetch(`${base}/simulate-freeze`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ account_ids, k: 4 }),
        }).then(jsonResponse),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function approve() {
    if (!plan) return;
    setBusy(true);
    setError("");
    try {
      await fetch(`${base}/approve-freeze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Approval-Token": token,
        },
        body: JSON.stringify({
          plan_id: plan.plan_id,
          confirm_simulated_freeze: confirm,
        }),
      }).then(jsonResponse);
      setToken("");
      setConfirm(false);
      const body = await fetch(`${base}/freeze-impact`).then(jsonResponse);
      setOrders(body.orders ?? []);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const last = plan?.steps.at(-1);
  return (
    <section className="freeze-impact" aria-labelledby="freeze-impact-title">
      <h4 id="freeze-impact-title">What would a freeze interrupt?</h4>
      <p className="muted">
        Test historical transfer routes on a disposable copy. No real funds move
        or freeze.
      </p>
      {error && (
        <p role="alert" className="notice error">
          {error}
        </p>
      )}
      {plan && (
        <>
          <p className="mono">Target: {plan.collector}</p>
          <table className="impact-table">
            <caption>Modeled impact within the measured scope</caption>
            <thead>
              <tr>
                <th>Measure</th>
                <th>Before</th>
                <th>After</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th>Senders reaching target</th>
                <td>{plan.before.senders_reaching_collector}</td>
                <td>{plan.after.senders_reaching_collector}</td>
              </tr>
              <tr>
                <th>Historical inflow (USD)</th>
                <td>{plan.before.inflow_volume.toLocaleString()}</td>
                <td>{plan.after.inflow_volume.toLocaleString()}</td>
              </tr>
              <tr>
                <th>Cycle paths through target</th>
                <td>{plan.before.cycles_remaining}</td>
                <td>{plan.after.cycles_remaining}</td>
              </tr>
            </tbody>
          </table>
          <ol className="impact-steps">
            {plan.steps.map((step) => (
              <li key={step.account}>
                <span className="mono">{step.account}</span>
                <span>
                  {step.after.senders_reaching_collector} senders still reach
                  the target
                </span>
              </li>
            ))}
          </ol>
          {plan.min_cut &&
            plan.min_cut.size !== null &&
            plan.min_cut.size > 0 && (
              <p className="mono">
                Exact minimum cut (FalkorDB max-flow):{" "}
                {plan.min_cut.accounts.join(", ")} ({plan.min_cut.size} account
                {plan.min_cut.size === 1 ? "" : "s"})
                {plan.min_cut.verified
                  ? " · verified on a fresh copy: 0 senders reach the target"
                  : " · verification on a fresh copy did not reach 0"}
              </p>
            )}
          <p>
            <strong>
              {last?.outside_community_counterparties.length ?? 0}
            </strong>{" "}
            affected counterparties outside the target’s computed community;{" "}
            <strong>
              {last?.outside_candidate_counterparties.length ?? 0}
            </strong>{" "}
            outside the candidate set. These are affected neighbors, not proven
            innocent accounts or fully disconnected users.
          </p>
          <details>
            <summary>Method and scope</summary>
            <p>{plan.method}</p>
            <p>{plan.scope}</p>
            <p>
              {plan.scratch_deleted
                ? "Scratch graph deleted after measurement."
                : "Scratch cleanup not confirmed."}
            </p>
          </details>
        </>
      )}
      {!orders.length && (
        <Button
          onClick={simulate}
          disabled={busy || data.case.status !== "closed"}
        >
          {busy
            ? "Measuring…"
            : plan
              ? "Re-run simulation"
              : "Simulate a freeze set"}
        </Button>
      )}
      {!!orders.length && (
        <div className="guardrail-summary" aria-live="polite">
          <strong>Modeled intervention receipt</strong>
          {orders.map(({ order, measurement }) => (
            <div key={order.id}>
              <p className="mono">{order.id}</p>
              <p>
                {order.status === "measured"
                  ? measurement?.matched_projection
                    ? "Measured outcome matches the projection."
                    : "Outcome differs from projection. Review required."
                  : "Transfer blocks recorded; measurement incomplete. Operator review required."}
              </p>
              {measurement?.before && measurement?.after && (
                <p>
                  Senders reaching target:{" "}
                  {JSON.parse(measurement.before).senders_reaching_collector} →{" "}
                  {JSON.parse(measurement.after).senders_reaching_collector}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
      {plan &&
        !!plan.freeze_ids.length &&
        !orders.length &&
        data.case.verdict === "FREEZE" && (
          <details className="approval-gate">
            <summary>Approve modeled freeze</summary>
            <p>
              Marks {plan.freeze_ids.join(", ")} frozen and their transfer edges
              blocked in the demo graph. Historical evidence is preserved.
            </p>
            <label>
              Operator approval token
              <input
                type="password"
                autoComplete="off"
                value={token}
                onChange={(e) => setToken(e.target.value)}
              />
            </label>
            <label className="approval-confirm">
              <input
                type="checkbox"
                checked={confirm}
                onChange={(e) => setConfirm(e.target.checked)}
              />
              I approve this exact plan’s modeled transfer blocks.
            </label>
            <Button onClick={approve} disabled={!confirm || !token || busy}>
              Apply modeled freeze and measure
            </Button>
          </details>
        )}
      {plan && data.case.verdict !== "FREEZE" && (
        <p className="muted">
          Exploration only. A closed FREEZE decision is required for approval.
        </p>
      )}
    </section>
  );
}
