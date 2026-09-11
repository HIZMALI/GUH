import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
const repo = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../..",
);
const directory = path.join(repo, "docs/verification");
const finalPath = path.join(directory, "v2-frontend-final-regression.json");
const reportPaths = [finalPath];
const reports = reportPaths.map((file) =>
  JSON.parse(fs.readFileSync(file, "utf8")),
);
const cases = new Map();
function visit(suites, attempt) {
  for (const suite of suites) {
    for (const spec of suite.specs || []) {
      const result = spec.tests[0].results.at(-1);
      const previous = cases.get(spec.title) || {
        title: spec.title,
        file: spec.file,
        attempts: [],
      };
      previous.attempts.push({
        report: attempt,
        status: result.status,
        duration_ms: result.duration,
      });
      previous.latest_status = result.status;
      cases.set(spec.title, previous);
    }
    visit(suite.suites || [], attempt);
  }
}
reports.forEach((report, index) =>
  visit(report.suites, path.basename(reportPaths[index])),
);
const names = [
  "fleet",
  "panel-clean",
  "early-warning",
  "scada-bank500",
  "scale-value",
  "notifications",
  "installation",
  "attention-policy",
  "warning-policy",
];
const screenshots = names.map((name) => {
  const file = `v2-${name}.png`;
  const data = fs.readFileSync(path.join(directory, file));
  return {
    file,
    bytes: data.length,
    width: data.readUInt32BE(16),
    height: data.readUInt32BE(20),
    sha256: crypto.createHash("sha256").update(data).digest("hex"),
  };
});
const observations = JSON.parse(
  fs.readFileSync(
    path.join(directory, "v2-frontend-observations.json"),
    "utf8",
  ),
);
const checked = Object.entries(observations).filter(([key]) =>
  key.startsWith("browser_errors:"),
);
const finalReport = reports[0];
const finalTestCount = [...cases.values()].filter((test) =>
  test.attempts.some((attempt) => attempt.report === path.basename(finalPath)),
).length;
const summary = {
  recorded_at: new Date().toISOString(),
  command: "npm run test:e2e:v2",
  final_regression_command:
    "E2E_REPORT_FILE=test-results-v2/final-regression.json npm run test:e2e:v2 (set environment variable using the local shell)",
  target: observations.target,
  unique_tests: cases.size,
  unique_passed: [...cases.values()].filter(
    (test) => test.latest_status === "passed",
  ).length,
  final_regression: finalReport?.stats || null,
  final_regression_unique_tests: finalReport ? finalTestCount : null,
  final_regression_complete: finalReport
    ? finalTestCount === cases.size &&
      finalReport.stats.unexpected === 0 &&
      finalReport.stats.skipped === 0
    : null,
  source_reports: reportPaths.map((file) => ({
    file: path.basename(file),
    sha256: crypto
      .createHash("sha256")
      .update(fs.readFileSync(file))
      .digest("hex"),
  })),
  browser_error_observation: {
    scope:
      "Latest per-test V2 browser captures in v2-frontend-observations.json retain their observed_at timestamps. The first V1 test separately asserts pageerror absence.",
    checked_tests: checked.length,
    errors: checked.flatMap(([, value]) => value.errors),
  },
  provenance:
    "All 13 tests authenticate against the local API. Three cases additionally use explicit transport/response fixtures for offline, invalid-sensor and pending-run presentation boundaries. ATTENTION/WARNING screenshots freeze captured real API responses only for browser rendering while the backend advances; notification counts are checked against the running API. SCADA tests read real local Modbus TCP. All telemetry is synthetic; no external delivery or physical device writes.",
  notification_policy: observations.notification_policy_v2,
  screenshots,
  cases: [...cases.values()],
};
fs.writeFileSync(
  path.join(directory, "v2-frontend-summary.json"),
  JSON.stringify(summary, null, 2),
);
console.log(
  JSON.stringify({
    unique_tests: summary.unique_tests,
    unique_passed: summary.unique_passed,
    final_regression_pass: summary.final_regression?.expected ?? null,
    final_regression_complete: summary.final_regression_complete,
    browser_errors: summary.browser_error_observation.errors.length,
    screenshots: screenshots.length,
  }),
);
if (
  summary.unique_passed !== summary.unique_tests ||
  summary.final_regression_complete === false ||
  summary.browser_error_observation.errors.length
)
  process.exitCode = 1;
