# ADR-0005: Hybrid header-based + subject-normalization threading

**Status:** Accepted

## Context

Only the non-digest source records (individually mailed or Yahoo-relayed, roughly 210 of the 724 mbox records — data-structures.md §2) ever carried genuine RFC `Message-ID`/`In-Reply-To`/`References` headers. Digest-embedded posts — the majority of actual post content once digests are expanded — were extracted from HTML with no email headers at all; they only ever have a Yahoo permalink ID, subject, author, and date. Header-based threading can therefore never directly resolve a reply relationship into or out of a digest-derived post — this is an intrinsic property of the source, not a gap to close.

## Decision

Thread resolution (FR-6) runs in two passes:

1. **Header pass**: build a `Message-ID → post id` lookup across every post that has a real `Message-ID`; for each post with `In-Reply-To`/`References`, resolve against that lookup and set `parent_id` if found.
2. **Subject-fallback pass**: for every post not assigned a parent in pass 1, normalize its subject (strip `Re:`/`Fwd:`/list-tag prefixes, case-fold, collapse whitespace) and group posts sharing that normalized subject; within each group, sort by normalized UTC date and chain each post's `parent_id` to the immediately preceding post in that group.

Mork's independently-computed thread/singleton counts (data-structures.md §4.2) are used as a development-time sanity cross-check (DR-7) against this algorithm's output — never as a pipeline dependency (ADR-0001).

## Consequences

- Threading is a heuristic, not a guarantee of factually correct reply structure, and is documented as such rather than presented to readers as authoritative.
- The subject-fallback chain assumes a linear reply order within a normalized-subject group; it does not attempt to infer branching structure the source gives no evidence for.
- Consistent with data-structures.md's finding that even Thunderbird's own threading algorithm resolved the large majority of this archive's threads as singletons — most content simply doesn't have deep reply chains to reconstruct.
