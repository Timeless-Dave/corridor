import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

test("saved cross-account memory is visible in step-one technical evidence", async ({
  page,
}) => {
  test.skip(
    process.env.CORRIDOR_MEMORY_BROWSER !== "1",
    "Requires completed M7 live report and local servers",
  );
  const report = JSON.parse(
    fs.readFileSync(path.resolve("../docs/m7-live-verification.json"), "utf8"),
  );
  expect(report.verified).toBe(true);
  expect(report.first_account).not.toBe(report.second_account);
  await page.goto(report.browser_paths[1]);
  await expect(
    page.getByRole("heading", { level: 1 }),
  ).toContainText(report.second_account);
  const finding = page.locator(".finding").first();
  await expect(finding).toContainText("Review account history");
  await finding.getByText("Technical details", { exact: true }).click();
  await expect(finding).toContainText(report.first_case.case_id);
  await page.screenshot({
    path: path.resolve("../docs/screenshots/m7-memory-step-one.png"),
    fullPage: true,
  });
});
