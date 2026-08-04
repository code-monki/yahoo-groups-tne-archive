"""Date/subject normalization, body sanitization, and PII scrubbing (DR-3,
FR-3, ADR-0008). This is the one place email-address removal happens --
applied unconditionally to every record regardless of source kind, and to
every field that can carry one (body text *and* author display name; the
digest parser was found to sometimes surface a raw email as the "display
name" for accounts that never set one -- see digest_parser.py).
"""

from __future__ import annotations

import re
from email.utils import parsedate_to_datetime

from bs4 import Comment

from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser

# Digest dates carry only a US timezone abbreviation ("... (PST)"), not a
# numeric offset -- dateutil can't resolve those on its own, so this fixed
# map is required. "Best effort" per DR-3: exact historical DST transition
# dates aren't modeled, a fixed offset per abbreviation is close enough for
# an archive's display/sort purposes.
_TZ_OFFSETS_HOURS = {
    "PST": -8, "PDT": -7,
    "MST": -7, "MDT": -6,
    "CST": -6, "CDT": -5,
    "EST": -5, "EDT": -4,
    "GMT": 0, "UTC": 0,
}
from datetime import timezone, timedelta
_TZINFOS = {abbr: timezone(timedelta(hours=h)) for abbr, h in _TZ_OFFSETS_HOURS.items()}

_TZ_ABBR_RE = re.compile(r"\(([A-Z]{2,4})\)\s*$")


def parse_date(date_original: str, source_kind: str) -> tuple[str, str]:
    """Return (date_utc_iso, date_original_verbatim)."""
    original = date_original.strip()
    if not original:
        raise ValueError("empty date_original")

    if source_kind == "digest":
        # e.g. "Sun Nov 16, 2008 1:36 pm (PST)" (already whitespace-collapsed
        # by the caller via BeautifulSoup's get_text) -- extract the trailing
        # abbreviation explicitly since dateutil can't resolve it unassisted.
        m = _TZ_ABBR_RE.search(original)
        tzinfos = _TZINFOS
        dt = dateutil_parser.parse(original, tzinfos=tzinfos, fuzzy=True)
        if dt.tzinfo is None:
            # Abbreviation wasn't recognized -- fall back to naive-as-UTC
            # rather than raising; DR-3 asks for best-effort, not perfection.
            dt = dt.replace(tzinfo=timezone.utc)
    else:
        # Direct/relayed posts' dates come from the mbox `Date:` header --
        # standard RFC 2822 with a real numeric offset.
        dt = parsedate_to_datetime(original)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

    dt_utc = dt.astimezone(timezone.utc)
    date_utc_iso = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    return date_utc_iso, original


_SUBJECT_PREFIX_RE = re.compile(
    r"^\s*(re|fwd?)\s*:\s*|^\s*\[traveller_tne\]\s*", re.IGNORECASE
)


def normalize_subject(subject: str) -> str:
    text = subject
    # Prefixes can repeat/combine ("Re: [Traveller_TNE] Re: ...") -- strip
    # repeatedly until nothing more matches, not just once.
    while True:
        stripped = _SUBJECT_PREFIX_RE.sub("", text, count=1)
        if stripped == text:
            break
        text = stripped
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


# Yahoo Groups presentational boilerplate (data-structures.md §5): specific
# known ad/sponsor/footer container ids. NOT a broad "ygrp-*" prefix match --
# ygrp-mlmsg/ygrp-content/ygrp-text etc. are the *legitimate* post-body
# wrapper ids in the direct/relayed full-page template and must be kept;
# only the ids actually confirmed (by direct inspection) to be ad/footer
# content are decomposed here.
_BOILERPLATE_IDS = re.compile(r"^ygrp-(sponsor|vital|actbar)$")

