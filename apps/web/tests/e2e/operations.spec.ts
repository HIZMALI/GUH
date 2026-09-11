import { test, expect, Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
const configPath = path.resolve(__dirname, "../../../../.env");
const secrets: Record<string, string> = fs.existsSync(configPath)
  ? Object.fromEntries(
      fs
        .readFileSync(configPath, "utf8")
        .split(/\r?\n/)
        .filter((s) => s && !s.startsWith("#"))
        .map((s) => {
          const at = s.indexOf("=");
          return [s.slice(0, at), s.slice(at + 1)];
        }),
    )
  : {};
function credential(key: string) {
  return process.env[key] || secrets[key] || "";
}
async function login(page: Page, role: "admin" | "viewer" = "admin") {
  await page.goto("/");
  await page
    .getByLabel("Kullanıcı adı", { exact: true })
    .fill(
      role === "admin" ? credential("ADMIN_USERNAME") || "admin" : "viewer",
    );
  await page
    .getByLabel("Parola", { exact: true })
    .fill(credential(role === "admin" ? "ADMIN_PASSWORD" : "VIEWER_PASSWORD"));
  await page.getByRole("button", { name: "Güvenli giriş yap" }).click();
  await expect(
    page.getByRole("heading", { name: "Filonun nabzı, tek ekranda." }),
  ).toBeVisible();
  await expect(
    page.getByText("Yerel API bağlı", { exact: true }),
  ).toBeVisible();
}
test.beforeAll(() => {
  if (!credential("ADMIN_PASSWORD") || !credential("VIEWER_PASSWORD"))
    throw new Error(
      "Set ADMIN_PASSWORD/VIEWER_PASSWORD or bootstrap root .env before real-backend E2E. No default passwords are embedded.",
    );
});

test("real API authentication, fleet ranking, hierarchy, drawing and telemetry trends", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await login(page);
  await expect(page.getByText("SENTETİK DEMO", { exact: true })).toBeVisible();
  const ranks = await page.locator(".risk-cell strong").allTextContents();
  expect(ranks.length).toBeGreaterThan(0);
  expect(ranks.map(Number)).toEqual(ranks.map(Number).sort((a, b) => b - a));
  await page.screenshot({
    path: "test-results/fleet-desktop.png",
    fullPage: true,
  });
  await page.getByLabel("Pano ara").fill("PNL-001");
  await expect(page.locator(".panel-row")).toHaveCount(1);
  await page.getByRole("button", { name: "PNL-001 pano detayını aç" }).click();
  await expect(
    page.getByRole("heading", { name: "Pano izleme şeması" }),
  ).toBeVisible();
  await expect(
    page.getByText("1600 mm (+100 / −0)", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "H1", exact: true }).click();
  await expect(page.locator(".sensor-title")).toContainText("Sıcaklık ve nem");
  await page.getByRole("button", { name: "P1", exact: true }).click();
  await expect(page.locator(".sensor-description")).toContainText(
    "pC ölçümü değildir",
  );
  await page.screenshot({
    path: "test-results/panel-desktop.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Ölçümler ve trendler", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Faz akımları", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".measurement")).toHaveCount(23);
  await expect(
    page.locator(".measurement").filter({ hasText: "L1 akımı" }),
  ).toContainText("Sentetik");
  await page.screenshot({
    path: "test-results/trends-desktop.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("real Modbus TCP master returns readable GridSentinel registers", async ({
  page,
}) => {
  await login(page);
  await page
    .getByRole("button", { name: "SCADA / Modbus", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "SCADA kayıtlarını okuyun." }),
  ).toBeVisible();
  await page.getByLabel("SCADA hedef panosu").selectOption("PNL-001");
  await expect(
    page.getByText("TCP okuması başarılı", { exact: true }),
  ).toBeVisible({ timeout: 30000 });
  await expect(page.locator(".register-table tbody tr")).toHaveCount(12);
  await expect(page.getByText("READ ONLY", { exact: true })).toHaveCount(12);
  await page.screenshot({
    path: "test-results/scada-desktop.png",
    fullPage: true,
  });
});

test("viewer cannot mutate simulator state and logout clears bearer session", async ({
  page,
  request,
}) => {
  await login(page, "viewer");
  await expect(
    page.getByRole("button", { name: "Senaryo başlat", exact: true }),
  ).toBeDisabled();
  const token = await page.evaluate(
    () =>
      JSON.parse(sessionStorage.getItem("gridsentinel.session")!).access_token,
  );
  const result = await request.post("/api/demo/scenario", {
    headers: { Authorization: `Bearer ${token}` },
    data: { scenario: "arc_event", panel_id: "PNL-001" },
  });
  expect(result.status()).toBe(403);
  await page.getByRole("button", { name: "Çıkış yap", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Operasyon merkezine giriş" }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => sessionStorage.getItem("gridsentinel.session")),
  ).toBeNull();
});

test("all ten scenario choices, selection persists in real API", async ({
  page,
  request,
}) => {
  test.setTimeout(150000);
  await login(page);
  await page
    .getByRole("button", { name: "Senaryo başlat", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.locator("#demo-scenario option")).toHaveCount(10);
  await page.getByLabel("Hedef sanal pano").selectOption("PNL-001");
  await page.getByLabel("Demo senaryosu").selectOption("arc_event");
  await page
    .getByRole("button", { name: "Senaryoyu çalıştır", exact: true })
    .click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(page.getByRole("status")).toContainText(
    "Arc Guard olayı senaryosu PNL-001 için seçildi",
  );
  const token = await page.evaluate(
    () =>
      JSON.parse(sessionStorage.getItem("gridsentinel.session")!).access_token,
  );
  await expect
    .poll(
      async () => {
        const response = await request.get("/api/panels/PNL-001", {
          headers: { Authorization: `Bearer ${token}` },
        });
        return (await response.json()).scenario;
      },
      { timeout: 30000 },
    )
    .toBe("arc_event");
  await page.getByLabel("Pano ara").fill("PNL-001");
  await page.getByRole("button", { name: "PNL-001 pano detayını aç" }).click();
  await expect(
    page.getByText("SENTETİK ARC EVENT", { exact: true }),
  ).toBeVisible({ timeout: 120000 });
  await page.getByRole("button", { name: /^Alarmlar \(/ }).click();
  const ack = page
    .getByRole("button", { name: "Alarmı onayla", exact: true })
    .first();
  await expect(ack).toBeVisible();
  await ack.click();
  await expect(page.getByRole("status")).toContainText(
    "Alarm onayı kaydedildi",
  );
  await page.getByRole("button", { name: "Bildirimler", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Bildirim günlüğü" }),
  ).toBeVisible();
  await expect(
    page.getByText("Simüle edildi", { exact: true }).first(),
  ).toBeVisible();
  // Return this dedicated demo panel to its ordinary synthetic stream.
  const restored = await request.post("/api/demo/scenario", {
    headers: { Authorization: `Bearer ${token}` },
    data: { scenario: "normal_operation", panel_id: "PNL-001" },
  });
  expect(restored.ok()).toBeTruthy();
});

test("failed transport explicitly marks cached telemetry as unavailable", async ({
  page,
}) => {
  await login(page);
  await page.route("**/api/fleet", (route) =>
    route.fulfill({
      status: 502,
      contentType: "application/json",
      body: JSON.stringify({ detail: "E2E transport interruption" }),
    }),
  );
  await page.getByRole("button", { name: "Yenile", exact: true }).click();
  await expect(page.locator(".connection-alert")).toContainText(
    "Canlı güncelleme alınamıyor",
  );
  await expect(page.locator(".connection-alert")).toContainText(
    "son değerler güncel kabul edilmemelidir",
  );
  await expect(
    page.getByText("API bağlantısı kesildi", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/offline-desktop.png",
    fullPage: true,
  });
});

test("mobile navigation and source disclosure remain usable without page overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "test-results/fleet-mobile.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Menüyü aç", exact: true }).click();
  await page
    .getByRole("button", { name: "Sistem ve kaynaklar", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Verinin kaynağı açık." }),
  ).toBeVisible();
  await expect(
    page.getByText("152 sentetik L1 örneği", { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});

test("quality contract: invalid humidity and lost Arc communication are unavailable, gateway is not sensor battery", async ({
  page,
  request,
}) => {
  await login(page);
  const token = await page.evaluate(
    () =>
      JSON.parse(sessionStorage.getItem("gridsentinel.session")!).access_token,
  );
  const response = await request.get("/api/panels/PNL-001", {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.ok()).toBeTruthy();
  // An explicit response fixture tests a sensor failure boundary; application data remains real API data.
  const fixture = await response.json();
  fixture.communication_ok = true;
  fixture.measurements.humidity_pct = 137;
  fixture.quality.humidity_pct = "invalid";
  fixture.arc.communication_ok = false;
  await page.route("**/api/panels/PNL-001", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(fixture),
    }),
  );
  await page.getByLabel("Pano ara").fill("PNL-001");
  await page.getByRole("button", { name: "PNL-001 pano detayını aç" }).click();
  await page.getByRole("button", { name: "H1", exact: true }).click();
  await expect(page.locator(".sensor-title")).toContainText(
    "— % RH · Geçersiz veri",
  );
  await expect(page.locator(".sensor-title")).not.toContainText("137");
  await page.getByRole("button", { name: "A1", exact: true }).click();
  await expect(page.locator(".sensor-title")).toContainText(
    "Bilinmiyor · iletişim yok",
  );
  await expect(page.locator(".arc-card")).toContainText(
    "BİLİNMİYOR · İLETİŞİM YOK",
  );
  await page.getByRole("button", { name: "G1", exact: true }).click();
  await expect(page.locator(".sensor-title")).toContainText("Gateway bağlı");
  await expect(page.locator(".sensor-title")).not.toContainText("pil");
  await page
    .getByRole("button", { name: "Ölçümler ve trendler", exact: true })
    .click();
  await expect(
    page.locator(".measurement").filter({ hasText: "Bağıl nem" }),
  ).toContainText("—");
  await expect(
    page.locator(".measurement").filter({ hasText: "Bağıl nem" }),
  ).toContainText("Geçersiz veri");
});
