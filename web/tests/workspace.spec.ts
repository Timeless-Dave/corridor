import { test, expect, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
const recorded = JSON.parse(
  fs.readFileSync(path.resolve("../docs/m5-live-verification.json"), "utf8"),
);
const fixture = recorded.saved;
fixture.grounding = [
  {
    policy: {
      id: "POL-AML-1",
      title: "Synthetic review policy 1",
      rule: "Fictional demo policy.",
    },
    source: { id: "DOC-1", title: "Fictional handbook 1" },
    precedent: { id: "DEC-6", summary: "Fictional precedent 6" },
    author: { id: "emp_6", name: "Fictional employee 6" },
    assignee: { id: "emp_0", name: "Fictional employee 0" },
    team: { id: "team_0", name: "Fictional team 0" },
  },
];
fixture.case.proposed_verdict = "FREEZE";
fixture.case.verdict = "MONITOR";
async function mock(page: Page) {
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    const p = url.pathname;
    if (p === "/api/flags")
      return route.fulfill({
        json: {
          flags: recorded.flags.flags.map((f: Record<string, unknown>) => ({
            ...f,
            open_cases: 0,
          })),
        },
      });
    if (p.includes("/investigate/"))
      return route.fulfill({ status: 202, json: { case_id: fixture.case.id } });
    if (p.endsWith("/history"))
      return route.fulfill({
        json: {
          cases: [
            {
              case_id: fixture.case.id,
              verdict: "MONITOR",
              pattern: "fan_in_mule",
              opened_at: 1792065600,
              key_findings: ["Recorded synthetic review"],
            },
          ],
        },
      });
    if (p.endsWith("/stream"))
      return route.fulfill({
        contentType: "text/event-stream",
        body: `id: 1\nevent: snapshot\ndata: ${JSON.stringify({ type: "snapshot", case_id: fixture.case.id, case: fixture.case, findings: fixture.findings })}\n\nid: 2\nevent: end\ndata: {"type":"end"}\n\n`,
      });
    return route.fulfill({ json: fixture });
  });
}
test("queue, start, saved verdict, replay, history and reload", async ({
  page,
}) => {
  await mock(page);
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Review queue" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Investigate collector_0", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Why this decision?" }),
  ).toBeVisible();
  await expect(
    page.getByText("Model proposed FREEZE. Code recorded MONITOR."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Why this decision?" }).click();
  await expect(
    page.getByText("Evidence replay", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Next evidence" }).click();
  await expect(page.locator(".finding-selected")).toHaveCount(1);
  await page
    .getByRole("button", { name: "Show accessible graph list" })
    .click();
  await expect(page.locator(".graph-list")).toBeVisible();
  await page.locator(".graph-list button").first().click();
  await expect(
    page.getByRole("heading", { name: "Node inspector" }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Why this decision?" }),
  ).toBeVisible();
  await page.locator(".back-link").click();
  await page
    .getByRole("button", { name: /Returning account/ })
    .first()
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
});
test("service errors and duplicate starts are actionable", async ({ page }) => {
  await mock(page);
  await page.route("**/api/investigate/*", (route) =>
    route.fulfill({ status: 409, json: { detail: "already running" } }),
  );
  await page.goto("/");
  await page
    .getByRole("button", { name: "Investigate collector_0", exact: true })
    .click();
  await expect(page.locator(".notice[role=alert]")).toContainText("history");
  await page.route("**/api/flags", (route) =>
    route.fulfill({ status: 503, json: {} }),
  );
  await page.getByRole("button", { name: "Refresh queue" }).click();
  await expect(page.locator(".notice[role=alert]")).toContainText(
    "unavailable",
  );
});
test("mobile and tablet tabs, reduced motion, keyboard focus and WebGL fallback", async ({
  page,
}) => {
  await mock(page);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (
      this: HTMLCanvasElement,
      type: string,
      ...args: unknown[]
    ) {
      if (type === "webgl" || type === "webgl2") return null;
      return original.apply(this, [type, ...args] as never);
    } as typeof original;
  });
  for (const width of [390, 820]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await expect(
      page.getByRole("button", {
        name: "Investigate collector_0",
        exact: true,
      }),
    ).toBeEnabled();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.goto("/cases/" + fixture.case.id);
    await page.getByRole("tab", { name: "Graph", exact: true }).click();
    await expect(
      page.getByText("3D is unavailable.", { exact: false }),
    ).toBeVisible();
    await page.getByRole("tab", { name: "Decision", exact: true }).click();
    await expect(
      page.getByRole("button", { name: "Why this decision?" }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.keyboard.press("Tab");
    expect(
      await page.evaluate(
        () => getComputedStyle(document.activeElement!).outlineStyle,
      ),
    ).not.toBe("none");
  }
});
test("browser reconnect resumes stream and accepts restart snapshot", async ({
  page,
}) => {
  await mock(page);
  let attempts = 0;
  await page.route("**/api/cases/*/stream", async (route) => {
    attempts++;
    if (attempts === 1) return route.abort();
    return route.fulfill({
      contentType: "text/event-stream",
      body:
        "id: 3\nevent: snapshot\ndata: " +
        JSON.stringify({ type: "snapshot", case: fixture.case }) +
        '\n\nid: 4\nevent: end\ndata: {"type":"end"}\n\n',
    });
  });
  await page.goto("/cases/" + fixture.case.id);
  await expect(page.getByText("Saved case", { exact: true })).toBeVisible({
    timeout: 20000,
  });
  expect(attempts).toBeGreaterThan(1);
});
