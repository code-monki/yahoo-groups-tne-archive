# ADR-0001: Canonical JSON dataset as the sole interface to source data

**Status:** Accepted

## Context

The source archive (`mail_archives/YahooArchive`, an mbox, plus the disposable `YahooArchive.msf` Mork cache) is frozen and read-only — no new mail will ever arrive (concept.md §1). 71% of mbox records are Yahoo digest bundles, each packing multiple distinct posts into one HTML email (data-structures.md §2) — real per-post structure has to be recovered, not just read off. Every downstream consumer (the site generator, the search-index builder) needs a clean, uniform view of "posts," not raw email/digest plumbing.

## Decision

A one-shot Python ETL pipeline parses the mbox (expanding digests, deduplicating via the Yahoo permalink ID, resolving threads, normalizing dates to UTC, stripping boilerplate and PII) into a single canonical JSON dataset (`data/posts.json`), committed to the repository. All downstream tooling — the Eleventy site build, the Pagefind indexing step, anything else built later — reads only from this dataset. Nothing downstream ever opens `mail_archives/YahooArchive` or `YahooArchive.msf` directly (DR-6).

## Consequences

- Decouples the messy, one-time "parse Yahoo's HTML" problem from "build a good website" — the two can be worked on, tested, and reasoned about independently.
- Because the source never changes, re-running the ETL is only needed to fix a parsing bug or add a field, not on any recurring schedule.
- Any new field a future page template needs must be added to this schema and the ETL re-run — there is deliberately no live fallback to raw source data at request/build time.
- `YahooArchive.msf` is retained only as a development-time cross-check (DR-7) — e.g. comparing computed thread counts against Thunderbird's own — never a pipeline dependency.
