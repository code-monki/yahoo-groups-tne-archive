# ADR-0002: Eleventy as the static site generator

**Status:** Accepted

## Context

The site needs many templated page types (post permalinks, threads, author pages, topic pages, year/month browse pages) generated from one large, cross-linked JSON dataset (ADR-0001) — not a blog's simple one-post-per-file model. It must build to fully static output for GitHub Pages (NFR-8), and must not get in the way of hand-written, accessibility-first markup (NFR-1–NFR-4).

## Decision

Use Eleventy (11ty) with Nunjucks templates.

**Alternatives considered:**
- **Hugo** — comparable fit and faster builds, but Go templates are more awkward for the volume of hand-written, accessibility-sensitive markup this project needs than Nunjucks.
- **Pelican** — a natural fit with the Python ETL (ADR-0001), but its content model is more blog-post-shaped and less suited to the thread/author/topic cross-indexing this site requires.
- **Astro** — strong DX and zero-JS-by-default output, but its component model is more machinery than "many pages from one big JSON file" needs, and it adds a heavier Node toolchain for no corresponding benefit here.

## Consequences

- Adds Node.js to the toolchain alongside Python (two runtimes in CI) — acceptable since each stage is isolated per ADR-0001.
- Full control over every element of markup, which is what keeps WCAG 2.2 AA conformance (NFR-1) a design property rather than something bolted on after the fact.
- Output is plain HTML/CSS/JS with nothing framework-specific shipped to the browser, keeping the Lighthouse 90+ target (NFR-5) the default outcome rather than a fight.
