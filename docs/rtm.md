# Requirements Traceability Matrix: Traveller_TNE Archive Site

**Status:** Draft
**Traces:** [srs.md](srs.md) requirements → design decisions in [hld.md](hld.md), [dd.md](dd.md), [ui-design.md](ui-design.md), and [adr/](adr/) → planned verification method.

## How to read this

Each row maps one SRS requirement to (a) the concrete design artifact(s) that satisfy it and (b) how it will eventually be verified. The **Verification Method** column uses short codes tied to the test tooling already chosen in dd.md §11 — this fixes *how* each requirement will be checked; the actual test cases, thresholds-as-run, and pass/fail records are the Test Plan's job (next document), not this one's.

| Code | Method |
|---|---|
| `[Build]` | Automated build-time assertion or script (grep/regex scan, file-count/path check, uniqueness check) |
| `[A11y]` | Automated accessibility scan (`@axe-core/playwright`, per dd.md §11) |
| `[Perf]` | Lighthouse CI run (per dd.md §11) |
| `[Link]` | Automated link-integrity check (`linkinator`, per dd.md §11) |
| `[Manual]` | Defined manual procedure (sample review, keyboard walkthrough, heuristic review) |

Some requirements already have partial design-time evidence — not just a plan to verify later, but something already checked. These are marked **✓ pre-verified** and noted specifically; everything else is traceable-but-pending, awaiting real implementation.

## 1. Functional Requirements

### 1.1 Content & post display

| ID | Design Reference | Verification |
|---|---|---|
| FR-1 | hld.md §6 (URL map), dd.md §2 (`id` field), dd.md §7.2 (`post.njk`) | `[Build]` file-count/path assertion |
| FR-2 | dd.md §2 (schema fields), ui-design.md §5 (Post page spec) | `[Manual]` sample review + `[Build]` field-match assertion |
| FR-3 | data-structures.md §5 (boilerplate signatures identified), dd.md §4 (`normalize.py`) | `[Build]` automated boilerplate-signature scan |
| FR-4 | ADR-0008, dd.md §4 (`normalize.py` PII scrub) | `[Build]` automated email-regex scan (shared mechanism with DR-4) |
| FR-5 | dd.md §2 (`author.display_name`), ui-design.md §5 | `[Manual]` sample byline review |

### 1.2 Threading

| ID | Design Reference | Verification |
|---|---|---|
| FR-6 | ADR-0005 (hybrid algorithm), dd.md §4 (`thread.py`) | `[Manual]` hand-verified test-set comparison |
| FR-7 | ui-design.md §5 ("context strip") — **✓ pre-verified**: rendered in mockup, `screenshots/post-*.png` | `[Manual]` sample review |
| FR-8 | hld.md §6 (`/threads/<id>/`), dd.md §7.2 (`thread.njk`), ui-design.md §5 (Thread view) — **✓ pre-verified**: `screenshots/thread-*.png` | `[Manual]` sample review |

### 1.3 Search

| ID | Design Reference | Verification |
|---|---|---|
| FR-9 | ADR-0003 (Pagefind), hld.md §8, dd.md §8 | `[Manual]` network-trace check |
| FR-10 | ADR-0003 (stemming) — **✓ pre-verified**: mockup demonstrates the exact "orbit"/"orbiting" case, `screenshots/search-*.png` | `[Manual]` documented test case |
| FR-11 | ADR-0003, hld.md §1 (pipeline diagram: index built post-build), dd.md §10 (`make index`) | `[Perf]` page-load trace |
| FR-12 | dd.md §8 (ADR-0011 custom Pagefind UI) | `[Manual]` sample result click-through |
| FR-13 | ADR-0011 — **✓ pre-verified**: subject-first ranking + `<mark>` highlight rendered in mockup, `screenshots/search-*.png` | `[Manual]` sample review |

### 1.4 Browse & navigation

| ID | Design Reference | Verification |
|---|---|---|
| FR-14 | hld.md §6 (`/browse/<year>/<month>/`), dd.md §7.1 — **✓ pre-verified**: real 2005–2019 counts rendered, `screenshots/browse-*.png` | `[Build]` count-match assertion |
| FR-15 | hld.md §6 (`/authors/`), dd.md §7.1, §7.3 (slug rule) — **✓ pre-verified**: `screenshots/authors-*.png` | `[Build]` count-match assertion |
| FR-16 | ui-design.md §5 (Header) — **✓ pre-verified**: identical nav present across all 11 mockup screens, both themes | `[Build]`/`[Manual]` markup-consistency check |
| FR-17 | hld.md §6 (`/topics/`), dd.md §2 (`subject_normalized`), dd.md §7.1 — **✓ pre-verified**: real subjects/authors from source archive, `screenshots/topics-*.png` | `[Build]` reachability check |

