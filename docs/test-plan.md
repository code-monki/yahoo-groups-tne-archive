# Test Plan: Traveller_TNE Archive Site

**Status:** Draft
**Traces:** [rtm.md](rtm.md) (requirement → design → verification method) → this document (verification method → concrete, numbered test case) → future CI runs (test case → pass/fail record).

This is the last planned document before implementation. It doesn't introduce new decisions — every test case here executes a Verification Method the RTM already assigned, against an Acceptance Criterion the SRS already defined. Where this document does add something new, it's the missing middle layer: concrete test-case IDs, a representative-sample definition, and entry/exit gating — the things that turn "this will be checked with axe-core" into an actual, repeatable, pass/fail procedure.

## 1. Scope

Covers verification of every **Must** requirement before public launch. **Should**/**Could** requirements (FR-13 already promoted to Must in an earlier revision; remaining Coulds are FR-21/FR-22, Shoulds are DR-5/DR-7) are tested but do not gate launch — see §5.

Out of scope: load/stress testing (a static site on GitHub Pages' CDN has no meaningful capacity concern at this archive's size — ~900 pages is not a scale question), penetration testing (no attack surface beyond static file serving — no forms that write anywhere, no auth, no server), and localization testing (concept.md §2.3: English-only, no i18n requirement).

## 2. Representative page sample

Per dd.md §11's reasoning (all posts share one template, so template-level coverage is what's meaningful, not per-post coverage), automated per-page checks (axe-core, Lighthouse) run against one instance of each of the 11 real page templates (dd.md §7.2), not all ~900+ generated pages:

`home` · `post` · `thread` · `author` · `authors-index` · `topic` · `topics-index` · `browse-year` · `browse-month` · `search` · `help`

Fixture selection for templates with variable content (post, thread, author, topic, browse-year, browse-month) should include at least one instance with: a long body, a short/singleton post, and — once real data exists — the actual longest thread and largest browse-year in the archive, not just an arbitrary example. `sitemap.xml` is excluded from UI-focused checks (it's not HTML) but included in the build-output existence check (TC-DATA-08).

## 3. Entry criteria

- `make build` completes with exit code 0 (implies `make data` succeeded and produced a non-empty `data/posts.json`).
- `make index` completes with exit code 0.
- No entry criterion requires a specific post/thread count — the pipeline's actual output, whatever it is, is what gets tested, per ADR-0001's one-shot-ETL model (there's no "expected count" to match ahead of running it for real, only the internal-consistency checks in §4's data test cases).

## 4. Test cases — Data integrity

Run against `data/posts.json` directly, before or independent of the site build. These gate `make build` in CI (a data-integrity failure should stop the pipeline before it wastes time building a site on bad data).

| Case ID | Traces to | Procedure | Pass criterion |
|---|---|---|---|
| TC-DATA-01 | DR-1 | Count posts extracted from digest records vs. non-digest records; hand-diff ≥10 sampled digests against their source HTML. | Extracted count matches manual sample counts; no unexplained extraction errors in the sample. |
| TC-DATA-02 | DR-2, FR-4 (dedup half) | Scan all `id` values for duplicates. | Zero duplicate `id`s. |
| TC-DATA-02b | DR-2 (quoted-content half) | Pick a known post containing a quoted reply; diff its `body_html` before/after the dedup pass. | Quoted text present and unchanged. |
| TC-DATA-03 | DR-3 | Parse every record's `date_utc` as ISO 8601 UTC; check `date_original` non-empty. | 100% valid `date_utc`; 100% non-empty `date_original`. |
| TC-DATA-04 | DR-4, FR-4 | Regex-scan the full canonical JSON for email-address-shaped substrings. | Zero matches. |
| TC-DATA-05 | DR-5 | Hand-diff ≥1 digest per calendar year that has digests (empirically 2008–2018, not the full 2005–2019 archive range — no digests exist outside that window) against its parsed output. | No unexplained extraction errors in any sampled year. |
| TC-DATA-06 | DR-6 | `grep`/static-analysis the site generator and search-index builder source for references to `YahooArchive` or `YahooArchive.msf` paths. | Zero references outside the ETL module itself. |
| TC-DATA-07 | DR-7 | Compare pipeline's computed thread/singleton counts against the Mork-derived 472-thread/580-singleton reference (data-structures.md §4.2). | Within a reasonable tolerance, or deviation is explained in dev notes — not a hard numeric gate (data-structures.md never claimed the Mork figures were exactly reproducible, only a sanity signal). |
| TC-DATA-08 | DR-8, FR-20 | Place a test file in `attachments/<id>/`, run `make build`, confirm it's byte-identical in build output at the expected path; confirm `_site/sitemap.xml` exists and is non-empty. | File copied correctly; build produces no error when a referenced attachment is absent (that's the expected, handled state per FR-26). |

## 5. Test cases — Functional (site behavior)

Executed against the built site (`_site/`) via Playwright, or by manual procedure where noted. Each case's ID groups by SRS section for easy RTM cross-reference.

| Case ID | Traces to | Procedure | Pass criterion |
|---|---|---|---|
| TC-FUNC-01 | FR-1 | Count post records in canonical dataset; count `_site/posts/*/index.html` files. | Counts match exactly; each returns 200 with no query-string dependency. |
| TC-FUNC-02 | FR-2, FR-5 | For ≥10 sampled post pages (years/authors varied), diff rendered author/date/subject/body against the dataset record. | Exact match, all four fields present. |
| TC-FUNC-03 | FR-3 | Scan rendered post bodies for `ygrp-`/Yahoo footer boilerplate signatures, across digest- and non-digest-sourced posts. | Zero matches. |
| TC-FUNC-04 | FR-6 | Run the hand-verified reply-relationship test set (built during DR-5/TC-DATA-05 sampling) against computed `thread_id`/`parent_id`. | 100% match for header-based cases; hand-reviewed subject-fallback sample matches expected grouping. |
| TC-FUNC-05 | FR-7 | For posts with known parent/replies, check rendered links resolve; for posts with neither, check no broken/empty link markup renders. | All links resolve; no dead markup for the no-parent/no-reply case. |
| TC-FUNC-06 | FR-8 | For ≥5 threads of size 3+, load the thread page and confirm all member posts render in one ordered view. | All members present, single URL, no click-through required. |
| TC-FUNC-07 | FR-9, FR-11, NFR-6 | Load `/search/` with JS enabled and network inspection open; confirm index fetch/parse only, no server round-trip on query. | No non-static network calls after initial load; matches FR-9/FR-11's client-only requirement. |
| TC-FUNC-08 | FR-10 | Query a root word (e.g. "orbit"); confirm a result containing only an inflected form ("orbiting") is returned. | Stemmed match returned even without literal query string present. |
| TC-FUNC-09 | FR-12, FR-13 | Run ≥5 sample searches; verify each result links to its permalink, subject matches rank above body-only matches, snippets show `<mark>`-highlighted terms. | All three hold for every sampled query. |
| TC-FUNC-10 | FR-14, FR-15, FR-17 | Compare Browse/Authors/Topics index counts against dataset aggregates. | Exact match. |
| TC-FUNC-11 | FR-16 | Diff nav markup (including Help link) across one sample page per template. | Identical markup, all 11 templates. |
| TC-FUNC-12 | FR-18, FR-25 | Manual checklist against the Help page: origin/date-range stated, unofficial-status disclaimer present, how-to-use content present, full takedown policy + both contact channels present. | All items present. |
| TC-FUNC-13 | FR-19 | Set OS/browser `prefers-color-scheme` to dark, load a fresh page with no prior toggle interaction; repeat for light. | Site matches OS preference without requiring the manual toggle. |
| TC-FUNC-14 | FR-23, FR-26, FR-27 | (a) For a post with a present attachment file, confirm working download link. (b) For one without, confirm the FR-26 modal renders and is keyboard-operable. (c) Add a file for a case-(b) post, rebuild, re-check it now matches case (a) with no other change. | All three behaviors confirmed; (c) specifically proves FR-27's "just add the file" property. |
| TC-FUNC-15 | FR-24 | Check footer on one sample page per template for a working link to `/help/#takedown`. | Present and functional on all 11 templates. |

