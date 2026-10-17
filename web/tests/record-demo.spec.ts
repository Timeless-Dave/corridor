import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

test("record a saved-case walkthrough for participant narration", async ({
  browser,
}) => {
  test.skip(
    process.env.CORRIDOR_RECORD_DEMO !== "1",
    "Explicit local recording only",
  );
  test.setTimeout(180000);
  const report = JSON.parse(
    fs.readFileSync(path.resolve("../docs/m7-live-verification.json"), "utf8"),
  );
  const context = await browser.newContext({
    baseURL: "http://127.0.0.1:3001",
    viewport: { width: 1440, height: 960 },
    recordVideo: {
      dir: path.resolve("../docs/demo/raw"),
      size: { width: 1440, height: 960 },
    },
  });
  const page = await context.newPage();
  const video = page.video()!;
  try {
    await page.goto("/");
    await expect(
      page.getByRole("button", {
        name: "Investigate collector_0",
        exact: true,
      }),
    ).toBeVisible();
    await page.waitForTimeout(8000);
    await page.goto(report.browser_paths[0]);
    await expect(
      page.getByRole("button", { name: "Why this decision?" }),
    ).toBeVisible();
    await page.waitForTimeout(6000);
    await page.getByRole("button", { name: "Use flat view" }).click();
    await page.waitForTimeout(5000);
    await page.getByRole("button", { name: "Fit graph to view" }).click();
    await page.getByRole("button", { name: "Why this decision?" }).click();
    await page.waitForTimeout(5000);
    await page.getByRole("button", { name: "Next evidence" }).click();
    await page.waitForTimeout(6000);
    await page.goto(report.browser_paths[1]);
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      report.second_account,
    );
    const first = page.locator(".finding").first();
    await first.getByText("Technical details", { exact: true }).click();
    await expect(first).toContainText(report.first_case.case_id);
    await page.waitForTimeout(12000);
  } finally {
    await context.close();
    await video.saveAs(
      path.resolve("../docs/demo/corridor-saved-walkthrough.webm"),
    );
  }
});
