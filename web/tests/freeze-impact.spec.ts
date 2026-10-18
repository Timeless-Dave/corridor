import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const saved = JSON.parse(fs.readFileSync(path.resolve("../docs/m5-live-verification.json"), "utf8")).saved;
const before = { inflow_volume: 4866, senders_reaching_collector: 12, cycles_remaining: 0 };
const after = { inflow_volume: 0, senders_reaching_collector: 0, cycles_remaining: 0 };
const plan = { plan_id: "test-plan", collector: "collector_0", freeze_ids: ["collector_0"], before, after, steps: [{ account: "collector_0", after, outside_community_counterparties: [], outside_candidate_counterparties: [] }], method: "PageRank-ordered greedy heuristic; not a minimum-set guarantee", scope: "Bounded historical routes, not future savings.", scratch_deleted: true };

test("modeled approval requires explicit confirmation and shows a durable receipt", async ({ page }) => {
  let approved = false;
  await page.route("**/api/**", async (route) => {
    const url = route.request().url();
    if (url.endsWith("/freeze-impact")) return route.fulfill({ json: { plan, orders: approved ? [{ order: { id: "freeze-test", status: "measured" }, measurement: { before: JSON.stringify(before), after: JSON.stringify(after), matched_projection: true } }] : [] } });
    if (url.endsWith("/approve-freeze")) {
      expect(route.request().postDataJSON()).toEqual({ plan_id: "test-plan", confirm_simulated_freeze: true });
      expect(route.request().headers()["x-approval-token"]).toBe("test-only-token");
      approved = true;
      return route.fulfill({ json: { matched_projection: true } });
    }
    if (url.endsWith("/stream")) return route.fulfill({ contentType: "text/event-stream", body: 'id: 1\nevent: end\ndata: {"type":"end"}\n\n' });
    return route.fulfill({ json: { ...saved, case: { ...saved.case, status: "closed", verdict: "FREEZE" } } });
  });
  await page.goto(`/cases/${saved.case.id}`);
  await expect(page.getByRole("heading", { name: "What would a freeze interrupt?" })).toBeVisible();
  await page.getByText("Approve modeled freeze", { exact: true }).click();
  const approve = page.getByRole("button", { name: "Apply modeled freeze and measure" });
  await expect(approve).toBeDisabled();
  await page.getByLabel("Operator approval token").fill("test-only-token");
  await expect(approve).toBeDisabled();
  await page.getByLabel("I approve this exact plan’s modeled transfer blocks.").check();
  await approve.click();
  await expect(page.getByText("Measured outcome matches the projection.")).toBeVisible();
  await page.reload();
  await expect(page.getByText("freeze-test", { exact: true })).toBeVisible();
  await expect(approve).toHaveCount(0);
});

test("MONITOR cases can inspect impact but cannot approve", async ({ page }) => {
  await page.route("**/api/**", async (route) => {
    if (route.request().url().endsWith("/freeze-impact")) return route.fulfill({ json: { plan, orders: [] } });
    if (route.request().url().endsWith("/stream")) return route.fulfill({ contentType: "text/event-stream", body: 'id: 1\nevent: end\ndata: {"type":"end"}\n\n' });
    return route.fulfill({ json: { ...saved, case: { ...saved.case, status: "closed", verdict: "MONITOR" } } });
  });
  await page.goto(`/cases/${saved.case.id}`);
  await expect(page.getByText("Exploration only. A closed FREEZE decision is required for approval.")).toBeVisible();
  await expect(page.getByText("Approve modeled freeze", { exact: true })).toHaveCount(0);
});
