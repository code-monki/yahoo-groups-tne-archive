"""Attachment extraction (DR-8, ADR-0006).

Populates only `filename` + `source` on each post -- never `available`,
which is computed at Eleventy build time from the attachments/ directory
(dd.md §6/§7.1), not stored in the committed dataset (see hld.md §3's
corrected example and the Phase 2 plan's doc-correction #1).

`source: "mime_embedded"` has a clean, fully automatable detection rule
(a non-text MIME part). `source: "files_section_reference"` does not --
nothing in the mbox structurally marks "this post references Yahoo Groups'
separate Files/Photos section" (data-structures.md §5). That's handled here
as a candidate-flagging pass for manual review, not an automatic
classification, and is logged rather than silently guessed at.
"""

from __future__ import annotations

import logging
import mailbox
import re

logger = logging.getLogger(__name__)


def extract_mime_attachments(msg: mailbox.mboxMessage) -> list[dict]:
    attachments = []
    if not msg.is_multipart():
        return attachments
    for part in msg.walk():
        content_type = part.get_content_type()
        if content_type in ("text/plain", "text/html", "multipart/mixed", "multipart/alternative"):
            continue
        filename = part.get_filename()
        if not filename:
            continue
        attachments.append({"filename": filename, "source": "mime_embedded"})
    return attachments


# data-structures.md §5: 6 messages found with subjects/bodies referencing
# Yahoo Groups' separate Files/Photos section notifications. This keyword
# search is deliberately over-inclusive (a candidate list for a human to
# review, not an automatic attachment assignment) since there's no reliable
# way to derive the actual referenced filename from these words alone.
_FILES_SECTION_KEYWORD_RE = re.compile(
    r"\b(uploaded|new file|download your files|files section|photos? section)\b",
    re.IGNORECASE,
)


def find_files_section_candidates(posts: list[dict]) -> list[str]:
    """Return post ids whose subject/body suggest a Files/Photos-section
    reference, for manual review -- not auto-populated as an attachment."""
    candidates = []
    for post in posts:
        haystack = f"{post['subject']} {post['body_text']}"
        if _FILES_SECTION_KEYWORD_RE.search(haystack):
            candidates.append(post["id"])
    if candidates:
        logger.info(
            "found %d posts possibly referencing Yahoo Groups' Files/Photos "
            "section (manual review needed to confirm and name the actual "
            "file, if recoverable): %s",
            len(candidates),
            candidates,
        )
    return candidates