### 1.5 Help & documentation

| ID | Design Reference | Verification |
|---|---|---|
| FR-18 | hld.md §6 (`/help/`) — **✓ pre-verified**: `screenshots/help-*.png`. **Gap**: ui-design.md's §5 component list has no dedicated Help-page entry (only referenced via footer/nav) — see §4 below. | `[Manual]` content-element checklist |

### 1.6 Presentation extras

| ID | Design Reference | Verification |
|---|---|---|
| FR-19 | ui-design.md §8 (Theming), dd.md §9 (`tokens.css`, `data-theme`) — **✓ pre-verified**: every one of the 22 screenshots is a real light/dark pair rendered from the actual token values | `[Manual]` OS-preference toggle test |
| FR-20 | hld.md §6 (path), ADR-0016 (hand-rolled sitemap template, no plugin dependency), dd.md §7.4 (mechanism + OG metadata) | `[Build]` sitemap/meta presence scan |
| FR-21 (Could) | hld.md §6 (path only) | `[Manual]` |
| FR-22 (Could) | hld.md §6 (path only) | `[Build]` aggregate match |

### 1.7 Attachment handling

| ID | Design Reference | Verification |
|---|---|---|
| FR-23 | ADR-0006, dd.md §6 — **✓ pre-verified**: available-state rendered, `screenshots/post-*.png` | `[Build]` link-resolution check |
| FR-26 | ADR-0006, dd.md §6, ui-design.md §5 (native `<dialog>` modal) — **✓ pre-verified**: unavailable-state affordance rendered in mockup (the modal's *open* state itself wasn't captured in the static screenshot set, since it's a transient interaction, not a navigable screen — available to check live in the artifact) | `[A11y]`/`[Manual]` keyboard-activation + focus-trap check |
| FR-27 | ADR-0006, ADR-0007/ADR-0009 (ID stability underpins this), dd.md §5/§6 | `[Manual]` add-file-and-rebuild scenario test |

### 1.8 Legal & policy display

| ID | Design Reference | Verification |
|---|---|---|
| FR-24 | ADR-0014, ui-design.md §5 (Footer) — **✓ pre-verified**: centered takedown link present in all 22 screenshots | `[Build]`/`[Link]` link-presence check |
| FR-25 | srs.md FR-25 + concept.md §12 (policy text itself) — **✓ pre-verified**: full policy content rendered, `screenshots/help-*.png`. **Gap**: same as FR-18, no dedicated ui-design.md Help-page component entry. | `[Manual]` content checklist (email address, GitHub Issues link, policy text all present) |

## 2. Data Requirements

| ID | Design Reference | Verification |
|---|---|---|
| DR-1 | dd.md §4 (`parse_mbox.py`, `digest_parser.py`), data-structures.md §2.1 | `[Manual]` spot-check sample digests |
| DR-2 | ADR-0010 (tie-break rule), dd.md §5 | `[Build]` uniqueness-key scan |
| DR-3 | dd.md §4 (`normalize.py`), dd.md §2 (`date_utc`/`date_original` fields) | `[Build]` ISO 8601 validity scan |
| DR-4 | ADR-0008, dd.md §4 | `[Build]` regex scan (shared mechanism with FR-4) |
| DR-5 | dd.md §4 (digest-parser validation note) | `[Manual]` yearly sample diff |
| DR-6 | ADR-0001, dd.md §1 (repo layout: pipeline reads only `mail_archives/`, writes `data/posts.json`; site reads only the dataset) | `[Build]` source-grep static analysis |
| DR-7 | hld.md §4 step 5 (Mork cross-check) | `[Manual]` dev-time comparison note |
| DR-8 | ADR-0006, dd.md §1/§2/§6 (`attachments/<id>/<filename>`) | `[Build]` file-copy verification |

## 3. Non-Functional Requirements

### 3.1 Accessibility

| ID | Design Reference | Verification |
|---|---|---|
| NFR-1 | ui-design.md (whole document), dd.md §11 | `[A11y]` automated scan |
| NFR-2 | ui-design.md §5 (native `<dialog>`/`<details>`), dd.md §11 | `[A11y]`/`[Manual]` keyboard walkthrough |
| NFR-3 | hld.md §7 (landmark/heading rules), dd.md §11 | `[A11y]` automated crawl |
| NFR-4 | ui-design.md §2 — **✓ pre-verified, and the strongest evidence in this whole matrix**: actual computed WCAG contrast ratios (not just planned), every text/background pair checked before any component used them | `[A11y]` automated contrast check (confirms at implementation time what's already computed here) |

### 3.2 Performance & quality

| ID | Design Reference | Verification |
|---|---|---|
| NFR-5 | dd.md §11 (Lighthouse CI), ADR-0004 (no CSS framework), ADR-0013 (system fonts) | `[Perf]` Lighthouse CI run |
| NFR-6 | ADR-0015 (page-scoped, `defer`red, query-param handoff from other pages), dd.md §9 | `[Perf]` network/performance trace — confirms the search script tag is absent outside `search.njk` |

### 3.3 Usability

| ID | Design Reference | Verification |
|---|---|---|
| NFR-7 | hld.md §7 — **✓ pre-verified in part**: all ten Nielsen heuristics already mapped to specific site elements (not just planned to be reviewed later, an initial mapping already exists) | `[Manual]` documented heuristic review against the finished implementation |

### 3.4 Hosting & deployment

| ID | Design Reference | Verification |
|---|---|---|
| NFR-8 | ADR-0002 (Eleventy static output), hld.md §9 | `[Build]` static-output audit |
| NFR-9 | hld.md §9 (GitHub Actions workflow), concept.md §12 (repo name decided) | `[Build]` successful automated deployment run |

### 3.5 Legal & licensing

| ID | Design Reference | Verification |
|---|---|---|
| NFR-10 | concept.md §12 | `[Manual]` `LICENSE` file presence/content check |
| NFR-11 | concept.md §12, ADR-0014, FR-25 | `[Manual]` content presence check on Help page |

## 4. External Interface Requirements

| ID | Design Reference | Verification |
|---|---|---|
| IR-1 | hld.md §9, ADR-0002/ADR-0003 (no third-party service dependency by design) | `[Build]` dependency/network audit |
| IR-2 | concept.md §4 (non-goals), hld.md §6 | `[Manual]` full browser-only walkthrough |

## 5. Traceability gaps identified

Compiling this matrix surfaced three real gaps — this is the RTM doing its job, not a failure of earlier documents. All three were closed immediately rather than carried forward:

1. ~~**FR-20 (sitemap + OG/Twitter metadata)**~~ — **Closed, properly.** Same lesson as NFR-6 below: the first pass named a mechanism (a sitemap plugin) without weighing it as a real choice. Recorded as [ADR-0016](adr/0016-sitemap-hand-rolled-not-plugin.md): hand-rolled template, no plugin dependency, consistent with ADR-0004's precedent and the project's explicit low-maintenance-forever goal (concept.md §3).
2. ~~**FR-18/FR-25 (Help page)**~~ — **Closed.** ui-design.md §5 now has a dedicated Help-page component entry.
3. ~~**NFR-6 (non-blocking search JS)**~~ — **Closed, properly this time.** The first pass at closing this gap added the mechanism straight into dd.md §9 as an implementation footnote without treating it as a real decision — it was pointed out that the choice between "search works instantly from every page" and "search costs nothing except on its own page" is a genuine tradeoff, not just a detail. Recorded as [ADR-0015](adr/0015-search-loads-only-on-search-page.md): page-scoped `defer`, with other pages' search boxes handing off via a plain GET to `/search/?q=...` that auto-runs on load.

## 6. Coverage summary

| Category | Count | Design-traced | Pre-verified now (mockup/computed evidence) |
|---|---|---|---|
| Functional (FR) | 25 | 25/25 | 13 |
| Data (DR) | 8 | 8/8 | 0 (all pending real ETL implementation) |
| Non-functional (NFR) | 11 | 11/11 | 2 (NFR-4, NFR-7 partially) |
| External Interface (IR) | 2 | 2/2 | 0 |
| **Total** | **46** | **46/46** | **15** |

Every requirement traces to a design decision; none are orphaned. The "pre-verified" count is a bonus of having built the interactive mockup and the computed contrast table before writing this RTM — most of those are FR items whose visual/UX shape the mockup already demonstrates, not a substitute for the real automated checks the Test Plan will define.
