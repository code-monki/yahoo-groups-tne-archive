# Defect log

Running record of defects found during implementation, classified by [test-plan.md §10](test-plan.md#10-defect-severity--launch-gating)'s severity scale. This log exists to satisfy test-plan.md §13's exit criterion ("all Major-severity findings are logged, even if not yet fixed") and to give a durable, reviewable record beyond the in-code rationale comments left at each fix site.

Entries found and fixed *during* implementation (i.e. before any `docs/test-plan.md` case has actually been run — that's Phase 9) are logged here anyway: they're real defects a future maintainer would want visibility into, even though no formal test run caught them.

| # | Severity | Phase found | Summary | Status |
|---|---|---|---|---|
| 1 | Critical | 4 | Post/thread breadcrumb showed a different post's subject than the page's own content | Fixed |
| 2 | Major | 4 | `<title>`/OG description double-HTML-escaped for posts whose subject contains a quote or ampersand (410/4060 posts, 10%) | Fixed |
| 3 | Critical | 4 | Duplicate posts across threads; dedup kept a synthetic-UUID copy over the real Yahoo-permalink copy | Fixed |
| 4 | Critical | 5 | Build failure (`ENAMETOOLONG`) generating author pages, from a garbled ~300-char "author name" | Fixed |
| 5 | Major | 5 | Topic index/detail pages displayed the normalized grouping key instead of the topic's real subject | Fixed |

---

## 1. Breadcrumb shows wrong post's subject

**Severity:** Critical (violates FR-7/hld.md §6's per-page navigation context on every post and thread page — not an edge case, structurally wrong on arbitrary pages depending on build-time pagination order).

**Found:** Phase 4 checkpoint verification, via Playwright screenshot of `/posts/6312/` — breadcrumb read "Some thoughts on the kinetic energy of projectiles…." while the page's own `<h1>` correctly read "Possibly useful colony info".

**Root cause:** `post.njk`/`thread.njk` defined `eleventyComputed.breadcrumb` as a Nunjucks template string nested inside a YAML array in front matter. Front matter is parsed once into a single JS object tree; Eleventy's per-pagination-item computed-data resolution shared/mutated that same array/object across all 4060 (resp. 726) generated pages instead of producing an independent value per page, so a page's breadcrumb could end up reflecting whichever other pagination item's data last wrote to the shared object.

**Fix:** Moved `breadcrumb` computation into a JS function in a `.11tydata.js` companion file (`site/post.11tydata.js`, `site/thread.11tydata.js`), which returns a fresh array per invocation — sidesteps the shared-object issue entirely rather than working around it.

**Verified:** Programmatic check comparing `<title>` against the breadcrumb's `aria-current` text across all 4060 built post pages — 0 mismatches (previously would have been widespread had the bug not also depended on pagination/build timing).

## 2. Double-escaped title/description for subjects with quotes or ampersands

**Severity:** Major (visibly wrong `<title>`/meta text for a real 10% slice of posts; doesn't break navigation or data integrity, so short of Critical).

**Found:** Same Phase 4 verification pass, while root-causing #1 — spot-checking `<title>` against breadcrumb text surfaced a case (`&amp;quot;` instead of `&quot;`) that wasn't the breadcrumb bug itself.

**Root cause:** Same front-matter-template-string mechanism as #1: `title`/`description` were also Nunjucks template strings in front matter, so Eleventy rendered them once to resolve the computed value, then the layout's `{{ title }}` rendered (and HTML-escaped) that already-escaped string a second time.

**Fix:** Same as #1 — moved into the `.11tydata.js` JS functions, rendered exactly once by the layout.

**Verified:** 410/4060 posts (subjects containing `"`, `&`, `'`, `<`, or `>`) spot-checked post-fix; confirmed single-escaped output.

## 3. Duplicate posts / wrong copy kept in cross-path dedup

**Severity:** Critical (DR-2 violation — duplicate post records reaching the canonical dataset — and directly user-visible as a duplicated post inside a thread view).

**Found:** Phase 4 Playwright thread-page screenshot review, cross-referenced against `data/posts.json`.

**Root cause:** `pipeline/dedupe.py`'s fuzzy cross-path merge (same post extracted twice — once as an individually-relayed email, once inside a digest — yielding two different `id` values, a real Yahoo permalink for one copy and a synthetic UUID for the other) tie-broke purely on body length. For the two confirmed real-archive cases, the synthetic-UUID copy's body was accidentally ~2% longer than the real-permalink copy's, so the merge discarded the real permalink.

**Fix:** `_merge_group()`'s sort key now prefers a real Yahoo-permalink id unless the competing candidate's body is substantially more complete (<80% of the max body length among the group) — a real completeness gap still wins, extraction-path noise no longer does.

**Verified:** Re-ran full ETL; confirmed both known cases (post ids 6312, 6373) now keep the permalink copy; dataset-wide duplicate-id count is 0.

## 4. Build failure from a misparsed digest post

**Severity:** Critical (build-breaking — `make build` cannot complete at all until fixed).

**Found:** Rebuilding the site after adding `author.njk` in Phase 5 — Eleventy's `mkdir` failed with `ENAMETOOLONG` on an author slug ~300 characters long.

**Root cause:** A 2010 digest reply (mbox digest record index 259) quoted an entire earlier post verbatim in its own body — including that post's real permalink anchor and literal "Posted by:" line. `pipeline/digest_parser.py`'s pattern-based post-boundary detection (permalink anchor + nearby "Posted by:" text, by design not strictly DOM-scoped — see that module's docstring) matched this quoted content as a second, phantom top-level post, extracting the quoted block's surrounding text as a ~300-character "author name". Because this phantom entry's `id` collided with the real post's `id` (both correctly resolved to permalink `6835`) and its body was *longer* than the legitimate copy's (having absorbed the replying author's own preceding text too), `dedupe.py`'s length-based tie-break (already loosened by fix #3, but not blind to length entirely) kept the phantom over the legitimate copy.

**Fix:** Added `_URL_LIKE_SUBJECT_RE` to `digest_parser.py` — a real digest subject is never a literal hyperlink, so a candidate whose extracted "subject" text is itself a bare URL is rejected before it's treated as a post start. Also added a defensive slug-length cap (80 characters, mirrored in both `pipeline/ids.py` and `site/_data/posts.js`) so any future extraction anomaly of this general shape degrades to a truncated slug rather than a build failure.

**Verified:** Re-ran full ETL; post 6835 now resolves to the legitimate `daryl` / "Hexographer" entry; full rebuild succeeds with 0 errors; longest author display name in the dataset dropped from ~300 to 38 characters.

## 5. Topic pages show the normalized grouping key, not the real subject

**Severity:** Major (wrong but non-crashing display text on every topic page — 730 pages affected).

**Found:** Phase 5 Playwright verification of `/topics/` — first entry read "question for the group" (lowercase, no "Re:") instead of a real captured subject.

**Root cause:** `site/_data/posts.js` grouped posts by `subject_normalized` (deliberately lowercased and "Re:"/list-prefix-stripped, so that "Question for the group" and "Re: Question for the group" group together) but then used that same normalized string as the topic's *display* subject, rather than a real post's actual subject field.

**Fix:** Topic's display `subject` is now `posts[0].subject` — the real subject of the chronologically earliest post in the group (the array is already ascending by `date_utc`, mirroring `data/posts.json`'s own sort order).

**Verified:** Rebuilt; spot-checked several topics for correct casing/prefix; confirmed `posts[0]` really is the earliest post via the existing chronological-ordering guarantee documented in `site/_data/posts.js`.
