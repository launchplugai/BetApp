import { test, expect } from "@playwright/test";

test.describe("Evaluation API (/app/evaluate)", () => {
  test("POST /app/evaluate returns evaluation result", async ({ request }) => {
    const res = await request.post("/app/evaluate", {
      data: {
        input: "Lakers -5.5, Chiefs ML, Over 220",
        tier: "GOOD",
      },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    // Evaluation should return structured result
    expect(body).toHaveProperty("success");
  });
});

test.describe("Landing page (/app?screen=landing)", () => {
  test("loads landing screen", async ({ page }) => {
    await page.goto("/app?screen=landing");
    await expect(page.locator("body")).toContainText(/DNA|bet|engine|start/i);
  });
});

test.describe("Root redirect", () => {
  test("/ redirects to /app", async ({ page }) => {
    await page.goto("/");
    await page.waitForURL(/\/app/);
    await expect(page).toHaveURL(/\/app/);
  });
});
