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
        # A mailto <a>'s children (below) can include this tag -- once that
        # <a> is cleared, this tag is no longer attached to the document,
        # even though it's still in this already-materialized find_all()
        # list.
        if tag.parent is None:
            continue
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
            if href.lower().startswith("mailto:"):
                # The href already tells us, unambiguously, that this
                # anchor's visible text is an email address -- clear it
                # here rather than leaving it to flow into get_text() and
                # relying on the text-level scrub regex to find it again
                # from scratch. That regex has to tolerate a genuine
                # mid-token line-wrap (Yahoo inserts <wbr> inside long
                # addresses, which get_text(separator="\n") turns into a
                # real newline), and that same tolerance can't distinguish
                # "this fragment continues the address on the next line"
                # from "an unrelated real word happens to sit immediately
                # before the address's first line" -- confirmed against the
                # real archive (post source msg 211, digest-embedded):
                # "...]On Behalf Of\nshadow@shadowgard.\ncom" matched as one
                # address starting at "Of", deleting that real word along
                # with the address. Clearing the text at the DOM level,
                # where the anchor boundary is still known, removes the
                # address without ever exposing this ambiguity to the
                # regex. The plain-text hard-wrap case (quoted replies with
                # no HTML structure at all) has no such boundary available
                # and still needs the text-level regex's tolerance.
                tag.clear()
            else:
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

# The gap between "To:" and "CC:" is safely bounded by "CC:" as a literal,
# unambiguous anchor -- however much junk a greedy character class eats,
# it still has to stop exactly where the real "CC:" text is. The gap
# *after* "CC:" has no such anchor, which is exactly what a synthetic
# multi-level-nesting test caught (a concern the user raised, checking
# this fix would actually scale rather than assuming it does): the same
# unbounded-character-class approach applied there greedily consumed the
# leading quote marker off the *next* header's or the genuinely quoted
# reply's own first line the moment that line happened to start with the
# same characters ("> Don't do that..." lost its "> ", confirmed against
# the real archive, post 7234, already deployed with this bug). Fixed by
# only ever consuming *complete lines* that are entirely junk (whitespace/
# quote-markers/footnote-brackets, nothing else) -- a line with real
# content after its quote marker fails to match "entirely junk" and is
# correctly left alone, quote marker included.
_JUNK_LINE_TEXT = r"[ \t]*(?:>[ \t]*)*(?:\[\d+\][ \t]*)*\n"
_JUNK_TOKEN_HTML = r"(?:&gt;|&lt;|<a>\s*</a>|\[\d+\])"
_JUNK_LINE_HTML = rf"[ \t]*(?:{_JUNK_TOKEN_HTML}[ \t]*)*<br\s*/?>"

_ORIGINAL_MESSAGE_TEXT_RE = re.compile(
    r"-------- Original message --------\s*Subject:\s*(?P<subject>.*?)\s*From:\s*(?P<from>.*?)"
    rf"\s*To:[\s<>\[\]0-9]*CC:(?:{_JUNK_LINE_TEXT})*",
    re.DOTALL,
)
_ORIGINAL_MESSAGE_HTML_RE = re.compile(
    r"-------- Original message --------\s*Subject:\s*(?P<subject>.*?)\s*From:\s*(?P<from>.*?)"
    rf"\s*To:(?:[\s>\[\]0-9]|&gt;|&lt;|<br\s*/?>|<a>\s*</a>)*CC:(?:{_JUNK_LINE_HTML})*",
    re.DOTALL,
)


