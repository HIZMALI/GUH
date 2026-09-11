import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

export default defineConfig(base, {
  outputDir: "test-results-v2/artifacts",
  reporter: [
    ["list"],
    [
      "json",
      {
        outputFile:
          process.env.E2E_REPORT_FILE || "test-results-v2/results.json",
      },
    ],
  ],
});
