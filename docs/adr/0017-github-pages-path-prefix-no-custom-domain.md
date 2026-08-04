# ADR-0017: Accept the GitHub Pages subpath; no custom domain

**Status:** Accepted

## Context

The repo is `code-monki/yahoo-groups-tne-archive` — a project repo, not a `<user>.github.io` repo. Without a custom domain, GitHub Pages serves it at `https://code-monki.github.io/yahoo-groups-tne-archive/`, not at the domain root. This wasn't addressed by any prior design document, but it affects nearly everything: every internal link in every one of the 11 templates, the hand-rolled sitemap (ADR-0016), and Pagefind's asset base path (ADR-0003/ADR-0011) all need to resolve correctly under that subpath, not root — a detail that works by accident when serving locally (root-served by `make serve`) and silently breaks every internal link/asset only once actually deployed, if not designed in from the start.

The alternative — a custom domain — would remove the subpath entirely, but costs money (domain registration, however modest), and no document across the entire design phase (concept.md through the ADR log) ever raised a custom domain as something this project needs or wants. srs.md §2.2 states an explicit constraint: no budget for paid services.

## Decision

Accept the GitHub Pages default subpath. Configure Eleventy's `pathPrefix` (`.eleventy.js`) to `/yahoo-groups-tne-archive/`, and use its `url` filter/shortcode for every internal link, the sitemap, and Pagefind's asset references — established from Phase 1 of implementation, not retrofitted later.

## Consequences

- No added cost, consistent with the existing no-paid-services constraint.
- The canonical site URL is `https://code-monki.github.io/yahoo-groups-tne-archive/`, not a clean root domain — a minor cosmetic cost for a project whose primary audience arrives via search or a direct link, not by guessing a URL.
- Fully reversible later: if a custom domain is ever added, it's a `pathPrefix: ""` config change plus a `CNAME` file — not a template rewrite — *provided* the `url` filter convention is actually followed everywhere from the start, which is why this is being decided now rather than left implicit.
- Every template, the sitemap, and the search JS must consistently use the `url` filter rather than hand-written absolute paths — a discipline that has to hold across all of Phases 3–8, not just Phase 1's scaffolding.
