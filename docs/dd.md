# Detailed Design: Traveller_TNE Archive Site

**Status:** Draft
**Derived from:** [hld.md](hld.md), [srs.md](srs.md), [data-structures.md](data-structures.md)

This document resolves the three items the HLD deferred (§11: attachment/UUID items were closed there already; Pagefind UI depth and dedup tie-breaking are closed here), and gives the field-by-field schema and module/script breakdown the HLD deliberately left at illustrative level.

## 1. Repository layout

```
yahoo-groups-tne-archive/
├── mail_archives/              # read-only source, never modified
│   ├── YahooArchive
│   └── YahooArchive.msf        # dev-time cross-check only (ADR-0001)
├── attachments/                # DR-8 — sparse, grows over time
│   └── <permalink-id>/<original-filename>
├── data/
│   └── posts.json              # canonical dataset (ADR-0001), committed
├── pipeline/                   # Python ETL (§4)
│   ├── etl.py
│   ├── parse_mbox.py
│   ├── digest_parser.py
│   ├── dedupe.py
│   ├── thread.py
│   ├── normalize.py
│   ├── ids.py
│   └── attachments.py
├── site/                       # Eleventy source (§7)
│   ├── _data/
│   ├── _includes/
│   │   ├── layouts/
│   │   └── components/
│   ├── css/
│   ├── js/
│   └── *.njk
├── docs/                       # this doc set
├── Makefile
└── .github/workflows/deploy.yml
```

## 2. Canonical dataset — full schema

One JSON array of post objects in `data/posts.json`. No separate `authors.json`/`topics.json`/etc. — author, topic, year/month, and thread groupings are all computed at Eleventy build time from this single file (§7.2), per ADR-0001's "one dataset, multiple derived views" principle.

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Yahoo permalink numeric ID (as string) where one exists; otherwise a UUID v5 (§3). Primary key; also the `/posts/<id>/` path segment and the attachment-matching key. |
| `id_type` | `"yahoo_permalink"` \| `"synthetic_uuid"` | yes | Transparency field — lets the DD/build tooling (and a future maintainer) distinguish provenance without guessing from the string shape. |
| `source_kind` | `"digest"` \| `"relayed"` \| `"direct"` | yes | Per data-structures.md §2's kind A/B/C; drives dedup precedence (§5) and threading eligibility (ADR-0005). |
| `source_mbox_index` | integer | yes | 0-based index of the originating mbox record; provenance/debugging only, never rendered. |
| `subject` | string | yes | As-authored. |
| `subject_normalized` | string | yes | Lowercased, `Re:`/`Fwd:`/`[Traveller_TNE]`-stripped, whitespace-collapsed. Used for FR-17's topic index and ADR-0005's fallback threading. |
| `author.display_name` | string | yes | Never an email address (ADR-0008). |
| `author.profile_handle` | string \| null | no | Yahoo profile handle when the source exposed one (data-structures.md §2.1); purely a display nicety. |
| `author.slug` | string | yes | See §7.3 for the slugging/collision rule — computed once, stable across rebuilds. |
| `date_utc` | string (ISO 8601, UTC) | yes | DR-3. |
| `date_original` | string | yes | As found in the source, verbatim. |
| `body_html` | string | yes | Sanitized fragment: boilerplate stripped (data-structures.md §5), safe tag subset only. |
| `body_text` | string | yes | Plain-text derived from `body_html` at ETL time (tags stripped, entities decoded) — used for OG/meta descriptions (FR-20); not used for search, since Pagefind indexes rendered HTML directly (ADR-0003). |
| `thread_id` | string | yes | The root post's `id` for the thread this post belongs to (ADR-0005). |
| `parent_id` | string \| null | yes | Null for thread roots. |
| `reply_ids` | array of string | yes | Empty array if none. |
| `attachments` | array of object | yes | Empty array if none referenced. Each: `{ "filename": string, "available": boolean, "source": "mime_embedded" | "files_section_reference" }` — `available` is computed at *build* time (§6), never hand-set. |
| `yahoo_url` | string \| null | no | Dead provenance link (Yahoo Groups no longer resolves it); development/citation use only. |

## 3. Synthetic ID generation (resolves ADR-0007's open point)

**Decision:** UUID **v5** (deterministic, namespace + name), not v4. See [ADR-0009](adr/0009-uuid-v5-for-synthetic-ids.md).

- A fixed namespace UUID is defined once in `pipeline/ids.py` and never changes.
- For a permalink-less post that has a real `Message-ID` (true for 719/724 source records per data-structures.md), the name input is that `Message-ID` string.
- For the small remainder with neither a permalink nor a `Message-ID`, the name input is `subject_normalized + "|" + author.display_name + "|" + date_utc` — still fully deterministic, since the source is frozen (ADR-0001).

