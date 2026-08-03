# ADR-0006: Attachment availability determined by build-time file presence

**Status:** Accepted

## Context

Posts may reference attachments: a small number embedded directly in the mbox (one `.xls`, one `.png`), and an unknown further number referencing Yahoo Groups' separate Files/Photos section, which was never part of the mbox export at all and may or may not be recoverable later (data-structures.md §5 — a Dec 2019 thread has a member claiming to have saved everything before Yahoo deleted it, with an offer to pass it to the archive owner that may or may not have been followed up on). "A post references an attachment" and "that attachment's file is present in this repository" are therefore independent facts that can change independently of each other, potentially years apart.

The user's original framing suggested detecting missing attachments via a runtime 404. The actual underlying intent, confirmed by the user, was simpler: detect availability whenever files are added, which — given this project's normal commit/push/CI-to-GitHub-Pages cycle — happens at build time, not at request time.

## Decision

Attachment availability is computed purely from whether a matching file exists under `attachments/<permalink-id>/<original-filename>` at build time — never a hardcoded per-post flag in the canonical dataset, and never a client-side runtime check. When present, the file is copied into the build output and the post page renders a working download link (FR-23). When absent, the post page renders an affordance that opens an accessible "not currently available in this archive" modal, implemented as a native `<dialog>` element (FR-26).

The nested-by-permalink-ID folder structure (rather than a flatter naming scheme) was chosen as more faithful to the source's own per-message identity.

## Consequences

- Adding a previously-unavailable file to `attachments/` and rebuilding is, on its own, sufficient to switch a post's page from the "not available" modal to a working download link (FR-27) — no other code or content change required.
- No client-side network probing needed to detect availability, which is simpler and a better fit for keyboard/AT operability (NFR-2) and non-blocking JS (NFR-6) than a runtime-404 approach would have been.
- Requires a build (not just a file copy) to take effect — acceptable, since this project has no "live" deployment path other than a GitHub Actions build.