## 6. Test cases — Accessibility

| Case ID | Traces to | Procedure | Pass criterion |
|---|---|---|---|
| TC-A11Y-01 | NFR-1 | `@axe-core/playwright` scan against all 11 representative templates (§2), both themes. | Zero critical/serious violations, all 22 (template × theme) runs. |
| TC-A11Y-02 | NFR-2 | Manual keyboard-only walkthrough (no mouse) of every interactive element per template: nav, search, theme toggle, the FR-26 modal, breadcrumbs. | Every element reachable and operable; visible focus indicator at every stop. |
| TC-A11Y-03 | NFR-3 | Automated crawl: exactly one `<h1>` per page, no skipped heading levels, no `<img>` missing `alt`. | Holds site-wide, not just the sample. |
| TC-A11Y-04 | NFR-4 | Automated contrast check across all 11 templates, both themes. | Zero failures against WCAG 2.2 AA — this is a confirmation of ui-design.md §2's already-computed ratios against the real rendered output, not a first-time check. |

## 7. Test cases — Performance & SEO

| Case ID | Traces to | Procedure | Pass criterion |
|---|---|---|---|
| TC-PERF-01 | NFR-5 | Lighthouse CI against all 11 templates, mobile + desktop presets. | ≥90 in Performance, Accessibility, Best Practices, and SEO — all templates, both presets. |
| TC-PERF-02 | NFR-6, ADR-0015 | Network trace on a non-search page: confirm no Pagefind/`search.js` request occurs. Network trace on `/search/`: confirm it loads `defer`red and doesn't block FCP. | Zero search-related requests off `/search/`; no measurable FCP delay attributable to search assets on `/search/` itself. |
| TC-PERF-03 | FR-20, ADR-0016 | Confirm `sitemap.xml` is well-formed XML listing every built page; spot-check 3 pages' `<head>` for canonical URL + OG/Twitter tags. | Sitemap valid and complete; metadata present on sampled pages. |

