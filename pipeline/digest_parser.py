"""Extract individual posts embedded in Yahoo Groups digest emails.

Real-data finding (see docs/dd.md §4, docs/adr/0005 area, and the Phase 2
implementation notes): digest HTML is not one template but at least three
structural variants across 2008-2018 -- a "classic" <dl>/<dd> layout using
/message/<id> links, a "topics" redesign using semantic <h2>/<h3>/<h4> tags
and /conversations/topics/<id> links, and a fully inline-style div-based
layout that still uses /message/<id> links. Rather than maintain a brittle
parser per era (more variants may exist that weren't in the sample), this
module extracts by pattern rather than by fixed structure: every variant
consistently marks a real post's start with a permalink-bearing <a> followed
shortly by the literal text "Posted by:" -- generic table-of-contents/reply
backlinks that share the same href pattern do NOT have that marker nearby,
which is what distinguishes a genuine post entry from an incidental link.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

# Tried in order; the first pattern to match a given href wins.
_PERMALINK_PATTERNS = (
    re.compile(r"/message/(\d+)"),
    re.compile(r"/conversations/topics/(\d+)"),
    re.compile(r"[?&]msgId=(\d+)"),
)

# Any of these appearing marks the start of the digest's boilerplate
# footer (sponsor block, "Visit Your Group", unsubscribe links, etc.) --
# text a post-start anchor should never be found after.
_FOOTER_MARKERS = (
    "ygrp-vital",
    "ygrp-sponsor",
    "Visit Your Group",
)

# How far past a candidate permalink anchor to look for "Posted by:"
# before concluding it's not a genuine post-start (just a backlink). Distance
# alone isn't a reliable discriminator -- it varies by template era (as low
# as ~20 chars in the classic layout, ~450 in the div-based one) enough that
# no single threshold cleanly separates real posts from every era's nav
# links, so this window is intentionally generous; _NAV_LINK_TEXT below is
# the real filter.
_POSTED_BY_WINDOW = 700

# Every template era's per-post action bar links back to the same permalink
# with generic anchor text like this -- these must never be mistaken for a
# genuine post-start even though they match the permalink pattern and do
# have a "Posted by:" somewhere within the window above.
_NAV_LINK_TEXT_RE = re.compile(
    r"^(all messages|messages in this topic|reply|reply via web post|"
    r"view all topics|create new topic|individual email|forward)\b",
    re.IGNORECASE,
)

# Confirmed against the real archive (digest record 259, permalink 6835): a
# reply can quote an *entire* previous post inline, verbatim -- including
# that post's own permalink anchor and "Posted by:" line -- which otherwise
# passes every check above (real permalink href, non-empty non-nav anchor
# text, a genuine "Posted by:" within the window) and gets misread as a
# second, phantom post-start. The tell: its "subject" is the anchor's own
# raw link text, i.e. the URL itself -- a real digest subject is never
# literally a hyperlink.
_URL_LIKE_SUBJECT_RE = re.compile(r"^https?://")

# How far past "Posted by:" the author's name/handle/email can appear.
# Generous enough to cover every sampled era's markup overhead, but bounded
# so the search can't wander into the post body and pick up a mailto link
# someone else is quoted at deep in a reply.
_AUTHOR_ZONE_WINDOW = 600

_QUOTED_NAME_RE = re.compile(r'"([^"]+)"\s*(\S*)')


def _parse_name_and_handle(text: str) -> tuple[str, str | None]:
    """Split a 'Posted by:' text blob into (display_name, inline_handle | None).

    Two shapes are seen across template eras: a quoted display name followed
    by a bare trailing handle token (`"Jeff Dougherty" as18cdr`), or no
    quotes at all -- either a bare handle ("ret7army", for an account with no
    display name set) or, in the classic template's fallback case, the raw
    email address itself. Either way this function only splits; it never
    scrubs -- email addresses are left intact here and removed downstream in
    normalize.py's scrub_email_addresses(), which is the single place ADR-0008
    PII removal happens, deliberately not duplicated in the parser.
    """
    text = text.strip()
    m = _QUOTED_NAME_RE.match(text)
    if m:
        name = m.group(1).strip()
        handle = m.group(2).strip() or None
        return name, handle
    return text, None

_POSTED_BY_RE = re.compile(r"Posted by:", re.IGNORECASE)
_ANCHOR_RE = re.compile(r'<a\b[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
_MAILTO_RE = re.compile(r'<a\b[^>]*href="mailto:([^"?]*)[^"]*"[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
_PROFILE_RE = re.compile(r'<a\b[^>]*href="[^"]*profiles\.yahoo\.com/([^"?]+)[^"]*"', re.IGNORECASE)


def _strip_tags(html_fragment: str) -> str:
    return BeautifulSoup(html_fragment, "lxml").get_text(separator=" ", strip=True)


def _strip_header(segment_html: str, date_original: str) -> str:
    """Remove the subject/author/date header from a captured segment,
    returning the remaining body markup as a well-formed HTML string.

    Works at the DOM level (find the top-level node containing the date
    text, keep only nodes after it) rather than by string-slicing raw HTML,
    which is what left dangling unmatched tags at the front of the fragment
    in an earlier version of this function.
    """
    soup = BeautifulSoup(segment_html, "lxml")
    root = soup.body or soup
    top_level_nodes = list(root.contents)

    # Match against the *stripped* date text, since date_original was itself
    # produced by _strip_tags() and won't contain the raw &nbsp;/markup the
    # unparsed segment does.
    marker = date_original if date_original else "Posted by:"
    node_texts = [
        (node.get_text(" ", strip=True) if hasattr(node, "get_text") else str(node))
        for node in top_level_nodes
    ]
    cut_after = None
    for i, t in enumerate(node_texts):
        if marker and marker in t:
            cut_after = i
            break

    if cut_after is None:
        # No recognizable header marker found -- nothing to strip.
        return segment_html

    for node in top_level_nodes[: cut_after + 1]:
        if hasattr(node, "decompose"):
            node.decompose()
        else:
            node.extract()

    return "".join(str(c) for c in root.contents).strip()


@dataclass
class DigestPost:
    permalink_id: str
    subject: str
    author_display_name: str
    author_profile_handle: str | None
    date_original: str
    body_html: str


def _extract_permalink_id(href: str) -> str | None:
    for pattern in _PERMALINK_PATTERNS:
        m = pattern.search(href)
        if m:
            return m.group(1)
    return None


def _footer_start(html: str) -> int:
    """Character offset of the earliest boilerplate-footer marker, or len(html) if none.

    Every digest opens with one or more <style> blocks (some digests have
    two <head>/<style> pairs back to back -- a malformed but consistent
    artifact of Yahoo's template merging) that *define* CSS rules for
    #ygrp-sponsor/#ygrp-vital -- those definitions match the marker text too,
    long before any real footer content, so the search has to start after
    the *last* stylesheet, not just the first, or a second style block would
    still be mistaken for the real footer.
    """
    search_from = html.rfind("</style>")
    search_from = search_from + len("</style>") if search_from != -1 else 0
    positions = [html.find(marker, search_from) for marker in _FOOTER_MARKERS]
    positions = [p for p in positions if p != -1]
    return min(positions) if positions else len(html)


def extract_digest_posts(html: str) -> list[DigestPost]:
    """Parse a digest email's HTML body into its constituent posts.

    Only considers content before the first boilerplate-footer marker, so
    the digest's own footer/sponsor block never gets misread as a post.
    """
    limit = _footer_start(html)
    candidates: list[tuple[int, str, str]] = []  # (offset, href, inner_html)
    for m in _ANCHOR_RE.finditer(html, 0, limit):
        href, inner_html = m.group(1), m.group(2)
        permalink_id = _extract_permalink_id(href)
        if permalink_id is None:
            continue
        # Genuine post-start anchors carry real subject text; nav/pagination
        # links matching the same href pattern (e.g. "View All Topics") don't.
        subject_text = _strip_tags(inner_html)
        if not subject_text or _NAV_LINK_TEXT_RE.match(subject_text):
            continue
        if _URL_LIKE_SUBJECT_RE.match(subject_text):
            continue
        window = html[m.end():m.end() + _POSTED_BY_WINDOW]
        if not _POSTED_BY_RE.search(window):
            continue
        candidates.append((m.start(), permalink_id, subject_text))

    posts: dict[str, DigestPost] = {}
    for i, (offset, permalink_id, subject_text) in enumerate(candidates):
        segment_end = candidates[i + 1][0] if i + 1 < len(candidates) else limit
        segment = html[offset:segment_end]

        posted_by_pos = _POSTED_BY_RE.search(segment)
        after_posted_by = segment[posted_by_pos.end():] if posted_by_pos else ""
        # The author's name/handle/email always appear within a short window
        # of "Posted by:" -- bounding this search matters because `segment`
        # also contains the full post body, which may itself quote someone
        # else's mailto link deep in a reply; an unbounded search risks
        # picking that up instead of the actual author's.
        author_zone = after_posted_by[:_AUTHOR_ZONE_WINDOW]

        mailto_match = _MAILTO_RE.search(author_zone)
        if mailto_match:
            # Classic template: the real display name is plain text *before*
            # the mailto link, whose own visible text is just the email
            # address again ("DED" <a href="mailto:...">dedly@snet.net</a>).
            # Modern templates: name (and sometimes a trailing handle) live
            # *inside* the link's own text instead, with nothing meaningful
            # before it. Try the former first, fall back to the latter.
            pre_mailto_text = _strip_tags(author_zone[:mailto_match.start()])
            mailto_inner_text = _strip_tags(mailto_match.group(2))
            # Confirmed against the real archive: a handful of "modern
            # topics" template entries have a genuinely empty name span
            # inside the mailto link (Yahoo's own rendering, not our
            # extraction) with no plain text before it either -- e.g. seven
            # of the archive's most prolific poster's own digest-derived
            # posts, which would otherwise silently fork into a second,
            # blank-named "author" distinct from their ~470 other posts.
            # The mailto address's local part is the same fallback display
            # name Yahoo itself uses elsewhere in this archive when no
            # display name was set, so it's a consistent choice here too.
            email_local_part = mailto_match.group(1).split("@", 1)[0]
            candidate_text = pre_mailto_text or mailto_inner_text or email_local_part
        else:
            candidate_text = _strip_tags(author_zone.split("<h4", 1)[0])

        author_display_name, inline_handle = _parse_name_and_handle(candidate_text)

        profile_match = _PROFILE_RE.search(author_zone)
        author_profile_handle = profile_match.group(1).strip() if profile_match else inline_handle

        # The date's position relative to "Posted by:" varies by era: the
        # classic template has it *after* (in a separate <h4> following the
        # author), the div-based "modern" template has it *before*
        # (". Posted by:" is literally the tail of the date's own sentence).
        # Search a zone spanning both sides, bounded the same way as the
        # author zone and for the same reason: an unbounded search risks
        # matching a date-like string quoted deep in the post's own body,
        # e.g. someone else's attribution line in a reply.
        date_zone_start = max(0, (posted_by_pos.start() if posted_by_pos else 0) - _AUTHOR_ZONE_WINDOW)
        date_zone_end = (posted_by_pos.end() if posted_by_pos else 0) + _AUTHOR_ZONE_WINDOW
        date_zone = segment[date_zone_start:date_zone_end]
        date_match = re.search(
            r"(Sun|Mon|Tue|Wed|Thu|Fri|Sat)[a-z]*[,\s]+[A-Z][a-z]{2,8}&?n?b?s?p?;?\s*\d{1,2},?&?n?b?s?p?;?\s*\d{4}"
            r"[^()]{0,40}\([A-Z]{2,4}\)",
            date_zone,
        )
        date_original = _strip_tags(date_match.group(0)) if date_match else ""

        # Header (subject/author/date markup) is stripped at the DOM level,
        # not via string slicing -- slicing mid-markup left a dangling,
        # unmatched closing tag (e.g. a stray "</h4>" whose opening tag fell
        # before the cut point) at the front of the fragment, which lxml
        # fails to parse into anything at all. `segment` always starts from
        # a real, complete opening tag (the post-start anchor itself), so
        # parsing it whole and then removing nodes has no such problem.
        # Footer stripping (boilerplate ids/text) is normalize.sanitize_body's
        # job, applied uniformly across all source kinds, not just digests.
        body_html = _strip_header(segment, date_original)

        post = DigestPost(
            permalink_id=permalink_id,
            subject=subject_text,
            author_display_name=author_display_name,
            author_profile_handle=author_profile_handle,
            date_original=date_original,
            body_html=body_html,
        )

        # A permalink id can legitimately recur (TOC teaser + full entry, or
        # a backlink that happened to still pass the "Posted by:" check) --
        # keep whichever occurrence has the longer body, mirroring ADR-0010's
        # dedup tie-break at digest-internal granularity.
        existing = posts.get(permalink_id)
        if existing is None or len(body_html) > len(existing.body_html):
            posts[permalink_id] = post

    return list(posts.values())
