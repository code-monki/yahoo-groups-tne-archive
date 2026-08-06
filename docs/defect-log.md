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
| 6 | Major | 6 | Search's "Load more results" button stayed visible after all results were shown | Fixed |
| 7 | Major | 7 | Direct (non-digest) emails' Yahoo footer boilerplate ("Yahoo! Groups Links" etc.) leaked into 91/4060 post bodies | Fixed |
| 8 | Critical | 7 | Fixing #7 caused 5 posts' real content to be deleted entirely (empty body) | Fixed |
| 9 | Critical | 8 | `sitemap.xml` listed only 12 URLs instead of 5829 (one per paginated template, not all pages) | Fixed |
| 10 | Major | 8 | `og:description` contained a literal newline, producing malformed HTML on posts with a matching body | Fixed |
| 11 | Major | 8 | 7 digest posts had an empty author name, silently fragmenting one prolific poster's history into a spurious "unknown" author | Fixed |
| 12 | Major | 8 | Skip link scrolled to `<main>` but never moved actual keyboard focus there (WCAG 2.4.1) | Fixed |
| 13 | Minor | 8 | One archived post's own real `<h3>` subheadings skipped a level under the page's `<h1>` (no `<h2>`) | Fixed |
| 14 | Major | 9 | No `404.html` existed at all, despite hld.md §7 explicitly committing to one for the "help recognize/recover from errors" Nielsen heuristic | Fixed |
| 15 | Critical | 9 (post-launch) | Email-scrubbing regex only tolerated whitespace next to punctuation, missing addresses hard-wrapped mid-word by quoted plain-text mail — 224 real, live email addresses (personal and list addresses) were unscrubbed and publicly deployed | Fixed |
| 16 | Major | 9 (post-launch) | A third Yahoo footer variant ("Links:" plain-text reference list, dead tracking URLs) leaked into 128/4060 post bodies | Fixed |
| 17 | Major | 9 (post-launch) | Orphaned literal "mailto:" label text (address already scrubbed, prefix left behind) remained in 341/4060 post bodies | Fixed |
| 18 | Minor | 9 (post-launch) | "-------- Original message --------" quoted-forward headers rendered as garbled, hard-wrapped Subject/From/To/CC text with always-blank To:/CC: shown as noise | Fixed |
| 19 | Major | 9 (post-launch) | Fixing #18 shipped its own bug: the trailing cleanup after "CC:" was unbounded and silently deleted the leading quote marker off genuinely quoted reply text whenever it started with the same characters | Fixed |
| 20 | Major | 9 (post-launch) | Files-section manifest extraction duplicated entries: a reply quoting the upload notification inline matched the same extraction pattern as the real notification | Fixed |
| 21 | Major | 9 (post-launch) | Files-section manifest extraction silently dropped 4 of 10 real entries when the scrubbed-email remnant after "Uploaded by:" wrapped across extra blank lines | Fixed |

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

## 6. "Load more results" button stays visible after all results are shown

**Severity:** Major (wrong, misleading UI state on the one page with unbounded result counts — clicking it a second time is a harmless no-op, not data-lossy, so short of Critical).

**Found:** Phase 6 Playwright screenshot of a 4-result search ("hexographer") — the "Load more results" button rendered below a fully-shown result list with nothing left to load.

**Root cause:** `site/js/search.js` toggles the button via the native `hidden` attribute (`loadMoreBtn.hidden = shownCount >= total`), which is the semantically correct mechanism — but the browser's own `[hidden] { display: none }` rule lives in the lowest-priority user-agent stylesheet, and `site/css/components.css`'s `.btn { display: inline-block }` rule (loaded after `base.css`, equal specificity) wins the cascade by source order alone, silently canceling it. Confirmed via `getComputedStyle`: `display: inline-block` despite `hidden` being correctly set on the element.

**Fix:** Added `[hidden] { display: none !important; }` to `site/css/base.css` — a deliberate, narrow use of `!important`, since `[hidden]` means "must not render" and needs to win regardless of what other component classes coexist on an element.

**Verified:** `getComputedStyle(btn).display` is `none` when hidden; Playwright confirms the button is hidden for a fully-shown result set and visible when more results remain (e.g. "orbit", top 40 of 297 shown).

## 7. Direct emails' Yahoo footer boilerplate not stripped

**Severity:** Major (91/4060 posts carry unsubscribe-link/Terms-of-Service boilerplate as if it were part of the archived message).

**Found:** Phase 7 Playwright screenshot of a real post with an attachment — "Yahoo! Groups Links" / "To visit your group..." / "To unsubscribe..." / "Your use of Yahoo! Groups is subject to..." rendered as ordinary body content beneath the author's actual message.

