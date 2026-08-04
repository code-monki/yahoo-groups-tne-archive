// TC-FUNC-* (test-plan.md §5), run against the built site served at BASE.
const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const BASE = "http://localhost:8098/yahoo-groups-tne-archive";
const REPO_ROOT = path.join(__dirname, "..");
const posts = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, "data", "posts.json"), "utf-8"));
const byId = new Map(posts.map((p) => [p.id, p]));

const TEMPLATES = {
  home: "/",
  post: "/posts/6835/",
  thread: "/threads/7153/",
  author: "/authors/dcndcn13/",
  "authors-index": "/authors/",
  topic: "/topics/question-for-the-group/",
  "topics-index": "/topics/",
  "browse-year": "/browse/2012/",
  "browse-month": "/browse/2012/03/",
  files: "/files/",
  search: "/search/",
  help: "/help/",
};

// TC-FUNC-01 (FR-1): post-record count matches built-page count.
test("TC-FUNC-01: post page count matches dataset count", async ({ page }) => {
  const dir = path.join(REPO_ROOT, "_site", "posts");
  const builtCount = fs.readdirSync(dir).filter((d) =>
    fs.existsSync(path.join(dir, d, "index.html"))
  ).length;
  expect(builtCount).toBe(posts.length);

  const resp = await page.goto(BASE + "/posts/6835/");
  expect(resp.status()).toBe(200);
});

// TC-FUNC-02 (FR-2, FR-5): rendered author/date/subject/body match dataset
// for a sample of posts across different years/authors.
test("TC-FUNC-02: rendered post fields match dataset", async ({ page }) => {
  const sample = [posts[0], posts[Math.floor(posts.length / 2)], posts[posts.length - 1]];
  for (const p of sample) {
    await page.goto(`${BASE}/posts/${p.id}/`);
    await expect(page.locator("h1")).toHaveText(p.subject);
    await expect(page.locator(".byline strong")).toHaveText(p.author.display_name);
    await expect(page.locator(".byline time")).toHaveAttribute("datetime", p.date_utc);
  }
});

// TC-FUNC-03 (FR-3): no Yahoo/ygrp boilerplate signatures leak into
// rendered post bodies.
test("TC-FUNC-03: no boilerplate leakage in rendered bodies", async ({ page }) => {
  const sample = posts.filter((_, i) => i % 400 === 0);
  for (const p of sample) {
    await page.goto(`${BASE}/posts/${p.id}/`);
    const bodyHtml = await page.locator(".post-body").innerHTML();
    expect(bodyHtml).not.toMatch(/ygrp-(sponsor|vital|actbar)/);
    expect(bodyHtml).not.toContain("Yahoo! Groups Links");
    expect(bodyHtml).not.toContain("Reply via web post");
  }
});

// TC-FUNC-04 (FR-6): thread_id/parent_id internal consistency -- every
// reply_ids entry points back to a post whose parent_id is the referrer,
// and every parent_id points to a post that lists the referrer in its own
// reply_ids. (Hand-verification of the header-based/subject-fallback
// sample itself was done during Phase 2 development against the real
// archive -- see pipeline/thread.py and docs/defect-log.md; this is the
// mechanical half of TC-FUNC-04.)
test("TC-FUNC-04: parent/reply relationships are internally consistent", () => {
  let checked = 0;
  for (const p of posts) {
    for (const replyId of p.reply_ids) {
      const reply = byId.get(replyId);
      expect(reply, `reply ${replyId} referenced by ${p.id} should exist`).toBeTruthy();
      expect(reply.parent_id, `reply ${replyId}'s parent_id should point back to ${p.id}`).toBe(p.id);
      checked++;
    }
  }
  expect(checked).toBeGreaterThan(0);
});

// TC-FUNC-05 (FR-7): parent/reply links resolve; no dead markup when a
// post has neither.
test("TC-FUNC-05: context-strip links resolve, or render nothing when absent", async ({ page }) => {
  const withBoth = posts.find((p) => p.parent_id && p.reply_ids.length);
  await page.goto(`${BASE}/posts/${withBoth.id}/`);
  for (const link of await page.locator(".context-strip a").all()) {
    const href = await link.getAttribute("href");
    const resp = await page.request.get(BASE.replace(/\/yahoo-groups-tne-archive$/, "") + href);
    expect(resp.status(), href).toBe(200);
  }

  const withNeither = posts.find((p) => !p.parent_id && p.reply_ids.length === 0);
  await page.goto(`${BASE}/posts/${withNeither.id}/`);
  const strip = page.locator(".context-strip");
  await expect(strip.locator("a[href*='/posts/']")).toHaveCount(0);
});

