"""Thread resolution (ADR-0005's two-pass algorithm).

Only non-digest posts ever carry a real RFC Message-ID/In-Reply-To/
References -- digest-derived posts (the majority of content once digests are
expanded) only ever have a Yahoo permalink id, never email headers. Header-
based threading can therefore only ever link a non-digest post to another
non-digest post; everything else falls to subject-normalized chronological
chaining. This is an intrinsic property of the source, not a gap to close
(see ADR-0005).

Expects each post dict to carry transient `_message_id`, `_in_reply_to`, and
`_references` keys (populated by the ETL orchestrator for non-digest posts
only, from the raw mbox headers) -- these are not part of the canonical
schema and must be stripped by the caller before writing data/posts.json.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# data-structures.md §4.2's hand-extracted reference figures from the Mork
# cache -- a development-time sanity signal only (ADR-0001/data-structures.md
# §4.3 both rule out writing a live Mork parser), not a build-time dependency
# or a hard pass/fail gate.
_MORK_REFERENCE_THREAD_COUNT = 472
_MORK_REFERENCE_SINGLETON_COUNT = 580


def resolve_threads(posts: list[dict]) -> None:
    """Mutate each post dict in place, setting thread_id/parent_id/reply_ids."""
    by_message_id = {
        p["_message_id"]: p["id"] for p in posts if p.get("_message_id")
    }

    # Pass 1: header-based resolution.
    for post in posts:
        post["parent_id"] = None
        candidates = []
        if post.get("_in_reply_to"):
            candidates.append(post["_in_reply_to"])
        if post.get("_references"):
            # References can list multiple ancestors; the immediate parent
            # is conventionally the last one.
            candidates.extend(post["_references"])
        for candidate in reversed(candidates):
            parent_id = by_message_id.get(candidate)
            if parent_id and parent_id != post["id"]:
                post["parent_id"] = parent_id
                break

    # Pass 2: subject-normalized chronological chaining, for everything
    # pass 1 didn't resolve (this covers essentially all digest-derived
    # posts, plus any non-digest post whose header target wasn't found).
    unresolved = [p for p in posts if p["parent_id"] is None]
    by_subject: dict[str, list[dict]] = {}
    for post in unresolved:
        by_subject.setdefault(post["subject_normalized"], []).append(post)

    for subject, group in by_subject.items():
        if len(group) < 2:
            continue
        group.sort(key=lambda p: p["date_utc"])
        for earlier, later in zip(group, group[1:]):
            later["parent_id"] = earlier["id"]

    # Assemble thread_id (root's id) and reply_ids from the now-complete
    # parent_id graph.
    by_id = {p["id"]: p for p in posts}
    for post in posts:
        post["reply_ids"] = []
    for post in posts:
        if post["parent_id"]:
            by_id[post["parent_id"]]["reply_ids"].append(post["id"])

    def find_root(post: dict) -> dict:
        seen = set()
        current = post
        while current["parent_id"] and current["id"] not in seen:
            seen.add(current["id"])
            current = by_id[current["parent_id"]]
        return current

    for post in posts:
        post["thread_id"] = find_root(post)["id"]


def sanity_check_against_mork(posts: list[dict]) -> None:
    """Log-only comparison against data-structures.md §4.2's Mork-derived
    figures. Never raises -- a deviation is a development-time signal to
    look into, not a build failure (data-structures.md never claimed exact
    reproducibility, only a sanity check)."""
    thread_ids = {p["thread_id"] for p in posts}
    thread_sizes: dict[str, int] = {}
    for p in posts:
        thread_sizes[p["thread_id"]] = thread_sizes.get(p["thread_id"], 0) + 1
    singleton_count = sum(1 for size in thread_sizes.values() if size == 1)

    logger.info(
        "thread sanity check: computed %d threads (%d singletons) vs "
        "Mork reference %d threads (%d singletons)",
        len(thread_ids),
        singleton_count,
        _MORK_REFERENCE_THREAD_COUNT,
        _MORK_REFERENCE_SINGLETON_COUNT,
    )
