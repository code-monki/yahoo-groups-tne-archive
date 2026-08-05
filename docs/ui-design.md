# UI Design Specification: Traveller_TNE Archive Site

**Status:** Draft
**Derived from:** concept.md §8, hld.md §7–9, dd.md §9
**Fills:** the visual-design gap between dd.md's file structure (`tokens.css`, `base.css`, `components.css`) and actual values — nothing here changes DD architecture, it gives the missing content for it.

## 1. Design direction

concept.md §8's brief: modern, legible, high-contrast-by-default, minimal chrome — content is the focus. This document commits to **restrained editorial design over thematic RPG skinning** (no faux-retro sci-fi typography, no chrome/space imagery as decoration) — see [ADR-0012](adr/0012-editorial-design-over-thematic-skin.md). An archive whose job is to stay legible and pass WCAG/Lighthouse for years shouldn't chase a genre aesthetic that dates or that fights contrast/readability; the one nod to subject matter is a cool, technical-reading accent blue rather than anything more literal.

## 2. Design tokens — color

All pairs below are computed WCAG 2.2 contrast ratios (relative-luminance formula, not eyeballed), verified before any component spec uses them. Body/UI text needs ≥4.5:1 (AA, normal text); non-text UI components (borders that convey a boundary, e.g. buttons/inputs) need ≥3:1 per SC 1.4.11 — a purely decorative divider does not, so two separate border tokens exist rather than one border color serving both jobs.

| Token | Light | Dark |
|---|---|---|
| `--color-bg` | `#FFFFFF` | `#121417` |
| `--color-surface` (cards, modal, code blocks) | `#F5F6F8` | `#1B1E22` |
| `--color-text` | `#1A1A1A` | `#EDEDED` |
| `--color-text-muted` (dates, metadata) | `#55595E` | `#A8AEB5` |
| `--color-accent` (links, active state) | `#1F4FD6` | `#7FA8FF` |
| `--color-accent-on` (text placed on an accent-filled surface) | `#FFFFFF` | `#121417` |
| `--color-border-decorative` (list dividers — informational only, not a required cue) | `#D9DCE1` | `#33383D` |
| `--color-border-ui` (buttons, inputs, anything whose boundary is the only cue to its interactivity) | `#767B82` | `#7A8087` |
| `--color-focus` (focus ring — same hue as accent, kept as its own token in case that ever diverges) | `#1F4FD6` | `#7FA8FF` |

Verified ratios (computed, not asserted):

| Pair | Ratio | Needs | Pass |
|---|---|---|---|
| Light bg / text | 17.4:1 | 4.5:1 | AAA |
| Light bg / muted text | 7.1:1 | 4.5:1 | AAA |
| Light bg / accent (as link text) | 6.7:1 | 4.5:1 | AAA |
| Light accent-bg / accent-on text (buttons) | 6.7:1 | 4.5:1 | AAA |
| Light bg / border-ui | 4.3:1 | 3:1 | AA |
| Dark bg / text | 15.8:1 | 4.5:1 | AAA |
| Dark bg / muted text | 8.3:1 | 4.5:1 | AAA |
| Dark bg / accent (as link text) | 7.9:1 | 4.5:1 | AAA |
| Dark accent-bg / accent-on text (buttons) | 7.9:1 | 4.5:1 | AAA |
| Dark bg / border-ui | 4.6:1 | 3:1 | AA |

`--color-border-decorative` deliberately does *not* clear 3:1 in either theme — it's used only where a plainer, quieter division reads better (e.g. between search results) and where no information depends on it being visible (removing it entirely would cost nothing functionally). It must never be used as a button/input boundary; `--color-border-ui` is for that.

## 3. Typography

**Decision: system font stack, no web fonts** — see [ADR-0013](adr/0013-system-font-stack.md).

```css
font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
```

Type scale (all `rem`, scales with user font-size preference):

| Token | Size | Use |
|---|---|---|
| `--text-sm` | 0.875rem | metadata, timestamps, nav |
| `--text-base` | 1rem | body copy |
| `--text-lg` | 1.25rem | post subject (h1 on post pages) |
| `--text-xl` | 1.75rem | section/page titles |
| `--text-2xl` | 2.25rem | site name (home page only) |

Line length: post/thread body copy is capped at `65ch` max-width for readability; list/browse views may use the fuller container width.

## 4. Spacing & layout

4px base unit: `--space-1: 0.25rem` through `--space-8: 2rem` (doubling-ish scale: 4/8/12/16/24/32/48/64px). Content container max-width `760px`, centered, with `--space-4`–`--space-6` side padding depending on viewport.

**Breakpoints** (mobile-first, no layout logic below the smallest): base (any width) → `640px` (nav switches from collapsed to inline) → `1024px` (browse/search list views gain a secondary column for filters/facets, if any are added later).

No box-shadow-based elevation: surfaces (cards, the modal) are distinguished by `--color-surface` + a `--color-border-decorative` outline, not shadows — simpler in dark mode (shadows read poorly on dark backgrounds without extra tuning) and one less thing to get wrong for print/high-contrast-mode users.

## 5. Components

