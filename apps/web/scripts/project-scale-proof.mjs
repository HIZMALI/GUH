import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
const args = Object.fromEntries(
  process.argv.slice(2).map((arg) => {
    const index = arg.indexOf("=");
    return [arg.slice(0, index).replace(/^--/, ""), arg.slice(index + 1)];
  }),
);
const input = path.resolve(
  args.input || "../../docs/verification/load-results.json",
);
const raw = fs.readFileSync(input, "utf8");
const source = JSON.parse(raw);
if (
  !source.timestamp ||
  !Array.isArray(source.cases) ||
  source.cases.length !== 6
)
  throw new Error("Expected six measured HTTP/MQTT cases and a timestamp.");
const cases = source.cases.map((item) => {
  for (const key of [
    "devices",
    "expected",
    "committed",
    "committed_frames_per_second",
  ])
    if (typeof item[key] !== "number" || !Number.isFinite(item[key]))
      throw new Error(`Invalid measured field ${key}`);
  return {
    panels: item.devices,
    transport: item.transport.toUpperCase(),
    expected: item.expected,
    committed: item.committed,
    frames_per_second: item.committed_frames_per_second,
    api_p95_ms: item.fleet_api_ms.p95,
    passed: item.passed === true,
  };
});
const proof = {
  version: args.version || "v1",
  source_label: args.label || `${(args.version || "v1").toUpperCase()} yerel Docker yük doğrulaması`,
  measured_at: source.timestamp,
  source_path: path
    .relative(path.resolve("../.."), input)
    .replaceAll("\\", "/"),
  source_sha256: crypto.createHash("sha256").update(raw).digest("hex"),
  environment: "Yerel Docker / PostgreSQL / WSL2",
  limitation:
    "Dört turluk kısa burst; üretim SLO veya uzun süreli soak testi değildir. Sahada kapasite, gecikme veya sıfır kayıp garantisi vermez.",
  cases,
};
const output = path.resolve("src/data/scale-proof.json");
fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, JSON.stringify(proof, null, 2) + "\n");
console.log(
  `Projected ${cases.length} measured cases to src/data/scale-proof.json (${proof.version})`,
);
