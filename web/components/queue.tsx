"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import * as Dialog from "@radix-ui/react-dialog";
import {
  ArrowRight,
  ArrowUpRight,
  ClockCounterClockwise,
  MagnifyingGlass,
  X,
  ArrowClockwise,
  UserCircle,
  GlobeHemisphereWest,
} from "@phosphor-icons/react";
import { Shell, Badge } from "./shell";
import { Button } from "./ui/button";
import { AnimatedContent } from "./animated-content";
import { api, date, money } from "@/lib/evidence";
import type { Flag, HistoryCase } from "@/lib/types";
export function Queue() {
  const [flags, setFlags] = useState<Flag[]>([]),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [pending, setPending] = useState(""),
    [search, setSearch] = useState("");
  const [account, setAccount] = useState(""),
    [history, setHistory] = useState<HistoryCase[]>([]),
    [historyLoading, setHistoryLoading] = useState(false),
    [historyError, setHistoryError] = useState("");
  const router = useRouter();
  const refresh = () => {
    setLoading(true);
    setError("");
    api<{ flags: Flag[] }>("/flags")
      .then((r) => setFlags(r.flags))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };
  useEffect(() => {
    refresh();
  }, []);
  useEffect(() => {
    if (!account) return;
    let active = true;
    setHistory([]);
    setHistoryLoading(true);
    setHistoryError("");
    api<{ cases: HistoryCase[] }>(
      `/accounts/${encodeURIComponent(account)}/history`,
    )
      .then((r) => {
        if (active) {
          // An account can have multiple membership roles in the same case.
          setHistory(
            Array.from(new Map(r.cases.map((c) => [c.case_id, c])).values()),
          );
        }
      })
      .catch((e) => {
        if (active) setHistoryError(e.message);
      })
      .finally(() => {
        if (active) setHistoryLoading(false);
      });
    return () => {
      active = false;
    };
  }, [account]);
  const start = async (flag: Flag) => {
    if (pending) return;
    setPending(flag.account_id);
    setError("");
    try {
      const r = await api<{ case_id: string }>(
        `/investigate/${encodeURIComponent(flag.account_id)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ corridor: flag.corridor }),
        },
      );
      router.push("/cases/" + r.case_id);
    } catch (e) {
      setError((e as Error).message);
      setPending("");
    }
  };
  const visibleFlags = flags.filter((flag) =>
    flag.account_id.toLowerCase().includes(search.trim().toLowerCase()),
  );
  return (
    <Shell>
      <main className="queue-page">
        <AnimatedContent>
          <div className="page-kicker">
            <span className="live-dot" /> CONNECTED EVIDENCE. CLEARER DECISIONS.
          </div>
          <div className="queue-heading">
            <div>
              <h1>Every transfer has a story.</h1>
              <p>Follow the connections. See the evidence. Make the call.</p>
            </div>
            <div className="corridor-stamp">
              <GlobeHemisphereWest size={22} />
              <span>
                United States <ArrowRight size={14} /> Nigeria
                <small>US–NG remittance corridor</small>
              </span>
            </div>
          </div>
        </AnimatedContent>
        <section className="queue-surface" aria-labelledby="queue-title">
          <div className="section-heading">
            <div className="inline">
              <h2 id="queue-title">Review queue</h2>
              <span className="count">{loading ? "…" : flags.length}</span>
            </div>
            <Button
              variant="ghost"
              onClick={refresh}
              disabled={loading}
              aria-label="Refresh queue"
            >
              <ArrowClockwise size={16} /> Refresh
            </Button>
          </div>
          <div className="queue-toolbar">
            <span>
              Flagged accounts{" "}
              <span className="muted">/ Latest representative transfer</span>
            </span>
            <label className="search">
              <MagnifyingGlass size={17} />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Find an account"
                aria-label="Find an account"
              />
            </label>
          </div>
          {error && (
            <div className="notice error" role="alert">
              {error}
            </div>
          )}
          <div
            className="table-scroll"
            tabIndex={0}
            role="region"
            aria-label="Flagged accounts table, scroll horizontally on small screens"
          >
            <table>
              <thead>
                <tr>
                  <th>Account</th>
                  <th>Latest transfer</th>
                  <th>Corridor</th>
                  <th>Case history</th>
                  <th>
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={5} className="empty-state">
                      Loading the review queue…
                    </td>
                  </tr>
                ) : (
                  visibleFlags.map((f, i) => {
                    const tx = f.transfers[0];
                    return (
                      <tr key={f.account_id}>
                        <td>
                          <div className="account-cell">
                            <span className="account-avatar">
                              <UserCircle size={24} />
                            </span>
                            <span>
                              <strong className="mono">{f.account_id}</strong>
                              <small>
                                Flagged for review{" "}
                                <span className="row-index">
                                  {String(i + 1).padStart(2, "0")}
                                </span>
                              </small>
                            </span>
                          </div>
                        </td>
                        <td>
                          <strong className="amount">
                            {tx
                              ? money(tx.amount, tx.currency)
                              : "No transfer in view"}
                          </strong>
                          <small>
                            {tx
                              ? `${date(tx.ts)} · ${String(tx.corridor ?? "Route unavailable")}`
                              : "Review connected account activity"}
                          </small>
                        </td>
                        <td>
                          <span className="route-code">
                            {f.corridor.replaceAll("-", " → ")}
                          </span>
                          <small>Review corridor</small>
                        </td>
                        <td>
                          <button
                            className="history-button"
                            aria-label={`View history for ${f.account_id}`}
                            onClick={() => setAccount(f.account_id)}
                          >
                            <ClockCounterClockwise size={16} />
                            {f.returning_account
                              ? "Returning account"
                              : "No prior cases"}
                            <ArrowUpRight size={13} />
                          </button>
                          {f.open_cases > 0 && (
                            <small className="amber">
                              {f.open_cases} active case
                              {f.open_cases === 1 ? "" : "s"}
                            </small>
                          )}
                        </td>
                        <td>
                          <Button
                            variant="primary"
                            disabled={!!pending || f.open_cases > 0}
                            onClick={() => start(f)}
                            aria-label={"Investigate " + f.account_id}
                          >
                            {pending === f.account_id
                              ? "Starting…"
                              : f.open_cases
                                ? "In progress"
                                : "Investigate"}
                            <ArrowRight size={16} />
                          </Button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
            {!loading && !visibleFlags.length && (
              <div className="empty-state">
                {flags.length
                  ? "No matching accounts. Try another ID."
                  : "No flags are available."}
              </div>
            )}
          </div>
          <div className="queue-caption">
            <span>
              Explore four realistic payment scenarios. You can investigate each
              again.
            </span>
            <span>
              Powered by FalkorDB <ArrowUpRight size={13} />
            </span>
          </div>
        </section>
        <section className="workflow-note">
          <span className="note-number">01 → 02 → 03</span>
          <div>
            <h3>From a flag to a traceable decision.</h3>
            <p>
              See who is connected, which policy applies, and who owns the next
              step. Every saved decision keeps its supporting evidence.
            </p>
          </div>
          <span className="quiet-label">
            Synthetic cases.
            <br />
            Real graph reasoning.
          </span>
        </section>
      </main>
      <Dialog.Root
        open={!!account}
        onOpenChange={(open) => {
          if (!open) setAccount("");
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="drawer-overlay" />
          <Dialog.Content className="history-drawer">
            <Dialog.Title>Account history</Dialog.Title>
            <Dialog.Description className="mono">{account}</Dialog.Description>
            <Dialog.Close asChild>
              <Button
                variant="ghost"
                className="drawer-close"
                aria-label="Close history"
              >
                <X size={20} />
              </Button>
            </Dialog.Close>
            <div className="drawer-body">
              {historyLoading ? (
                <p>Loading prior cases…</p>
              ) : historyError ? (
                <p role="alert">{historyError}</p>
              ) : !history.length ? (
                <p>No prior cases for this account.</p>
              ) : (
                history.map((c) => (
                  <Link
                    className="history-card"
                    href={"/cases/" + c.case_id}
                    key={c.case_id}
                  >
                    <div className="inline">
                      <Badge value={c.verdict} />
                      <span>{date(c.opened_at)}</span>
                      <ArrowUpRight size={15} />
                    </div>
                    <strong>
                      {c.pattern?.replaceAll("_", " ") ??
                        "Investigation in progress"}
                    </strong>
                    <small className="mono">{c.case_id}</small>
                    <p>
                      {c.key_findings?.[0] ??
                        "Open the case to inspect its evidence."}
                    </p>
                  </Link>
                ))
              )}
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </Shell>
  );
}
