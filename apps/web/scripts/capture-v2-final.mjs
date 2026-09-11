import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium, expect } from "@playwright/test";
const root = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../..",
);
const directory = path.join(root, "docs/verification");
const args = Object.fromEntries(
  process.argv.slice(2).map((value) => value.replace(/^--/, "").split("=")),
);
const panelId = args.panel || "PNL-001";
const requiredVersion = args.version || "v2";
const secrets = Object.fromEntries(
  fs
    .readFileSync(path.join(root, ".env"), "utf8")
    .split(/\r?\n/)
    .filter((line) => line && !line.startsWith("#"))
    .map((line) => {
      const at = line.indexOf("=");
      return [line.slice(0, at), line.slice(at + 1)];
    }),
);
const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1440, height: 1100 },
  baseURL: process.env.E2E_BASE_URL || "http://127.0.0.1:3000",
});
const page = await context.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
page.on("console", (message) => {
  if (message.type() === "error") errors.push(message.text());
});
async function screenshot(name) {
  await page.evaluate(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
    return new Promise((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(resolve)),
    );
  });
  await page.screenshot({ path: path.join(directory, name), fullPage: true });
}
try {
  await page.goto("/");
  await page
    .getByLabel("Kullanıcı adı", { exact: true })
    .fill(process.env.ADMIN_USERNAME || secrets.ADMIN_USERNAME);
  await page
    .getByLabel("Parola", { exact: true })
    .fill(process.env.ADMIN_PASSWORD || secrets.ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Güvenli giriş yap" }).click();
  await expect(
    page.getByText("Yerel API bağlı", { exact: true }),
  ).toBeVisible();
  const token = await page.evaluate(
    () =>
      JSON.parse(sessionStorage.getItem("gridsentinel.session")).access_token,
  );
  const response = await context.request.get(`/api/panels/${panelId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.ok()).toBeTruthy();
  const panel = await response.json();
  expect(panel.pending_current_run).toBe(false);
  expect(panel.scenario).toBe("normal_operation");
  expect(panel.state).toBe("NORMAL");
  expect(panel.current_run_alarms).toHaveLength(0);
  await page.getByLabel("Pano ara").fill(panelId);
  await page
    .getByRole("button", { name: `${panelId} pano detayını aç` })
    .click();
  await expect(
    page.locator(".score-card").first().locator("strong"),
  ).toContainText(String(panel.risk_score));
  await expect(
    page.getByRole("button", {
      name: "Alarmlar (0) · Bu çalışma",
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "H1", exact: true }).click();
  await expect(page.locator(".sensor-title")).toContainText("TH-A / H1");
  await expect(page.locator(".sensor-title")).not.toContainText(
    "ölçüm bekleniyor",
  );
  await screenshot("v2-panel-clean.png");
  await page
    .getByRole("button", { name: "Yaygınlaştırma", exact: true })
    .click();
  const proof = JSON.parse(
    fs.readFileSync(
      path.join(root, "apps/web/src/data/scale-proof.json"),
      "utf8",
    ),
  );
  expect(proof.version).toBe(requiredVersion);
  await expect(page.locator(".scale-proof")).toContainText(
    `${requiredVersion.toUpperCase()} KANITI`,
  );
  await expect(page.locator(".scale-proof")).toContainText(proof.source_label);
  await expect(page.locator(".scale-proof")).toContainText(proof.source_path);
  await expect(page.locator(".scale-proof tbody tr")).toHaveCount(
    proof.cases.length,
  );
  await screenshot("v2-scale-value.png");
  expect(errors).toEqual([]);
  const result = {
    timestamp: new Date().toISOString(),
    passed: true,
    mode: "read_only_ui_capture",
    panel: panelId,
    demo_run_id: panel.demo_run_id,
    current_run_alarms: panel.current_run_alarms.length,
    panel_state: panel.state,
    risk_score: panel.risk_score,
    scale_version: proof.version,
    scale_source: proof.source_path,
    scale_source_sha256: proof.source_sha256,
    console_errors: errors,
    screenshots: ["v2-panel-clean.png", "v2-scale-value.png"],
  };
  fs.writeFileSync(
    path.join(directory, "v2-frontend-final-smoke.json"),
    JSON.stringify(result, null, 2),
  );
  console.log(JSON.stringify(result));
} finally {
  await browser.close();
}
