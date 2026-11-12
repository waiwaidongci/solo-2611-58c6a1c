const { chromium } = require("../../node_modules/playwright");
const fs = require("fs");
const path = require("path");

const base = process.env.BASE_URL || "http://localhost:18221";
const out = process.env.SCREENSHOT_DIR || path.join(__dirname, "..", "screenshots");
fs.mkdirSync(out, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const consoleErrors = [];
  page.on("console", (msg) => { if (msg.type() === "error") consoleErrors.push(msg.text()); });
  await page.goto(`${base}/login`, { waitUntil: "networkidle" });
  await page.screenshot({ path: path.join(out, "01-login.png"), fullPage: false });
  await page.getByRole("button", { name: "登录" }).click();
  await page.waitForURL("**/overview", { timeout: 30000 });
  await page.waitForSelector(".stat-row", { timeout: 30000 });
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: path.join(out, "02-overview.png"), fullPage: false });
  await page.getByRole("link", { name: /资产/ }).click();
  await page.waitForURL("**/datasets");
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: path.join(out, "03-datasets.png"), fullPage: false });
  await page.getByRole("link", { name: /编排/ }).click();
  await page.waitForURL("**/analyses");
  await page.waitForSelector(".grid-main", { timeout: 30000 });
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: path.join(out, "04-analyses.png"), fullPage: false });

  const token = await page.evaluate(() => localStorage.getItem("analytics_token"));
  const headers = { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
  const analyses = await page.evaluate(async (headers) => {
    const response = await fetch("/api/analyses", { headers });
    if (!response.ok) throw new Error(`analysis list failed: ${response.status}`);
    return response.json();
  }, headers);
  if (!analyses.items?.length) throw new Error("seed analysis missing");
  const run = await page.evaluate(async ({ id, headers }) => {
    const response = await fetch(`/api/analyses/${id}/run`, { method: "POST", headers });
    if (!response.ok) throw new Error(`run failed: ${response.status} ${await response.text()}`);
    return response.json();
  }, { id: analyses.items[0].id, headers });
  await page.goto(`${base}/runs/${run.id}`, { waitUntil: "networkidle" });
  await page.waitForSelector(".run-headline", { timeout: 30000 });
  await page.screenshot({ path: path.join(out, "05-result.png"), fullPage: true });
  await page.screenshot({ path: path.join(out, "06-result-viewport.png"), fullPage: false });
  fs.writeFileSync(path.join(out, "console-errors.json"), JSON.stringify(consoleErrors, null, 2));
  console.log(JSON.stringify({ screenshots: 6, runId: run.id, consoleErrors: consoleErrors.length }, null, 2));
  await browser.close();
})().catch((error) => { console.error(error); process.exit(1); });
