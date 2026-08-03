# ADR-0014: Footer carries only a takedown-policy link, not the full disclaimer text

**Status:** Accepted
**Revises:** the footer portion of the original FR-24 (concept.md §6/§12 attribution decision), which had put the full copyright/trademark paragraph in the footer itself.

## Context

The Notice-and-Takedown policy's placement was originally driven by legal advice calling out footer *prominence* specifically as "your strongest safeguard" — the concern being that most visitors land on a single post page via search and may never click through to a Help page, so the takedown pathway needed to be reachable from anywhere. The first implementation took that literally: the full copyright statement and Mongoose Publishing trademark disclaimer, as running text, in the footer of every page. Reviewing the mockup, this read as visually heavy for content that's identical on every single page — competing with the actual archived content for attention, at odds with the "minimal chrome" direction (ADR-0012).

## Decision

The footer carries only a single, centered link to the Help page's Notice-and-Takedown section. The full copyright statement and trademark disclaimer remain, in full, on the Help page only (FR-25) — not duplicated in the footer.

## Consequences

- Preserves the property the original legal advice actually required — a takedown pathway reachable in one click from any page — without the visual cost of repeating a full paragraph of legal text on every page.
- The footer link itself follows the same no-underline, discrete-unit link treatment as nav items and post titles (ui-design.md §5), not the inline-prose treatment, since it stands alone rather than sitting within a sentence.
- If an author needs the actual copyright/trademark statement text as reassurance before contacting the site, that requires one additional click (footer link → Help page) rather than reading it in place — accepted as a reasonable trade given the click is still available from every page.
