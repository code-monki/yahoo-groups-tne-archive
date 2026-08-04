# Attachment source

Populated over time with files referenced by archived posts (DR-8, ADR-0006), keyed as:

```
attachments/<post-id>/<original-filename>
```

Deliberately sparse — most posts have no attachment, and some referenced attachments (Yahoo Groups' separate Files/Photos section, never captured in the mbox export) may never be recovered. A post's page renders a working download link when its file is present here at build time, and an accessible "not currently available" affordance when it isn't (FR-23/FR-26/FR-27). Availability is never hand-set — it's computed fresh from this directory on every build.
