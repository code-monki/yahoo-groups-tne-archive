# Software Requirements Specification: Traveller_TNE Archive Site

**Status:** Draft
**Derived from:** [concept.md](concept.md), [data-structures.md](data-structures.md)

Requirement IDs in this document are stable identifiers for use by the later RTM and Test Plan — do not renumber existing requirements when adding new ones; append instead.

Every requirement below carries an **Acceptance Criteria** statement: the specific, checkable condition under which the requirement is considered satisfied. These are written to be verifiable by automated check, build-time assertion, or a defined manual procedure — not by judgment call. The Test Plan (a later deliverable) will turn these into actual executable test cases; this SRS fixes *what* "done" means for each requirement, not *how* it's tested.

## 1. Introduction

### 1.1 Purpose

This SRS formalizes the feature set and decisions agreed in [concept.md](concept.md) into individual, numbered, verifiable requirements, as the basis for the HLA/HLD, DD, RTM, and Test Plan that follow it in the project roadmap.

### 1.2 Scope

A static website, hosted on GitHub Pages, presenting the complete, read-only Traveller_TNE Yahoo! Group archive (724 source mbox records, spanning 18 May 2005 – 8 Aug 2019) as permalinked, threaded, full-text-searchable posts. No write path, no server-side component, no live data ingestion — see concept.md §4 for full non-goals.

### 1.3 Definitions

- **Post** — a single, individually-authored message, after digest expansion (data-structures.md §2). Not the same as an mbox record (514 of 724 mbox records are digests each containing multiple posts).
- **Canonical dataset** — the single greenfield JSON representation of all posts, produced once by the ETL pipeline, and used as the sole input to every downstream tool (concept.md §7).
- **Thread** — a set of posts connected by reply relationships (header-based or subject-fallback; data-structures.md §3).

### 1.4 References

- [concept.md](concept.md) — vision, feature set, direction
- [data-structures.md](data-structures.md) — source data format analysis

## 2. Overall Description

### 2.1 Product perspective

A new, standalone static site with no existing system to integrate with. The only "input system" is the frozen source archive (`mail_archives/`); the only "output system" is GitHub Pages.

### 2.2 Constraints

- Must build to static output only — no server runtime is available on the target host (GitHub Pages).
- Source data is fixed and finite; the ETL is a one-shot transform, not a recurring sync (concept.md §1, §7).
- No budget for paid services (fonts, search backends, analytics, etc.) — everything must run within GitHub's free Pages/Actions tiers.

### 2.3 Assumptions

- Target audience uses modern evergreen browsers (specific support matrix to be finalized in the HLD).
- Content is entirely English-language; no i18n/l10n requirement.
- The archive will not grow — no requirement anticipates future incremental ingestion of new posts.

## 3. Functional Requirements

Priority tags (**Must**/**Should**/**Could**) carry over from concept.md §6's MoSCoW grouping.

### 3.1 Content & post display

| ID | Pri. | Requirement | Acceptance Criteria |
|---|---|---|---|
| FR-1 | Must | The system shall render every unique post — after digest expansion and de-duplication (DR-2) — as its own permalinked static HTML page. | For a canonical dataset of N unique post records, build output contains exactly N static HTML files at a stable, predictable path (e.g. `/posts/<id>/`), each independently reachable with a 200 response and no query-string/fragment dependency. |
| FR-2 | Must | Each post page shall display, at minimum: author display name, normalized date/time (DR-3), subject, and full post body. | For a sample of ≥10 post pages spanning different years and authors, all four fields are present, non-empty, and match the corresponding canonical dataset record exactly. |
| FR-3 | Must | Post body markup shall have Yahoo Groups presentational boilerplate (CSS, ad/sponsor blocks, footer promotional text — data-structures.md §5) removed prior to rendering. | Automated scan of rendered post bodies for known boilerplate signatures (`ygrp-`, `groups.yahoo.com/group/Traveller_TNE` footer boilerplate text) returns zero matches, checked across both digest-sourced and non-digest-sourced posts. |
| FR-4 | Must | No page, dataset file, or metadata output by the system shall contain any email address, in any form. | Automated build-time scan of every generated output file (HTML, JSON, sitemap, search index) with an email-address pattern finds zero matches; build fails if any are found. |
| FR-5 | Must | Each post page shall display attribution to the post's author by display name. | For the FR-2 sample, each page's byline matches the canonical dataset's author display-name field exactly. |

