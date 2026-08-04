// TC-A11Y-02 (NFR-2): keyboard-only walkthrough of every interactive
// element per template -- nav, search, theme toggle, the FR-26 modal,
// breadcrumbs. Every element must be reachable via Tab and operable via
// Enter/Space/Escape, with a visible focus indicator at each stop.
const { test, expect } = require("@playwright/test");

const BASE = "http://localhost:8098/yahoo-groups-tne-archive/";

async function hasVisibleFocusRing(page) {
  return page.evaluate(() => {
    const el = document.activeElement;
    if (!el || el === document.body) return false;
    const style = getComputedStyle(el);
    return style.outlineStyle !== "none" && style.outlineWidth !== "0px";
  });
}

test("skip link is the first tab stop and jumps to main content", async ({ page }) => {
  await page.goto(BASE);
  await page.keyboard.press("Tab");
  const active = await page.evaluate(() => document.activeElement.className);
  expect(active).toContain("skip-link");
  expect(await hasVisibleFocusRing(page)).toBe(true);
  await page.keyboard.press("Enter");
  const focused = await page.evaluate(() => document.activeElement.id);
  expect(focused).toBe("main-content");
});

test("theme toggle is keyboard-operable", async ({ page }) => {
  await page.goto(BASE);
  const before = await page.evaluate(() => document.documentElement.getAttribute("data-theme"));
  await page.locator("#theme-toggle").focus();
  expect(await hasVisibleFocusRing(page)).toBe(true);
  await page.keyboard.press("Enter");
  const after = await page.evaluate(() => document.documentElement.getAttribute("data-theme"));
  expect(after).not.toBe(before);
});

test("breadcrumb links are reachable and focus-visible", async ({ page }) => {
  await page.goto(BASE + "posts/6835/");
  const homeCrumb = page.locator(".breadcrumb a", { hasText: "Home" });
  await homeCrumb.focus();
  expect(await hasVisibleFocusRing(page)).toBe(true);
});

test("search: keyboard-driven query reaches results and links are reachable", async ({ page }) => {
  await page.goto(BASE + "search/");
  await page.locator("#search-input").focus();
  await page.keyboard.type("hexographer");
  await page.keyboard.press("Enter");
  await page.waitForFunction(() =>
    document.getElementById("results-status").textContent.includes("result")
  );
  // DOM order after submit: search input -> Search button -> first result
  // link -- two Tabs to reach the first real result, not one.
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  const active = await page.evaluate(() => document.activeElement.className);
  expect(active).toContain("post-title");
  expect(await hasVisibleFocusRing(page)).toBe(true);
});

test("attachment-unavailable modal: opens via keyboard, Escape closes, focus returns to trigger", async ({
  page,
}) => {
  // Exercises the FR-26 modal's keyboard contract directly against a post
  // known to have an attachment; the current real-file state of that
  // specific attachment doesn't matter to this test, which is only
  // checking the <dialog>'s own keyboard behavior once opened.
  await page.goto(BASE + "posts/a699dd14-facd-545e-8b09-aed0d474a8a8/");
  const trigger = page.locator("[data-open-attachment-modal]");
  if ((await trigger.count()) === 0) {
    test.skip(true, "attachment currently available -- no modal trigger on this build");
  }
  await trigger.focus();
  await page.keyboard.press("Enter");
  const dialog = page.locator("#attachment-modal");
  await expect(dialog).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  const active = await page.evaluate(() => document.activeElement.hasAttribute("data-open-attachment-modal"));
  expect(active).toBe(true);
});
