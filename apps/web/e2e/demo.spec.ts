import { expect, test } from "@playwright/test";

test("a new visitor can trace a payment change to highlighted PDF evidence", async ({
  page,
}) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "Find the line item behind a payment change." }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Start audit/i }).click();
  await expect(
    page.getByRole("heading", {
      name: "Building an evidence trail, not a chain of thought.",
    }),
  ).toBeVisible();

  await page.getByRole("button", { name: "View completed demo now" }).click();
  await expect(
    page.getByRole("heading", {
      name: "Tax projection is $613.17 above the county bill",
    }),
  ).toBeVisible();
  await expect(page.getByRole("table")).toContainText("+$51.10");

  await page.getByRole("button", { name: /Open evidence/i }).click();
  await expect(page.getByRole("heading", { name: "Evidence viewer" })).toBeVisible();
  await expect(page.getByAltText("2025 property tax bill, page 1")).toBeVisible();
  await expect(page.getByLabel("Highlighted evidence: $11,552.00")).toBeVisible();

  await page.getByRole("tab", { name: "Annual escrow analysis" }).click();
  await expect(page.getByLabel("Highlighted evidence: $12,165.17")).toBeVisible();
  await expect(page.getByLabel("Action draft")).toHaveValue(/\$613\.17/);
});