### 3.2 Threading

| ID | Pri. | Requirement | Acceptance Criteria |
|---|---|---|---|
| FR-6 | Must | The system shall group posts into threads using, in priority order: (a) `In-Reply-To`/`References` header relationships where present; (b) normalized-subject matching (stripped `Re:`/list-tag prefixes, case-folded) within a reasonable time window, as fallback. | Against a hand-verified test set of posts with known reply relationships (checked directly in the source mbox), computed thread assignment matches expected grouping for 100% of header-based cases and for a defined, hand-reviewed sample of subject-fallback cases. |
| FR-7 | Must | Each post page shall show its thread context: a link to its parent post (if any) and links to its direct replies (if any). | For a sample of posts with known parent and/or replies, the rendered page contains a working link to each; posts with no parent/no replies render no broken or empty link element. |
| FR-8 | Must | Each thread shall be viewable as a single ordered view of the full conversation, not solely reconstructable by clicking through individual post pages. | For ≥5 threads of size 3+, navigating to the thread's page renders all member posts in one ordered view reachable via a single URL. |

### 3.3 Search

| ID | Pri. | Requirement | Acceptance Criteria |
|---|---|---|---|
| FR-9 | Must | The system shall provide full-text search across all post subjects and bodies, running entirely client-side. | With JS enabled, entering a known unique term returns the expected post(s); browser network inspection shows no server round-trip after the initial static asset/index load. |
| FR-10 | Must | Search matching shall apply stemming. | A documented test case: querying a root word (e.g. "orbit") returns a post containing only an inflected form ("orbiting") that does not contain the literal query string. |
| FR-11 | Must | The search index shall be generated at build time and shipped as a static asset; the client shall not construct the index at page-load time. | The index file exists as a build output artifact prior to any page load; a page-load performance trace shows only index fetch/parse, no index-construction pass, on the client. |
| FR-12 | Must | Each search result shall link directly to the matching post's permalink page. | For ≥5 sample searches, every result link navigates to the post's permalink URL matching the FR-1 path pattern. |
| FR-13 | Must | Search results shall display a matched-content snippet with query terms highlighted, and rank subject matches above body-only matches. | Results render an excerpt with the query term wrapped in a highlight element; for a query matching both a subject and a body-only post, the subject match is ordered first. |

### 3.4 Browse & navigation

| ID | Pri. | Requirement | Acceptance Criteria |
|---|---|---|---|
| FR-14 | Must | The system shall provide a chronological browse view, navigable by year and month. | A browse page lists every year present in the dataset; each links to a month/post listing whose counts match the canonical dataset's per-year post counts exactly. |
| FR-15 | Must | The system shall provide an author index listing all participants, each linking to a page listing that author's posts. | The author index lists every unique author display name in the dataset exactly once; each author page's post count matches the dataset. |
| FR-16 | Must | Global navigation, including a link to the Help/About page (FR-18), shall be present and consistent across every page template. | Automated check confirms identical navigation markup, including the Help/About link, on one sample page per template type. |
| FR-17 | Must | The system shall provide a subject/topic index independent of thread structure. | A topic index page exists grouping posts by normalized subject and is reachable/browsable without going through search. |

### 3.5 Help & documentation

| ID | Pri. | Requirement | Acceptance Criteria |
|---|---|---|---|
| FR-18 | Must | The system shall provide a single Help/About page, reachable from global navigation on every page, documenting what the archive is, its source/date range, its unofficial-fan-archive status, and how to use search/threading/browse features. | Manual review confirms all four content elements are present on the page, and FR-16 confirms it's linked from every template. |

### 3.6 Presentation extras