This means IDs never need to be persisted or tracked across ETL reruns to stay stable — re-running the pipeline from scratch always regenerates the identical ID for the identical source record, which is what makes permalinks (FR-1) safe to treat as permanent.

## 4. ETL pipeline — module breakdown

| Module | Responsibility |
|---|---|
| `parse_mbox.py` | Iterate the mbox via Python's `mailbox` module; classify each record's `source_kind` (digest / relayed / direct) per data-structures.md §2. |
| `digest_parser.py` | For digest records: `BeautifulSoup`-parse the `<h1>Messages</h1>` section, yield one raw post dict per `<dl>` entry (subject, author, date, body, Yahoo permalink ID) per data-structures.md §2.1. |
| `normalize.py` | Date parsing → `date_utc`/`date_original` (DR-3); subject normalization; HTML sanitization + boilerplate stripping (data-structures.md §5); email-address scrubbing (ADR-0008) — this is the one place PII removal happens, applied unconditionally to every record regardless of source kind. |
| `ids.py` | UUID v5 generation per §3; `author.slug` generation per §7.3. |
| `dedupe.py` | Group raw posts by `id`; apply §5's tie-break rule for any group with more than one member. |
| `thread.py` | ADR-0005's two-pass algorithm: header-based `Message-ID`/`In-Reply-To`/`References` resolution, then subject-normalized chronological chaining fallback. |
| `attachments.py` | Cross-reference each post's referenced attachment filename(s) against `attachments/<id>/` (§6). |
| `etl.py` | CLI entrypoint (`make data`): orchestrates the above in order, writes `data/posts.json`. |

## 5. Deduplication tie-breaking (resolves the HLD's open item)

**Decision:** when more than one raw record shares the same `id` (dedup key), keep the one with the **longer `body_text` after normalization** (a proxy for completeness), and **log a warning** naming the `id` and both `source_kind` values for manual review. See [ADR-0010](adr/0010-dedup-tiebreak-by-body-length.md).

Rationale: the source is static, so exact duplicates (the common, expected case — the same post arriving both individually and inside a digest) should be byte-identical after normalization and this rule never actually triggers a real choice. It exists purely as a defined, testable fallback for the *unexpected* case of a genuine content mismatch, rather than leaving that scenario to accidental "whichever the loop saw last" behavior. The warning log means a human notices if it ever actually fires, rather than the pipeline silently picking a side.

## 6. Attachment matching

Directory: `attachments/<id>/<original-filename>` (ADR-0006), keyed by the same `id` as the owning post.

At build time (not ETL time — this is why `attachments[].available` is computed by the site build per ADR-0006, not baked into `data/posts.json`): for each post's `attachments` entries, check whether `attachments/<id>/<filename>` exists; if so, copy it into the Eleventy output alongside the post's page and mark it available; if not, leave it unavailable and the post page renders the FR-26 modal instead.

## 7. Site generation (Eleventy)

### 7.1 Data loading

`site/_data/posts.js` reads `data/posts.json` once per build and exposes it as Eleventy global data; a companion module computes the derived, build-time-only views used by templates:

- **By author** (`author.slug` → posts), for `/authors/`.
- **By topic** (`subject_normalized` → posts), for `/topics/`.
- **By year/month** (`date_utc` → posts), for `/browse/`.
- **By thread** (`thread_id` → ordered posts), for `/threads/`.
- **Attachment availability** (§6), computed here rather than in the ETL.

### 7.2 Templates

One Nunjucks template per page type in the URL map (hld.md §6): `post.njk`, `thread.njk`, `author.njk` + `authors-index.njk`, `topic.njk` + `topics-index.njk`, `browse-year.njk` + `browse-month.njk`, `search.njk`, `help.njk`, `index.njk`. All extend `_includes/layouts/base.njk` (shared header/nav/footer/skip-link, per hld.md §7). `_includes/components/modal.njk` is the single shared native-`<dialog>` component used by FR-26.

### 7.3 Author/topic slugs

Lowercase, non-alphanumeric characters replaced with `-`, collapsed and trimmed. Collisions (two authors/topics normalizing to the same slug) are disambiguated by appending the **lowest `id` among that group's posts, sorted lexically** — deterministic and stable across rebuilds, unlike an iteration-order-based counter would be.

### 7.4 Sitemap & per-page metadata (FR-20)

`sitemap.xml` is a hand-rolled template (`sitemap.njk`, `permalink: sitemap.xml`), not a plugin dependency — see [ADR-0016](adr/0016-sitemap-hand-rolled-not-plugin.md). It iterates the same page collection every other template already walks, so it can't drift out of sync with what actually got built. Each template's `<head>` (via `_includes/layouts/base.njk`) emits a canonical URL and Open Graph/Twitter `<meta>` tags; the OG description for post pages uses the `body_text` field already in the canonical schema (§2), truncated to a reasonable length — no new ETL field needed, this was just an unstated mechanism until now.

