#!/usr/bin/env python3
"""ETL CLI entrypoint (`make data`). Orchestrates parse_mbox -> digest_parser
-> normalize -> ids -> dedupe -> thread -> attachments, writing
data/posts.json. See docs/dd.md §4 for the module breakdown this implements.
"""

from __future__ import annotations

import html
import json
import logging
import re
import sys
from email.utils import getaddresses
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import attachments as attachments_mod
import dedupe as dedupe_mod
import digest_parser
import ids as ids_mod
import normalize
import parse_mbox
import thread as thread_mod

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("etl")

REPO_ROOT = Path(__file__).parent.parent
MBOX_PATH = REPO_ROOT / "mail_archives" / "YahooArchive"
OUTPUT_PATH = REPO_ROOT / "data" / "posts.json"
FILES_OUTPUT_PATH = REPO_ROOT / "data" / "files.json"

# messageNum=<id> (from the ygrp-actbar "Reply" link's query string) is
# THIS message's own id. The more obvious-looking groups.yahoo.com/.../
# message/<id> path in the same action bar is deceptive for a reply --
# that's the "Messages in this topic" link, which points to the *topic
# root*, not the current message. Confirmed against the real archive: a
# whole 10-message reply chain (mbox indices 80-89) all resolved to the
# thread root's id "5313" under the old path-only extraction, because
# every reply's own actbar still carries that "Messages in this topic"
# link back to the root. messageNum= is tried first for exactly that
# reason; the path form remains as a fallback for pages that lack it.
_MESSAGE_NUM_RE = re.compile(r'messageNum=(\d+)')
_YAHOO_URL_RE = re.compile(r'groups\.yahoo\.com/group/Traveller_TNE/message/(\d+)')


def _build_post(
    *,
    permalink_id: str | None,
    source_kind: str,
    source_mbox_index: int,
    subject: str,
    author_display_name_raw: str,
    author_profile_handle: str | None,
    date_original: str,
    body_html_raw: str,
    yahoo_url: str | None,
    attachments: list[dict],
    message_id: str | None = None,
    in_reply_to: str | None = None,
    references: list[str] | None = None,
) -> dict:
    date_utc, date_original_verbatim = normalize.parse_date(date_original, source_kind)
    subject_normalized = normalize.normalize_subject(subject)
    body_html, body_text = normalize.sanitize_body(body_html_raw)
    body_html = normalize.scrub_email_addresses(body_html)
    body_text = normalize.scrub_email_addresses(body_text)
    body_html = normalize.reflow_original_message_header(body_html, is_html=True)
    body_text = normalize.reflow_original_message_header(body_text, is_html=False)
    author_display_name = normalize.scrub_author_display_name(author_display_name_raw)

    if permalink_id:
        post_id = permalink_id
        id_type = "yahoo_permalink"
    else:
        post_id = ids_mod.synthetic_id(
            message_id, subject_normalized, author_display_name, date_utc
        )
        id_type = "synthetic_uuid"

    return {
        "id": post_id,
        "id_type": id_type,
        "source_kind": source_kind,
        "source_mbox_index": source_mbox_index,
        "subject": subject,
        "subject_normalized": subject_normalized,
        "author": {
            "display_name": author_display_name,
            "profile_handle": author_profile_handle,
            "slug": None,  # filled in by resolve_author_slugs() dataset-wide pass
        },
        "date_utc": date_utc,
        "date_original": date_original_verbatim,
        "body_html": body_html,
        "body_text": body_text,
        "thread_id": None,  # filled in by thread.resolve_threads()
        "parent_id": None,
        "reply_ids": [],
        "attachments": attachments,
        "yahoo_url": yahoo_url,
        "_message_id": message_id,
        "_in_reply_to": in_reply_to,
        "_references": references or [],
    }


def _plain_text_to_html(text: str) -> str:
    """Wrap a plain-text email body as one <p> per paragraph (blank-line
    separated), HTML-escaped.

    Confirmed against the real archive: a single flat `<p>` around the
    entire message left normalize.py's boilerplate-marker truncation with
    no node-level boundary to cut at once a marker (e.g. "Yahoo! Groups
    Links") was added that -- for a plain-text email -- sits in the same
    lone text node as the real message. Truncation then removed the whole
    node, discarding real content along with the footer (5/4060 posts).
    Paragraph-level <p> tags give it a real boundary to cut at instead.
    Escaping is also new here: previously raw plain text was interpolated
    directly into HTML unescaped, so a literal "<" or "&" in someone's
    message could be misread as markup.
    """
    paragraphs = re.split(r"\r?\n\s*\r?\n", (text or "").strip())
    return "".join(
        f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>" for p in paragraphs if p.strip()
    )


