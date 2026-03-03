import { test, expect } from "@playwright/test";

test.describe("Main App UI (/app)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/app");
  });

  test("loads the dashboard screen", async ({ page }) => {
    // Page should load without error
    await expect(page).toHaveURL(/\/app/);

    // Dashboard should render with key elements
    await expect(page.locator("body")).toContainText(/DNA|dashboard|bet/i);
  });

  test("has navigation tabs", async ({ page }) => {
    // The app should have nav links for Home, Browse, Build
    const nav = page.locator("nav, [role='navigation'], .nav, .bottom-nav, .tab-bar");
    await expect(nav.first()).toBeVisible({ timeout: 10_000 });
  });

  test("dashboard shows user stats area", async ({ page }) => {
    // Dashboard should show stats like win rate, total parlays
    const body = page.locator("body");
    await expect(body).toContainText(/win rate|parlays|balance|protocol/i);
  });
});

test.describe("Browse screen (/app?screen=browse)", () => {
  test("loads browse screen", async ({ page }) => {
    await page.goto("/app?screen=browse");
    await expect(page).toHaveURL(/screen=browse/);
    await expect(page.locator("body")).toContainText(/browse|discover|game|event/i);
  });
});

test.describe("Builder screen (/app?screen=builder)", () => {
  test("loads builder screen", async ({ page }) => {
    await page.goto("/app?screen=builder");
    await expect(page).toHaveURL(/screen=builder/);
    await expect(page.locator("body")).toContainText(/build|parlay|leg|slip/i);
  });
});

test.describe("Auth screen (/app?screen=auth)", () => {
  test("loads auth screen", async ({ page }) => {
    await page.goto("/app?screen=auth");
    await expect(page).toHaveURL(/screen=auth/);
    await expect(page.locator("body")).toContainText(/sign|login|auth|email|password/i);
  });
});