**Root cause:** `normalize.py`'s `_BOILERPLATE_TEXT_MARKERS` only covered digest-specific footer phrasing (from Phase 2's digest-focused validation pass) — direct (non-digest) emails carry their own, differently-worded Yahoo-appended footer that no marker matched.

**Fix:** Added `"Yahoo! Groups Links"` to `_BOILERPLATE_TEXT_MARKERS`.

**Verified:** Re-ran full ETL; 0/4060 posts contain the marker text afterward (down from 91).

## 8. Fixing #7 deleted 5 posts' real content entirely

**Severity:** Critical (real archived content silently destroyed — worse than the defect the fix was meant to resolve).

**Found:** Immediately after applying #7's fix and re-running the ETL — the standard post-run validation sweep (0-empty-bodies check, run after every ETL change throughout this project) showed 5 empty bodies where there had been 0 before.

**Root cause:** Plain-text-only emails (no HTML MIME part — `_extract_non_digest_post`'s fallback path) had their *entire* raw body, including the Yahoo footer, wrapped in one single flat `<p>` tag with no paragraph structure. `normalize.py`'s marker-based truncation operates at DOM node granularity; with only one node covering the whole message, adding a marker that now matched *within* that single node gave the truncation logic no boundary finer than "the whole node" to cut at, so it removed the entire post body — real message and footer both — for the 5 posts where this fallback path applied and the message was plain-text.

**Fix:** `etl.py`'s new `_plain_text_to_html()` splits a plain-text body into one `<p>` per blank-line-separated paragraph (each individually HTML-escaped, which the old single-`<p>` fallback never did either — a latent, lower-severity gap in its own right, since a literal `<`/`&` in someone's plain-text message could previously have been misread as markup) before handing off to the same sanitize/truncate pipeline every other post goes through. This gives truncation a real paragraph boundary to cut the footer at without touching the paragraphs before it.

**Verified:** Re-ran full ETL; 0 empty bodies, 0 posts with the marker text, and the specific previously-emptied post ("[Traveller_TNE] Low Tech Stuff") confirmed to retain its full multi-paragraph real content with only the footer removed.

## 9. Sitemap only listed 12 URLs instead of 5829