def _extract_non_digest_post(record: parse_mbox.RawRecord) -> dict:
    msg = record.message
    text_plain, text_html = parse_mbox.extract_body_parts(msg)
    body_html_raw = text_html if text_html else _plain_text_to_html(text_plain)

    message_num_match = _MESSAGE_NUM_RE.search(body_html_raw) if text_html else None
    yahoo_url_match = _YAHOO_URL_RE.search(body_html_raw) if text_html else None
    if message_num_match:
        permalink_id = message_num_match.group(1)
        yahoo_url = f"http://groups.yahoo.com/group/Traveller_TNE/message/{permalink_id}"
    elif yahoo_url_match:
        permalink_id = yahoo_url_match.group(1)
        yahoo_url = yahoo_url_match.group(0)
    else:
        permalink_id = None
        yahoo_url = None

    display_name_raw = ""
    author_email = ""
    addresses = getaddresses([msg.get("From", "")])
    if addresses:
        display_name_raw, author_email = addresses[0]
    if not display_name_raw:
        display_name_raw = author_email

    references_header = msg.get("References") or ""
    references = references_header.split() if references_header else []

    return _build_post(
        permalink_id=permalink_id,
        source_kind=record.source_kind,
        source_mbox_index=record.index,
        subject=record.subject,
        author_display_name_raw=display_name_raw,
        author_profile_handle=None,
        date_original=msg.get("Date") or "",
        body_html_raw=body_html_raw,
        yahoo_url=yahoo_url,
        attachments=attachments_mod.extract_mime_attachments(msg),
        message_id=msg.get("Message-ID"),
        in_reply_to=msg.get("In-Reply-To"),
        references=references,
    )


def _extract_digest_posts(record: parse_mbox.RawRecord) -> list[dict]:
    msg = record.message
    _, text_html = parse_mbox.extract_body_parts(msg)
    if not text_html:
        return []
    raw_posts = digest_parser.extract_digest_posts(text_html)
    built = []
    for raw in raw_posts:
        built.append(
            _build_post(
                permalink_id=raw.permalink_id,
                source_kind="digest",
                source_mbox_index=record.index,
                subject=raw.subject,
                author_display_name_raw=raw.author_display_name,
                author_profile_handle=raw.author_profile_handle,
                date_original=raw.date_original,
                body_html_raw=raw.body_html,
                yahoo_url=f"http://groups.yahoo.com/group/Traveller_TNE/message/{raw.permalink_id}",
                attachments=[],  # digests never carry the actual attachment binary
            )
        )
    return built


def run(mbox_path: Path = MBOX_PATH, output_path: Path = OUTPUT_PATH) -> list[dict]:
    logger.info("loading records from %s", mbox_path)
    records = parse_mbox.load_records(str(mbox_path))
    logger.info("loaded %d records", len(records))

    all_posts: list[dict] = []
    parse_errors = 0
    for record in records:
        try:
            if record.source_kind == "digest":
                all_posts.extend(_extract_digest_posts(record))
            else:
                all_posts.append(_extract_non_digest_post(record))
        except Exception:
            parse_errors += 1
            logger.exception(
                "failed to extract record index=%d subject=%r", record.index, record.subject
            )
    logger.info("extracted %d raw posts (%d record-level errors)", len(all_posts), parse_errors)

    all_posts = dedupe_mod.dedupe(all_posts)
    logger.info("%d posts after dedup", len(all_posts))

    slugs = ids_mod.resolve_author_slugs(all_posts)
    for post in all_posts:
        post["author"]["slug"] = slugs[post["author"]["display_name"]]

    thread_mod.resolve_threads(all_posts)
    thread_mod.sanity_check_against_mork(all_posts)

    attachments_mod.find_files_section_candidates(all_posts)

    # ADR-0018: the Files section (a shared group repository, distinct from
    # per-post MIME attachments) has its own manifest, derived from Yahoo's
    # own upload-notification emails -- computed here, before the post
    # records below have their private threading fields stripped, though it
    # only actually needs id/subject/source_kind/body_text/date_utc.
    files_manifest = attachments_mod.extract_file_upload_notifications(all_posts)
    files_manifest.sort(key=lambda f: f["uploaded_date_utc"])

    for post in all_posts:
        del post["_message_id"], post["_in_reply_to"], post["_references"]

    all_posts.sort(key=lambda p: p["date_utc"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(all_posts, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("wrote %d posts to %s", len(all_posts), output_path)

    FILES_OUTPUT_PATH.write_text(
        json.dumps(files_manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("wrote %d files-section entries to %s", len(files_manifest), FILES_OUTPUT_PATH)

    return all_posts


if __name__ == "__main__":
    run()
