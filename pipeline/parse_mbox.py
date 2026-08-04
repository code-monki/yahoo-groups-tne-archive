"""Load the source mbox and classify each record's kind.

Per data-structures.md §2: a raw mbox record is one of three kinds --
a Yahoo digest bundling multiple posts, an individually-relayed post routed
through yahoogroups.com, or a post mailed directly to the list. Empirically
verified against the real 724-record archive: this classification rule
produces exactly the 514/22/188 split data-structures.md documented.
"""

from __future__ import annotations

import mailbox
from dataclasses import dataclass
from typing import Literal

SourceKind = Literal["digest", "relayed", "direct"]


@dataclass
class RawRecord:
    index: int
    source_kind: SourceKind
    message: mailbox.mboxMessage
    subject: str
    from_header: str


def classify_source_kind(msg: mailbox.mboxMessage) -> SourceKind:
    subject = msg.get("Subject") or ""
    if "Digest Number" in subject:
        return "digest"
    from_header = (msg.get("From") or "").lower()
    if "yahoogroups.com" in from_header:
        return "relayed"
    return "direct"


def load_records(mbox_path: str) -> list[RawRecord]:
    mbox = mailbox.mbox(mbox_path, factory=None)
    records = []
    for i, msg in enumerate(mbox):
        records.append(
            RawRecord(
                index=i,
                source_kind=classify_source_kind(msg),
                message=msg,
                subject=msg.get("Subject") or "",
                from_header=msg.get("From") or "",
            )
        )
    return records


def extract_body_parts(msg: mailbox.mboxMessage) -> tuple[str | None, str | None]:
    """Return (text_plain, text_html) for a message, decoding each part with
    its own declared charset (data-structures.md notes charset varies
    per-message/per-part, not archive-wide) and replacing undecodable bytes
    rather than raising -- a handful of malformed bytes shouldn't fail an
    otherwise-good record.
    """
    text_plain: str | None = None
    text_html: str | None = None
    if msg.is_multipart():
        parts = msg.walk()
    else:
        parts = [msg]
    for part in parts:
        content_type = part.get_content_type()
        if content_type not in ("text/plain", "text/html"):
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        charset = part.get_content_charset() or "iso-8859-1"
        try:
            decoded = payload.decode(charset, errors="replace")
        except LookupError:
            decoded = payload.decode("iso-8859-1", errors="replace")
        if content_type == "text/plain" and text_plain is None:
            text_plain = decoded
        elif content_type == "text/html" and text_html is None:
            text_html = decoded
    return text_plain, text_html