**Severity:** Critical (FR-20's core requirement — "listing every built page" — was violated by two orders of magnitude).

**Found:** Phase 8, immediately after writing `sitemap.njk` and building — `grep -c "<loc>"` returned 12 against an expected 5829+.

**Root cause:** Eleventy's `pagination.addAllPagesToCollections` defaults to `false`. Every one of the 6 paginated templates (post, thread, author, topic, browse-year, browse-month) was generating every real page correctly on disk, but only the *first* generated page of each was ever added to `collections.all` — which `sitemap.njk` iterates. The 12 that did appear were the 6 templates' first pagination item plus the 6 genuinely-static pages (home, authors-index, topics-index, browse-index, help, search).

**Fix:** Added `addAllPagesToCollections: true` to all 6 templates' `pagination:` front matter.

**Verified:** Sitemap URL count (5829) matches the independently-computed total (4060 posts + 725 threads + 183 authors + 730 topics + 16 years + 109 months + 6 static pages); validated as well-formed XML.

## 10. Malformed `og:description` from an unescaped newline

**Severity:** Major (invalid HTML — a `content="..."` attribute value spanning multiple raw lines — on any post whose first ~160 characters of body text cross a paragraph break).

**Found:** Phase 8 TC-PERF-03 spot-check of 3 pages' `<head>` tags — post 6835's `og:description` visibly broke across multiple lines mid-attribute.

**Root cause:** `post.11tydata.js`'s `truncate()` helper (introduced fixing defect #1/#2) cut `body_text` at a character offset without first collapsing whitespace, so a raw `\n` inside the truncated text landed directly inside the HTML attribute.

**Fix:** `truncate()` now collapses all whitespace (including newlines) to single spaces before cutting.

**Verified:** Rebuilt; scanned every post page's `content="..."` attributes for embedded newlines — 0 found (previously present on posts whose first paragraph was short).

## 11. Empty author name fragmented one poster's history

**Severity:** Major (FR-15's author index correctness — one real person's ~470 posts split across two apparent "authors," one of them an uninformative "unknown").

**Found:** Phase 8 TC-A11Y-01 axe scan of `/authors/` — flagged a real defect underneath the accessibility symptom: `<a href="/authors/unknown/"></a>`, a link with no text at all.

**Root cause:** `digest_parser.py`'s mailto-based author extraction had no fallback when both the text before a `Posted by:` mailto link and the mailto link's own inner text were empty (a genuine gap in Yahoo's own rendering for 7 entries, all from the "modern topics" template era). `_parse_name_and_handle` received an empty string and produced an empty display name, which `site/_data/posts.js` then slugified to the fallback `"unknown"`.

**Fix:** When both text sources are empty, `digest_parser.py` now falls back to the local part of the mailto address itself (e.g. `dcndcn13` from `dcndcn13@bbtel.com`) — the same style of fallback display name already used elsewhere in this archive for accounts with no display name set.

**Verified:** Re-ran full ETL; 0 posts with an empty author name; the affected posts now correctly resolve to the existing `dcndcn13` author (1 post) and an existing `Traveller_TNE` shared-address author (6 posts) rather than a synthetic "unknown" bucket. Total author count changed from 184 to 183 (the standalone "unknown" page no longer exists; no page lost, since both real identities already had pages).

## 12. Skip link didn't move keyboard focus

**Severity:** Major (WCAG 2.2 AA 2.4.1 "Bypass Blocks" — the link visually worked (scrolled) but a screen reader or keyboard-only user's actual focus position, and therefore their next Tab stop, stayed wherever it was before activating the link).

**Found:** Phase 8 TC-A11Y-02 keyboard-walkthrough test — activating the skip link and checking `document.activeElement.id` returned empty instead of `"main-content"`.

**Root cause:** `<main id="main-content">` in `base.njk` had no `tabindex`, and only elements that are natively focusable or carry an explicit `tabindex` actually receive DOM focus when a same-page anchor link targets them — browsers still scroll to an unfocusable target, which is why this looked correct visually.

**Fix:** Added `tabindex="-1"` to the `<main>` element (focusable via script/fragment-navigation only, not a new stop in normal Tab order).

**Verified:** Playwright: pressing Tab then Enter on the skip link now moves `document.activeElement` to `#main-content`.

## 13. One archived post's real subheadings skipped a level

**Severity:** Minor (isolated to 2 of 5829 pages — a post and its thread view — and is genuine archived content, not user-facing chrome).

**Found:** Phase 8 TC-A11Y-03 site-wide heading-structure crawl (all 5829 built pages, parsed directly rather than via a browser) — post 12244 (a Yahoo-authored "Understand what's changing in Yahoo Groups" notice) jumped from the page's own `<h1>` straight to `<h3>`, with no `<h2>` anywhere on the page.

**Root cause:** The original email's own HTML included real `<h3>` subsection headings, preserved as-is by `sanitize_body`'s allow-list — correct in isolation, but every post page already has exactly one `<h1>` (the subject), so body content needs to start no higher than `<h2>` to avoid a level skip. Confirmed this is the only occurrence in the entire archive (`grep` of every post's `body_html` for any heading tag found exactly these 2 `<h3>`s and nothing else, no `<h1>`/`<h2>`/`<h4>`+ anywhere).

**Fix:** `sanitize_body` now remaps any heading level surviving in body content so the shallowest one present becomes `<h2>`, shifting the rest by the same amount to preserve relative nesting.

**Verified:** Site-wide crawl re-run after the fix: 0 pages with a heading-level skip (down from 2), 0 pages with other than exactly one `<h1>`, 0 `<img>` missing `alt` — across all 5829 pages, not just the 11-template sample.

## 14. No custom 404 page existed

**Severity:** Major (an explicit design commitment in hld.md §7's Nielsen-heuristic mapping — "Help users recognize/recover from errors: A real, styled 404 page pointing back to search/home" — was never implemented in any of Phases 3-8; GitHub Pages would have served its own generic default instead).

**Found:** Phase 9's TC-USE-01 heuristic review, checking the actual build against hld.md §7's table row by row.

**Root cause:** Simple omission — no phase in the implementation plan explicitly called out a 404 template, and hld.md §7's mapping table wasn't cross-checked against the build until this review.

**Fix:** Added `site/404.njk` (`permalink: /404.html`, matching GitHub Pages' convention for a project site's custom 404), using the shared layout, with a search form and a link back to Home.

**Verified:** Builds to `_site/404.html`; renders correctly with full site chrome (nav, theme toggle, footer).

## 15. Live, unscrubbed email addresses (DR-4/ADR-0008 violation)

**Severity:** Critical — the most severe finding in this project. Real people's email addresses were present in `data/posts.json` and rendered on the publicly deployed site.

**Found:** Post-launch, prompted by the user reviewing a post's "worthless"-looking link footer and asking whether some of the referenced ids resolved to real archived posts. While tracing that footer's content by hand, an email address (`Traveller_TNE-digest@yahoogroups.com`) turned up fully intact inside it, split across a line-wrap. That led to a targeted scan for the same pattern across the whole dataset.

**Root cause:** `normalize.py`'s `_EMAIL_LOOSE_RE` was written to tolerate whitespace/newlines only immediately around the `@` symbol and around each `.` — correct for its original target (Yahoo's `<wbr>` insertion points, always placed at those specific spots) but blind to how quoted plain-text mail actually hard-wraps: at a fixed column, breaking **mid-word**, with no punctuation anywhere near the break (`starwolf@travellerf`\\n`reeport.com`, `digest@yahoogrou`\\n`ps.com`). A scan tolerant of arbitrary-position line breaks found 224 real matches across the dataset — genuine personal addresses (`starwolf@travellerfreeport.com` × 55, `kris@tactics-0.org` × 6, an editorial contact), not just Yahoo's own list-management aliases.

**Fix, and a fix to the fix:** The first repair (allowing a break at *any* position in the local-part/domain, tolerating bare spaces) closed the leak but immediately proved too permissive — it started eating unrelated prose, e.g. "look @ the example.com website" was swallowed whole as if it were one address. Verified against a manually-obfuscated real case (`martin.tajmar @ arcs.ac.at`, spaced out with no newline at all) that a same-permissiveness-for-both fix would regress. Landed on two distinct tolerances: bare spaces are allowed only *immediately around* `@` and each `.` (covers manual anti-harvester spacing), while a break *inside* a single local-part/domain-label token is only recognized when it's an actual newline (covers real line-wraps) — capped at one such internal break per token. This distinction is what keeps ordinary space-separated sentences from being swept in while still catching both real-world cases.

**Verified:** Re-ran the full ETL from raw source (not a re-scrub of already-processed JSON). Two independent scans — a strict contiguous-match regex and the newline/space-tolerant one that found the original 224 — both return 0 across `body_text`, `body_html`, `subject`, and `author.display_name` for all 4060 posts. Spot-checked every previously-leaking post for readability: real content intact, only the address itself removed. Full `make test` suite re-run clean (43 Playwright checks, both Lighthouse presets, 0 broken links across a 5838-link crawl) before redeploying.

**Process note:** This is exactly the kind of defect the project's design explicitly anticipated and built process around (ADR-0008 exists because of it) — and it still shipped, because the original Phase 2 validation sampled digest-template HTML structure, not this specific plain-text mid-word-wrap failure mode, and no later phase re-swept the full corpus for it. Found only because a user, reviewing unrelated output, thought a footer "looked worthless" and asked a clarifying question rather than accepting it. Logged here in full rather than summarized, since a future maintainer changing this regex again needs the two-tolerance distinction, not just "it was broken, now it's fixed."

## 16. A third Yahoo footer variant leaked into post bodies

**Severity:** Major (dead tracking URLs, numbered list noise — not a privacy issue on its own, but discovered in the same investigation as #15).

**Found:** Same investigation as #15 — the footer the user asked about was a plain-text "Links:\n------\n[1] ...\n[2] ..." reference-list rendering of Yahoo's per-message action bar (Reply/Reply to group/Message index/Members/Files/Group home/Yahoo home/Change delivery format/Digest/Unsubscribe/ToS), distinct from the two footer variants already fixed (#7, and the original digest-template markers from Phase 2).

**Root cause:** `_BOILERPLATE_TEXT_MARKERS` had no entry matching this specific rendering. Confirmed zero false positives before adding it: every one of the 128 posts containing the literal string `"Links:"` anywhere in `body_text` has this exact footer immediately following, nothing else.

**Fix:** Added `"Links:"` to `_BOILERPLATE_TEXT_MARKERS`.

**Verified:** Re-ran ETL; 0/4060 posts retain the marker afterward (down from 128); spot-checked the real content immediately preceding the footer in the post that prompted this (7395) — fully intact.

## 17. Orphaned "mailto:" label text

**Severity:** Major (dead, meaningless text — the address portion was already being correctly removed by the pre-existing scrubber in all these cases; only the inert `mailto:` prefix itself was left behind).

**Found:** Same investigation as #15/#16, following the user's specific observation that literal "mailto:" text in the output was "especially egregious." A scan for the literal substring turned up 341/4060 posts, mostly Outlook's `-----Original Message-----\nFrom: X [mailto:]On Behalf Of Y` quote-header convention, where the bracketed address had already been scrubbed, leaving `[mailto:]`.

**Fix:** `scrub_email_addresses` now additionally strips any literal `mailto:` (plus trailing whitespace) remaining after address removal — safe unconditionally, since by construction anything still attached to that prefix was already caught by the address-matching passes that run first.

**Verified:** Re-ran ETL; 0/4060 posts contain `"mailto:"` afterward (down from 341); spot-checked several for readability (e.g. `[mailto:]On Behalf Of DED` → `[]On Behalf Of DED`) -- surrounding quote-header text intact.

## 18. "-------- Original message --------" quote-headers rendered as garbled noise

**Severity:** Minor (readability/presentation only, 13/4060 posts — not a privacy or correctness issue like #15-17, but found in the same investigation).

**Found:** User review of a real post's raw content, flagging the exact example that later led to #15/#16/#17 — noting that hard-wrapped `Subject:`/`From:`/`To:`/`CC:` fields read as garbled and that always-blank `To:`/`CC:` labels added nothing.

**Root cause:** This quoted-forward convention (`-------- Original message --------\nSubject: X\nFrom: Y\nTo: Z\nCC: W`) is plain-text mail hard-wrapped at a fixed column with no regard for field boundaries -- the wrap can land mid-subject, mid-name, anywhere, so it displayed as a jumble rather than clean fields. Confirmed exhaustively before deciding to drop `To:`/`CC:` unconditionally: all 13 real occurrences of this exact header style have both fields empty (the value was always an email address, already removed elsewhere in the pipeline).

**Fix:** `normalize.reflow_original_message_header()` rebuilds the header as clean `Subject: ...` / `From: ...` lines (omitting either if empty), dropping `To:`/`CC:` entirely. Applied to both `body_text` and `body_html` with parallel regexes, since `body_html` renders as `<br/>`-joined lines rather than `\n`. Two rounds of real-data testing surfaced edge cases an initial version missed: multi-level quote markers (`"> > "`) needed a repeating-group match, not a single `>+`; a numbered footnote reference (`"[4] "`) from an overlapping "Links:"-footer (#16) bled into a captured field; and one post with a nested quote-of-a-quote had a second occurrence containing `&lt;`/literal `<>` (HTML-entity and already-scrubbed-bracket remnants respectively) that the initial gap-tolerance pattern didn't include, silently leaving that second occurrence unfixed.

**Verified:** Re-ran ETL; 0/4060 posts show an unformatted `To:...CC:` remnant in either body field (checked via a pattern independent of the fix's own regex, to avoid the check trivially passing by construction); the nested-quote post confirmed to have *both* of its occurrences cleanly reflowed. Spot-checked the exact post/output the user quoted -- matches what they asked for exactly.

## 19. #18's own fix silently deleted real quote markers

**Severity:** Major (content fidelity -- a genuine part of someone's quoted reply, "> Don't do that. Keep your son.", rendered as if it were unquoted top-level text instead; not privacy-sensitive like #15, but a real misrepresentation of archived content, and it shipped once before being caught).

**Found:** The user, after #18 deployed, raised a general concern rather than a specific bug: "There will always be instances of nested quotes, sometimes multiple levels of nested quotes in this sort of data" -- prompting a check of whether the fix actually scaled to arbitrary nesting depth, rather than assuming the two levels tested in #18 generalized. A synthetic 4-level-nested test confirmed the *matching* mechanism scales correctly (a single `re.sub` pass finds and fixes any number of occurrences) -- but the same test surfaced a second, unrelated bug: the reply text immediately following a fixed header lost its own leading quote marker whenever that text started with `>`. Confirmed against the real, already-deployed data: post 7234's `"> Don't do that. Keep your son."` had lost its `"> "`.

**Root cause:** #18's regex consumed a trailing run of "gap" characters (whitespace, `>`, digits, brackets) immediately after `CC:` to clean up leftover quote-only lines -- but that character class had no anchor to stop at. It kept consuming any matching character regardless of what followed, so when the genuinely quoted reply text's first line happened to start with the same characters (`"> Don't do that..."`), the run extended right into it and ate the marker along with the real content behind it. The `To:`...`CC:` gap earlier in the same regex was never at risk of this -- it's bounded by the literal `"CC:"` text as a real anchor, so a greedy match there still has to stop at an unambiguous point. The trailing gap had no equivalent anchor.

**Fix:** Replaced the unbounded trailing character class with a pattern that only ever consumes *complete lines* that are entirely junk (whitespace/quote-markers/footnote-brackets, nothing else, ending in a real line break) -- a line with actual words after its quote marker fails to match "entirely junk" and is left untouched, marker included.

**Verified:** Synthetic 4-level nested-quote test: all levels' distinct quote-marker depths (`">"`, `"> >"`, `"> > >"`) preserved correctly on their real content. Re-ran the full ETL from raw source and re-checked all 13 real occurrences directly: every genuine leading quote marker previously lost (7234, 7235, 7245, 7325, 7329, 7331) is now present and correct, while purely-empty quote-only lines are still cleaned up as intended. Full `make test` clean (43 Playwright checks, both Lighthouse presets, 0 broken links) before redeploying.

**Process note:** This is the second time in this same investigation (after #8) that fixing a boilerplate/formatting issue introduced its own content-loss bug on the first attempt. Both times, what actually caught it was testing against a *harder* real-world case (multi-paragraph content in #8, multi-level nesting here) rather than accepting that the cases already tested looked correct. Worth remembering as a standing pattern for any future change in this area: real archived text is quoted, forwarded, and re-quoted with enough structural variety that a fix validated against a handful of examples can still hide a failure mode one level of nesting away.

## 20. Files-manifest extraction duplicated entries from quoted replies

**Severity:** Major (would have shown "ConsolidatedTNEErrata.pdf" twice on the Files page, with the reply's own timestamp/description as if it were a second, separate upload).

**Found:** During development of ADR-0018's manifest extraction, before it ever shipped -- an initial test run against the real archive returned 11 entries where only 10 real uploads exist.

**Root cause:** The same "a reply quotes the entire previous message verbatim, including structural markers that look like the start of a new record" pattern already seen twice elsewhere in this pipeline (digest_parser.py's phantom-post bug, defect #4; the "-------- Original message --------" duplication risk in #18/#19). Post 6542, "Re: New file uploaded to Traveller_TNE", quotes the original notification (post 6541) inline, and the notification-extraction regex matched both.

**Fix:** `extract_file_upload_notifications()` skips any post whose subject starts with `"Re:"` -- the genuine auto-sent notification is never a reply, so this excludes the reply-quotes without needing to guess based on content.

**Verified:** Manifest count dropped from 11 to the correct 10, with no duplicate filenames sharing a notification-adjacent timestamp.

## 21. Files-manifest extraction silently dropped 4 of 10 real entries

**Severity:** Major (4 real, recoverable-filename uploads would have been entirely absent from the Files page with no indication anything was missing).

**Found:** Same pre-ship testing pass as #20 -- an initial run returned only 6 of the 10 real notification emails.

**Root cause:** The extraction regex expected `"Uploaded by : NAME <>"` (empty brackets, already scrubbed) on a single line before `"Description :"` could follow. In 4 of the 10 real notifications, the scrubbed remnant itself wraps across an extra blank line (`"Uploaded by : donm61873 <\n\n>\n"`) -- a `[^\n]*` immediately after the name only tolerated one line, so the regex failed to match at all for these four, silently, with no error.

**Fix:** Widened the gap between the uploader's name and the following `"Description:"` label to a non-greedy `.*?` (DOTALL), letting it span however many wrapped lines the scrubbed remnant happens to occupy.

**Verified:** All 10 real notifications extracted correctly; spot-checked each filename against the raw archive by hand.

## 22. Email-address scrubbing could delete an unrelated real word immediately before a `<wbr>`-split address

**Severity:** Major (content fidelity -- a real word silently vanished from already-shipped post bodies; not privacy-sensitive itself, but the same class of defect as #19: quoted-header cleanup work exposing a pre-existing bug in an adjacent, already-deployed mechanism).

**Found:** While investigating the user's request to make the Outlook `-----Original Message-----` quote-header (a second, distinct quoted-forward convention from #18/#19's) render consistently with the already-fixed one. A sample of that convention (post source msg 211, digest-embedded) showed `"[]On Behalf \nSent:"` in `body_text` -- the word "Of" was simply missing between "Behalf" and "Sent:".

**Root cause:** `sanitize_body()` already knows, unambiguously, that an `<a href="mailto:...">` anchor's visible text is an email address -- but it only stripped the `href` attribute, leaving the text itself to flow into `get_text(separator="\n", strip=True)` and rely on `scrub_email_addresses()`'s text-level regex to find it again from scratch. Yahoo inserts `<wbr>` inside long addresses for word-wrapping (`shadow@shadowgard.<wbr>com`), which `get_text()` turns into a real newline in the flattened text -- and `_EMAIL_LOOSE_RE`'s `_MIDTOKEN_BREAK` tolerance (added for #15, to reconstruct exactly this kind of split) can't distinguish "this fragment continues the address on the next line" from "an unrelated real word happens to sit immediately before the address's first line with no separating space" (BeautifulSoup's `strip=True` had already removed that space). Confirmed against the real archive: `"...]On Behalf Of\nshadow@shadowgard.\ncom"` matched as a single email address starting at "Of", deleting that real word along with the actual address.

**Fix:** `sanitize_body()` now clears a mailto anchor's own text content at the DOM level, at the same point it already drops the `href` -- the address is removed while the anchor boundary is still known, so it's never exposed to the text-level regex's line-wrap tolerance in the first place. (This required a small follow-on fix: the loop that strips disallowed tags iterates a pre-materialized `find_all()` list, and clearing an anchor's children can detach a not-yet-visited `<wbr>` tag from the tree before the loop reaches it -- guarded with a `tag.parent is None: continue` check.) The plain-text hard-wrapped case (quoted replies with no HTML structure at all, e.g. `"starwolf@travellerf\nreeport.com"`) has no DOM boundary available and still needs the text-level regex's tolerance -- this fix only removes the *HTML-anchor* source of the ambiguity, which was the one actually observed to eat real content.

**Verified:** Re-ran the full ETL from raw source; 1521/4060 posts changed. Diffed every change: all are either recovery of previously-eaten real words ("Of", "In", "list", "PM" confirmed across a random sample) or cleanup of scrubbing debris that the old text-level-only approach had left partially unremoved (a multiply-`<wbr>`-wrapped VERP unsubscribe local part, `"sentto-3162816-7459-1339775326-dcndcn13="`, previously survived as visible junk since it had no `@` left for the regex to anchor on). Zero email-address-shaped substrings remain anywhere in `body_text`/`body_html` across all 4060 posts (checked independently of this fix's own logic). Full `make test` clean before redeploying.

## 23. Outlook quote-header reflow (built for consistency with #18/#19, never shipped in its broken form): a two-pass regex design silently ate a real paragraph

**Severity:** Would have been Major if shipped (content fidelity) -- caught during this feature's own pre-ship validation, never deployed.

**Found:** Comprehensive validation across all 97 real posts containing the `-----Original Message-----` convention, run specifically *because* #19 already demonstrated that a fix validated against a sample can still hide a failure mode -- one post (6758) showed the reflowed `body_text` was ~967 characters shorter than the original.

**Root cause:** Two field orders are both real in the archive: `From/Sent-or-Date/To/Subject` (common) and `From/To/Sent-or-Date/Subject` (posts 7344, 7351). The first implementation handled these as two sequential `.sub()` passes over the whole text -- the second pass, intended only for the rarer order, re-scanned the *output* of the first. Post 6758 contains a second, unmarked header block later in the same body (a doubly-forwarded quote whose mail client didn't re-emit its own `-----Original Message-----` divider). The first pass correctly reflowed the first (marked) block and, by design, dropped its now-empty `To:` line. The second pass then searched that already-reflowed text for a `To:` near the same marker, didn't find one there anymore, and its lazy match kept searching until it found the *second* block's unrelated `To:` instead -- silently swallowing the entire real paragraph in between as if it were part of the header.

**Fix:** Replaced the two-pass design with a single regex per format (text/HTML) using an internal alternation between the two field orders, so each `-----Original Message-----` occurrence is matched exactly once. A match never re-scans another match's output, so a later unmarked block is structurally invisible to the pattern regardless of field order, instead of becoming a hazard for a same-text second pass.

**Verified:** Re-ran validation across all 97 real occurrences (both `body_text` and `body_html`): no shrink greater than the size of the header block itself for any post. Post 6758's second, unmarked block confirmed left untouched (not reflowed, not damaged) -- same accepted, by-design limitation as any other unmarked continuation header. Full ETL re-run, `make test` clean, before this feature shipped at all.

**Process note:** A third instance, after #8 and #19, of a formatting/cleanup fix's first implementation introducing its own content-loss bug -- and the second time specifically that a *second pass reusing the shape of the first fix's own output* was the mechanism (compare #19's unbounded trailing-gap consumption). Reinforces the same standing lesson recorded in #19: validate against the full real sample before shipping, not just the cases that motivated the fix.

## 24. Yahoo Mail's underscore-divided quote-header rendered as garbled noise

**Severity:** Minor (readability/presentation only, 198/4060 posts across `body_text`/`body_html` -- same category as #18, not a privacy or correctness issue).

**Found:** User screenshot of a real rendered post, flagging a `From: "" >` line with an empty quoted name and a stray `>` -- a fourth quoted-forward convention, distinct from #18/#19's `-------- Original message --------` and #22/#23's `-----Original Message-----`: Yahoo Mail's own "classic" compose view, divided by a plain underscore rule (`________________________________`) rather than any dashed marker text.

**Root cause:** Same shape as the other two conventions -- `From:`/`To:`/`Sent:`/`Subject:` fields, each on its own line, rendered as multiple blank-looking lines once the address inside `From:`/`To:` was scrubbed. In this convention specifically, when no display name was ever set, Yahoo's own rendering repeats the raw (now-scrubbed) address as both the quoted "display name" and the address itself -- `From: "ADDRESS" <ADDRESS>` -- so after scrubbing, both instances vanish, leaving only the surrounding punctuation (`""` and `<>`) visible with nothing between them. Checked directly against the real archive before treating this as a fix rather than a mis-render: in every one of the 39 raw source occurrences, any *real* display name (e.g. "Roger Malmstein", "Mike West") is plain text, never wrapped in the mailto anchor itself -- so #22's DOM-level anchor-clearing fix was never at risk of eating a real name here; the empty-quotes case is a faithful (if ugly) rendering of a message that genuinely never had a display name.

**Fix:** `normalize.reflow_underscore_original_message_header()`, following the same pattern as `reflow_original_message_header`/`reflow_outlook_original_message_header`: collapses the header into clean `From:`/`To:`/`Sent:` lines (each omitted if empty after cleanup -- `To:` in this convention always carries only the list's own scrubbed address, so it's dropped in every real occurrence), leaving `Subject:` and its value untouched for the same content-loss-avoidance reason as the `-----Original Message-----` fix. A new shared `_strip_scrubbed_address_remnants()` helper (factored out of the two existing Outlook-field cleaners) additionally strips empty `""` pairs and unpaired `"` quote marks, needed for this convention's `""` remnant.

**Verified:** Re-ran the full ETL from raw source; 163/4060 posts changed. Diffed against the pre-fix dataset: no shrink larger than the header block itself for any post; zero email-address-shaped substrings remain anywhere in the dataset afterward. Full `make test` clean before redeploying.

## 25. Underscore-divider regex (built for #24, never shipped in its slow form): catastrophic backtracking on non-matching input

**Severity:** Would have been Major if shipped (a hang, not a crash, on `make data` -- silent and hard to diagnose) -- caught during this feature's own pre-ship validation, never deployed.

**Found:** The comprehensive real-data validation pass run for #24 (the same discipline #19/#23 established: check every real occurrence, not just the cases that motivated the fix) hung indefinitely instead of completing in the few seconds every prior validation script in this investigation took.

**Root cause:** The divider pattern was `_{2,}(?:\s*_{2,})*` -- a quantified group whose own body is quantified over a character class (underscores) that the group is itself repeated against, alternating with another quantified class (whitespace). This is the textbook catastrophic-backtracking shape: on a non-matching candidate (any post containing an unrelated run of underscores/whitespace *not* actually followed by a real `From:`/`To:`/`Sent:`/`Subject:` block -- common, since underscore-rule signature separators appear elsewhere in the archive with nothing header-like after them), the regex engine can partition that run combinatorially many ways before concluding no match is possible, rather than failing fast.

**Fix:** Replaced with `_[_\s]*_` -- a single unquantified-then-quantified-then-unquantified sequence (one `[_\s]*` between two literal `_` anchors) that matches the same realistic text with no nested ambiguity, and is provably linear-time regardless of input.

**Verified:** The same validation pass that previously hung past a 120-second timeout completed in well under a second afterward, with identical results (153/198 candidates matched in both `body_text` and `body_html`, one flagged case confirmed as an unrelated digest "Posted by:" line the pattern correctly never touched). Full ETL re-run against the real 4060-post corpus completed without incident.

**Process note:** A structural cousin of #19/#23, not a content-fidelity failure this time but the same underlying lesson: a regex validated only against the handful of examples that motivated it (here, the 39 real matching occurrences) can still hide a failure mode that only a full-corpus, adversarial-enough validation pass (here, posts containing the trigger substring *without* the full header following it) exposes. Worth remembering as a standing pattern for any future header-reflow work in this pipeline: test against the full real sample, and specifically include near-miss/non-matching cases, not just clean matches.

## Related but not logged as a defect: Pagefind's fuzzy matching has no reliable "no results" threshold

Not a defect — a documented constraint discovered while investigating one. `pagefind.search()` uses edit-distance fuzzy matching that returns *something* for almost any input, including nonsense strings (e.g. "zzzznonexistentqueryterm" scored up to ~4 against the real index). An attempt to filter these out with a minimum relevance score was reverted after it also filtered out a genuine, FR-10-required stemmed match (post 6381, "orbiting" only, scored 4.13 — indistinguishable from noise by score alone). `site/js/search.js` intentionally does not score-filter results; see the comment at its `runSearch()` function for the full reasoning. FR-9 through FR-13 have no requirement that "no results" be reachable for arbitrary/garbage input, so this is accepted as-is rather than worked around further.
