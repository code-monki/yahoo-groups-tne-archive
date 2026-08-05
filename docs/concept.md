# Concept Document: Traveller_TNE Archive Site

**Status:** Draft — ideation phase
**Depends on:** [data-structures.md](data-structures.md)

## 1. Origin of the data

The source material is a full export of the **Traveller_TNE** Yahoo! Group (`Traveller_TNE@yahoogroups.com`), a mailing list for the *Traveller: The New Era* tabletop RPG setting, active 2005–2020 (its own final activity records the group's winding-down as Yahoo Groups itself shut down). This archive is one member's local Thunderbird export and is, as far as we know, the only surviving copy of this community's discussion history.

The export is **frozen and read-only**: no new mail will ever arrive. See [data-structures.md](data-structures.md) for the full breakdown, but in short:

- 724 mbox records, real date range 18 May 2005 – 11 Jan 2020.
- 71% of those records are Yahoo digest bundles, each containing multiple individual posts — so the true post count is higher than 724 and won't be known precisely until digest expansion is implemented.
- Threading exists partially via headers, partially only recoverable via subject-matching.
- The `.msf` file is a disposable Thunderbird cache, not a data source.

Because the source is static and finite, **we have full freedom to re-derive a clean, greenfield canonical dataset once**, rather than building an ingestion pipeline that has to tolerate ongoing change. This is a one-shot ETL problem, not a live sync problem — a meaningful simplification that should shape every downstream design decision (no incremental re-ingest logic, no conflict resolution, no live indexing service).

## 2. Vision

Turn a inbox export that is currently unreadable outside of a mail client into a public, permanent, pleasant-to-browse **static archive website** — something a *Traveller* fan (or the original participants) can land on from a search engine or a link, read a thread end-to-end, and actually find things in, years after the source community is gone.

## 3. Goals

- **Preserve** the full content and authorship of the archive faithfully and permanently.
- **Make it navigable**: real threaded conversations, not a flat chronological dump.
- **Make it findable**: full-text search across all posts, working entirely client-side (no backend, no server-side search API — this is a GitHub Pages static site).
- **Make it good**: modern visual design, WCAG 2.2 AA conformance, and high Lighthouse scores (Performance/Accessibility/Best Practices/SEO) are explicit, non-negotiable quality bars for this project — not aspirational polish added at the end.
- **Make it durable**: plain static HTML/CSS/JS, buildable and deployable with free tooling (GitHub Actions → GitHub Pages), no ongoing hosting cost or maintenance burden.

## 4. Non-goals (for this iteration)

- No user accounts, comments, or any write path — this is a read-only archive of a closed community.
- No server-side component of any kind (rules out anything requiring a database or API at runtime).
- No attempt to import the data back into a live mail system or re-syndicate it as a mailing list.
- No real-time/incremental ingestion — the ETL from mbox to canonical JSON is a build-time step run against a fixed source, not a recurring sync job.
- Not attempting to be a general-purpose "mbox-to-website" tool for other archives, even though the pipeline may end up reusable — this project is scoped to the Traveller_TNE archive specifically.

## 5. Users & use cases

- **A former list member** searching for a specific ship design, house rule, or thread they remember participating in.
- **A new *Traveller* fan** discovering the archive via search engine, browsing by topic/author/date to get oriented in a community they never experienced live.
- **A researcher/archivist** wanting confidence the content is complete and citable (permalinks per post, clear provenance).

Across all three, the core interaction loop is: **search or browse → land on a thread → read it in context → follow related threads/authors**.

## 6. Initial feature set

Grouped by priority (MoSCoW), scoped to a first public release:

**Must have**
- Every post rendered as its own permalinked page, with author, date, subject, and body faithfully preserved.
- Threaded view: a post shows its parent/children and the full conversation tree, not just itself in isolation.
- Full-text search across all post bodies and subjects, client-side, fast, with stemming (so "orbits"/"orbiting" matches "orbit").
- Chronological browse (by year/month) as a fallback navigation path for content with no clean thread.
- Author index: list of participants, with a page per author linking to their posts.
- Responsive layout usable on mobile and desktop.
- WCAG 2.2 AA conformance (keyboard navigation, semantic structure, color contrast, focus visibility, screen-reader-sensible markup throughout — not just alt text).
- **Help/About page**: a single static page documenting, for a first-time visitor, what this site is (origin of the archive, date range, unofficial fan-archive status per §12), how to use it (how search and threading work, what "digest" means if it surfaces anywhere, how to read a thread), and where to find the fair-use/attribution disclaimer. This is a non-functional requirement in its own right — it's the site's answer to Nielsen heuristic #10 (help and documentation) — not just another content page, and should be linked from global navigation on every page, not buried.
- **Copyright, trademark & Notice-and-Takedown policy**: the Help/About page carries the full copyright statement (zero ownership claimed over archived content; original authors retain copyright), the Mongoose Publishing trademark disclaimer (§12), the full Notice-and-Takedown policy text, and both contact channels (email + GitHub Issues, §12), inviting any original author to request removal or anonymization of their own posts. Every page footer carries only a link to that policy — kept deliberately minimal (just the link, not the disclaimer text itself) so the "reachable from every page" property is preserved without a paragraph of legal text competing for attention on every page.
- Topic/subject index independent of thread structure (useful given how many older posts have no reply headers at all).
- Search result ranking that favors subject matches and recency reasonably, with snippet/highlight of the matched terms.
- Dark/light theme support (respecting `prefers-color-scheme`), since this is explicitly meant to look modern.
- Sitemap + per-page metadata (Open Graph/Twitter cards, canonical URLs) for good SEO/Lighthouse "Best Practices"/"SEO" scores and reasonable link-preview behavior when shared.
- **Attachment handling, with graceful degradation for content we don't yet have.** Where a post's referenced attachment file is present at build time, render a working download link. Where it isn't — which, per data-structures.md §5, covers not just the 2 known mbox-embedded files but an unknown number of posts referencing Yahoo Groups' separate "Files"/"Photos" section (never part of this mbox export, and possibly recoverable later from a private copy someone made before Yahoo deleted it in Dec 2019) — show an affordance that opens a modal explaining the attachment isn't currently available in this archive, rather than a dead link or silent omission. Availability must be determined purely by whether the file exists in a build-time source folder (not a hardcoded per-post flag), so that dropping a recovered file into that folder and rebuilding is the *entire* process for making a previously-unavailable attachment appear — no other code or content change required. This is what makes the feature meaningfully forward-compatible with attachments that may surface later.

**Should have**
(none currently — the two former Should-have items on theming/metadata/search-ranking/topic-index moved to Must have above)

**Could have (stretch, later)**
- "On this day" / random-thread discovery widget.
- Basic stats page (posts per year, most active authors, thread-size distribution) — a nice use of data we're already computing.

**Explicitly deferred / not in scope yet**
- Any form of tagging/categorization beyond what's derivable from subjects/threads.
- Multi-archive support (this is Traveller_TNE only).

## 7. Data direction

- The mbox/digest/Mork ingestion described in [data-structures.md](data-structures.md) happens **once**, offline, producing a **canonical JSON dataset** (one record per real post — after digest expansion — with stable IDs, resolved author identity, resolved parent/thread relationships, and cleaned HTML body). This JSON becomes the single source of truth for everything downstream.
- The site generator, the search-index builder, and any future tooling all read from that canonical JSON — none of them touch the raw mbox or `.msf` directly. This decouples "how do we parse Yahoo's weird digest HTML" (a one-time, messy problem) from "how do we build a nice website" (a clean problem once the JSON exists).
- Because the archive is frozen, the canonical JSON can be checked into the repo as a build artifact/fixture rather than regenerated on every build — regeneration is only needed if we find and fix a parsing bug, not on a schedule.

## 8. Presentation & UX direction

- **Nielsen's heuristics** as the working usability checklist during design/review — in particular: visibility of system status (clear "where am I in this thread/site" wayfinding), match between system and real-world conversational structure (threads should *read* like conversations), user control (easy back-out from search/thread views), consistency, recognition-over-recall (visible navigation, not memorized URLs), flexibility (multiple paths to the same content: search, browse-by-date, browse-by-author, thread traversal), and help/documentation (the Help/About page in §6, always reachable, not a one-time onboarding modal).
- **WCAG 2.2 AA** is a hard requirement, verified, not assumed — target for the later Test Plan artifact to include actual automated (axe/Lighthouse) and manual (keyboard-only pass, screen reader spot-check) verification, not just "we used semantic HTML."
- **Lighthouse**: target 90+ across Performance, Accessibility, Best Practices, and SEO. This is achievable for a static site by default but constrains choices downstream — e.g., the search index and any client JS need to be lean and not block rendering, images (if any) need proper sizing, and fonts/CSS need to avoid layout shift.
- Visual design: modern, legible, high-contrast-by-default, minimal chrome — the archive's content (30k+ messages of hobbyist worldbuilding) should be the focus, not a heavy design layer on top of it.

## 9. Technical direction (high level — detail belongs in the HLD)

- **Hosting**: GitHub Pages, meaning 100% static output, no server runtime, no server-side search. Repo: **`yahoo-groups-tne-archive`**, deployed to that repo's associated GitHub Pages site via a GitHub Actions workflow (build-on-push, no manual deploy step).
- **Search**: needs to run entirely in the browser against a prebuilt index. The Makefile target for "generating a stemmed index" (§10) implies the index (stems, postings) is computed at build time and shipped as a static asset the client-side search UI queries — avoiding a heavy client-side indexing pass at page-load time.
- **Site generation approach** (specific SSG/framework choice, templating, styling approach) is an open decision — deliberately not locked in this concept document. It belongs in the HLA/HLD once we've agreed the feature set above is right.

## 10. Build & tooling direction

Once we move from ideation into implementation, a top-level `Makefile` will act as the single orchestrator for the project, so there's one obvious entry point regardless of what's happening underneath (Python for ETL, Node for the search index/site build, or otherwise). Anticipated targets (to be finalized in the HLD/DD, not built yet):

- `make help` — self-documenting list of targets (default target).
- `make data` — run the mbox/digest ETL and (re)produce the canonical JSON dataset.
- `make index` — generate the stemmed full-text search index from the canonical JSON.
- `make build` — generate the static site output.
- `make serve` — run a local dev server for preview.
- `make test` — run accessibility/Lighthouse/link-check validation.
- `make clean` — remove generated artifacts.
- `make deploy` — publish to GitHub Pages (likely superseded by a GitHub Actions workflow calling the same targets, so local and CI builds never drift apart).

This is captured here as direction only — the Makefile itself is a build-phase deliverable, not an ideation-phase one.

## 11. Roadmap

1. **Ideation** *(this document + data-structures.md)* — understand the data, agree on scope and direction. ← we are here
2. **SRS** — formalize the feature set in §6 into numbered, testable requirements.
3. **HLA/HLD** — architecture: SSG choice, canonical JSON schema, search index design, threading algorithm, site information architecture, accessibility approach.
4. **DD** — detailed design: module/script breakdown, data model field-by-field, build pipeline stages.
5. **RTM** — trace every SRS requirement to design and test coverage.
6. **Test Plan** — accessibility (WCAG 2.2 AA), Lighthouse thresholds, functional test coverage (search correctness, thread reconstruction correctness against the Mork cross-check), cross-browser/responsive checks.
7. **Implementation** — Makefile-orchestrated build pipeline, site generation, deployment via GitHub Actions.

We move to step 2 only once this concept document is agreed to be complete and accurate.

## 12. Open questions / risks carried forward

From [data-structures.md §6](data-structures.md#6-open-questions-to-resolve-beforeduring-implementation):

- ~~**Privacy**~~ — **Decided.** Real email addresses will **not** be published, in any form (no redaction tricks, no obfuscation-but-technically-derivable versions — simply omitted from all public output). Display names associated with posts **will** be published as-is. This applies to the canonical JSON dataset itself, not just the rendered HTML — email addresses should be stripped/excluded during the mbox→JSON ETL step (§7) rather than filtered only at render time, so no build artifact that could end up in the public repo or site ever carries them. This needs to be reflected as a hard requirement in the SRS and specifically verified in the Test Plan.
- ~~**Digest parsing completeness / template variance**~~ — **Resolved by delegation.** No specific handling mandated; this is now an implementation-time validation task (sample across 2005–2019, branch the parser only if actually needed) rather than a decision blocking ideation.
- ~~**De-duplication vs. quoted content**~~ — **Decided.** Duplicate *records* of the same post (e.g. arriving both individually and inside a digest) must be eliminated via the `/message/<id>` permalink as dedup key. A post **quoting** part or all of an earlier message in its own body is normal reply content, not a duplicate, and is left as-is.
- ~~**Timezone normalization**~~ — **Decided.** Best-effort conversion of every post's date/time to a single standard, sortable format — UTC, ISO 8601 — regardless of source format. Original wall-clock text may be retained alongside the normalized value for display purposes.

- ~~**Attribution**~~ — **Decided, refined.** Each post is attributed to its author (display name — see the privacy decision above for why not email). The site shall carry: (1) a copyright statement making clear the site claims **zero ownership** of archived content and that original authors retain copyright over their own writing; (2) a trademark disclaimer that this is an unofficial, non-commercial fan preservation project, not affiliated with or endorsed by the rights holder — exact holder name pending confirmation, see below; (3) a **Notice-and-Takedown policy**, prominent (footer, linked from every page, and detailed on the Help/About page — FR-18), inviting any original author to request removal or anonymization of their posts, with a stated contact channel — see below. This positions the site squarely as non-commercial digital preservation (comparable to Internet Archive / Usenet preservation mirrors), which is the standard footing for this kind of archive.
- ~~**Domain/repo naming**~~ — **Decided.** Repo is `yahoo-groups-tne-archive`; deploys via GitHub Actions to that repo's GitHub Pages site.
- ~~**Code license**~~ — **Decided.** Apache 2.0 for the pipeline/site source code.
- ~~**Content license**~~ — **Decided.** No explicit license is granted over archived post content. Original authors retain copyright; content is republished here under a non-commercial, historical/educational preservation rationale, with a Notice-and-Takedown policy (above) as the practical mitigation if an author objects. This matches option (a) previously recommended in this document.

- ~~**Trademark disclaimer wording**~~ — **Decided.** Names Mongoose Publishing, per your original direction: *"Traveller in all its forms is the property of Mongoose Publishing. This is an unofficial, non-commercial fan site with no affiliation."*
- ~~**Takedown-request contact channel**~~ — **Decided.** Both: `codemonki@outlook.com` as the primary contact, plus a link to open a GitHub Issue on the `yahoo-groups-tne-archive` repo as an alternative.

All of §12 is now fully settled.
