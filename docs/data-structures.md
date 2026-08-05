# Source Data: Structure & Analysis

This document describes the raw archive files under [`mail_archives/`](../mail_archives/) as they actually exist on disk, based on direct inspection (not assumptions from file extensions). It's the foundation for the static-site build pipeline (mbox → normalized posts → threads → search index → static HTML).

Archive: the **Traveller_TNE** Yahoo! Group (`Traveller_TNE@yahoogroups.com`) — a mailing list for the *Traveller: The New Era* tabletop RPG setting.

## 1. Files present

| File | Format | Size | Role |
|---|---|---|---|
| `YahooArchive` | Unix **mbox** (`From `-delimited), CRLF line endings, mixed per-message charsets | 48,196,544 bytes | **Authoritative source.** Every email, in full, with original headers. |
| `YahooArchive.msf` | Mozilla **Mork** database v1.4 (Thunderbird's per-folder index/cache) | 393,853 bytes | Derived index only — Thunderbird's summary of the mbox above (flags, thread grouping, sort state). Not an independent data source. |

**Message count:** 724 messages (`grep -ac "^From - " YahooArchive`).

### 1.1 `YahooArchive` — mbox

- Standard `mboxo`-style format: each message begins with a line `From - <ctime-style-date>`. **That date is the local export/Thunderbird-download timestamp, not the message's original date** — in this file every `From ` line reads `Sep 04–05 2025` regardless of the mail's real date. Ignore it; use the `Date:` header instead.
- Line terminators are CRLF throughout (Windows-style), consistent with Thunderbird on Windows having produced the file.
- No global charset: `Content-Type: text/plain; charset="..."` / `text/html; charset="..."` is declared **per message** (and per MIME part). Observed charsets: `utf-8` (193), `iso-8859-1` (191), `us-ascii` (13), `windows-1252` (5), `windows-1250` (3), plus messages with no explicit charset. A build script must decode per-part using the declared charset, not assume one globally.
- Thunderbird-proprietary headers are present on every message (`X-Mozilla-Status`, `X-Mozilla-Status2`, `X-Mozilla-Keys`, `X-Account-Key`, `X-UIDL`) — these are local client metadata (read/flag state), not content, and should be dropped/ignored during extraction.
- Real date range (from `Date:` headers): **18 May 2005 – 11 Jan 2020**. All 724 records have a valid, parseable `Date:` header — corrected post-launch from an earlier pass that misread this as ending 8 Aug 2019, having conflated the `From -` line's known-unreliable local-export timestamp (correctly disregarded, per above) with the real `Date:` header of the archive's final ~5 months (Oct 2019 – Jan 2020, 12 genuine records: the group's own winding-down correspondence as Yahoo Groups shut down, including a real "New deadline for Yahoo Groups data request" email from Yahoo's own `info@comms.yahoo.net`). Not noise — real archive content, now correctly included throughout. Yearly volume is uneven — heaviest in 2012 and 2014, thin in the early and final years.

Python's standard `mailbox.mbox` module parses this file correctly (verified: 724 messages read, matches the raw `From ` count).

## 2. Message shape: three distinct kinds of "email" in this archive

This is the most important structural finding, and it changes how "one email = one post" cannot be assumed.

Yahoo Groups delivered mail to subscribers in three different modes depending on each subscriber's settings, and all three ended up in this one mailbox:

| Kind | Count | From header | Identifying trait |
|---|---|---|---|
| **A. Individual post (direct mail)** | ~188 | Real person's address (not `yahoogroups.com`) | Sent by a member's own mail client directly to the list; standard headers only. |
| **B. Individual post (relayed by Yahoo, "immediate" mode)** | ~22 | Often `name+email@... [Traveller_TNE]` via `yahoogroups.com` routing, or `<Traveller_TNE@yahoogroups.com>` for system notices (polls, file/photo uploads) | One post per email, but Yahoo rewrote/relayed it. Later-era ones (~2015+) carry a real `/message/<id>` permalink in the HTML body and usable `In-Reply-To`/`References` headers. |
| **C. Digest bundle** | **514** (71% of all messages!) | `<Traveller_TNE@yahoogroups.com>` | Subject is literally `[Traveller_TNE] Digest Number NNNN`. **One mbox record contains multiple distinct posts** bundled into one HTML email. |

**Kind C is the crux of the parsing problem.** 514 of the 724 mbox records are digests, each bundling a variable number of individual posts (commonly 1–3, sometimes more) inside a single `text/html` body — there is no separate MIME part per post. Naively treating each mbox record as "one message" would merge multiple unrelated posts (different authors, subjects, dates) into a single post, and the site's post/thread/search granularity would be wrong for the majority of the archive's content.

### 2.1 Digest internal structure

Each digest's HTML body contains a `<h1>Messages</h1>` section with one block per bundled post, structured as:

```html
<dl class="first">
  <dt>1. </dt>
  <dd class="last">
    <h2>
      <a href="http://groups.yahoo.com/group/Traveller_TNE/message/6312;...">
        Possibly useful colony info
      </a>
    </h2>
    <h3>Posted by:      "DED"      <a href="mailto:dedly@snet.net?...">
        dedly@snet.net </a>
        <a href="http://profiles.yahoo.com/dedtraveller">dedtraveller</a>
    </h3>
    <h4>Sun Nov&nbsp;16,&nbsp;2008 1:36&nbsp;pm (PST)</h4>
    <div class="ygrp-content">
      ... post body (HTML) ...
    </div>
  </dd>
</dl>
```

Per embedded post, this yields everything needed for a clean per-post record:

- **Canonical Yahoo message ID** — the numeric id in `/message/<id>` (e.g. `6312`). This is the single most valuable field in the whole archive: it's a stable, group-wide unique key, independent of mbox ordering or duplicate subjects, and it's the natural permalink slug for the static site (`/messages/6312/`).
- **Real subject** (the actual post title, not the digest wrapper's `Digest Number NNNN`).
- **Real author** — display name, email (in a `mailto:` link, sometimes address-obfuscated later on), and Yahoo profile handle/link.
- **Real post date/time** (human-formatted, e.g. `Sun Nov 16, 2008 1:36 pm (PST)` — needs parsing, and the timezone is an abbreviation not an offset).
- **Post body** as HTML.

A digest email also contains a shorter "topics/table of contents" teaser section earlier in the page (duplicate `Posted by:` / subject / link fragments) — extraction logic needs to target the `#ygrp-detail` / `<h1>Messages</h1>` full section specifically, not the teaser, to avoid double-counting.

**Not yet fully characterized:** the exact HTML is Yahoo Groups' template and has minor variations across the ~2005–2019 span (Yahoo revised the digest template at least once). The count of embedded posts per digest was not exhaustively validated across all 514 digests — a naive regex undercounted on the one digest tested by hand vs. an eyeballed read. **Action item for the build script:** parse with a real HTML parser (e.g. `BeautifulSoup`/`lxml`, not regex), iterate `<dl>` blocks under the "Messages" heading, and spot-check counts against the Mork thread/message totals (§3) before trusting the extraction.

### 2.2 Kind A/B (non-digest) posts

These map 1:1 to an mbox record. Kind A (direct mail, ~188 messages) has no Yahoo permalink at all — identity/threading must come from standard headers. Kind B late-era relayed posts (~2015+) do carry a `/message/<id>` link in the footer and usable `References`/`In-Reply-To`, matching kind C's addressing scheme — worth reusing the same permalink-extraction logic.

## 3. Threading

Header-based threading is present but only covers a minority of records directly:

| Header | Coverage (of 724 mbox records) |
|---|---|
| `Message-ID` | 719 / 724 |
| `In-Reply-To` | 123 / 724 |
| `References` | 82 / 724 |
| Subject starts with `Re:` | 121 / 724 |

Two things temper this:

1. Once digests (kind C) are expanded per §2, the *effective* per-post `Message-ID`/threading picture is different (and better) than the raw mbox header stats above suggest, since most content lives inside digests where each embedded post has its own identity via the `/message/<id>` permalink even without an RFC `Message-ID`.
2. Threading quality is era-dependent: pre-~2014 traffic relies almost entirely on subject-line matching (little to no `In-Reply-To`/`References`); 2015+ traffic (after a Yahoo Groups platform change) has real `In-Reply-To`/`References` chains.

**Implication for the build:** a single threading strategy won't work uniformly. Recommended approach — build a thread graph using, in priority order: (1) `In-Reply-To`/`References` where present, (2) normalized subject (strip `Re:`/`[Traveller_TNE]` prefixes, case-fold, collapse whitespace) as a fallback grouping key, matched within a reasonable time window. Cross-check the result against Thunderbird's own thread grouping in the Mork file (§4) as a sanity signal, not as ground truth.

## 4. `YahooArchive.msf` — Mork database (Thunderbird index)

Mork is Mozilla's old text-based, ad hoc "database" format (not JSON, not SQLite — a bespoke pseudo-JS-object-literal syntax). This file is Thunderbird's local folder cache: read/unread state, view sort order, and a **derived thread index** it computed from the mbox. **It is not a separate data source** — everything meaningful in it is either (a) reconstructible from the mbox itself, or (b) purely local Thunderbird UI state (column widths, sort column, MRU time) with no bearing on content.

### 4.1 Format shape

```
// <!-- <mdb:mork:z v="1.4"/> -->
<  <(a=c)>  // dict alias-table declaration, encoding: (f=iso-8859-1)
  (B8=storeToken)(B9=replyTo)...   // column-id -> column-name dictionary
<(58F=76)(589=47224ced)(81=0)(80=1)>              // a row: cell-id=value pairs
[40:m(^9B=76)(^8F=76)(^91^589)(^90=0)(^92=1)]     // a table/row using dict refs (^ = alias lookup)
```

- A **dictionary block** at the top maps short hex IDs to column names — this is effectively self-documenting. Relevant columns confirmed present: `subject`, `sender`, `message-id`, `references`, `recipients`, `date`, `flags`, `msgThreadId`, `threadId`, `threadFlags`, `threadNewestMsgDate`, `children`, `threadSubject`, `numMsgs`, etc.
- Rows are `<(cellId=value)(cellId=value)...>`, where a leading `^` means "look up by alias/reference" rather than literal value (Mork deduplicates repeated strings via an alias table).
- Tables like `[40:m(^9B=76)(^8F=76)(^91^589)(^90=0)(^92=1)]` are **thread meta-rows**: `9B`=threadRoot id, `8F`=threadId, `91`=newest message date, `90`=threadFlags, `92`=children count.

### 4.2 What it confirms

- `numMsgs` in the folder-info row = `722` (hex `2d2`), vs. 724 `From ` lines in the mbox — a small (2-message) discrepancy, likely local Thunderbird bookkeeping (e.g. a message expunged from the index but still physically present in the mbox file, or vice versa). Not concerning, but worth a passing sanity check in the build script (warn if final extracted-post count deviates wildly from ~722–724).
- **472 distinct threads** were computed by Thunderbird over what it counted as ~726 messages (sum of `children` counts across thread rows). Children-per-thread distribution: 580 threads with exactly 1 message (singletons), 19 with 2, 7 with 3, and a long tail up to 9. I.e. **the large majority of threads, by Thunderbird's own subject+reference-based grouping, are single, unreplied posts** — consistent with a slow-moving hobbyist mailing list. This is a useful expectation-setter: don't expect deep reply chains: it validates the fallback subject-matching approach in §3 rather than requiring anything fancier.

### 4.3 Recommendation

**Do not write a Mork parser for the site pipeline.** It adds real complexity (Mork's dictionary/alias/multi-table syntax is fiddly and underdocumented) for a file that contributes no information the mbox doesn't already have, once digests are properly expanded. Treat `YahooArchive.msf` purely as a **validation reference** during development — e.g., "does my computed thread/singleton ratio roughly match Thunderbird's 580/472 split?" — and exclude it from the actual build pipeline and from anything shipped to GitHub Pages.

## 5. Other structural notes relevant to the build

- **Attachments embedded in mbox are rare**: only one `.xls` and one `.png` found across all 724 records. The pipeline should handle a `multipart/mixed` message containing a `multipart/alternative` (text/plain + text/html) plus a base64 attachment part (this exact shape was observed — see the `.xls` example) rather than assuming attachment-free mail.
- **Yahoo Groups' separate "Files"/"Photos" section is a distinct, largely-missing data source.** 6 messages have subjects containing "New file uploaded to Traveller_TNE" or "Download your files NOW" — the latter from December 2019, when Yahoo announced it was deleting all uploaded files/photos ("Yahoo is deleting all uploaded files, so if you want them and haven't already done so, grab them NOW"). One reply (from "Leonard Erickson aka shadow") states *"I grabbed everything (files, photos and messages). For the files & photos, I can just send them to you"* (to the archive owner, "DED"), and mentions a third party ("Johan Solo") who separately downloaded everything including messages into a SQLite database. **Practical implication**: posts in this archive reference files/photos that were never part of this mbox export at all (they lived on Yahoo's web servers, not in email) — some of that content may exist in a private copy (the archive owner's, or the "shadow"/"Johan Solo" copies mentioned above) and could plausibly be added to this project later. The site's attachment-handling design should treat "attachment referenced by a post" and "attachment file actually present in this repo" as two independent facts, not assume the latter follows from the former — see concept.md §6 / srs.md FR-23/FR-26/FR-27 for the resulting requirement.
- **Content-Transfer-Encoding**: `quoted-printable` (331), `7bit` (241), `8bit` (4) — standard, no surprises; Python's `email`/`mailbox` modules decode these transparently via `get_payload(decode=True)`.
- **List/administrative headers** are consistent and can be used for provenance/footer stripping: `List-Id: <Traveller_TNE.yahoogroups.com>`, `Mailing-List:`, `List-Unsubscribe:`, `Precedence: bulk`. Non-digest HTML bodies (and digest bodies) both carry substantial Yahoo Groups CSS/boilerplate (`#ygrp-*` styles, "For more information about this group..." footers, ad/sponsor placeholders) that should be stripped during body extraction, not rendered as-is.
- **Senders**: 65 unique raw `From` strings; a handful of prolific posters dominate (`Peter Gray`, `DED`/`dedly@snet.net`, `shadow@shadowgard.com`, `ret7army@yahoo.com`, etc.) alongside the two system addresses. Useful for an eventual "browse by author" view.
- **Body size**: min 2.6 KB, max ~1.95 MB (a large digest), average ~65 KB per mbox record — digest bloat (repeated CSS/boilerplate per email) explains the average being much larger than a typical single post.

## 6. Open questions to resolve before/during implementation

1. ~~**Exact digest HTML template variants across 2005–2019**~~ — **Resolved by delegation.** No specific handling was mandated; confirming template consistency (or branching the parser if needed) is an implementation-time validation task during ETL development, not a design decision — sample across the year range and branch the parser only if actually needed.
2. ~~**De-duplication**~~ — **Resolved.** Real duplicate *records* (e.g., the same post arriving both as an individual email and inside a digest) must be eliminated using the `/message/<id>` permalink as the dedup key. Partial/full **quoted text** *within* a post's body (someone quoting a prior message when replying) is expected and is not deduplication's concern — that's normal reply content and stays as-is in the quoting post's body.
3. ~~**Timezone normalization**~~ — **Resolved.** Best-effort conversion of all date/times to a single standard, sortable format — UTC, ISO 8601 — for every post regardless of source (mbox `Date:` header offsets, or digest's human-formatted `PST`/`PDT`-style timestamps). "Best effort" because some abbreviations are inherently ambiguous (e.g. historical DST rules); exact original wall-clock display text can still be retained alongside the normalized value if useful for the reader.
4. **Address obfuscation / privacy** — **Resolved separately**, see [concept.md §12](concept.md#12-open-questions--risks-carried-forward): no email addresses are published in any form; display names only.

---

*Analysis performed by direct inspection of `mail_archives/YahooArchive` (724 messages) and `mail_archives/YahooArchive.msf` using `grep`, Python's `mailbox` module, and manual Mork syntax reading. No external tools or prior documentation were relied upon.*
