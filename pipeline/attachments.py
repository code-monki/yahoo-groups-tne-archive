"""Attachment extraction (DR-8, ADR-0006), and separately, the group-level
Files section manifest (added post-launch per real user feedback -- FR-23/
26/27 and this module's original design only ever covered per-post MIME
attachments, not Yahoo Groups' separate shared Files repository, which is a
genuinely distinct thing: files uploaded directly to the group rather than
attached to an individual email).

Populates only `filename` + `source` on each post -- never `available`,
which is computed at Eleventy build time from the attachments/ directory
(dd.md §6/§7.1), not stored in the committed dataset (see hld.md §3's
corrected example and the Phase 2 plan's doc-correction #1).

`source: "mime_embedded"` has a clean, fully automatable detection rule
(a non-text MIME part). `source: "files_section_reference"` does not --
nothing in the mbox structurally marks "this post references Yahoo Groups'
separate Files/Photos section" (data-structures.md §5) *in general*. That's
handled here as a candidate-flagging pass for manual review, not an
automatic classification, and is logged rather than silently guessed at.

One specific, common case of that general problem *does* have a fully
automatable extraction, discovered later than the rest of this module:
Yahoo's own "New file uploaded to Traveller_TNE" notification emails,
auto-sent to the whole group on every upload, carry the filename/uploader/
description in a fixed, structured format -- see
extract_file_upload_notifications() below. This covers a real subset of
files-section activity, not all of it (someone discussing a file inline in
a reply, with no notification captured in this archive, still needs manual
review via find_files_section_candidates()).
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


# Yahoo's own auto-notification, sent to the whole group on every Files-
# section upload -- a fixed template, structured enough to extract cleanly:
#   Hello, This email message is a notification to let you know that
#   a file has been uploaded to the Files area of the Traveller_TNE
#   group.
#   File        : /ConsolidatedTNEErr
#   ata.pdf
#   Uploaded by : donm61873 <>
#   Description : Consolidated TNE Errata (v0.02) draft
#   You can access this file at the URL:
#   ...
# Values wrap mid-word at the same fixed text-wrap column as everything
# else in this archive (see normalize.py's email/header-reflow fixes) --
# confirmed against the real archive, "ConsolidatedTNEErr\nata.pdf". The
# filename field is dewrapped by removing the break entirely (mid-word,
# no real whitespace at the break in every sampled case); the description
# field is dewrapped by replacing the break with a space (ordinary wrapped
# prose, where the break *does* represent a real word boundary).
_FILE_NOTIFICATION_RE = re.compile(
    r"File\s*:\s*/(?P<filename>.+?)\s*\n"
    r"Uploaded by\s*:\s*(?P<uploader>\S+).*?\n"
    r"Description\s*:\s*(?P<description>.*?)\s*\n"
    r"You can access this file at the URL",
    re.DOTALL,
)


def extract_file_upload_notifications(posts: list[dict]) -> list[dict]:
    """Return a manifest of Files-section uploads, derived from Yahoo's own
    per-upload notification emails -- filename, uploader, description, and
    the notification post's own date_utc/id (the upload's date and its
    source record, for traceability back to data/posts.json).

    Only ever adds a manifest entry when the fixed template above actually
    matches; never guesses. A file uploaded without a captured notification
    (or referenced only in a reply, discussed but not itself the upload
    notification) is not represented here -- see
    find_files_section_candidates() for that broader, human-reviewed set.
    """
    manifest = []
    for post in posts:
        if post["source_kind"] != "digest":
            continue
        # A reply to the notification ("Re: New file uploaded...") often
        # quotes the entire original notification inline (the same "whole
        # previous message quoted verbatim" pattern seen elsewhere in this
        # archive) -- confirmed against the real archive: post 6542, a
        # reply, matches this template just as cleanly as 6541, the actual
        # notification it's replying to, and would otherwise duplicate the
        # manifest entry. The genuine notification's subject is never
        # "Re:"-prefixed; only accepting those excludes the reply-quotes
        # without needing to guess based on content.
        if post["subject"].strip().lower().startswith("re:"):
            continue
        if "Files area of the" not in post["body_text"]:
            continue
        m = _FILE_NOTIFICATION_RE.search(post["body_text"])
        if not m:
            continue
        filename = re.sub(r"\s*\n\s*", "", m.group("filename")).strip()
        description = re.sub(r"\s*\n\s*", " ", m.group("description")).strip()
        manifest.append(
            {
                "filename": filename,
                "uploader": m.group("uploader").strip(),
                "description": description,
                "uploaded_date_utc": post["date_utc"],
                "source_post_id": post["id"],
            }
        )
    logger.info(
        "extracted %d Files-section upload notifications into the manifest",
        len(manifest),
    )
    return manifest
