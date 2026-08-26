import fs from "node:fs/promises";
import path from "node:path";

import { chromium } from "@playwright/test";

const baseURL = process.env.DEMO_BASE_URL ?? "http://127.0.0.1:3000";
const holdScale = Number(process.env.DEMO_HOLD_SCALE ?? "1");
const outputDirectory = path.resolve(process.cwd(), "../../docs/demo/raw");
const outputPath = path.join(outputDirectory, "servicerswitch-demo.webm");

await fs.mkdir(outputDirectory, { recursive: true });

const browser = await chromium.launch();
const context = await browser.newContext({
  recordVideo: { dir: outputDirectory, size: { height: 720, width: 1280 } },
  viewport: { height: 720, width: 1280 },
});
const page = await context.newPage();
const video = page.video();

const hold = (milliseconds) => page.waitForTimeout(milliseconds * holdScale);
const show = async (locator, milliseconds) => {
  await locator.scrollIntoViewIfNeeded();
  await hold(milliseconds);
};

await page.goto(baseURL, { waitUntil: "networkidle" });
await page
  .getByRole("heading", { name: "Find the line item behind a payment change." })
  .waitFor();
await hold(10_000);

await page.getByRole("radio", { name: /Tax projection error/i }).click();
await hold(7_000);
await page.getByRole("button", { name: /Start audit/i }).click();
await hold(4_500);

await page.getByRole("heading", { name: /Tax projection is/i }).waitFor();
await hold(13_000);
await show(page.getByRole("heading", { name: /Payment change decomposition/i }), 18_000);
await show(page.getByRole("heading", { name: "Findings" }), 13_000);
await show(page.getByRole("heading", { name: /What ran/i }), 8_000);

await page.getByRole("button", { name: /Open evidence/i }).click();
await page.getByRole("heading", { name: /Evidence viewer/i }).waitFor();
await hold(13_000);
await show(page.getByRole("heading", { name: /Evidence viewer/i }), 13_000);

await page.getByRole("tab", { name: /Annual escrow analysis/i }).click();
await hold(15_000);
await page.getByRole("tab", { name: /2025 property tax bill/i }).click();
await hold(8_000);

await show(page.getByRole("heading", { name: /Why this deserves review/i }), 15_000);
await show(page.getByRole("heading", { name: /Draft a servicer request/i }), 17_000);
await show(page.getByRole("heading", { name: /Evidence viewer/i }), 8_000);
await show(page.getByRole("heading", { name: /Tax projection is/i }), 15_000);

await context.close();
await video.saveAs(outputPath);
await browser.close();

console.log(`Recorded demo to ${outputPath}`);
