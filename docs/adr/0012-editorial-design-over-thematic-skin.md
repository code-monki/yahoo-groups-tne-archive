# ADR-0012: Editorial/neutral visual design over thematic RPG skin

**Status:** Accepted

## Context

The archive's subject matter is a *Traveller* (sci-fi RPG) mailing list, which invites an obvious temptation: a "space/sci-fi" themed skin (chrome typography, starfield backgrounds, genre iconography). concept.md §8 already set a brief of "modern, legible, high-contrast-by-default, minimal chrome," and this site is meant to stay legible and pass WCAG/Lighthouse for years, not read as a period-piece fan-site skin.

## Decision

Restrained editorial design: a neutral, content-first layout (ui-design.md), with the sole nod to subject matter being a cool, technical-reading accent blue rather than any literal sci-fi imagery, iconography, or display typography.

## Consequences

- Lower risk to long-term accessibility and Lighthouse scores — genre-themed decorative elements (background imagery, low-contrast "atmospheric" color choices, unusual display fonts) are a common source of both contrast failures and performance cost, and this design avoids that category of risk entirely.
- The site will read as a plain, editorial archive rather than a themed fan-site — a deliberate trade-off in favor of durability and accessibility over genre flourish. Revisit only if the user later wants a more thematic treatment layered on top, e.g., a header illustration that doesn't touch body/text color tokens.

## Amendment (header brand mark)

The user asked for the *Traveller: The New Era* box-cover sunburst in the header. That specific artwork is another company's copyrighted illustration — a separate and larger concern than the trademark-*name* disclaimer this project already carries (FR-24), which covers using the word "Traveller," not reproducing published cover art. Reproducing or closely tracing the actual cover illustration was ruled out on that basis, not a design-taste basis.

The agreed resolution: a small, **original** geometric sunburst mark (radiating lines from a center point, a generic and long-standing heraldic/decorative motif with no single owner) rendered in `--color-accent`, sized as a logomark beside the site name. This is a deliberate, narrow exception to this ADR's "accent color only, no imagery" stance — scoped to one small identifying mark, not a reopening of the broader decision. No other imagery, iconography, or decoration is introduced by this change.
