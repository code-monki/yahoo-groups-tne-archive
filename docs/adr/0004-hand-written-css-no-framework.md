# ADR-0004: Hand-written CSS, no framework

**Status:** Accepted

## Context

concept.md §8 sets a design brief of "modern, legible, high-contrast-by-default, minimal chrome — the archive's content should be the focus, not a heavy design layer on top of it." Lighthouse Performance (NFR-5) penalizes shipped-but-unused CSS.

## Decision

Plain modern CSS: custom properties for design tokens (color, spacing, type scale), native `prefers-color-scheme` media queries for theming (FR-19), Grid/Flexbox/logical properties for layout. No Tailwind, Bootstrap, or comparable framework.

## Consequences

- Slightly more manual work per component than reaching for pre-built utility classes or components.
- Avoids an entire category of "unused CSS" performance risk, and avoids a framework's own visual defaults working against the "minimal chrome" brief.
- Design tokens (colors in particular) are defined once and contrast-verified against WCAG 2.2 AA for both themes before any page uses them (NFR-4), rather than checked page-by-page after the fact.
