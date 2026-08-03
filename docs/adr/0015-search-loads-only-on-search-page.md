# ADR-0015: Search JS/index loads only on the search page; other pages hand off via URL

**Status:** Accepted

## Context

NFR-6 requires the search index asset and any core-interaction JS not block first render of page content, anywhere on the site. Pagefind's runtime and index asset (ADR-0003) are lazy by design, but they still have real weight, and a search box appears on more than just `/search/` itself — the mockup's Home screen has its own inline search form (ui-design.md, `screenshots/home-*.png`). That creates a real choice, not just an implementation detail: should search be instantly interactive from wherever its box appears (meaning the search JS has to be at least `defer`-loaded on every page that has one), or should every page other than `/search/` carry zero search-related cost, at the price of an extra navigation for anyone who starts typing from, say, Home?

## Decision

Page-scoped, not global. `site/js/search.js` and Pagefind's runtime/index asset are included via a `defer`red `<script>` only on `search.njk`. A search box on any other page (Home's, most notably) is a plain HTML `<form method="get" action="/search/">` — no JS dependency to "start" a search from elsewhere. `search.njk` reads its `q` query-string parameter on load and, once Pagefind initializes, runs that query automatically — so the user experience is type once, submit once, see results, not type-submit-then-retype-on-a-blank-search-page.

## Consequences

- Every page except `/search/` carries zero search-related JS or index weight — the strongest reading of NFR-6 available (absence, not just non-blocking presence), and the simplest to verify (`[Build]`/`[Perf]`: confirm the script tag is template-scoped, not in the shared layout).
- The cost is one extra page navigation between typing a query on Home and seeing results — acceptable on a static site where that navigation is just as fast as any other page load, and fully mitigated for the user by the auto-run-on-load behavior (no re-typing, no extra click beyond the one they already made).
- Free progressive enhancement as a side effect, not an extra design effort: the Home search form is a real GET form to a real URL, so it functions (navigates to search results) even with JavaScript disabled, right up to the point where Pagefind itself is needed to actually run the query.
- If a future requirement calls for live, no-navigation search-as-you-type from every page, this ADR would need to be revisited — noted here so that request isn't mistaken for a bug in this behavior.