# The full-page template's known, reliably-content-only wrapper. Preferred
# over the denylist above when present -- see sanitize_body().
_CONTENT_WRAPPER_IDS = re.compile(r"^ygrp-(text|content)$")
_BOILERPLATE_TEXT_MARKERS = (
    "For more information about this group, please visit",
    "For help with Yahoo! Groups, please visit",
    "Visit Your Group",
    "MARKETPLACE",
    "Switch to:",
    "Recent Activity",
    # Per-post action bar, trailing each digest-derived post's captured
    # segment (digest_parser.py) -- same phrases that module's
    # _NAV_LINK_TEXT_RE filters out when they appear as a whole anchor.
    "Reply via web post",
    "Messages in this topic",
    "All Messages",
    # Direct (non-digest) emails' own Yahoo-appended footer -- confirmed
    # against the real archive: 91/4060 posts, missed by the markers above
    # since those all target digest-specific boilerplate phrasing.
    "Yahoo! Groups Links",
    # A third footer variant: some mail clients render the same per-message
    # action bar as plain text, converting every link to a "[N]" reference
    # with the actual URLs collected under a "Links:" heading -- found via
    # user review of a real post, not the earlier sampling passes. 128/4060
    # posts, confirmed zero false positives (every occurrence of "Links:"
    # in the whole dataset is this exact footer, nothing else). Entirely
    # dead content even when not stripped for PII reasons: numbered
    # tracking-parameter-laden groups.yahoo.com URLs to a service that no
    # longer exists, and orphaned "mailto:" fragments left over once
    # scrub_email_addresses removes the actual address.
    "Links:",
)

_ALLOWED_TAGS = {
    "p", "br", "div", "span", "b", "i", "em", "strong", "u",
    "a", "ul", "ol", "li", "blockquote", "pre", "code", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6", "table", "tr", "td", "th",
}


def _truncate_at_marker(container) -> None:
    """Drop boilerplate-marker content from `container`'s direct children,
    recursing into the first child instead of discarding it wholesale when
    that's where the marker match falls and it has children of its own to
    search more precisely (see sanitize_body's docstring for why this needs
    to be recursive at all: some templates run the footer text into the same
    tag as the real content, separated only by <br>, not as a sibling)."""
    nodes = list(container.contents)
    node_texts = [
        (node.get_text("", strip=False) if hasattr(node, "get_text") else str(node))
        for node in nodes
    ]
    cumulative = 0
    offsets = []
    for t in node_texts:
        offsets.append((cumulative, cumulative + len(t)))
        cumulative += len(t)
    full_text = "".join(node_texts)

    cut_index = None
    for marker in _BOILERPLATE_TEXT_MARKERS:
        pos = full_text.find(marker)
        if pos == -1:
            continue
        for i, (start, end) in enumerate(offsets):
            if start <= pos < end:
                cut_index = i if cut_index is None else min(cut_index, i)
                break

    if cut_index is None:
        return

    matched_node = nodes[cut_index]
    real_content_precedes = full_text[: offsets[cut_index][0]].strip() != ""
    if real_content_precedes or not hasattr(matched_node, "contents") or not matched_node.contents:
        # Either real (non-whitespace) content precedes the match at this
        # level -- not just an earlier sibling that happens to have a lower
        # index, which could itself be nothing but whitespace -- so it's
        # safe to just drop the matched node onward; or the matched node has
        # nothing further to recurse into. Either way, this is as precise as
        # the cut can get.
        for node in nodes[cut_index:]:
            node.decompose() if hasattr(node, "decompose") else node.extract()
        return

    # The match is in the very first node, and that node has children --
    # descend into it so any real content preceding the marker *within* it
    # is preserved, rather than deleting the whole node (and everything
    # genuine it contains) outright.
    _truncate_at_marker(matched_node)
    for node in nodes[cut_index + 1:]:
        node.decompose() if hasattr(node, "decompose") else node.extract()


