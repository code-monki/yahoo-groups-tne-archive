"""Synthetic post IDs (ADR-0009) and author slug resolution (dd.md §7.3)."""

from __future__ import annotations

import re
import uuid

# Fixed once, never changes (ADR-0009) -- part of what a UUID v5 needs, not
# a secret; any stable UUID works as long as it's never altered afterward.
NAMESPACE_UUID = uuid.UUID("6f1b4d3c-6b3e-4e8a-9a8b-6d2f1e3c9a7d")


def synthetic_id(
    message_id: str | None,
    subject_normalized: str,
    author_display_name: str,
    date_utc: str,
) -> str:
    """Deterministic UUID v5 for a post with no Yahoo permalink ID.

    Re-running the ETL from a clean checkout always regenerates the same ID
    for the same source record (the source is frozen, ADR-0001), so nothing
    needs to be persisted across runs to keep permalinks stable.
    """
    if message_id:
        name = message_id
    else:
        name = f"{subject_normalized}|{author_display_name}|{date_utc}"
    return str(uuid.uuid5(NAMESPACE_UUID, name))


_SLUG_INVALID_RE = re.compile(r"[^a-z0-9]+")

# A display name is normally a handful of words; this is defense-in-depth
# against extraction failures upstream (e.g. digest_parser.py misreading a
# quoted post's body as an author name, confirmed against the real archive
# on permalink 6835) producing a several-hundred-character slug that breaks
# the filesystem (ENAMETOOLONG on some OSes) -- capped well above any
# plausible real name/handle, not a length any legitimate value should hit.
_SLUG_MAX_LEN = 80


def _slugify(text: str) -> str:
    slug = _SLUG_INVALID_RE.sub("-", text.lower()).strip("-")
    slug = slug[:_SLUG_MAX_LEN].strip("-")
    return slug or "unknown"


def resolve_author_slugs(posts: list[dict]) -> dict[str, str]:
    """Map each unique author display_name to a stable slug.

    Must run as a single dataset-wide pass after all posts exist -- the
    collision rule (append the lowest post id in the colliding group) needs
    to see every author at once, not decide slugs per-record inline as posts
    are processed one at a time.
    """
    posts_by_author: dict[str, list[str]] = {}
    for post in posts:
        name = post["author"]["display_name"]
        posts_by_author.setdefault(name, []).append(post["id"])

    base_slug_to_names: dict[str, list[str]] = {}
    for name in posts_by_author:
        base_slug_to_names.setdefault(_slugify(name), []).append(name)

    slugs: dict[str, str] = {}
    for base_slug, names in base_slug_to_names.items():
        if len(names) == 1:
            slugs[names[0]] = base_slug
            continue
        # Collision: disambiguate by the lowest post id each name's posts
        # include, sorted lexically -- deterministic and stable across
        # rebuilds, unlike an iteration-order-based counter would be.
        names_with_min_id = sorted(
            (min(posts_by_author[name]), name) for name in names
        )
        for min_id, name in names_with_min_id:
            slugs[name] = f"{base_slug}-{min_id}"

    return slugs
