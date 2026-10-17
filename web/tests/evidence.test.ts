import { describe, it, expect } from "vitest";
import {
  acceptEvent,
  transferIds,
  exactEdge,
  parse,
  message,
} from "../lib/evidence";
import type { Finding, GraphEdge } from "../lib/types";
describe("persisted evidence and event cursors", () => {
  it("deduplicates reconnect delivery without losing new events", () => {
    let cursor = 0;
    const events = [];
    for (const id of ["1", "2", "2", "1", "3"]) {
      const result = acceptEvent(cursor, id, { type: "finding", case_id: "c" });
      if (result) {
        cursor = result.cursor;
        events.push(result.event);
      }
    }
    expect(events).toHaveLength(3);
    expect(cursor).toBe(3);
  });
  it("accepts a durable snapshot after the current cursor", () => {
    expect(
      acceptEvent(6, "7", { type: "snapshot", case_id: "c" }),
    ).toMatchObject({ cursor: 7, event: { type: "snapshot" } });
    expect(acceptEvent(6, "NaN", { type: "end", case_id: "c" })).toBeNull();
  });
  it("highlights only explicit transfer identities, not every adjacent edge", () => {
    const f = {
      result_json: JSON.stringify([
        { transfers: ["tx-1"], edge_ids: ["tx-2"], accounts: ["a", "b"] },
      ]),
    } as Finding;
    const ids = transferIds(f);
    expect([...ids]).toEqual(["tx-1", "tx-2"]);
    expect(
      exactEdge(
        {
          id: 1,
          source: "a",
          target: "b",
          type: "SENT",
          properties: { id: "tx-1" },
        } as GraphEdge,
        ids,
      ),
    ).toBe(true);
    expect(
      exactEdge(
        {
          id: 2,
          source: "a",
          target: "b",
          type: "SENT",
          properties: { id: "unrelated" },
        } as GraphEdge,
        ids,
      ),
    ).toBe(false);
    expect(exactEdge({ properties: {} } as GraphEdge, ids)).toBe(false);
  });
  it("handles historical records without raw results", () => {
    expect(transferIds({} as Finding).size).toBe(0);
    expect(parse("bad", [])).toEqual([]);
  });
  it("provides actionable failure states", () => {
    expect(message(409)).toContain("history");
    expect(message(429)).toContain("Wait");
    expect(message(503)).toContain("retry");
  });
});