| ID | Pri. | Requirement | Acceptance Criteria |
|---|---|---|---|
| FR-19 | Must | The system shall support a dark/light visual theme, honoring `prefers-color-scheme`. | With OS/browser color scheme set to dark (resp. light), the site renders in the matching theme without requiring a manual toggle. |
| FR-20 | Must | The system shall emit a sitemap and per-page metadata (canonical URL, Open Graph/Twitter card tags). | `sitemap.xml` exists at site root listing all generated page URLs; a sample of pages each have a `<link rel="canonical">` and OG title/description tags in `<head>`. |
| FR-21 | Could | The system may provide a discovery feature (e.g. "on this day" or random-thread) on the home page. | The home page element links to a valid, existing post/thread on ≥3 manual reloads. |
| FR-22 | Could | The system may provide a statistics page (posts per year, most active authors, thread-size distribution). | Stats page totals match the canonical dataset's computed aggregates. |

### 3.6a Attachment handling

Context (data-structures.md §5): only 2 attachments are embedded in the mbox itself, but an unknown further number of posts *reference* files/photos that lived only in Yahoo Groups' separate Files/Photos section — never part of this mbox export, and possibly recoverable later from a private copy (evidence: Dec 2019 "grab your files NOW before Yahoo deletes them" thread, where one member claims to have saved everything and offered to send it to the archive owner). "Attachment referenced by a post" and "attachment file present in this repo" are therefore two independent facts, and the design must not conflate them.

Design note: the user's original framing suggested a runtime 404 triggering the fallback UI. This SRS instead specifies **build-time file-presence detection** (FR-27) as the mechanism — it produces the identical user-visible behavior (working link when available, explanatory modal when not, automatic switch-over the moment a file is added and the site is rebuilt) without requiring client-side network requests to check file existence, which is simpler, more reliable, and better for NFR-2 (keyboard/AT operability) and NFR-6 (no unnecessary blocking/async JS) on a static site. Revisit only if a concrete case emerges where build-time detection can't work.

| ID | Pri. | Requirement | Acceptance Criteria |
|---|---|---|---|
| FR-23 | Must | For a post referencing an attachment, when the corresponding file is present in the site's attachment source folder at build time, the system shall render a working download link to that file on the post's page. | For each of the archive's known attachment-bearing posts with a file present in the attachment source folder at build time, the generated page contains a link resolving (200 response, correct content) to the copied file in the deployed site. |
| FR-26 | Must | For a post referencing an attachment whose file is *not* present in the attachment source folder at build time, the system shall instead render an affordance that opens an accessible modal dialog stating the attachment is not currently available in this archive. | For each attachment-referencing post currently lacking a file, the page shows the fallback affordance; activating it via mouse or keyboard opens a modal with the stated message; the modal is dismissible and fully keyboard-operable (NFR-2). |
| FR-27 | Must | Attachment availability shall be determined solely by file presence in a dedicated attachment source folder at build time — never a hardcoded per-post flag — so that adding a previously-missing file to that folder and rebuilding is sufficient, on its own, to switch that post's page from the FR-26 modal to the FR-23 download link. | Starting from a post currently showing the FR-26 modal, adding a correctly-named file to the attachment source folder and rebuilding results in that post's page rendering the FR-23 link, with no other code or per-post metadata change. |

### 3.7 Legal & policy display

| ID | Pri. | Requirement | Acceptance Criteria |
|---|---|---|---|
| FR-24 | Must | Every page footer shall carry a link to the Help/About page's Notice-and-Takedown policy section (FR-25). The copyright statement (site claims no ownership of archived content; original authors retain copyright) and the Mongoose Publishing trademark disclaimer (concept.md §12) are full-text content on the Help/About page only, not repeated in the footer — kept minimal by design (revised from an earlier draft that put the full disclaimer text in the footer itself; a link is enough to preserve the "reachable from every page" property the original legal advice called for, without the visual weight of a full paragraph on every page). | Automated check confirms a working link to `/help/#takedown` (or equivalent anchor) is present in the footer on one sample page per template type; the copyright/trademark text itself is verified only on the Help page under FR-25/FR-18. |
| FR-25 | Must | The Help/About page shall publish the full Notice-and-Takedown policy, inviting any original author to request removal or anonymization of their posts, listing both contact channels: `codemonki@outlook.com` and a link to open a GitHub Issue on the `yahoo-groups-tne-archive` repository. | Manual review confirms the policy text, the email address, and a working GitHub Issues link are all present on the Help/About page. |

### 3.8 Explicitly out of scope

