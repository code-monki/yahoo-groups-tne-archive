# ADR-0009: UUID v5 for synthetic IDs

**Status:** Accepted
**Supersedes:** narrows [ADR-0007](0007-synthetic-ids-use-uuid.md), which left the UUID version undecided.

## Context

ADR-0007 decided that posts without a Yahoo permalink ID get a UUID, but left open whether that's random (v4) or deterministic (v5), flagging that v4 would require persisting generated IDs across ETL reruns to keep permalinks stable — an extra piece of state to manage.

## Decision

Use UUID **v5** (namespace + name, SHA-1-based, deterministic). A fixed namespace UUID is defined once in `pipeline/ids.py`. The name input is the post's `Message-ID` header where one exists (true for 719/724 source records — data-structures.md), or `subject_normalized + "|" + author.display_name + "|" + date_utc` for the small remainder lacking both a permalink and a `Message-ID`.

## Consequences

- No state needs to be persisted across ETL runs — re-running the pipeline from a clean checkout always regenerates the identical ID for the identical source record, because the source is frozen (ADR-0001).
- Removes the concern ADR-0007 flagged about v4 requiring an ID-stability mechanism — that concern doesn't apply to v5.
- If the *input* to the hash ever needs to change (e.g. a bug fix changes how `subject_normalized` is computed), every synthetic ID derived from it changes too, breaking any previously-published permalinks using it. Acceptable given the source is static and this is expected to be rare/one-time, but worth remembering if it comes up.
