"""Cross-record deduplication (DR-2, ADR-0010).

Distinct from digest_parser.py's own internal dedup (the same id appearing
twice *within one digest*, e.g. a table-of-contents teaser plus the full
entry) -- this module handles the same post appearing across *different*
mbox records entirely, e.g. once as an individually-relayed email and again
inside a digest.

Two passes, not one:

1. Exact `id` match -- the common case, where both copies resolved to the
   same real Yahoo permalink.
2. Fuzzy match on (author, subject_normalized, date within a few minutes)
   -- found empirically: a post mailed directly *and* also appearing in a
   digest doesn't always yield the same `id` for both copies. The direct
   copy has no permalink to extract if its footer lacks the expected
   Yahoo action-bar markup, so it gets a distinct synthetic UUID (ids.py)
   instead of the digest copy's real permalink -- two different `id`
   values for what's actually one post, invisible to pass 1. Confirmed
   against the real archive: rare (2 pairs across 4020 posts) but real,
   and it produces a visibly duplicated post/thread if left alone.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# How close two same-author, same-subject posts' timestamps have to be to
# be treated as the same post via two paths rather than a coincidence (e.g.
# a recurring system subject like "Poll results for Traveller_TNE" posted
# on two genuinely different occasions -- those are typically hours or days
# apart, well outside this window).
_FUZZY_WINDOW_SECONDS = 600

# Timing plus (author, subject) alone isn't enough -- confirmed against the
# real archive: an active poster can send several genuinely distinct replies
# in the same fast-moving sub-thread within minutes of each other, which
# looks identical to "same post, two paths" on timing alone. Only merge if
# the bodies are *also* substantially similar; a bounded prefix keeps this
# cheap even for the rare multi-thousand-character digest body.
_SIMILARITY_PREFIX_LEN = 500
_SIMILARITY_THRESHOLD = 0.65
_WHITESPACE_RE = re.compile(r"\s+")


def _normalized_prefix(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip().lower()[:_SIMILARITY_PREFIX_LEN]


def _bodies_similar(a: dict, b: dict) -> bool:
    ratio = SequenceMatcher(
        None, _normalized_prefix(a["body_text"]), _normalized_prefix(b["body_text"])
    ).ratio()
    return ratio >= _SIMILARITY_THRESHOLD


def _merge_group(group: list[dict], label: str) -> dict:
    # Longer body is the primary proxy for completeness (ADR-0010), but a
    # real Yahoo permalink id is worth more than a handful of extra
    # whitespace/formatting characters from a different extraction path --
    # confirmed against the real archive, where the two confirmed genuine
    # cross-path duplicates differed by under 2% in body length, and a
    # pure length comparison would have discarded the real permalink
    # (id 6312) in favor of an arbitrary synthetic UUID for no real gain.
    # Only overridden if the permalink copy's body is *substantially*
    # shorter (a real completeness difference, not extraction-path noise).
    max_len = max(len(p["body_text"]) for p in group)
    def sort_key(p: dict) -> tuple[bool, int]:
        is_near_longest = len(p["body_text"]) >= max_len * 0.8
        has_permalink = p["id_type"] == "yahoo_permalink"
        return (has_permalink and is_near_longest, len(p["body_text"]))

    group.sort(key=sort_key, reverse=True)
    kept, *dropped = group
    logger.warning(
        "dedup (%s): kept id=%s source_kind=%s (body_text len=%d), dropped %s",
        label,
        kept["id"],
        kept["source_kind"],
        len(kept["body_text"]),
        [(p["id"], p["source_kind"], len(p["body_text"])) for p in dropped],
    )
    return kept


def _parse_utc(date_utc: str) -> datetime:
    return datetime.strptime(date_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def dedupe(posts: list[dict]) -> list[dict]:
    # Pass 1: exact id match.
    by_id: dict[str, list[dict]] = {}
    for post in posts:
        by_id.setdefault(post["id"], []).append(post)
    pass1 = [
        _merge_group(group, "exact id") if len(group) > 1 else group[0]
        for group in by_id.values()
    ]

    # Pass 2: fuzzy match on (author, subject_normalized), merging any pair
    # within the time window above -- deliberately conservative (same
    # author, same normalized subject, *and* close in time all three) to
    # avoid merging genuinely distinct posts that happen to share a subject.
    by_author_subject: dict[tuple[str, str], list[dict]] = {}
    for post in pass1:
        key = (post["author"]["display_name"], post["subject_normalized"])
        by_author_subject.setdefault(key, []).append(post)

    result = []
    for group in by_author_subject.values():
        if len(group) == 1:
            result.append(group[0])
            continue
        group.sort(key=lambda p: p["date_utc"])
        merged_indices: set[int] = set()
        clusters: list[list[dict]] = []
        for i, post in enumerate(group):
            if i in merged_indices:
                continue
            cluster = [post]
            for j in range(i + 1, len(group)):
                if j in merged_indices:
                    continue
                gap = (_parse_utc(group[j]["date_utc"]) - _parse_utc(post["date_utc"])).total_seconds()
                if gap > _FUZZY_WINDOW_SECONDS:
                    break  # group is time-sorted; no later post can be closer
                if _bodies_similar(post, group[j]):
                    cluster.append(group[j])
                    merged_indices.add(j)
                # else: within the time window but substantially different
                # content -- a genuinely distinct post (e.g. a fast reply
                # exchange), not a same-post-two-paths duplicate. Keep
                # looking at subsequent posts rather than stopping, since
                # time-sortedness doesn't guarantee similarity-sortedness.
            clusters.append(cluster)
        for cluster in clusters:
            result.append(_merge_group(cluster, "fuzzy author+subject+time") if len(cluster) > 1 else cluster[0])

    return result
