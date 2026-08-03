# ADR-0010: Dedup tie-break by body length, with a warning log

**Status:** Accepted

## Context

DR-2 dedupes posts by Yahoo permalink ID, for the expected case of the same post arriving both individually and inside a digest. The HLD (§11) flagged an unhandled edge case: what happens if two records sharing that key have *materially different* content — a scenario that shouldn't occur given the source is static, but was left undefined rather than accidentally resolved by loop iteration order.

## Decision

When a dedup group has more than one member, keep the one with the longer normalized `body_text`, and log a warning naming the `id` and both records' `source_kind` for manual review.

## Consequences

- In the expected case (identical content from two delivery paths), this rule never actually makes a meaningful choice — both members are equal or near-equal in length.
- In the unexpected case (genuine mismatch), the pipeline doesn't silently pick a side — a human sees the warning and can investigate, rather than the discrepancy being invisible.
- "Longer body" is a proxy for completeness, not a guarantee of correctness — acceptable given this path is not expected to be exercised in practice.
