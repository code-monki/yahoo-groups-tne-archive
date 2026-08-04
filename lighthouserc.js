// TC-PERF-01 (NFR-5): Lighthouse CI against the same 11 representative
// templates (test-plan.md §2) the axe-core/Playwright suites use, not all
// ~5830 generated pages -- same reasoning as test-plan.md §2 itself (all
// posts/threads/authors/topics/browse-months share one template each, so
// template-level coverage is what's meaningful).
const FIXTURES = [
  "/index.html",
  "/posts/6835/index.html",
  "/threads/7153/index.html",
  "/authors/dcndcn13/index.html",
  "/authors/index.html",
  "/topics/question-for-the-group/index.html",
  "/topics/index.html",
  "/browse/2012/index.html",
  "/browse/2012/03/index.html",
  "/search/index.html",
  "/help/index.html",
];

module.exports = {
  ci: {
    collect: {
      staticDistDir: "./_site",
      url: FIXTURES,
      numberOfRuns: 1,
    },
    assert: {
      assertions: {
        "categories:performance": ["error", { minScore: 0.9 }],
        "categories:accessibility": ["error", { minScore: 0.9 }],
        "categories:best-practices": ["error", { minScore: 0.9 }],
        "categories:seo": ["error", { minScore: 0.9 }],
      },
    },
    upload: {
      target: "filesystem",
      outputDir: "./.lighthouseci",
    },
  },
};