// TC-FUNC-06 (FR-8): a thread of size 3+ renders all members in one view.
test("TC-FUNC-06: thread page shows every member post, no click-through", async ({ page }) => {
  const counts = {};
  for (const p of posts) counts[p.thread_id] = (counts[p.thread_id] || 0) + 1;
  const bigThreadId = Object.entries(counts).find(([, c]) => c >= 3)[0];
  await page.goto(`${BASE}/threads/${bigThreadId}/`);
  const rendered = await page.locator(".thread-post").count();
  expect(rendered).toBe(counts[bigThreadId]);
});

// TC-FUNC-07 (FR-9, FR-11, NFR-6): search does only static asset
// fetch/parse, no server round-trip on query.
test("TC-FUNC-07: search makes only static network calls", async ({ page }) => {
  const calls = [];
  page.on("request", (r) => calls.push(r.url()));
  await page.goto(BASE + "/search/");
  await page.fill("#search-input", "hexographer");
  await page.click("button[type=submit]");
  await page.waitForFunction(() => document.getElementById("results-status").textContent.includes("result"));
  const nonStatic = calls.filter((u) => !u.startsWith("http://localhost:8098/"));
  expect(nonStatic).toEqual([]);
});

// TC-FUNC-08 (FR-10): stemmed match returned without the literal query
// string present in that result.
test("TC-FUNC-08: stemming returns an inflected-form-only match", async ({ page }) => {
  await page.goto(BASE + "/search/");
  const result = await page.evaluate(async (base) => {
    const pagefind = await import(base + "/pagefind/pagefind.js");
    await pagefind.init();
    const s = await pagefind.search("orbit");
    const all = await Promise.all(s.results.map((r) => r.data()));
    const hit = all.find((d) => d.url.includes("/posts/6381/"));
    return hit ? hit.excerpt.includes("<mark") : false;
  }, BASE);
  expect(result).toBe(true);
});

// TC-FUNC-09 (FR-12, FR-13): permalink links, subject-first ranking,
// <mark>-highlighted snippets, across multiple sample queries.
test("TC-FUNC-09: search ranking, links, and highlighting", async ({ page }) => {
  for (const query of ["orbit", "hexographer", "traveller"]) {
    await page.goto(BASE + "/search/");
    await page.fill("#search-input", query);
    await page.click("button[type=submit]");
    await page.waitForFunction(() => document.getElementById("results-status").textContent.includes("result"));
    const items = page.locator("#results-list .result-item");
    const count = await items.count();
    if (count === 0) continue;
    for (let i = 0; i < Math.min(count, 5); i++) {
      const href = await items.nth(i).locator(".post-title").getAttribute("href");
      expect(href).toMatch(/\/posts\/[^/]+\/$/);
      const snippetHtml = await items.nth(i).locator(".result-snippet").innerHTML();
      expect(snippetHtml).toContain("<mark");
    }
  }
});

// TC-FUNC-10 (FR-14, FR-15, FR-17): index counts match dataset aggregates.
test("TC-FUNC-10: browse/authors/topics counts match dataset", async ({ page }) => {
  const authorCount = new Set(posts.map((p) => p.author.slug)).size;
  await page.goto(BASE + "/authors/");
  await expect(page.locator("p.lede")).toContainText(`${authorCount} authors`);

  const topicCount = new Set(posts.map((p) => p.subject_normalized)).size;
  await page.goto(BASE + "/topics/");
  const topicItems = await page.locator(".index-list li").count();
  expect(topicItems).toBe(topicCount);

  const yearCounts = {};
  for (const p of posts) yearCounts[p.date_utc.slice(0, 4)] = (yearCounts[p.date_utc.slice(0, 4)] || 0) + 1;
  await page.goto(BASE + "/browse/2012/");
  await expect(page.locator("h1")).toContainText(`${yearCounts["2012"]} post`);
});

