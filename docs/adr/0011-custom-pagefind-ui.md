# ADR-0011: Custom Pagefind UI instead of the default widget

**Status:** Accepted

## Context

ADR-0003 chose Pagefind for search but deferred how much of its default `PagefindUI` drop-in widget to use versus building custom markup against its JS API. FR-13 requires subject-favoring ranking and highlighted snippets; ADR-0004 committed to hand-written CSS matching the site's own design tokens; hld.md §7 already commits to Nielsen's "visibility of system status" via things like breadcrumbs and active-nav-highlighting.

## Decision

Build a custom search UI (`site/js/search.js`, `search.njk`) against Pagefind's JS API (`pagefind.search()`, `pagefind.filter()`) rather than using the default `PagefindUI` widget.

## Consequences

- Full control over result markup: a semantic `<ol>`/`<li>` list rather than the widget's generic divs, and an `aria-live="polite"` region announcing result-count changes as the user types/searches.
- Full control over snippet/highlight rendering and result ordering, so FR-13's exact ranking/highlight requirements are met precisely rather than approximated by the widget's defaults.
- No need to override the widget's own shipped CSS to match ADR-0004's design tokens — one less source of visual/CSS-specificity friction.
- More implementation work up front than dropping in the pre-built widget — accepted as worthwhile given the accessibility and design-consistency requirements already committed to elsewhere in this project.
