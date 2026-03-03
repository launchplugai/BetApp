import { test, expect } from "@playwright/test";

test.describe("Health & Build endpoints", () => {
  test("GET /health returns healthy", async ({ request }) => {
    const res = await request.get("/health");
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.status).toBe("healthy");
    expect(body.service).toBe("dna-matrix");
    expect(body.environment).toBe("production");
  });

  test("GET /build returns build info", async ({ request }) => {
    const res = await request.get("/build");
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.service).toBe("dna-bet-engine");
    expect(body).toHaveProperty("build_time_utc");
    expect(body).toHaveProperty("server_time_utc");
  });
});
