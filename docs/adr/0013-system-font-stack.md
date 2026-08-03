# ADR-0013: System font stack, no web fonts

**Status:** Accepted

## Context

Typography choice affects performance (NFR-5's Lighthouse ≥90 target) — web fonts add network requests and are a common cause of layout shift (CLS) and render-blocking delay if not carefully subsetted and preloaded.

## Decision

Use the OS/browser's own UI font via a system font stack (`ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`) for all text, headings included. No self-hosted or third-party web fonts.

## Consequences

- Zero font-loading network requests, zero associated CLS/render-blocking risk — one less category of Lighthouse Performance regression to guard against.
- Typography looks slightly different across operating systems (San Francisco on macOS/iOS, Segoe UI on Windows, Roboto on Android/ChromeOS) rather than being pixel-identical everywhere — accepted as consistent with ADR-0012's restrained, content-first design direction rather than a brand-typography-driven one.
- If a more distinctive display typeface is wanted later (e.g., for the site name only), it can be added as a single, carefully subsetted, `font-display: swap` web font scoped to that one element without revisiting this decision for body/UI text.