def sanitize_body(html: str) -> tuple[str, str]:
    """Return (body_html_clean, body_text_plain).

    Strips Yahoo boilerplate, inline style="" attributes (pervasive in the
    "modern" digest template -- see digest_parser.py), and anything outside
    a conservative tag allow-list, while keeping genuine authored content.
    """
    soup = BeautifulSoup(html, "lxml")
    # lxml auto-wraps any fragment in <html><body>...</body></html>, so the
    # real top-level fragment siblings live in soup.body.contents, not
    # soup.contents (which would just be the single <html> node).
    root = soup.body or soup

    # The direct/relayed full-page template (unlike a digest-derived
    # segment, which digest_parser.py has already carved down to just one
    # post) wraps the real content in a dedicated #ygrp-text/#ygrp-content
    # element, alongside numerous *other* boilerplate sections that keep
    # turning up under yet more distinct ids (ygrp-actbar, ygrp-ft,
    # ygrp-grft, ygrp-vitnav, ...) -- enumerating and denylisting every one
    # individually doesn't scale and reliably misses one. Where this known
    # content wrapper exists, use it directly instead of playing whack-a-mole
    # with the rest of the page; the denylist below remains as the fallback
    # for content with no such wrapper (e.g. digest segments).
    content_wrapper = soup.find(id=_CONTENT_WRAPPER_IDS)
    if content_wrapper is not None:
        root = content_wrapper
    else:
        # Only relevant in the fallback case -- if a known content wrapper
        # was found above, everything outside it is already excluded from
        # the output regardless, so there's nothing for this to do.
        for el in list(soup.find_all(id=_BOILERPLATE_IDS)):
            el.decompose()
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()

    # A digest-derived post's captured segment (digest_parser.py) ends with
    # Yahoo's per-post action bar ("Reply via web post", "Messages in this
    # topic", ...) trailing after the real content; some full-page templates
    # (e.g. poll-result notifications) instead run the equivalent footer
    # text directly into the *same* <p> as the real content, separated only
    # by <br> tags, not as a separate sibling element. _truncate_at_marker
    # handles both: it drops trailing sibling nodes from the marker's node
    # onward, same as before, but recurses into that node's own children
    # first when the match falls in the very first node and that node has
    # children of its own -- otherwise a giant single-paragraph post would
    # have its entire content, marker included, deleted wholesale.
    _truncate_at_marker(root)

    # A handful of source emails carry their own real heading markup (e.g.
    # a Yahoo-authored "Understand what's changing" notice with <h3>
    # subsections) -- confirmed against the real archive, one post. Every
    # post page has exactly one <h1> (the subject, in post.njk/thread.njk),
    # so any heading surviving from the body needs to start at <h2> or a
    # screen reader's heading outline skips a level (WCAG 2.2 AA, NFR-3).
    # Preserves relative nesting; only shifts the whole group as a unit.
    body_headings = root.find_all(re.compile(r"^h[1-6]$"))
    if body_headings:
        min_level = min(int(h.name[1]) for h in body_headings)
        shift = 2 - min_level
        if shift != 0:
            for h in body_headings:
                h.name = f"h{max(2, min(6, int(h.name[1]) + shift))}"

    for tag in soup.find_all(True):
        # lxml's own <html>/<body> wrapper -- structural, not content; must
        # not be unwrapped or `root.contents` (still referencing the `body`
        # tag object) would empty out as its children get reparented away.
        if tag.name in ("html", "body"):
            continue
        if tag.name not in _ALLOWED_TAGS:
            tag.unwrap()
            continue
        attrs_to_keep = {}
        if tag.name == "a" and tag.has_attr("href"):
            href = tag["href"]
            # mailto: hrefs are a real PII vector even after the plain-text
            # email scrub -- an address here is frequently percent-encoded
            # ("mailto:name%40domain.com"), which a literal "@" regex search
            # never matches. A mailto link also has no working purpose on a
            # read-only static archive with no mail backend, so there's no
            # downside to dropping it outright rather than trying to keep
            # scrubbing it correctly.
            if not href.lower().startswith("mailto:"):
                attrs_to_keep["href"] = href
        tag.attrs = attrs_to_keep

    body_text = root.get_text(separator="\n", strip=True)
    body_html = "".join(str(c) for c in root.contents).strip()
    return body_html, body_text


