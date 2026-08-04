// TC-A11Y-01 (NFR-1): axe-core scan against all 11 representative templates
// (test-plan.md §2), both themes -- zero critical/serious violations.
// TC-A11Y-04 (NFR-4) is folded in here: axe-core's default ruleset
// includes WCAG 2.2 AA color-contrast checks, so a dedicated contrast pass
// would just be re-running the same scan a second time.
const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

const BASE = "http://localhost:8098/yahoo-groups-tne-archive";

// One fixture per template (dd.md §7.2 / test-plan.md §2), picked for real
// content: the largest author/topic/thread/browse-year in the archive
// rather than an arbitrary example, per test-plan.md §2's fixture guidance.
const PAGES = {
  home: "/",
  post: "/posts/6835/",
  thread: "/threads/7153/",
  author: "/authors/dcndcn13/",
  "authors-index": "/authors/",
  topic: "/topics/question-for-the-group/",
  "topics-index": "/topics/",
  "browse-year": "/browse/2012/",
  "browse-month": "/browse/2012/03/",
  search: "/search/",
  help: "/help/",
};

for (const [name, path] of Object.entries(PAGES)) {
  for (const theme of ["light", "dark"]) {
    test(`axe: ${name} (${theme})`, async ({ page }) => {
      // Setting data-theme at runtime (post-load) triggers base.css's
      // 120ms color transition on links/buttons -- scanning immediately
      // after would catch axe mid-transition on an interpolated color that
      // matches neither theme's real tokens (confirmed: an initial version
      // of this test reported failures on colors like #406ee4, which is
      // neither theme's actual --color-accent). emulateMedia loads the
      // page directly in the target theme via the prefers-color-scheme
      // media query instead, with no runtime transition involved.
      await page.emulateMedia({ colorScheme: theme });
      await page.goto(BASE + path);
      const results = await new AxeBuilder({ page }).analyze();
      const serious = results.violations.filter(
        (v) => v.impact === "critical" || v.impact === "serious"
      );
      if (serious.length) {
        console.log(JSON.stringify(serious, null, 2));
      }
      expect(serious, `${name} (${theme}) violations`).toEqual([]);
    });
  }
}
