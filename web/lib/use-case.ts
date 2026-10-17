"use client";
import { useEffect, useState, useRef } from "react";
import { api, acceptEvent } from "./evidence";
import type { CaseData, StreamEvent } from "./types";
export function useCase(caseId: string) {
  const [data, setData] = useState<CaseData | null>(null),
    [error, setError] = useState(""),
    [connection, setConnection] = useState("Loading case"),
    [epoch, setEpoch] = useState(0);
  const cursor = useRef(0);
  useEffect(() => {
    let active = true,
      source: EventSource | null = null,
      timer: ReturnType<typeof setTimeout> | undefined,
      busy = false,
      queued = false,
      ended = false,
      restored = false;
    cursor.current = 0;
    setError("");
    setConnection("Loading case");
    setData(null);
    const refresh = async () => {
      if (busy) {
        queued = true;
        return;
      }
      busy = true;
      try {
        const saved = await api<CaseData>(
          "/cases/" + encodeURIComponent(caseId),
        );
        if (!active) return;
        setData(saved);
        setError("");
        if (ended)
          setConnection(
            saved.case.status === "closed"
              ? "Saved case"
              : "Interrupted · review saved evidence",
          );
      } catch (e) {
        if (active) setError((e as Error).message);
      } finally {
        busy = false;
        if (queued && active) {
          queued = false;
          void refresh();
        }
      }
    };
    const schedule = () => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => void refresh(), 300);
    };
    const handle = (event: MessageEvent<string>) => {
      if (!event.data) return;
      let value: StreamEvent;
      try {
        value = JSON.parse(event.data);
      } catch {
        return;
      }
      const accepted = acceptEvent(cursor.current, event.lastEventId, value);
      if (!accepted) return;
      cursor.current = accepted.cursor;
      if (value.type === "snapshot") {
        restored = true;
        setConnection("Restored from saved evidence");
      }
      if (value.type === "error")
        setError(
          value.text ??
            "Investigation interrupted. Inspect saved evidence before retrying.",
        );
      if (
        value.type === "finding" ||
        value.type === "guardrail" ||
        value.type === "snapshot" ||
        value.type === "closed"
      )
        schedule();
      if (value.type === "end") {
        ended = true;
        source?.close();
        if (timer) clearTimeout(timer);
        void refresh();
      }
    };
    (async () => {
      await refresh();
      if (!active) return;
      source = new EventSource(
        "/api/cases/" + encodeURIComponent(caseId) + "/stream",
      );
      [
        "opened",
        "finding",
        "guardrail",
        "closed",
        "snapshot",
        "end",
        "error",
      ].forEach((type) =>
        source!.addEventListener(type, handle as EventListener),
      );
      source.onopen = () => {
        if (active && !restored) setConnection("Live investigation");
      };
      source.onerror = (event) => {
        if (event instanceof MessageEvent) return;
        if (active && !ended) setConnection("Connection lost · reconnecting");
      };
    })();
    return () => {
      active = false;
      source?.close();
      if (timer) clearTimeout(timer);
    };
  }, [caseId, epoch]);
  return { data, error, connection, retry: () => setEpoch((x) => x + 1) };
}
