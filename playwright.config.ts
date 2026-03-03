import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config for DNA Bet Engine E2E tests.
 *
 * Runs against the live Railway deployment by default.
 * Override with BASE_URL env var for local testing.
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  retries: 1,
  reporter: [["html", { open: "never" }], ["list"]],
  use: {
    baseURL:
      process.env.BASE_URL || "https://dna-production-cb47.up.railway.app",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
