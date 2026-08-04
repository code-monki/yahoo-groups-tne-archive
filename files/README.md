# Files-section source

Populated over time with recovered files from Yahoo Groups' separate Files section (ADR-0018) — genuinely distinct from `attachments/`, which holds files embedded in individual emails. These were uploaded directly to the group's shared file repository, never captured in the mbox export, and can only be recovered from someone's personal backup (see data-structures.md §5's Dec 2019 lead).

Keyed the same way `attachments/` is, by the manifest entry's `source_post_id` (the id of the "New file uploaded" notification email that recorded the upload):

```
files/<source-post-id>/<original-filename>
```

The manifest itself (`data/files.json`) is generated automatically by `pipeline/attachments.py`'s `extract_file_upload_notifications()` — parsed from Yahoo's own notification emails, not hand-maintained. Deliberately sparse — most manifest entries have no recovered file yet. The `/files/` page renders a working download link when a file is present here at build time, and an accessible "not currently available" affordance when it isn't, exactly like post attachments (FR-23/26/27). Availability is never hand-set — it's computed fresh from this directory on every build.
