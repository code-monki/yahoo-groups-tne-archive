#!/usr/bin/env python3
"""Data-integrity checks (test-plan.md §4, TC-DATA-*), run against the
committed data/posts.json directly -- gates `make build` in CI, since a
data-integrity failure should stop the pipeline before it wastes time
building a site on bad data (test-plan.md §4's own framing).

TC-DATA-01, 05, 07 require hand/manual sampling against source HTML and
are not re-automated here (they were performed during Phase 2 development
against the real archive -- see the dedupe/digest_parser docstrings and
docs/defect-log.md for what that sampling found). This script covers every
TC-DATA-* case that's actually mechanical.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
POSTS_PATH = REPO_ROOT / "data" / "posts.json"
FILES_PATH = REPO_ROOT / "data" / "files.json"

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_ISO_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    global _failed
    _failed = True


_failed = False


def main() -> int:
    posts = json.loads(POSTS_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(posts)} posts from {POSTS_PATH}")

    # TC-DATA-02 (DR-2, FR-4): zero duplicate ids.
    ids = [p["id"] for p in posts]
    dupes = len(ids) - len(set(ids))
    if dupes:
        fail(f"TC-DATA-02: {dupes} duplicate post ids")
    else:
        print("PASS: TC-DATA-02 (0 duplicate ids)")

    # TC-DATA-03 (DR-3): 100% valid date_utc, 100% non-empty date_original.
    bad_dates = [p["id"] for p in posts if not _ISO_UTC_RE.match(p.get("date_utc") or "")]
    empty_original = [p["id"] for p in posts if not (p.get("date_original") or "").strip()]
    if bad_dates:
        fail(f"TC-DATA-03: {len(bad_dates)} posts with invalid date_utc, e.g. {bad_dates[:3]}")
    elif empty_original:
        fail(f"TC-DATA-03: {len(empty_original)} posts with empty date_original, e.g. {empty_original[:3]}")
    else:
        print("PASS: TC-DATA-03 (100% valid date_utc, 100% non-empty date_original)")

    # TC-DATA-04 (DR-4, FR-4): zero email-address-shaped substrings anywhere
    # in the canonical JSON.
    full_text = json.dumps(posts, ensure_ascii=False)
    email_matches = _EMAIL_RE.findall(full_text)
    if email_matches:
        fail(f"TC-DATA-04: {len(email_matches)} email-shaped substrings found, e.g. {email_matches[:3]}")
    else:
        print("PASS: TC-DATA-04 (0 email addresses)")

    # TC-DATA-07 (DR-7): thread/singleton counts within reasonable range of
    # the Mork-derived reference (472 threads / 580 singletons) -- a sanity
    # signal per data-structures.md, not an exact-match gate. Logged, not
    # failed, since the two figures were never expected to match exactly
    # (Mork counts raw messages including ones this pipeline correctly
    # excludes/merges -- see thread.py's sanity_check_against_mork).
    thread_ids = set(p["thread_id"] for p in posts)
    from collections import Counter

    counts = Counter(p["thread_id"] for p in posts)
    singletons = sum(1 for c in counts.values() if c == 1)
    print(
        f"INFO: TC-DATA-07: computed {len(thread_ids)} threads ({singletons} singletons) "
        f"vs Mork reference 472 threads (580 singletons) -- see thread.py's own "
        f"sanity_check_against_mork log output for the accepted-deviation rationale"
    )

    # Empty-body check (not a named TC- case on its own, but the standing
    # invariant every ETL change in this project has been validated
    # against -- see docs/defect-log.md #7/#8).
    empty_bodies = [p["id"] for p in posts if not (p.get("body_text") or "").strip()]
    if empty_bodies:
        fail(f"0 empty bodies invariant: {len(empty_bodies)} posts with empty body_text, e.g. {empty_bodies[:3]}")
    else:
        print("PASS: 0 posts with empty body_text")

    # TC-DATA-09 (DR-9): the Files-section manifest is subject to the same
    # no-email rule as the post dataset (ADR-0018).
    files = json.loads(FILES_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(files)} files-manifest entries from {FILES_PATH}")
    files_text = json.dumps(files, ensure_ascii=False)
    files_email_matches = _EMAIL_RE.findall(files_text)
    if files_email_matches:
        fail(f"TC-DATA-09: {len(files_email_matches)} email-shaped substrings found in files.json, e.g. {files_email_matches[:3]}")
    else:
        print("PASS: TC-DATA-09 (0 email addresses in files.json)")

    if _failed:
        print("\nDATA INTEGRITY: FAILED")
        return 1
    print("\nDATA INTEGRITY: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
