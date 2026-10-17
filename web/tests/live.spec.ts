import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
test("live browser investigation and saved pattern review", async ({
  page,
}) => {
  test.skip(
    process.env.CORRIDOR_LIVE_BROWSER !== "1",
    "Explicit live model verification only",
  );
  test.setTimeout(300000);
  const folder = path.resolve("../docs/screenshots");
  fs.mkdirSync(folder, { recursive: true });
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Investigate shared_0", exact: true }),
  ).toBeEnabled({ timeout: 45000 });
  await page.screenshot({
    path: path.join(folder, "m6-queue-desktop.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Investigate shared_0", exact: true })
    .click();
  await page.waitForURL("**/cases/**");
  const caseId = page.url().split("/").pop()!;
  await page.evaluate((id) => {
    const state = window as typeof window & {
      verificationEvents?: { type: string; at: number }[];
    };
    state.verificationEvents = [];
    const stream = new EventSource("/api/cases/" + id + "/stream");
    ["opened", "finding", "guardrail", "closed", "end"].forEach((type) =>
      stream.addEventListener(type, () => {
        state.verificationEvents!.push({ type, at: Date.now() });
        if (type === "end") stream.close();
      }),
    );
  }, caseId);
  await expect(page.locator(".finding").first()).toBeVisible({
    timeout: 90000,
  });
  await page.screenshot({
    path: path.join(folder, "m6-live-investigation.png"),
    fullPage: true,
  });
  await expect(
    page.getByRole("button", { name: "Why this decision?" }),
  ).toBeVisible({ timeout: 220000 });
  await expect(page.getByText("Saved case", { exact: true })).toBeVisible({
    timeout: 45000,
  });
  await expect(page.locator("canvas")).toBeVisible();
  await page.getByRole("button", { name: "Fit graph to view" }).click();
  await page.getByRole("button", { name: "Use flat view" }).click();
  await page.getByRole("button", { name: "Use spatial view" }).click();
  await page.getByRole("button", { name: "Zoom in" }).click();
  await page.getByRole("button", { name: "Zoom out" }).click();
  await page.screenshot({
    path: path.join(folder, "m6-verdict-desktop.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Why this decision?" }).click();
  await page.getByRole("button", { name: "Next evidence" }).click();
  await page.screenshot({
    path: path.join(folder, "m6-evidence-replay.png"),
    fullPage: true,
  });
  const events = await page.evaluate(
    () =>
      (
        window as typeof window & {
          verificationEvents?: { type: string; at: number }[];
        }
      ).verificationEvents ?? [],
  );
  expect(events.some((e) => e.type === "end")).toBe(true);
  expect(
    Math.max(...events.map((e) => e.at)) - Math.min(...events.map((e) => e.at)),
  ).toBeGreaterThan(500);
  const saved = await (await page.request.get("/api/cases/" + caseId)).json();
  expect(saved.case.status).toBe("closed");
  expect(saved.grounding[0].source.id).toBe("DOC-1");
  const prior = JSON.parse(
    fs.readFileSync(path.resolve("../docs/m3-live-verification.json"), "utf8"),
  );
  const reviewed = [];
  for (const run of prior.runs) {
    await page.goto("/cases/" + run.decision.case_id);
    await expect(
      page.getByRole("button", { name: "Why this decision?" }),
    ).toBeVisible({ timeout: 45000 });
    await expect(page.locator("canvas")).toBeVisible();
    reviewed.push({ account: run.account_id, case_id: run.decision.case_id });
  }
  await page.setViewportSize({ width: 820, height: 1000 });
  await page.getByRole("tab", { name: "Graph", exact: true }).click();
  await expect(page.locator("canvas")).toBeVisible();
  await page.screenshot({
    path: path.join(folder, "m6-tablet-graph.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("tab", { name: "Decision", exact: true }).click();
  await page.screenshot({
    path: path.join(folder, "m6-mobile-verdict.png"),
    fullPage: true,
  });
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Investigate collector_0", exact: true }),
  ).toBeEnabled();
  await page.screenshot({
    path: path.join(folder, "m6-mobile-queue.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  fs.writeFileSync(
    path.resolve("../docs/m6-live-verification.json"),
    JSON.stringify(
      {
        recorded_at: new Date().toISOString(),
        case_id: caseId,
        verdict: saved.case.verdict,
        events,
        reviewed,
        grounding: saved.grounding,
        errors,
      },
      null,
      2,
    ) + "\n",
  );
  expect(errors).toEqual([]);
});