## 8. Test cases — Usability

| Case ID | Traces to | Procedure | Pass criterion |
|---|---|---|---|
| TC-USE-01 | NFR-7 | Structured review of the finished implementation against all 10 Nielsen heuristics, using hld.md §7's heuristic→element mapping as the starting checklist (not the final word — re-verify each against the actual build, not just the design intent). | Every heuristic addressed or explicitly accepted with documented rationale. |

## 9. Test cases — Hosting, deployment & legal

| Case ID | Traces to | Procedure | Pass criterion |
|---|---|---|---|
| TC-DEPLOY-01 | NFR-8, IR-1 | Inspect build output for any server-side process/database dependency; audit build pipeline + full site crawl for third-party service calls. | Fully static output; no calls beyond GitHub Actions/Pages themselves. |
| TC-DEPLOY-02 | NFR-9 | Push to the default branch of `yahoo-groups-tne-archive`; confirm the Actions workflow builds and deploys with zero manual steps. | Successful automated deployment, no manual intervention. |
| TC-DEPLOY-03 | IR-2 | Full walkthrough of every Must-have FR using only a standard browser (no CLI/API/companion app). | Completable end-to-end. |
| TC-LEGAL-01 | NFR-10 | Confirm `LICENSE` at repo root contains the full Apache License 2.0 text. | Present, complete. |
| TC-LEGAL-02 | NFR-11, FR-25 | Confirm the content-rights statement (no license granted over archived content, authors retain copyright, non-commercial preservation rationale) appears on the Help page. | Present, matches concept.md §12's agreed text. |
| TC-LINK-01 | (cross-cutting) | `linkinator` crawl of the full built `_site/` output. | Zero broken internal links, including thread/author/topic cross-links and attachment links. |

## 10. Defect severity & launch gating

| Severity | Definition | Gates launch? |
|---|---|---|
| **Critical** | Any Must-requirement test case fails; any critical/serious axe-core violation; any Lighthouse category <90 on any template; any email address found in output (FR-4/DR-4); any broken permalink. | Yes — blocks launch until fixed and re-tested. |
| **Major** | A Should-requirement (DR-5, DR-7) fails, or a Must-requirement passes its stated Acceptance Criterion but with an edge case that clearly violates its intent. | No, but must be logged and scheduled before the next content/data change. |
| **Minor** | A Could-requirement (FR-21, FR-22) fails or is incomplete. | No. |

## 11. Regression strategy

The source archive is frozen (ADR-0001) — there is no scheduled regression cadence tied to new content, because there is no new content. Re-run the full suite (§4–§9) whenever: the ETL pipeline changes (bug fix, schema change), a template or CSS token changes, a new attachment file is added to `attachments/` (re-run at minimum TC-DATA-08, TC-FUNC-14, TC-LINK-01), or dependencies are upgraded (Eleventy, Pagefind, Playwright/axe-core/Lighthouse CI themselves). Not on a calendar schedule.

## 12. CI integration

All automated cases (`TC-DATA-*`, most `TC-FUNC-*`, `TC-A11Y-*`, `TC-PERF-*`, `TC-DEPLOY-01`, `TC-LEGAL-*`, `TC-LINK-01`) run under `make test` (dd.md §10) using the tooling dd.md §11 already named (`@axe-core/playwright`, `@lhci/cli`, `linkinator`), invoked by the GitHub Actions workflow after `make build` and before `actions/deploy-pages` — a Critical-severity failure fails the workflow and blocks deployment automatically, rather than relying on someone remembering to check. Manual-procedure cases (`TC-A11Y-02`, `TC-USE-01`, portions of `TC-FUNC-12`) are a pre-launch checklist, not a CI gate — they need a human, but are still required before the "exit criteria" in §13 are considered met.

## 13. Exit criteria

Ready to launch when: every Critical-severity case in §10 passes, all Major-severity findings are logged (even if not yet fixed), and TC-USE-01's heuristic review is complete with every finding addressed or explicitly accepted. Minor findings (Could-have gaps) do not block.

## 14. Traceability completion

This document assigns a concrete case ID to every Verification Method rtm.md named, closing the loop rtm.md §"How to read this" explicitly left open ("the actual test cases... are the Test Plan's job"). No SRS requirement lacks a corresponding test case; no test case here lacks a traced-to requirement.