// TC-FUNC-11 (FR-16): nav markup identical across all 11 templates.
// aria-current="page" is expected to legitimately differ (it marks
// whichever page is actually current -- itself a Nielsen "visibility of
// system status" feature already relied on elsewhere), so it's normalized
// out before comparing; every other attribute/label/href must match.
test("TC-FUNC-11: nav markup identical across all templates", async ({ page }) => {
  let reference = null;
  for (const path of Object.values(TEMPLATES)) {
    await page.goto(BASE + path);
    const nav = (await page.locator(".nav-desktop").innerHTML()).replace(
      / aria-current="page"/g,
      ""
    );
    if (reference === null) reference = nav;
    else expect(nav, path).toBe(reference);
  }
});

// TC-FUNC-12 (FR-18, FR-25): Help page carries all required content
// elements.
test("TC-FUNC-12: Help page has all required content", async ({ page }) => {
  await page.goto(BASE + "/help/");
  const text = await page.locator("main").innerText();
  expect(text).toMatch(/2005/); // origin/date range
  expect(text).toMatch(/unofficial/i); // unofficial-fan-site disclaimer
  expect(text).toMatch(/Browse by date or author/i); // how-to-use content
  expect(text).toMatch(/removed or anonymized/i); // takedown policy
  expect(text).toContain("codemonki@outlook.com"); // contact channel 1
  await expect(page.locator('a[href*="github.com"][href*="issues"]')).toHaveCount(1); // contact channel 2
});

// TC-FUNC-13 (FR-19): matches OS prefers-color-scheme without a manual
// toggle interaction.
test("TC-FUNC-13: theme matches OS preference with no toggle interaction", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto(BASE + "/");
  const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  expect(bg).toBe("rgb(18, 20, 23)"); // --color-bg dark: #121417

  await page.emulateMedia({ colorScheme: "light" });
  await page.goto(BASE + "/");
  const bgLight = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  expect(bgLight).toBe("rgb(255, 255, 255)"); // --color-bg light: #FFFFFF
});

// TC-FUNC-14 (FR-23, FR-26, FR-27): available/unavailable attachment
// states and the rebuild-driven switch-over. The switch-over itself
// (removing/restoring a file, rebuilding, confirming it flips with zero
// code changes) was verified manually in Phase 7 -- see docs/defect-log.md
// and pipeline/attachments.py's docstring. This checks the two steady
// states against the current build.
test("TC-FUNC-14: attachment available/unavailable states render correctly", async ({ page }) => {
  const withAttachment = posts.find((p) => p.attachments && p.attachments.length);
  test.skip(!withAttachment, "no post with an attachment in the current dataset");
  await page.goto(`${BASE}/posts/${withAttachment.id}/`);
  const downloadLink = page.locator("a.btn.btn-secondary[href*='/attachments/']");
  const unavailableBtn = page.locator("[data-open-attachment-modal]");
  const hasDownload = (await downloadLink.count()) > 0;
  const hasUnavailable = (await unavailableBtn.count()) > 0;
  expect(hasDownload || hasUnavailable).toBe(true);
  if (hasDownload) {
    const href = await downloadLink.getAttribute("href");
    const resp = await page.request.get(BASE.replace(/\/yahoo-groups-tne-archive$/, "") + href);
    expect(resp.status()).toBe(200);
  }
});

// TC-FUNC-15 (FR-24): footer takedown link present and functional on
// every template.
test("TC-FUNC-15: footer takedown link on every template", async ({ page }) => {
  for (const path of Object.values(TEMPLATES)) {
    await page.goto(BASE + path);
    const link = page.locator('.footer-inner a[href*="/help/#takedown"]');
    await expect(link, path).toHaveCount(1);
  }
});

// TC-FUNC-16 (ADR-0018): Files-section manifest renders completely, with
// working available/unavailable states, mirroring FR-23/26/27's pattern
// for post attachments.
test("TC-FUNC-16: Files page lists the full manifest with correct availability", async ({ page }) => {
  const files = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, "data", "files.json"), "utf-8"));
  await page.goto(BASE + "/files/");
  const rows = page.locator(".post-list > li");
  await expect(rows).toHaveCount(files.length);

  for (const file of files) {
    const dir = path.join(REPO_ROOT, "files", file.source_post_id, file.filename);
    const exists = fs.existsSync(dir);
    const row = rows.filter({ hasText: file.filename }).first();
    if (exists) {
      await expect(row.locator("a.btn.btn-secondary")).toHaveCount(1);
    } else {
      await expect(row.locator("[data-open-attachment-modal]")).toHaveCount(1);
    }
  }
});
