# ADR-0007: Synthetic IDs for permalink-less posts use UUIDs

**Status:** Accepted
**Narrowed by:** [ADR-0009](0009-uuid-v5-for-synthetic-ids.md), which settles the v4-vs-v5 question left open below.

## Context

The canonical dataset's `id` field (hld.md §3) is used as the deduplication key (DR-2), the permalink path segment (FR-1), and the attachment-matching key (ADR-0006). Most posts have a Yahoo message permalink ID to use directly, but not every post is guaranteed to have one — some non-digest/individually-mailed posts have no Yahoo URL at all. A stable value is still required for these.

## Decision

Where no Yahoo permalink ID exists, generate a UUID during ETL and never recompute it on subsequent pipeline runs. Exact UUID version — v4 (random) versus v5 (deterministic, derived from a stable input such as the post's `Message-ID` or a hash of its content) — is left to the DD to decide.

## Consequences

- Guarantees `id` uniqueness and stability across rebuilds without depending on Yahoo's dead numbering scheme for every post.
- If v4 (random) is chosen in the DD, the ETL must persist generated IDs somewhere stable across runs (e.g. in the committed dataset itself, treated as append-only for this field) rather than regenerating them fresh each time, or permalinks would break on every rebuild. If v5 (deterministic) is chosen instead, this concern doesn't apply. The DD must state which and, if v4, how stability is preserved.