def _clean_header_field(raw: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", raw)
    text = re.sub(r"<a>\s*</a>", "", text)
    # Outlook's own header block bolds its field labels ("<b>From:</b>",
    # "<b>On Behalf Of </b>") -- irrelevant once the label text itself is
    # dropped or reduced to a single clean value.
    text = re.sub(r"</?b>", "", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&quot;", '"', text)
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


# A second, distinct quoted-forward convention -- Outlook's own
# "-----Original Message-----" header (four dashes, capitalized
# differently, no "found via review" quirks shared with the 8-dash one
# above). 97/4060 posts, confirmed by direct sampling of the real archive.
# Two sub-styles, both handled by one pattern since the field order and
# anchors are identical:
#   - The mailing-list-relay style: "From:" is blank (the visible From was
#     the list's own relay address, now scrubbed) and the real author's
#     name instead follows "On Behalf Of" on the next line -- Outlook
#     renders this as "[mailto:address]On Behalf Of Name", and once the
#     scrubbed address leaves only the empty brackets, this reads as
#     "[]On Behalf Of Name".
#   - A plain client-forward style ("From: Name <address>", "Date:" instead
#     of "Sent:") -- the address's surrounding "<>" are left empty the same
#     way once scrubbed.
# A rarer BlackBerry-forward variant (one real post, two occurrences)
# additionally carries "Sender:"/"Reply-To:" fields with no real content of
# their own -- handled by treating them as one more thing to discard rather
# than adding them to the four displayed fields.
#
# Unlike the 8-dash convention, there's no fixed literal (like "CC:") that
# reliably marks the end of the *Subject* value before real reply content
# begins -- a wrapped subject can run directly into the next line of actual
# body text with no blank line or other separator in the plain-text
# rendering (confirmed against the real archive, post 5262: "...make you go
# hmmmm\nVirus is self aware." -- both are on their own line with nothing
# to structurally tell them apart). Rather than guess where the subject
# ends -- exactly the kind of assumption that produced the content-loss
# regression in the 8-dash fix (defect #19) -- this reflow stops at the
# "Subject:" label itself and leaves the value, and everything after it,
# untouched. That means an occasional two-line subject won't fully collapse
# to one line, but nothing real is ever at risk of being eaten.
_QUOTE_WS_TEXT = r"[\s>]*"
_QUOTE_WS_HTML = r"(?:\s|&gt;|&lt;|<br\s*/?>|<a>\s*</a>)*"
# Two field orders are both confirmed in the real archive: From/Sent-or-
# Date/To/Subject (the common case) and From/To/Sent-or-Date/Subject (posts
# 7344, 7351). Both are tried as a single alternation within one match
# attempt per "-----Original Message-----" occurrence, not as two separate
# passes -- an earlier version of this ran the two field orders as two
# sequential .sub() passes over the whole text, which broke on a post
# (6758) containing a *second*, unmarked header block later in the same
# body (no "-----Original Message-----" of its own, just a bare repeat of
# the From/Sent/To/Subject convention -- a doubly-forwarded quote whose
# client didn't re-emit the divider line). The primary field order
# correctly reflowed the first block and, as designed, dropped its now-
# empty "To:" line; the second pass then re-scanned that already-reflowed
# output looking for "To:" near the same marker, didn't find it there
# anymore, and its lazy match kept searching until it found the *second*
# block's "To:" instead -- silently swallowing the entire real paragraph in
# between as if it were part of the header. A single regex with the two
# field orders as internal alternatives never re-scans its own output, so
# this can't recur: each match attempt is independent, and once the first
# occurrence is consumed by re.sub, the second (unmarked, unmatched) block
# is structurally invisible to this pattern regardless of order.
_OUTLOOK_ORIGINAL_MESSAGE_TEXT_RE = re.compile(
    r"-----Original Message-----" + _QUOTE_WS_TEXT + r"From:\s*(?P<from>.*?)"
    + r"(?:"
    + _QUOTE_WS_TEXT + r"(?P<when_label_a>Sent|Date):\s*(?P<when_a>.*?)"
    + _QUOTE_WS_TEXT + r"To:\s*(?P<to_a>.*?)"
    + r"|"
    + _QUOTE_WS_TEXT + r"To:\s*(?P<to_b>.*?)"
    + _QUOTE_WS_TEXT + r"(?P<when_label_b>Sent|Date):\s*(?P<when_b>.*?)"
    + r")"
    + _QUOTE_WS_TEXT + r"Subject:[ \t]*\r?\n?[ \t]*",
    re.DOTALL,
)
_OUTLOOK_ORIGINAL_MESSAGE_HTML_RE = re.compile(
    r"-----Original Message-----" + _QUOTE_WS_HTML + r"(?:<b>)?From:(?:</b>)?\s*(?P<from>.*?)"
    + r"(?:"
    + _QUOTE_WS_HTML + r"(?:<b>)?(?P<when_label_a>Sent|Date):(?:</b>)?\s*(?P<when_a>.*?)"
    + _QUOTE_WS_HTML + r"(?:<b>)?To:(?:</b>)?\s*(?P<to_a>.*?)"
    + r"|"
    + _QUOTE_WS_HTML + r"(?:<b>)?To:(?:</b>)?\s*(?P<to_b>.*?)"
    + _QUOTE_WS_HTML + r"(?:<b>)?(?P<when_label_b>Sent|Date):(?:</b>)?\s*(?P<when_b>.*?)"
    + r")"
    + _QUOTE_WS_HTML + r"(?:<b>)?Subject:(?:</b>)?[ \t]*(?:<br\s*/?>)?[ \t]*",
    re.DOTALL,
)
# "Sender:"/"Reply-To:" carry no content of their own in every observed
# occurrence and aren't one of the four displayed fields -- if either
# lands inside a captured field's raw span (the main pattern has no anchor
# for them), drop the label rather than let it render as a bare
# "Sender:"/"Reply-To:" with nothing after it.
_OUTLOOK_NOOP_FIELD_RE = re.compile(r"\b(?:Sender|Reply-To):\s*", re.IGNORECASE)


def _strip_scrubbed_address_remnants(text: str) -> str:
    """Drop the punctuation left behind once an address inside it has
    already been scrubbed to nothing: empty "[]" (a stripped "[mailto:...]"),
    empty "" (a display-name-that-was-just-the-address, quoted in the
    Outlook convention's fallback rendering), and "<"/">" individually
    rather than as a matched pair -- the closing ">" of an empty "<>" can
    land right at the boundary with the next field's own quote-marker
    tolerance (_QUOTE_WS_TEXT/_QUOTE_WS_HTML also accepts a bare ">"),
    which can end up consuming it instead of leaving it in this capture.
    Safe unconditionally in any of these header fields: any address that
    was ever inside this punctuation has already been scrubbed, so none of
    these characters ever carries real content on their own here.
    """
    text = re.sub(r"\[\s*\]", "", text)
    text = re.sub(r'"\s*"', "", text)
    text = re.sub(r"[<>]", "", text)
    return text


def _clean_outlook_name_field(raw: str) -> str:
    text = _clean_header_field(raw)
    text = _OUTLOOK_NOOP_FIELD_RE.sub("", text)
    text = _strip_scrubbed_address_remnants(text)
    m = re.search(r"On Behalf Of\s*", text, flags=re.IGNORECASE)
    if m:
        text = text[m.end():]
    return re.sub(r"\s+", " ", text).strip()


def _clean_outlook_to_field(raw: str) -> str:
    text = _clean_header_field(raw)
    text = _OUTLOOK_NOOP_FIELD_RE.sub("", text)
    text = _strip_scrubbed_address_remnants(text)
    return re.sub(r"\s+", " ", text).strip()


def reflow_outlook_original_message_header(text: str, is_html: bool) -> str:
    """Rewrite a "-----Original Message-----" quoted-forward header onto
    clean, single-line fields, matching reflow_original_message_header's
    treatment of the other quoted-forward convention. Unlike that function,
    the Subject value itself (and everything after it) is left untouched --
    see the module-level comment above for why.
    """
    sep = "<br/>\n" if is_html else "\n"

    def repl(m: re.Match) -> str:
        when_label = m.group("when_label_a") or m.group("when_label_b")
        when_raw = m.group("when_a") if m.group("when_a") is not None else m.group("when_b")
        to_raw = m.group("to_a") if m.group("to_a") is not None else m.group("to_b")
        sender = _clean_outlook_name_field(m.group("from"))
        when = _clean_header_field(when_raw)
        to = _clean_outlook_to_field(to_raw)
        parts = ["-----Original Message-----"]
        if sender:
            parts.append(f"From: {sender}")
        if when:
            parts.append(f"{when_label}: {when}")
        if to:
            parts.append(f"To: {to}")
        parts.append("Subject:")
        return sep.join(parts) + " "

    pattern = _OUTLOOK_ORIGINAL_MESSAGE_HTML_RE if is_html else _OUTLOOK_ORIGINAL_MESSAGE_TEXT_RE
    return pattern.sub(repl, text)


# A fourth quoted-forward convention -- Yahoo Mail's own "classic" compose
# view, divided by a plain underscore rule rather than any dashed or
# bracketed marker text. 39 real occurrences, confirmed by direct sampling.
# Field order is fixed (From/To/Sent/Subject -- To always carries only the
# list's own scrubbed address, never a personal one, so it's dropped every
# time in practice, same as the two 8-dash-convention fields it echoes).
# The divider itself is long enough that Yahoo inserts <wbr> inside it the
# same as it does for addresses (confirmed: "____________<wbr>_________
# <wbr>_________<wbr>__", always the same total length) -- in body_text
# this becomes several separate "___"-only lines (get_text() puts a real
# newline at each <wbr>), in body_html the <wbr> tags carry no content of
# their own and are simply unwrapped, so the underscores end up as one
# unbroken run with nothing to split on.
# A single bounded [_\s]* between two literal "_" anchors, not a repeated
# group of "_{2,}" alternating with whitespace -- the latter shape (a
# quantified group whose own body is itself quantified over a character
# class it also matches outside the group) is the classic catastrophic-
# backtracking trap: on non-matching input, the engine can partition a long
# run of underscores/whitespace combinatorially many ways before giving up.
# This form matches the same realistic text with a single quantifier, no
# nested ambiguity, and provably linear-time backtracking.
_UNDERSCORE_DIVIDER_TEXT = r"_[_\s]*_"
_UNDERSCORE_ORIGINAL_MESSAGE_TEXT_RE = re.compile(
    _UNDERSCORE_DIVIDER_TEXT
    + _QUOTE_WS_TEXT + r"From:\s*(?P<from>.*?)"
    + _QUOTE_WS_TEXT + r"To:\s*(?P<to>.*?)"
    + _QUOTE_WS_TEXT + r"Sent:\s*(?P<when>.*?)"
    + _QUOTE_WS_TEXT + r"Subject:[ \t]*\r?\n?[ \t]*",
    re.DOTALL,
)
_UNDERSCORE_ORIGINAL_MESSAGE_HTML_RE = re.compile(
    r"_{2,}"
    + _QUOTE_WS_HTML + r"(?:<b>)?From:(?:</b>)?\s*(?P<from>.*?)"
    + _QUOTE_WS_HTML + r"(?:<b>)?To:(?:</b>)?\s*(?P<to>.*?)"
    + _QUOTE_WS_HTML + r"(?:<b>)?Sent:(?:</b>)?\s*(?P<when>.*?)"
    + _QUOTE_WS_HTML + r"(?:<b>)?Subject:(?:</b>)?[ \t]*(?:<br\s*/?>)?[ \t]*",
    re.DOTALL,
)


def reflow_underscore_original_message_header(text: str, is_html: bool) -> str:
    """Rewrite Yahoo Mail's underscore-divided quoted-forward header onto
    clean, single-line fields -- same treatment and same rationale for
    leaving the Subject value itself untouched as
    reflow_outlook_original_message_header.
    """
    sep = "<br/>\n" if is_html else "\n"

    def repl(m: re.Match) -> str:
        sender = _clean_outlook_name_field(m.group("from"))
        to = _clean_outlook_to_field(m.group("to"))
        when = _clean_header_field(m.group("when"))
        parts = ["________________________________"]
        if sender:
            parts.append(f"From: {sender}")
        if to:
            parts.append(f"To: {to}")
        if when:
            parts.append(f"Sent: {when}")
        parts.append("Subject:")
        return sep.join(parts) + " "

    pattern = _UNDERSCORE_ORIGINAL_MESSAGE_HTML_RE if is_html else _UNDERSCORE_ORIGINAL_MESSAGE_TEXT_RE
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
