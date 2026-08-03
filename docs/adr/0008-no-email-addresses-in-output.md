# ADR-0008: No email addresses in any output artifact

**Status:** Accepted

## Context

Many posts in the source mbox carry real personal email addresses, some Yahoo-obfuscated, some not (data-structures.md §6). This is being published permanently and publicly on GitHub Pages.

## Decision

Email addresses are stripped/excluded at the ETL stage (ADR-0001) — they are never written into the canonical dataset — rather than filtered or redacted only at render time. Display names associated with posts are published as-is; email addresses are not published in any form (FR-4/DR-4).

## Consequences

- The guarantee is structural: no render path, template, or future feature can leak an email address that was never present in the dataset it reads from, rather than relying on every downstream consumer to remember to redact it.
- Verified by an automated build-time scan of every generated output artifact (HTML, JSON, sitemap, search index) for email-address-shaped substrings, per FR-4's acceptance criteria in srs.md.