Per concept.md §4/§6: no user accounts, comments, or write path of any kind; no tagging/categorization beyond what's derivable from subjects/threads; no support for archives other than Traveller_TNE; no live/incremental ingestion.

## 4. Data Requirements

| ID | Pri. | Requirement | Acceptance Criteria |
|---|---|---|---|
| DR-1 | Must | The ETL pipeline shall produce a single canonical JSON dataset from the source mbox, expanding each digest record (data-structures.md §2.1) into its constituent individual posts. | Total extracted post count equals the sum of posts found across all 514 digest records plus the ~210 non-digest records; digest expansion count spot-checked by hand against ≥10 sampled digests. |
| DR-2 | Must | The ETL pipeline shall eliminate duplicate post *records* (the same post appearing via more than one source path, e.g. individually *and* inside a digest) using the Yahoo message permalink ID (`/message/<id>`) as the dedup key. Quoted content *within* a post's own body is not deduplication's concern and is left untouched. | Automated uniqueness check on the permalink-ID key across the full canonical dataset finds zero duplicates; a known post containing quoted reply text retains that text in its body field unchanged. |
| DR-3 | Must | The ETL pipeline shall normalize every post's date/time to UTC in ISO 8601 format, best-effort, retaining the original source-formatted date/time string alongside the normalized value. | 100% of post records have a valid, parseable ISO 8601 UTC normalized-date field, and a non-empty original-date-string field. |
| DR-4 | Must | The canonical dataset shall not contain any email-address field or value anywhere in its schema. | Automated regex scan of the canonical JSON file(s) finds zero email-address-shaped substrings. |
| DR-5 | Should | The digest-HTML parser shall be validated by sampling across the full 2005–2019 date range, branching parser logic only where an actual template variance is found. | A documented sample (≥1 digest per calendar year present in the archive) has been manually diffed against its parsed output with no unexplained extraction errors. |
| DR-6 | Must | The site generator, search-index builder, and any other downstream tooling shall read only from the canonical dataset — never from the raw mbox or `.msf` file directly. | Static analysis (source grep) of the site generator and search-index builder finds no reference to the raw `YahooArchive` or `YahooArchive.msf` file paths. |
| DR-7 | Should | The Mork (`.msf`) thread/singleton counts (data-structures.md §4.2) shall be used as a sanity cross-check against the pipeline's own computed thread count during development. | A documented comparison shows the pipeline's computed thread/singleton counts within a reasonable tolerance of the Mork-derived 472-thread/580-singleton figures, with any material deviation explained in dev notes. |
| DR-8 | Must | The build process shall source attachment files from a dedicated directory in the repository (distinct from `mail_archives/`), matched to posts by a stable key (e.g. Yahoo permalink ID + original filename), and copy any present, matched file into the site's build output as part of every build. This is the mechanism FR-23/FR-26/FR-27 depend on. | A file placed in the designated attachment source directory under the expected naming convention appears, byte-identical, in the site's build output at the expected path after running the build; its absence produces no build error (per FR-26, absence is an expected, handled state, not a failure). |

## 5. Non-Functional Requirements

### 5.1 Accessibility

| ID | Pri. | Requirement | Acceptance Criteria |
|---|---|---|---|
| NFR-1 | Must | All page templates shall conform to WCAG 2.2 Level AA. | Automated axe-core scan of every unique page template reports zero critical/serious violations. |
| NFR-2 | Must | All interactive functionality shall be fully operable via keyboard alone, with visible focus indication at all times. | Manual keyboard-only walkthrough (no mouse) reaches and operates every interactive element on each template, with a visible focus indicator at each stop. |
| NFR-3 | Must | All pages shall use semantic HTML landmarks and a logical, non-skipping heading structure; all non-text content shall have text alternatives. | Automated crawl confirms exactly one `<h1>` per page, no skipped heading levels, and no `<img>` missing an `alt` attribute, site-wide. |
| NFR-4 | Must | Color contrast shall meet or exceed WCAG 2.2 AA thresholds, in both light and dark themes if FR-19 is implemented. | Automated contrast checker reports zero failures against WCAG 2.2 AA thresholds, sampled across all templates in both themes. |

### 5.2 Performance & quality