## 8. Search (resolves the HLD's open item)

**Decision:** a **custom search UI built against Pagefind's JS API** (`pagefind.search()`/`pagefind.filter()`), not the default drop-in `PagefindUI` widget. See [ADR-0011](adr/0011-custom-pagefind-ui.md).

Rationale: the default widget ships its own CSS that would need substantial overriding to match ADR-0004's hand-written design tokens, and a custom implementation gives exact control over: semantic result markup (an actual `<ol>`/`<li>` list, not divs); an `aria-live="polite"` region announcing result counts as they change (Nielsen "visibility of system status," already committed to in hld.md §7); and precise snippet/highlight rendering and subject-favoring result ordering to satisfy FR-13 exactly as specified, rather than whatever the default widget's ranking happens to produce.

## 9. CSS/JS architecture

Actual token values, color palette (with verified contrast ratios), type scale, spacing scale, breakpoints, and component-level visual specs are defined in **[ui-design.md](ui-design.md)** — this section names only the file structure they live in.

- `site/css/tokens.css` — all custom-property design tokens (color, spacing, type scale) per ui-design.md §§2–4, light values by default, dark overrides under `@media (prefers-color-scheme: dark)` and a `[data-theme]` override for the manual toggle (hld.md §8).
- `site/css/base.css` — element defaults, layout primitives.
- `site/css/components.css` — nav, modal, search results, thread view, etc.
- `site/js/theme-toggle.js` — manual theme override, persisted to `localStorage`. Small and needed before first paint (to avoid a flash of the wrong theme), so it's inlined or loaded blocking in `<head>` — the one deliberate exception to "nothing blocks first render," justified by what it's preventing.
- `site/js/search.js` — the custom Pagefind UI from §8. Per [ADR-0015](adr/0015-search-loads-only-on-search-page.md), included via a `defer`red `<script>` on `search.njk` only, not in the shared layout — every other page, including Home's own search box, carries zero cost from it. `search.njk` reads a `q` query-string parameter on load and auto-runs it once Pagefind initializes, so a query typed into Home's plain-GET-form search box and submitted there resolves in one navigation, not a navigate-then-retype.

## 10. Build pipeline — concrete commands

| Makefile target | Command(s) |
|---|---|
| `make data` | `python3 pipeline/etl.py` → writes `data/posts.json`. **Human-run only, never invoked by `make build`** — `mail_archives/` is gitignored (it holds unredacted PII, ADR-0008) and simply isn't present in a fresh CI checkout, so any auto-trigger here would break every CI build. Re-run this locally and commit the result whenever the ETL changes or a parsing bug is fixed (concept.md §7). |
| `make build` | `npx @11ty/eleventy` → `make index`. Consumes whatever `data/posts.json` is already committed — no dependency on `mail_archives/` existing. |
| `make index` | `npx pagefind --site _site` |
| `make serve` | `npx @11ty/eleventy --serve` |
| `make test` | `npx playwright test` (axe-core scan, §11) + `npx lhci autorun` (§11) + `npx linkinator _site` |
| `make clean` | remove `_site/` and Pagefind output; `data/posts.json` untouched |

GitHub Actions: checkout → set up Python + Node → `make build` → `make test` (gate — a Critical-severity failure per test-plan.md §10 stops the deploy) → `actions/deploy-pages`. CI never calls `make data`, per `make build`'s note above.

## 11. Test tooling (implementation detail for the later Test Plan)

- **Accessibility**: `@axe-core/playwright`, run against one representative page per template type (not all ~1000+ post pages individually — they share a template, so template-level coverage is what's meaningful).
- **Performance/SEO/Best Practices**: Lighthouse CI (`@lhci/cli`), same representative-page-per-template sampling, asserting NFR-5's ≥90 thresholds.
- **Link integrity**: `linkinator` against the full built `_site/` output, catching broken internal links (thread/author/topic cross-links, attachment links).

These are tool choices, not architecture decisions — no new ADRs for them; the Test Plan document will turn them into actual gating criteria and CI steps.

## 12. Traceability preview

This document adds concrete design elements for FR-1–FR-27, DR-1–DR-8, and NFR-1–NFR-9 at the module/field level; the RTM (next) maps each requirement to the specific row/module/field introduced here plus its eventual Test Plan verification.

## 13. New ADRs from this document

- [ADR-0009](adr/0009-uuid-v5-for-synthetic-ids.md) — UUID v5 for synthetic IDs
- [ADR-0010](adr/0010-dedup-tiebreak-by-body-length.md) — Dedup tie-break by body length + warning log
- [ADR-0011](adr/0011-custom-pagefind-ui.md) — Custom Pagefind UI instead of the default widget

## 14. Open items

None carried forward — all items the HLD deferred to this document are resolved above. Proceed to the RTM.