_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# Percent-encoded form ("name%40domain.com") -- found, at real scale (in the
# thousands), in visible quoted-footer text (e.g. "List-Unsubscribe:
# mailto:...") that survives even after mailto: href attributes are dropped
# in sanitize_body, since this occurs in plain text content, not an
# attribute value. _EMAIL_RE alone never matches this: there is no literal
# "@" character in the raw string, just the three literal characters "%40".
_EMAIL_ENCODED_RE = re.compile(r"[A-Za-z0-9._\-]+%40[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# Both of the above assume the address is one contiguous run, but
# body_text is produced by BeautifulSoup's get_text(separator="\n") --
# wherever the *source* HTML soft-wrapped a long address across multiple
# text nodes (a <wbr> or <br> inside the domain, the same wrapping
# data-structures.md already noted for long URLs), that separator turns the
# wrap into a literal newline sitting inside the address, splitting it
# before either regex above ever sees a contiguous match.
#
# An earlier version of this regex only tolerated whitespace immediately
# around the "@"/"%40" marker and around each dot -- correct for <wbr>,
# which Yahoo only ever inserted at those specific points. Confirmed
# against the real archive (live site, found via manual review): quoted
# plain-text mail instead hard-wraps at a fixed column, breaking mid-word
# with no punctuation anywhere near the break --
# "starwolf@travellerf\nreeport.com", "digest@yahoogrou\nps.com" -- which
# the old pattern could not see at all, leaving real, live email addresses
# unscrubbed (224 matches across the dataset, including personal addresses,
# not just Yahoo's own list-management aliases). Two different break
# styles are tolerated, deliberately not the same pattern, to avoid a
# worse problem than the one being fixed: an early version that allowed
# *any* whitespace, unlimited times, anywhere in the local-part/domain
# mangled ordinary prose too -- "look @ the example.com website" was
# swallowed whole as if "look" through "example.com" were one address,
# since bare spaces between separate real words satisfied the same
# pattern a genuine line-wrap does. The two real cases need different
# tolerance:
#   - Immediately around "@" and each "." -- old-school manual
#     anti-harvester obfuscation ("name @ domain . com") has no newline
#     at all, confirmed against the real archive ("martin.tajmar @
#     arcs.ac.at"), so bare spaces/tabs are allowed here.
#   - *Inside* a single local-part/domain-label token -- only a genuine
#     line-wrap does this, and a line-wrap always inserts an actual
#     newline (optionally followed by a quoted-reply "> " marker on the
#     continuation line), never a bare space; requiring the newline is
#     what keeps ordinary space-separated prose from being swept in.
#     Capped at one such break per token -- a real wrap splits a token
#     once, not repeatedly.
_PUNCT_BREAK = r"[ \t]*(?:\n[ \t]*(?:>[ \t]*)?)?"
_MIDTOKEN_BREAK = r"\n[ \t]*(?:>[ \t]*)?"
_LOCAL_RUN = rf"[A-Za-z0-9._%+\-]+(?:{_MIDTOKEN_BREAK}[A-Za-z0-9._%+\-]+)?"
_DOMAIN_LABEL_RUN = rf"[A-Za-z0-9\-]+(?:{_MIDTOKEN_BREAK}[A-Za-z0-9\-]+)?"
_EMAIL_LOOSE_RE = re.compile(
    rf"{_LOCAL_RUN}{_PUNCT_BREAK}(?:@|%40){_PUNCT_BREAK}{_DOMAIN_LABEL_RUN}"
    rf"(?:{_PUNCT_BREAK}\.{_PUNCT_BREAK}{_DOMAIN_LABEL_RUN})*{_PUNCT_BREAK}\.{_PUNCT_BREAK}[A-Za-z]{{2,}}"
)


def scrub_email_addresses(text: str) -> str:
    """Remove email addresses from free text (ADR-0008), in plain,
    percent-encoded ("name%40domain.com"), and soft-wrapped-across-a-newline
    form. Applied to body text and to author display names alike -- the
    digest parser can surface a raw email as someone's "name" when they
    never set a display name.
    """
    text = _EMAIL_LOOSE_RE.sub("", text)
    text = _EMAIL_ENCODED_RE.sub("", text)
    text = _EMAIL_RE.sub("", text)
    # What's left after the substitutions above is never a real address --
    # by construction, any actual address matching this literal "mailto:"
    # prefix was already removed along with it. Found via manual review:
    # 341/4060 posts carry Outlook's "-----Original Message-----\nFrom: X
    # [mailto:]On Behalf Of Y" quote-header convention, where scrubbing the
    # address correctly leaves the orphaned "mailto:" label behind with
    # nothing after it -- inert, meaningless text on its own, not a privacy
    # concern anymore but still worth not showing.
    text = re.sub(r"\bmailto:\s*", "", text)
    return text.strip()


# One more quoted-forward convention, found via user review of a real post
# (7326): "-------- Original message -------- Subject: X From: Y To: Z
# CC: W" -- a plain-text mail client's rendering of a forwarded message's
# headers, hard-wrapped at a fixed column with no regard for field
# boundaries (the wrap can land mid-subject, mid-name, anywhere). To: and
# CC: are empty in every one of the 13 real occurrences of this pattern
# (their value was always an email address, already removed elsewhere) --
# confirmed exhaustively, not assumed, before deciding to drop them
# unconditionally rather than render an empty label. The gap between "To:"
# and "CC:" separately tolerates quote markers (">" in text, the HTML-
# escaped "&gt;" in body_html) and numbered-footnote references ("[4]")
# that can land there when this header overlaps a "Links:"-style footer
# (defect #16) in the same quoted block.
_ORIGINAL_MESSAGE_TEXT_RE = re.compile(
    r"-------- Original message --------\s*Subject:\s*(?P<subject>.*?)\s*From:\s*(?P<from>.*?)"
    r"\s*To:[\s<>\[\]0-9]*CC:[\s<>\[\]0-9]*",
    re.DOTALL,
)
_ORIGINAL_MESSAGE_HTML_RE = re.compile(
    r"-------- Original message --------\s*Subject:\s*(?P<subject>.*?)\s*From:\s*(?P<from>.*?)"
    r"\s*To:(?:[\s>\[\]0-9]|&gt;|&lt;|<br\s*/?>|<a>\s*</a>)*CC:(?:[\s>\[\]0-9]|&gt;|&lt;|<br\s*/?>)*",
    re.DOTALL,
)


def _clean_header_field(raw: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", raw)
    text = re.sub(r"<a>\s*</a>", "", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&lt;", "<", text)
    # Quote markers only ever mean something at the start of a wrapped
    # line ("> " or repeated "> > " for nested quoting) -- collapsed after,
    # once real line breaks are gone, whitespace-only.
    text = re.sub(r"^(?:\s*>)+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[\d+\]\s*", "", text)
    return re.sub(r"\s+", " ", text).strip()


def reflow_original_message_header(text: str, is_html: bool) -> str:
    """Rewrite a "-------- Original message --------" quoted-forward header
    onto clean, single-line fields, dropping To:/CC: (always empty in this
    convention) instead of rendering blank labels.
    """
    pattern = _ORIGINAL_MESSAGE_HTML_RE if is_html else _ORIGINAL_MESSAGE_TEXT_RE
    sep = "<br/>\n" if is_html else "\n"

    def repl(m: re.Match) -> str:
        subject = _clean_header_field(m.group("subject"))
        sender = _clean_header_field(m.group("from"))
        parts = ["-------- Original message --------"]
        if subject:
            parts.append(f"Subject: {subject}")
        if sender:
            parts.append(f"From: {sender}")
        return sep.join(parts) + sep + sep

    return pattern.sub(repl, text)


def scrub_author_display_name(name: str) -> str:
    """An author display name that's actually just an email address (no real
    name was ever set) is reduced to the local part only -- still not a
    usable, contactable email address, but keeps *something* identifying
    rather than an empty string.
    """
    m = _EMAIL_RE.fullmatch(name.strip())
    if m:
        return name.split("@", 1)[0].strip()
    return scrub_email_addresses(name)