| ID | Pri. | Requirement | Acceptance Criteria |
|---|---|---|---|
| NFR-5 | Must | Every page template shall score 90 or above in Lighthouse Performance, Accessibility, Best Practices, and SEO, on mobile and desktop presets. | Lighthouse CI run against each unique page template records ≥90 in all four categories, both presets. |
| NFR-6 | Must | The search index asset and any JS required for core interactions shall not block first render of page content. | Network/performance trace shows the search index and core-interaction JS loaded async/deferred, with no measurable delay to First Contentful Paint attributable to them. |

### 5.3 Usability

| ID | Pri. | Requirement | Acceptance Criteria |
|---|---|---|---|
| NFR-7 | Must | The design shall be reviewed against all ten of Nielsen's usability heuristics prior to release. | A documented heuristic-review artifact covers all 10 heuristics against the final design, each finding marked addressed or accepted-with-rationale, completed before launch. |

### 5.4 Hosting & deployment

| ID | Pri. | Requirement | Acceptance Criteria |
|---|---|---|---|
| NFR-8 | Must | The site shall build to fully static output with no server-side runtime dependency, deployable as-is to GitHub Pages. | Build output consists solely of static files (HTML/CSS/JS/JSON/images); no server-side process or database is present in or required by the deployed artifact. |
| NFR-9 | Must | The site shall deploy from the `yahoo-groups-tne-archive` GitHub repository via a GitHub Actions workflow, requiring no manual deployment step. | A GitHub Actions workflow in that repo builds and publishes to GitHub Pages on push to the default branch (or manual dispatch), verified by a successful automated deployment run. |

### 5.5 Legal & licensing

| ID | Pri. | Requirement | Acceptance Criteria |
|---|---|---|---|
| NFR-10 | Must | Site source code (ETL pipeline, generator, templates, tooling) shall be published under the Apache License 2.0. | A `LICENSE` file containing the full Apache License 2.0 text exists at the repo root. |
| NFR-11 | Must | A content-rights statement — no license granted over archived content, authors retain copyright, republished under a non-commercial preservation rationale (concept.md §12) — shall be published site-wide before launch. | The exact content-rights statement text appears (verbatim, or with only placeholder substitution) on the Help/About page and/or global footer of the deployed site. |

## 6. External Interface Requirements

| ID | Requirement | Acceptance Criteria |
|---|---|---|
| IR-1 | Build/deploy toolchain interfaces with GitHub Actions (CI) and GitHub Pages (hosting) only — no other external service dependency. | Dependency audit of the build pipeline and a full crawl of the deployed site show no calls to any third-party service (no external API keys/endpoints, no third-party network requests) beyond GitHub Actions/Pages themselves. |
| IR-2 | The only human interface is the website itself, via a standard web browser; no CLI, API, or app interface is in scope for end users. | Full walkthrough of every Must-have FR is completable in a standard browser alone, with no companion app, CLI, or API required. (The Makefile — concept.md §10 — is a developer/build-time interface, out of scope here.) |

## 7. Priority Summary

| Priority | Count |
|---|---|
| Must | FR-1–FR-20, FR-23–FR-27; DR-1–DR-4, DR-6, DR-8; NFR-1–NFR-11 |
| Should | DR-5, DR-7 |
| Could | FR-21, FR-22 |

## 8. Open items carried forward

- **Legal/licensing** (code license, content license, trademark disclaimer wording, takedown contact channel): resolved, reflected in FR-24, FR-25, NFR-10, NFR-11.
- ~~**Attachment source folder — naming/matching convention**~~ (DR-8): resolved in dd.md §1/§2 — `attachments/<id>/<original-filename>`, keyed by the same `id` as the owning post (ADR-0006).
- **Recovered Yahoo Groups Files/Photos content — provenance unknown.** data-structures.md §5 documents that at least one group member claimed to have saved the group's Files/Photos section before Yahoo deleted it in Dec 2019, and offered to send it to the archive owner — but whether that transfer happened, and whether any such files are actually in hand for this project, is unconfirmed. Doesn't block FR-23/26/27 (which are designed to work correctly whether zero or many files are ever supplied), but worth the archive owner following up on that 2019 offer if the fuller archive is desired.
