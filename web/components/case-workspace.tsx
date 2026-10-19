"use client";
import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import {
  ArrowLeft,
  ArrowRight,
  Play,
  Pause,
  Check,
  WarningCircle,
  ShieldCheck,
  Code,
  ArrowClockwise,
  Path,
  UserCircle,
  X,
  FileText,
} from "@phosphor-icons/react";
import { Shell, Badge } from "./shell";
import { Button } from "./ui/button";
import { AnimatedContent } from "./animated-content";
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from "./ui/resizable";
import { FreezeImpact } from "./freeze-impact";
import { useCase } from "@/lib/use-case";
import { label, parse, transferIds } from "@/lib/evidence";
import type { CaseData, Finding, GraphNode } from "@/lib/types";
const EvidenceGraph = dynamic(() => import("./evidence-graph"), {
  ssr: false,
  loading: () => <div className="graph-empty">Loading evidence graph…</div>,
});
function Properties({
  value,
}: {
  value: Record<string, unknown> | null | undefined;
}) {
  return (
    <dl className="property-list">
      {Object.entries(value ?? {}).map(([key, val]) => (
        <div key={key}>
          <dt>{key.replaceAll("_", " ")}</dt>
          <dd>{typeof val === "object" ? JSON.stringify(val) : String(val)}</dd>
        </div>
      ))}
    </dl>
  );
}
function RuleCheck({ check }: { check: NonNullable<CaseData["rule_check"]> }) {
  const rows: [boolean, string][] = [
    [
      check.corroborated_accounts.length > 0,
      check.corroborated_accounts.length
        ? check.corroborated_accounts
            .map((a) => `${a}: ${check.supports[a].map(label).join(" + ")}`)
            .join("; ")
        : "No account is cited by two independent positive evidence tools",
    ],
    [
      check.structural.length > 0,
      check.structural.length
        ? "Structural evidence: " + check.structural.map(label).join(", ")
        : "No PageRank or community result recorded",
    ],
    [
      check.scratch_plan,
      check.scratch_plan
        ? "Freeze measured on a scratch graph copy"
        : "No completed scratch-graph freeze plan",
    ],
  ];
  return (
    <div className="rule-check" aria-label="Freeze rule check">
      <strong>
        Freeze rule check:{" "}
        {check.freeze_allowed ? "all conditions met" : "FREEZE not allowed"}
      </strong>
      <ul>
        {rows.map(([ok, text]) => (
          <li key={text} className={ok ? "ok" : "missing"}>
            <span aria-hidden>{ok ? "✓" : "–"}</span> {text}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Decision({
  data,
  onReplay,
}: {
  data: CaseData;
  onReplay: () => void;
}) {
  const c = data.case,
    g = data.grounding?.[0],
    closed = c.status === "closed",
    reasons = Array.isArray(c.guardrail_reasons)
      ? c.guardrail_reasons
      : parse<string[]>(c.guardrail_reasons, []);
  return (
    <AnimatedContent className="decision-content">
      <div className="decision-label">
        <ShieldCheck size={20} />{" "}
        {closed ? "Recorded decision" : "Decision pending"}
      </div>
      {closed ? (
        <>
          <div className="verdict-title">
            <Badge value={String(c.verdict ?? "MONITOR")} />
            <div className="risk-value">
              {typeof c.risk === "number"
                ? Math.round(c.risk * 100) + "%"
                : "Unavailable"}
              <small>Model risk estimate</small>
            </div>
          </div>
          <h3>{String(c.pattern ?? "none").replaceAll("_", " ")}</h3>
          {c.error && (
            <div className="notice error">
              {c.error === "unknown_account"
                ? "Unknown account: an input error, not a clearance."
                : "Company grounding requires review."}
            </div>
          )}
          <p className="rationale">
            {String(
              c.rationale ?? "Review the saved findings for this decision.",
            )}
          </p>
          {data.rule_check && <RuleCheck check={data.rule_check} />}
          {c.proposed_verdict && c.proposed_verdict !== c.verdict && (
            <p className="override">
              Model proposed {String(c.proposed_verdict)}. Code recorded{" "}
              {String(c.verdict)}.
            </p>
          )}
          {reasons.length > 0 && (
            <div className="guardrail-summary">
              <strong>Code-enforced checks</strong>
              {reasons.map((r, i) => (
                <p key={i}>{r}</p>
              ))}
            </div>
          )}
          <Button
            variant="primary"
            onClick={onReplay}
            disabled={!data.findings.length}
          >
            <Path size={17} /> Why this decision?
          </Button>
        </>
      ) : (
        <p className="muted">
          The agent is gathering evidence. A decision appears after policy and
          precedent checks.
        </p>
      )}
      {closed && <FreezeImpact data={data} />}
      <div className="grounding-section">
        <h4>
          <FileText size={16} /> Company grounding
        </h4>
        <div className="grounding-item">
          <small>Applied policy</small>
          <strong>{String(g?.policy?.title ?? "Not assigned")}</strong>
          {g?.policy && (
            <>
              <span className="mono">{String(g.policy.id)}</span>
              <p>{String(g.policy.rule ?? "")}</p>
            </>
          )}
        </div>
        <div className="grounding-item">
          <small>Source document</small>
          <strong>{String(g?.source?.title ?? "Unavailable")}</strong>
          <span className="mono">{String(g?.source?.id ?? "")}</span>
        </div>
        <div className="grounding-item">
          <small>Precedent</small>
          <strong>{String(g?.precedent?.id ?? "Not assigned")}</strong>
          <p>{String(g?.precedent?.summary ?? "")}</p>
          <span>By {String(g?.author?.name ?? "unavailable author")}</span>
        </div>
        <div className="assignee">
          <UserCircle size={30} />
          <div>
            <strong>{String(g?.assignee?.name ?? "Unrouted")}</strong>
            <small>{String(g?.team?.name ?? "Analyst review required")}</small>
          </div>
        </div>
      </div>
      <details>
        <summary>Accounts in this decision</summary>
        <ul className="member-list">
          {(Array.isArray(data.routing.members) ? data.routing.members : [])
            .filter(
              (m: { id: string }, i: number, a: { id: string }[]) =>
                m.id && a.findIndex((n) => n.id === m.id) === i,
            )
            .map((m: { id: string; role: string }) => (
              <li key={m.id}>
                <span className="mono">{m.id}</span>
                <small>{m.role}</small>
              </li>
            ))}
        </ul>
      </details>
    </AnimatedContent>
  );
}
export function CaseWorkspace({ caseId }: { caseId: string }) {
  const { data, error, connection, retry } = useCase(caseId),
    [index, setIndex] = useState(-1),
    [node, setNode] = useState<GraphNode | null>(null),
    [replay, setReplay] = useState(false),
    [playing, setPlaying] = useState(false),
    [mobileTab, setMobileTab] = useState("evidence"),
    [wide, setWide] = useState(false);
  useEffect(() => {
    const m = window.matchMedia("(min-width: 1100px)");
    const update = () => setWide(m.matches);
    update();
    m.addEventListener("change", update);
    return () => m.removeEventListener("change", update);
  }, []);
  const findings = useMemo(
    () =>
      [...(data?.findings ?? [])].sort(
        (a, b) => a.step - b.step || a.id.localeCompare(b.id),
      ),
    [data?.findings],
  );
  const selected = findings[index];
  const evidence = data?.evidence.find((e) => e.finding_id === selected?.id);
  const transfers = useMemo(() => transferIds(selected), [selected]);
  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(
      () =>
        setIndex((i) => {
          if (i >= findings.length - 1) {
            setPlaying(false);
            return i;
          }
          return i + 1;
        }),
      2200,
    );
    return () => clearInterval(timer);
  }, [playing, findings.length]);
  const beginReplay = () => {
    setReplay(true);
    setIndex(0);
    setNode(null);
    setMobileTab("evidence");
  };
  const select = (i: number) => {
    setIndex(i);
    setPlaying(false);
    setNode(null);
  };
  const trail = (
    <section className="evidence-panel">
      <div className="panel-heading">
        <h2>Evidence trail</h2>
        <span>
          {findings.filter((f) => f.tool !== "guardrail").length}{" "}
          {findings.filter((f) => f.tool !== "guardrail").length === 1
            ? "step"
            : "steps"}
        </span>
      </div>
      <div className="trail-scroll">
        {!findings.length ? (
          <div className="empty-state">Waiting for the first finding…</div>
        ) : (
          findings.map((f, i) => {
            const cites =
                data?.evidence.find((e) => e.finding_id === f.id)?.cited ?? [],
              rejected = parse<string[]>(f.rejected_citations, []);
            return (
              <article
                key={f.id}
                className={
                  "finding " +
                  (index === i ? "finding-selected " : "") +
                  (f.tool === "guardrail" ? "guardrail" : "")
                }
              >
                <button
                  className="finding-select"
                  onClick={() => select(i)}
                  aria-pressed={index === i}
                >
                  <span className="step-number">
                    {f.tool === "guardrail" ? (
                      <ShieldCheck size={15} />
                    ) : (
                      String(f.step).padStart(2, "0")
                    )}
                  </span>
                  <span>
                    <strong>{label(f.tool)}</strong>
                    <small>
                      {f.interpretation_source === "deterministic"
                        ? "Deterministic check"
                        : "Evidence interpretation"}
                    </small>
                  </span>
                  <Check size={14} className="step-check" />
                </button>
                <p>{f.text}</p>
                <div className="finding-footer">
                  <span>
                    {cites.length} cited node{cites.length === 1 ? "" : "s"}
                  </span>
                  {rejected.length > 0 && (
                    <span className="amber">
                      {rejected.length} rejected citation
                      {rejected.length === 1 ? "" : "s"}
                    </span>
                  )}
                </div>
                <details>
                  <summary>
                    <Code size={13} /> Technical details
                  </summary>
                  <small>Parameters</small>
                  <pre>{JSON.stringify(parse(f.params, {}), null, 2)}</pre>
                  <small>Raw result</small>
                  <pre>{JSON.stringify(parse(f.result_json, []), null, 2)}</pre>
                  {data?.evidence.find((e) => e.finding_id === f.id)
                    ?.query_text && (
                    <>
                      <small>Fixed Cypher query</small>
                      <pre>
                        {
                          data.evidence.find((e) => e.finding_id === f.id)
                            ?.query_text
                        }
                      </pre>
                    </>
                  )}
                </details>
              </article>
            );
          })
        )}
      </div>
    </section>
  );
  const graph = data ? (
    <EvidenceGraph
      graph={data.subgraph}
      cited={evidence?.cited ?? []}
      transfers={transfers}
      selected={node?.id ?? ""}
      onSelect={(n) => {
        setNode(n);
        setMobileTab("decision");
      }}
    />
  ) : (
    <div className="empty-state">Loading case…</div>
  );
  const inspector = (
    <section className="inspector">
      <div className="panel-heading">
        <h2>{node ? "Node inspector" : "Decision & context"}</h2>
        {node && (
          <Button
            variant="ghost"
            aria-label="Close node inspector"
            onClick={() => setNode(null)}
          >
            <X size={16} />
          </Button>
        )}
      </div>
      <div className="inspector-scroll">
        {node ? (
          <>
            <span className="node-kind">{node.labels.join(" · ")}</span>
            <h3 className="mono node-title">{node.id}</h3>
            <Properties value={node.properties} />
          </>
        ) : data ? (
          <Decision key={data.case.status} data={data} onReplay={beginReplay} />
        ) : (
          <p>Loading company context…</p>
        )}
      </div>
    </section>
  );
  return (
    <Shell caseView>
      <main className="case-page">
        <div className="case-heading">
          <div>
            <div className="case-eyebrow">
              ACCOUNT INVESTIGATION{" "}
              <span className="mono">{caseId.slice(0, 17)}</span>
            </div>
            <h1>
              {data?.case.requested_account_id ?? "Case evidence"}{" "}
              <Badge
                value={
                  data?.case.status === "closed" ? data.case.verdict : "OPEN"
                }
              />
            </h1>
          </div>
          <div className="case-state" role="status" aria-live="polite">
            <span
              className={connection === "Live investigation" ? "live-dot" : ""}
            />
            {connection}
            {data?.case.step_cap_reached === true && (
              <span className="amber">Step cap reached</span>
            )}
            <Button variant="ghost" onClick={retry} aria-label="Refresh case">
              <ArrowClockwise size={17} />
            </Button>
          </div>
        </div>
        {error && (
          <div className="notice error" role="alert">
            <WarningCircle size={18} />
            {error}
            <Button variant="ghost" onClick={retry}>
              Retry
            </Button>
          </div>
        )}
        {replay && (
          <div className="replay-bar">
            <span>
              <Path size={17} /> Evidence replay
            </span>
            <span>
              {index + 1} of {findings.length}
            </span>
            <Button
              variant="ghost"
              aria-label="Previous evidence"
              disabled={index <= 0}
              onClick={() => select(index - 1)}
            >
              <ArrowLeft size={17} />
            </Button>
            <Button
              variant="secondary"
              aria-label={playing ? "Pause replay" : "Play replay"}
              disabled={index >= findings.length - 1}
              onClick={() => setPlaying(!playing)}
            >
              {playing ? <Pause size={16} /> : <Play size={16} />}
            </Button>
            <Button
              variant="ghost"
              aria-label="Next evidence"
              disabled={index >= findings.length - 1}
              onClick={() => select(index + 1)}
            >
              <ArrowRight size={17} />
            </Button>
            <span className="replay-tool">
              {selected ? label(selected.tool) : ""}
            </span>
            <Button
              variant="ghost"
              aria-label="Exit replay"
              onClick={() => {
                setReplay(false);
                setPlaying(false);
                setIndex(-1);
              }}
            >
              <X size={16} />
            </Button>
          </div>
        )}
        <div className="workspace">
          {wide ? (
            <ResizablePanelGroup direction="horizontal">
              <ResizablePanel defaultSize={27} minSize={21}>
                {trail}
              </ResizablePanel>
              <ResizableHandle />
              <ResizablePanel defaultSize={47} minSize={30}>
                {graph}
              </ResizablePanel>
              <ResizableHandle />
              <ResizablePanel defaultSize={26} minSize={21}>
                {inspector}
              </ResizablePanel>
            </ResizablePanelGroup>
          ) : (
            <Tabs.Root
              value={mobileTab}
              onValueChange={setMobileTab}
              className="mobile-workspace"
            >
              <Tabs.List
                className="mobile-tabs"
                aria-label="Investigation panels"
              >
                <Tabs.Trigger value="evidence">Evidence</Tabs.Trigger>
                <Tabs.Trigger value="graph">Graph</Tabs.Trigger>
                <Tabs.Trigger value="decision">Decision</Tabs.Trigger>
              </Tabs.List>
              <Tabs.Content value="evidence">{trail}</Tabs.Content>
              <Tabs.Content value="graph">{graph}</Tabs.Content>
              <Tabs.Content value="decision">{inspector}</Tabs.Content>
            </Tabs.Root>
          )}
        </div>
        <div className="case-footer">
          <span>Every finding links to the graph nodes it cites.</span>
          <span>Synthetic data · nothing real is frozen</span>
        </div>
      </main>
    </Shell>
  );
}