- **Header**: static (not sticky, to avoid extra layout/CLS complexity). Leftmost element is a small original sunburst mark (inline SVG, radiating lines in `--color-accent`, `aria-hidden="true"` since it's decorative and the site name text already conveys identity) — see [ADR-0012's amendment](adr/0012-editorial-design-over-thematic-skin.md#amendment-header-brand-mark) for why this is an original mark and not the actual TNE cover art. Followed by the two-line site name/subtitle, then nav (Home / Browse / Authors / Topics / Files / Search / Help), then the theme toggle button. Below `640px`, nav collapses into a native `<details>`/`<summary>` disclosure rather than a custom JS-driven menu — keyboard operability and open/closed semantics come for free, consistent with ADR-0006's "prefer native elements" pattern. (The mockup implements the two nav states as separate markup rather than trying to force the `<details>` open via CSS for the wide viewport — a `<details>` element's content stays natively hidden whenever it lacks the `open` attribute, regardless of `display` overrides on ancestors, so a CSS-only trick to keep it "always open" above 640px doesn't actually work.)
- **Breadcrumb**: every non-home page carries a `Home › Section › Detail`-style trail (native links/buttons, not decorative text), giving a persistent way back to the parent list in addition to global nav — this is the concrete implementation of hld.md §7's "visibility of system status" / breadcrumb commitment.
- **Help page**: plain prose content (no novel interactive pattern) — an intro paragraph, a "using the archive" section, the trademark/copyright disclaimer block (styled via `--color-surface`, matching the Modal's surface treatment for visual consistency), and the Notice-and-Takedown section (FR-25) with both contact channels as inline links. Reachable from every page's nav (FR-16) and the footer's single link (FR-24).
- **Footer**: deliberately minimal — a single, centered link to `/help/#takedown` (FR-24). No copyright/trademark text in the footer itself; that full text lives only on the Help page (FR-25), keeping the footer light on every other page while still making the takedown pathway one click away from anywhere on the site.
- **Post page**: subject as `<h1>`; byline shows `author.display_name` and a human-formatted `date_original`, with `date_utc` as the `<time datetime="...">` element's machine-readable value (both present per DR-3, only one need be visually prominent); a "context strip" above the body links to the parent post (if any) and lists direct replies (if any) per FR-7; attachment link or FR-26 modal-trigger button sits at the end of the body.
- **Thread view**: a simple vertical list, each post separated by `--color-border-decorative`, with a left accent border (`--color-accent`, 3px) on the post currently being read when linked to mid-thread — not a deeply indented tree, matching ADR-0005's linear-chain reality rather than implying branching structure the data doesn't support.
- **Search**: input + an `aria-live="polite"` results-count region + results as a semantic `<ol>`; matched terms rendered with the native `<mark>` element (not a custom span+class) for its built-in semantics and free default styling that CSS can still override.
- **Modal** (FR-26): native `<dialog>`, centered, `::backdrop` dimmed, max-width `480px`, a heading, the "not currently available in this archive" message, and a close button — focus trap and Escape-to-close are native behavior, not hand-built.
- **Buttons/links**: two link treatments, chosen so nothing relies on color alone to signal interactivity — **discrete-unit links** (nav items, the logo/wordmark, post titles in any list, browse/author/topic index entries, the footer takedown link) get no underline, since each is already its own distinct row/element with weight and position doing that job, not surrounding prose; **inline links** (anything sitting within a sentence of running text — breadcrumb trails, the Help page's contact `mailto:`/GitHub-issue links) keep the underline, which is what WCAG's "don't distinguish a link from surrounding text by color alone" is actually protecting against. Buttons use `--color-accent` fill with `--color-accent-on` text.

## 6. Motion

Minimal by default (no decorative animation). Any transition that exists (theme toggle, modal open/close) is wrapped in a `prefers-reduced-motion: no-preference` check and reduces to an instant state change otherwise.

## 7. Traceability

Implements the visual side of NFR-1/NFR-3/NFR-4 (WCAG), FR-19 (theming), and the file structure `dd.md` §9 already named without giving it content. Component specs above map directly to the templates listed in `dd.md` §7.2.

## 8. Mockup reference screenshots

Rendered directly from the interactive mockup (`screenshots/`), one row per page type, light and dark theme side by side. These are the actual contrast-verified tokens from §2 as they render in a browser — not a redrawn approximation — captured via a headless Chrome/Playwright pass over the mockup's local HTML rather than the hosted artifact (the published artifact URL requires an authenticated session to render, which a headless browser doesn't have; the local file is byte-identical content).

| Screen | Light | Dark |
|---|---|---|
| Home | <img src="screenshots/home-light.png" width="420"> | <img src="screenshots/home-dark.png" width="420"> |
| Post | <img src="screenshots/post-light.png" width="420"> | <img src="screenshots/post-dark.png" width="420"> |
| Thread | <img src="screenshots/thread-light.png" width="420"> | <img src="screenshots/thread-dark.png" width="420"> |
| Browse (index) | <img src="screenshots/browse-light.png" width="420"> | <img src="screenshots/browse-dark.png" width="420"> |
| Browse (year detail) | <img src="screenshots/browse-year-light.png" width="420"> | <img src="screenshots/browse-year-dark.png" width="420"> |
| Authors (index) | <img src="screenshots/authors-light.png" width="420"> | <img src="screenshots/authors-dark.png" width="420"> |
| Author (detail) | <img src="screenshots/author-light.png" width="420"> | <img src="screenshots/author-dark.png" width="420"> |
| Topics (index) | <img src="screenshots/topics-light.png" width="420"> | <img src="screenshots/topics-dark.png" width="420"> |
| Topic (detail) | <img src="screenshots/topic-light.png" width="420"> | <img src="screenshots/topic-dark.png" width="420"> |
| Search | <img src="screenshots/search-light.png" width="420"> | <img src="screenshots/search-dark.png" width="420"> |
| Help | <img src="screenshots/help-light.png" width="420"> | <img src="screenshots/help-dark.png" width="420"> |

## New ADRs from this document

- [ADR-0012](adr/0012-editorial-design-over-thematic-skin.md) — Editorial/neutral visual design over thematic RPG skin
- [ADR-0013](adr/0013-system-font-stack.md) — System font stack, no web fonts
