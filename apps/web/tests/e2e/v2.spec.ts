import {
  test,
  expect,
  type Page,
  type APIRequestContext,
} from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import type { Panel } from "../../src/lib/types";

const root = path.resolve(__dirname, "../../../..");
const proof = path.join(root, "docs/verification");
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
const observations: Record<string, unknown> = {
  recorded_at: new Date().toISOString(),
  target: process.env.E2E_BASE_URL || "http://127.0.0.1:3000",
  scope:
    "Local Docker V2 UI; synthetic telemetry; no external delivery or device writes",
};
function record(key: string, value: unknown) {
  observations[key] = value;
  const existing = fs.existsSync(
    path.join(proof, "v2-frontend-observations.json"),
  )
    ? JSON.parse(
        fs.readFileSync(
          path.join(proof, "v2-frontend-observations.json"),
          "utf8",
        ),
      )
    : {};
  fs.writeFileSync(
    path.join(proof, "v2-frontend-observations.json"),
    JSON.stringify({ ...existing, ...observations }, null, 2),
  );
}
const browserErrors = new WeakMap<Page, string[]>();
test.beforeEach(({ page }) => {
  const errors: string[] = [];
  browserErrors.set(page, errors);
  page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(`console: ${message.text()}`);
  });
});
test.afterEach(async ({ page }, info) => {
  const errors = browserErrors.get(page) || [];
  await info.attach("browser-errors", {
    body: JSON.stringify(errors),
    contentType: "application/json",
  });
  record(`browser_errors: ${info.title}`, {
    observed_at: new Date().toISOString(),
    errors,
  });
  expect(errors).toEqual([]);
});
async function login(page: Page, viewer = false) {
  await page.goto("/");
  await page
    .getByLabel("Kullanıcı adı", { exact: true })
    .fill(
      viewer ? "viewer" : process.env.ADMIN_USERNAME || secrets.ADMIN_USERNAME,
    );
  await page
    .getByLabel("Parola", { exact: true })
    .fill(
      process.env[viewer ? "VIEWER_PASSWORD" : "ADMIN_PASSWORD"] ||
        secrets[viewer ? "VIEWER_PASSWORD" : "ADMIN_PASSWORD"],
    );
  await page.getByRole("button", { name: "Güvenli giriş yap" }).click();
  await expect(
    page.getByRole("heading", { name: "Filonun nabzı, tek ekranda." }),
  ).toBeVisible();
  await expect(
    page.getByText("Yerel API bağlı", { exact: true }),
  ).toBeVisible();
  return page.evaluate(
    () =>
      JSON.parse(sessionStorage.getItem("gridsentinel.session")!)
        .access_token as string,
  );
}
async function openPanel(page: Page) {
  await page.getByLabel("Pano ara").fill("PNL-001");
  await page.getByRole("button", { name: "PNL-001 pano detayını aç" }).click();
  await expect(
    page.getByRole("heading", { name: "Pano izleme şeması" }),
  ).toBeVisible();
}
async function getPanel(request: APIRequestContext, token: string) {
  const response = await request.get("/api/panels/PNL-001", {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.ok()).toBeTruthy();
  return response.json() as Promise<Panel>;
}
async function shot(page: Page, name: string) {
  const closeToast = page.getByRole("button", {
    name: "Bildirimi kapat",
    exact: true,
  });
  if (await closeToast.isVisible()) await closeToast.click();
  await page.evaluate(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
    return new Promise<void>((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
    );
  });
  await page.screenshot({
    path: path.join(proof, `v2-${name}.png`),
    fullPage: !["fleet", "notifications"].includes(name),
  });
}

test("V2 focused thermal-PD run proves ordered warning and new-run isolation without deleting history", async ({
  page,
  request,
}) => {
  test.setTimeout(190000);
  const token = await login(page);
  await shot(page, "fleet");
  await openPanel(page);
  const old = await getPanel(request, token);
  const started = Date.now();
  const post = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/demo/scenario") &&
      response.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Termal + PD demosu", exact: true })
    .click();
  const selection = await post;
  expect(selection.request().postDataJSON()).toMatchObject({
    panel_id: "PNL-001",
    scenario: "combined_thermal_pd",
    focus: true,
  });
  expect(selection.ok()).toBeTruthy();
  const run = await selection.json();
  expect(run.demo_run_id).not.toBe(old.demo_run_id);
  await expect(
    page.getByRole("button", { name: "Bu demo çalışması", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  const policyProof: Record<string, unknown> = { run_id: run.demo_run_id };
  // Capture real run responses. Freeze only browser rendering during each shot,
  // because ATTENTION lasts less than the existing four-second UI refresh.
  const panelRoute = /\/api\/panels\/PNL-001(?:\?|$)/;
  for (const state of ["ATTENTION", "WARNING"] as const) {
    await expect.poll(async () => (await getPanel(request, token)).state, {
      timeout: 60000, intervals: [200],
    }).toBe(state);
    const captured = await getPanel(request, token);
    expect(captured.state).toBe(state);
    const response = await request.get("/api/notifications", {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(response.ok()).toBeTruthy();
    const notifications = (await response.json()).items.filter(
      (item: { demo_run_id: string }) => item.demo_run_id === run.demo_run_id,
    );
    const channels = (captured.actions || []).filter((a) => a.type === "notification");
    expect(notifications).toHaveLength(state === "ATTENTION" ? 0 : 2);
    expect(channels).toHaveLength(state === "ATTENTION" ? 0 : 2);
    expect(captured.current_run_alarms?.some((a) => a.severity === state)).toBeTruthy();
    await page.route(panelRoute, (route) => route.fulfill({ json: captured }));
    await expect(page.locator(".action-card .action-list p").first()).toContainText(
      state === "ATTENTION" ? "Dikkat" : "Uyarı",
    );
    if (state === "ATTENTION") {
      await expect(page.locator(".action-card")).not.toContainText("SMS_MOCK");
      await expect(page.locator(".action-card")).not.toContainText("WHATSAPP_MOCK");
    } else {
      expect(notifications.map((n: { channel: string }) => n.channel).sort())
        .toEqual(["sms_mock", "whatsapp_mock"]);
      await expect(page.locator(".action-card")).toContainText("SMS_MOCK");
      await expect(page.locator(".action-card")).toContainText("WHATSAPP_MOCK");
    }
    await shot(page, state === "ATTENTION" ? "attention-policy" : "warning-policy");
    await page.unroute(panelRoute);
    policyProof[state] = { step: captured.demo_step, notifications: notifications.length,
      channels: channels.map((a) => a.channel), persistent_alarm: true,
      screenshot_mode: "real API response frozen only for browser rendering" };
  }
  record("notification_policy_v2", policyProof);
  await expect
    .poll(async () => (await getPanel(request, token)).early_warning?.status, {
      timeout: 145000,
      intervals: [1500, 2500, 3000],
    })
    .toBe("demonstrated");
  const critical = await getPanel(request, token);
  expect(critical.early_warning!.lead_steps).toBeGreaterThan(0);
  const states = critical.early_warning!.transitions.map((item) => item.state);
  expect(states).toEqual(
    expect.arrayContaining(["NORMAL", "ATTENTION", "WARNING", "CRITICAL"]),
  );
  expect(states.indexOf("WARNING")).toBeLessThan(states.indexOf("CRITICAL"));
  expect(
    critical.current_run_history!.every(
      (item) => item.demo_run_id === run.demo_run_id,
    ),
  ).toBeTruthy();
  await expect(page.locator(".lead-time.demonstrated")).toContainText(
    "sentetik demo adımı önce",
  );
  await expect(page.locator(".action-card")).toContainText("Trip ve reset");
  await expect(page.locator(".contributions")).toContainText(
    "Termal + PD korelasyonu",
  );
  await expect(page.locator(".contributions")).not.toContainText(
    "thermal_pd_correlation",
  );
  await shot(page, "early-warning");
  record("focused_thermal_pd", {
    run_id: run.demo_run_id,
    wall_seconds_observed: (Date.now() - started) / 1000,
    lead_steps: critical.early_warning!.lead_steps,
    transitions: critical.early_warning!.transitions,
    unit: critical.early_warning!.unit,
  });

  await page
    .getByRole("button", { name: "Senaryo başlat", exact: true })
    .click();
  await page.getByLabel("Demo senaryosu").selectOption("normal_operation");
  await page
    .getByRole("button", { name: "Senaryoyu çalıştır", exact: true })
    .click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect
    .poll(
      async () => {
        const panel = await getPanel(request, token);
        return (
          panel.scenario === "normal_operation" &&
          panel.demo_run_id !== run.demo_run_id &&
          !panel.pending_current_run &&
          panel.state === "NORMAL"
        );
      },
      { timeout: 30000 },
    )
    .toBeTruthy();
  const clean = await getPanel(request, token);
  expect(clean.current_run_alarms).toHaveLength(0);
  expect(
    clean.current_run_history!.every(
      (item) =>
        item.demo_run_id === clean.demo_run_id && item.state !== "CRITICAL",
    ),
  ).toBeTruthy();
  expect(
    clean.historical_alarms!.some(
      (item) => item.demo_run_id === run.demo_run_id,
    ),
  ).toBeTruthy();
  expect(
    clean.full_history!.some(
      (item) =>
        item.demo_run_id === run.demo_run_id && item.state === "CRITICAL",
    ),
  ).toBeTruthy();
  await expect(
    page.getByRole("button", {
      name: "Alarmlar (0) · Bu çalışma",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.locator(".score-card").first().locator("strong"),
  ).not.toContainText("—");
  await page.getByRole("button", { name: "H1", exact: true }).click();
  await expect(page.locator(".sensor-description")).toContainText(
    "Sağ yardımcı",
  );
  const h1 = page
    .locator('svg g[role="button"]')
    .filter({ has: page.locator("text", { hasText: "H1" }) });
  await expect(h1.locator("circle").first()).toHaveAttribute("cx", "439");
  await expect(h1.locator("circle").first()).toHaveAttribute("cy", "292");
  await shot(page, "panel-clean");
  await page.getByRole("button", { name: "Tüm geçmiş", exact: true }).click();
  await expect(
    page.getByRole("button", {
      name: /^Alarmlar \([1-9][0-9]*\) · Tüm geçmiş$/,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Ölçümler ve trendler", exact: true })
    .click();
  await expect(page.getByTestId("history-scope-summary")).toContainText(
    "Tüm geçmiş",
  );
  const older = page.getByRole("button", {
    name: "Daha eski ölçümler",
    exact: true,
  });
  if (clean.full_history_has_more) {
    const historyResponse = page.waitForResponse(
      (response) =>
        response.url().includes("/history?scope=all") && response.ok(),
    );
    await older.click();
    const response = await historyResponse;
    const beforeId = Number(
      new URL(response.url()).searchParams.get("before_id"),
    );
    const loaded = await response.json();
    expect(loaded.items.length).toBeGreaterThan(0);
    expect(
      loaded.items.every((item: { id: number }) => item.id < beforeId),
    ).toBeTruthy();
  }
  record("run_isolation", {
    new_run_id: clean.demo_run_id,
    current_run_alarm_count: clean.current_run_alarms!.length,
    historical_alarm_count: clean.historical_alarms!.length,
    historical_critical_preserved: true,
    h1: "right auxiliary compartment, cx439/cy292",
  });
});

test("V2 pending response boundary never presents previous-run measurements as new live data", async ({
  page,
  request,
}) => {
  const token = await login(page);
  const fixture = await getPanel(request, token);
  fixture.pending_current_run = true;
  fixture.current_run_history = [];
  fixture.current_run_alarms = [];
  fixture.current_run_events = [];
  fixture.risk_score = 98;
  fixture.measurements.temperature_c = 188;
  fixture.early_warning = {
    transitions: [],
    warning_step: null,
    critical_step: null,
    lead_steps: null,
    status: "pending",
    unit: "synthetic_demo_steps",
    message: "Yeni çalışma ölçümü bekleniyor.",
  };
  await page.route("**/api/panels/PNL-001", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(fixture),
    }),
  );
  const fleetResponse = await request.get("/api/fleet", {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(fleetResponse.ok()).toBeTruthy();
  const fleetFixture = await fleetResponse.json();
  fleetFixture.panels = fleetFixture.panels.map((panel: Panel) =>
    panel.id === fixture.id ? fixture : panel,
  );
  await page.route("**/api/fleet", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(fleetFixture),
    }),
  );
  await page.getByRole("button", { name: "Yenile", exact: true }).click();
  await page.getByLabel("Pano ara").fill("PNL-001");
  await expect(page.locator(".panel-row .risk-cell strong")).toHaveText("—");
  await expect(page.locator(".panel-row")).toContainText("Ölçüm bekleniyor");
  await expect(page.locator(".priority-card")).not.toContainText("PNL-001");
  await openPanel(page);
  await expect(
    page.locator(".score-card").first().locator("strong"),
  ).toContainText("—");
  await expect(page.locator(".score-card").first()).not.toContainText("98");
  await expect(
    page.getByText("Ölçüm bekleniyor", { exact: true }).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "H1", exact: true }).click();
  await expect(page.locator(".sensor-title")).toContainText(
    "Bu çalışma için ölçüm bekleniyor",
  );
  await page
    .getByRole("button", { name: "Ölçümler ve trendler", exact: true })
    .click();
  await expect(
    page.locator(".measurement").filter({ hasText: "Bağlantı sıcaklığı" }),
  ).toContainText("—");
  await expect(
    page.locator(".measurement").filter({ hasText: "Bağlantı sıcaklığı" }),
  ).not.toContainText("188");
  await expect(page.locator(".empty-chart").first()).toBeVisible();
});

test("V2 real SCADA master resolves all six bank boundaries through PNL-500", async ({
  page,
}) => {
  await login(page);
  await page
    .getByRole("button", { name: "SCADA / Modbus", exact: true })
    .click();
  const cases = [
    ["PNL-001", 1, 1502, 1],
    ["PNL-247", 1, 1502, 247],
    ["PNL-248", 2, 1503, 1],
    ["PNL-494", 2, 1503, 247],
    ["PNL-495", 3, 1504, 1],
    ["PNL-500", 3, 1504, 6],
  ] as const;
  for (const [id, bank, port, unit] of cases) {
    await page.getByLabel("SCADA hedef panosu").selectOption(id);
    await expect(page.getByTestId("scada-bank").locator("b")).toHaveText(
      String(bank),
    );
    await expect(page.getByTestId("scada-port").locator("b")).toHaveText(
      String(port),
    );
    await expect(page.getByTestId("scada-unit").locator("b")).toHaveText(
      String(unit),
    );
    await expect(
      page.getByText("TCP okuması başarılı", { exact: true }),
    ).toBeVisible();
    await expect(page.locator(".register-table tbody tr")).toHaveCount(12);
  }
  await shot(page, "scada-bank500");
  record(
    "scada_bank_boundaries",
    cases.map(([panel, bank, port, unit]) => ({
      panel,
      bank,
      port,
      unit,
      registers: 12,
      transport: "real Modbus TCP master",
    })),
  );
});

test("V2 deployment presents sourced scale evidence, installation classes and blank parametric TCO", async ({
  page,
}) => {
  await login(page);
  await page
    .getByRole("button", { name: "Yaygınlaştırma", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Mevcut yatırımı koruyarak büyüyün." }),
  ).toBeVisible();
  await expect(page.locator(".scale-proof tbody tr")).toHaveCount(6);
  const projection = JSON.parse(
    fs.readFileSync(
      path.join(root, "apps/web/src/data/scale-proof.json"),
      "utf8",
    ),
  );
  await expect(page.locator(".scale-proof")).toContainText(
    projection.source_path,
  );
  await expect(page.locator(".scale-proof")).toContainText(
    projection.source_label,
  );
  await shot(page, "scale-value");
  await page
    .getByRole("button", { name: "Kurulum / A–B–C", exact: true })
    .click();
  await expect(page.locator(".installation-classes > section")).toHaveCount(3);
  await expect(page.locator(".installation-table")).toContainText(
    "Wireless = canlı çalışma izni değildir",
  );
  await shot(page, "installation");
  await page
    .getByRole("button", { name: "Maliyet modeli", exact: true })
    .click();
  for (const input of await page.locator(".tco-form input").all())
    await expect(input).toHaveValue("");
  await expect(page.getByTestId("tco-incomplete")).toBeVisible();
  const costs: Record<string, string> = {
    "Pano sayısı": "100",
    "Değerlendirme dönemi (yıl)": "3",
    "Para birimi": "TEST",
    Gateway: "10",
    "İzole arayüzler": "10",
    Sensörler: "10",
    Kurulum: "10",
    "Devreye alma": "10",
    "Varsa planlı kesinti maliyeti": "10",
    "Opsiyonel PD katmanı": "10",
    "Ortak sunucu · filonun tamamı": "1000",
    "Yıllık bakım · pano başına": "20",
    "Yıllık pil değişimi · pano başına": "5",
  };
  for (const [label, value] of Object.entries(costs))
    await page.getByLabel(label, { exact: true }).fill(value);
  await expect(page.getByTestId("tco-per-panel")).toHaveText("155,00 TEST");
  await expect(page.getByTestId("tco-fleet-total")).toHaveText(
    "15.500,00 TEST",
  );
  await page.getByLabel("Kesinti saat maliyeti", { exact: true }).fill("50");
  await expect(page.locator(".payback-output")).toContainText(
    "Fayda alanları eksik",
  );
  await page.getByLabel("Pano sayısı", { exact: true }).fill("0");
  await expect(page.getByTestId("tco-incomplete")).toBeVisible();
  await expect(page.getByTestId("tco-results")).toHaveCount(0);
  await page
    .getByRole("button", { name: "Girdileri temizle", exact: true })
    .click();
  for (const input of await page.locator(".tco-form input").all())
    await expect(input).toHaveValue("");
  record("deployment", {
    scale_source: projection.source_path,
    scale_sha256: projection.source_sha256,
    cost_values: "Test inputs only, not quotes",
    expected_panel_tco: 155,
    expected_fleet_tco: 15500,
    blank_defaults: true,
    zero_denominator_blocked: true,
  });
});

test("V2 global alarm filters and notifications retain unmistakable simulated delivery labels", async ({
  page,
}) => {
  await login(page);
  await page
    .locator("nav")
    .getByRole("button", { name: /^Alarm merkezi/ })
    .click();
  await page.getByLabel("Alarm çalışma filtresi").selectOption("current");
  await page.getByLabel("Alarm önem filtresi").selectOption("CRITICAL");
  await page.getByLabel("Alarm durum filtresi").selectOption("active");
  const rows = page.locator(".alarm-item");
  for (const row of await rows.all()) {
    await expect(row.locator(".badge")).toContainText("Kritik");
    await expect(row.locator("small")).toContainText("Aktif");
  }
  await page.getByRole("button", { name: "Bildirimler", exact: true }).click();
  await expect(page.locator(".notification-demo-banner")).toContainText(
    "SIMULATED · SİMÜLE EDİLDİ",
  );
  await expect(
    page.getByRole("columnheader", { name: "ALARM", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Simüle edildi", { exact: true }).first(),
  ).toBeVisible();
  await shot(page, "notifications");
  record("notifications", {
    delivery: "SIMULATED local mock records",
    filters: ["current run", "CRITICAL", "active"],
  });
});

test("V2 viewer quick demos are disabled and deployment remains usable on mobile", async ({
  page,
}) => {
  await login(page, true);
  await openPanel(page);
  await expect(
    page.getByRole("button", { name: "Termal + PD demosu", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Ark demosu", exact: true }),
  ).toBeDisabled();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Menüyü aç", exact: true }).click();
  await page
    .getByRole("button", { name: "Yaygınlaştırma", exact: true })
    .click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page
    .getByRole("button", { name: "Maliyet modeli", exact: true })
    .click();
  await expect(page.getByTestId("tco-incomplete")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  record("roles_mobile", {
    viewer_quick_actions_disabled: true,
    viewport: "390x844",
    page_overflow: false,
  });
});
