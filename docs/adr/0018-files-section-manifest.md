# ADR-0018: Group-level Files section, auto-extracted manifest

**Status:** Accepted

## Context

Real user feedback after launch identified a gap the original design never covered: Yahoo Groups had two genuinely distinct upload mechanisms. FR-23/26/27 (and everything built for them in Phase 7) cover *per-post* attachments — a file physically embedded in one specific email's MIME parts, tied to that one post. Yahoo Groups' separate **Files section** was a shared repository users uploaded to directly, independent of any single email, and this archive had no representation of it at all until now.

data-structures.md §5 already noted the Files section existed and wasn't captured in the mbox export, and `pipeline/attachments.py`'s `find_files_section_candidates()` (Phase 2) flagged posts that merely *mention* it, for manual review — but that's a candidate list, not a browsable feature, and it was never surfaced anywhere in the site itself.

Investigating the gap turned up something the original candidate-flagging pass didn't exploit: Yahoo auto-sent a structured notification email to the whole group on every Files-section upload (`"New file uploaded to Traveller_TNE"`, containing fixed `File:`/`Uploaded by:`/`Description:` fields). That's a real, automatable data source for a manifest — filename, uploader, description, and upload date — for the subset of Files-section activity where that notification survived in the archive. It does not cover every file ever uploaded (some are only ever mentioned in a reply, with no notification captured), and it cannot recover the file *bytes* themselves — those only ever lived on Yahoo's own file hosting, never in the mbox.

## Decision

- A new top-level `/files/` page, linked from global nav, listing every upload the notification-manifest captures: filename, uploader, description, upload date, and a download link or an accessible "not currently available" affordance -- the same available/unavailable pattern FR-26/27 already established for post attachments, reused rather than re-invented (same `<dialog>` component, same build-time-presence detection, same `[data-open-attachment-modal]` wiring).
- The manifest (`data/files.json`) is derived automatically by `pipeline/attachments.py`'s `extract_file_upload_notifications()`, parsing Yahoo's fixed notification template -- not hand-maintained, so it can't drift from the archive the way a manually-curated list would, and it regenerates correctly on every `make data` run like everything else in the pipeline.
- Real file bytes are supplied the same way post attachments are (`attachments/<post-id>/<filename>`): dropped into `files/<source-post-id>/<filename>` at any time, with availability computed fresh at build time from the filesystem, never hand-set. The manifest and the actual files are independent concerns, exactly like the attachments schema note in dd.md §6/§7.1 (`available` is never stored in committed data) -- the same design already validated for the reason FR-27 exists.
- Out of scope, deliberately: recovering the file bytes themselves. That's a manual, ongoing task for whoever has access to a personal backup of the old Files section (data-structures.md §5's Dec 2019 "someone claims to have saved everything" lead is the most promising avenue) -- this ADR only builds the place for those files to go once found, same as attachments/ did in Phase 7 before any real file existed there.

## Consequences

- The site can now honestly represent "we know N files existed here, M are still missing" -- exactly the kind of visibility that prompted the original feedback, and a natural call-to-action for community members who might have their own copies.
- `find_files_section_candidates()`'s broader, human-reviewed candidate list remains valuable and unchanged for posts that reference a file without a captured notification email -- this manifest doesn't replace it, it covers a real but different subset.
- A second post-launch scope addition on top of a project that otherwise treated its SRS as closed before implementation began -- accepted the same way ADR-0017 was: real-world information (in that case GitHub's own hosting behavior, here real user feedback) that no amount of upfront design review could have surfaced, addressed via the same phased, ADR-documented process as everything else rather than as an undocumented side-fix.
