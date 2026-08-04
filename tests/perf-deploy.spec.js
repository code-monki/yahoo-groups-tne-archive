// TC-PERF-02 (NFR-6, ADR-0015) and TC-DEPLOY-01 (NFR-8, IR-1).
const { test, expect } = require("@playwright/test");

const BASE = "http://localhost:8098/yahoo-groups-tne-archive";

test("TC-PERF-02: search assets load only on /search/, deferred there", async ({ page }) => {
  const calls = [];
  page.on("request", (r) => calls.push(r.url()));
  await page.goto(BASE + "/");
  const searchRelated = calls.filter((u) => u.includes("pagefind") || u.includes("search.js"));
  expect(searchRelated).toEqual([]);

  calls.length = 0;
  await page.goto(BASE + "/search/");
  const scriptTag = await page.locator('script[src*="search.js"]').getAttribute("src");
  expect(scriptTag).toBeTruthy();
  const isDeferred = await page.evaluate(() => {
    const s = document.querySelector('script[src*="search.js"]');
    return s.defer === true;
  });
  expect(isDeferred).toBe(true);
});

test("TC-DEPLOY-01: no third-party network calls anywhere in a site walk", async ({ page }) => {
  const external = [];
  page.on("request", (r) => {
    const u = r.url();
    if (!u.startsWith("http://localhost:8098/") && !u.startsWith("data:")) external.push(u);
  });
  for (const path of ["/", "/posts/6835/", "/threads/7153/", "/authors/", "/search/", "/help/"]) {
    await page.goto(BASE + path);
  }
  expect(external).toEqual([]);
});
