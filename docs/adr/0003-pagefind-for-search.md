# ADR-0003: Pagefind for full-text search

**Status:** Accepted

## Context

FR-9–FR-13 require full-text search across all post subjects/bodies, running entirely client-side (no server, per GitHub Pages hosting), with stemming, subject-favoring ranking, and highlighted snippets, and with the index generated at build time rather than constructed in-browser (FR-11).

## Decision

Use Pagefind, run as a post-build step against Eleventy's rendered HTML output (ADR-0002).

**Alternatives considered:**
- **Lunr.js / elasticlunr** — solid, well-known libraries, but the document collection fed to them has to be assembled and shipped separately from the rendered HTML, creating a second thing that must stay in sync with what the site actually shows.
- **Custom inverted index** — full control, but reimplements stemming, ranking, and highlight-generation that Pagefind already provides, tested, at no cost — not a reasonable risk to take on for a first release.

Pagefind was preferred specifically because it indexes the *already-built* static HTML rather than a separately-maintained document collection — the index structurally cannot drift from what's actually rendered — and it is SSG-agnostic, so it has no opinion about Eleventy either.

## Consequences

- Search indexing is a required, ordered step after the site build completes (`make index` depends on a completed `make build`) — reflected directly in the Makefile design (hld.md §9).
- The local dev server (`make serve`) does not get live search-index updates on every edit; acceptable for a frozen-content archive site.
- Exact UI customization depth (Pagefind's default UI vs. custom markup against its API) is deferred to the DD.
