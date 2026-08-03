# Design Documents

System design documentation for the Traveller_TNE Archive site, in the order they're produced.

| Doc | Status | Description |
|---|---|---|
| [data-structures.md](data-structures.md) | Done | Reverse-engineered structure of the source mbox/Mork files. |
| [concept.md](concept.md) | Done | Vision, initial feature set, and direction. |
| [srs.md](srs.md) | Draft | Formal, numbered requirements (FR/DR/NFR/IR), derived from the concept doc. |
| [hld.md](hld.md) | Draft | Architecture: tech stack (Eleventy + Pagefind + Python ETL), data schema, threading algorithm, IA, accessibility approach. |
| [adr/](adr/README.md) | Ongoing | Architecture Decision Records — one durable, dated file per significant decision, added to as the project progresses (not a single doc that gets "finished"). |
| [dd.md](dd.md) | Draft | Detailed design: full field-by-field schema, ETL module breakdown, Eleventy site structure, build pipeline commands. |
| [ui-design.md](ui-design.md) | Draft | Visual design spec: contrast-verified color tokens, typography, spacing, component specs. |
| [rtm.md](rtm.md) | Draft | Every SRS requirement traced to its design decision and planned verification method; surfaced and closed 5 gaps along the way (FR-20 ×2 passes, FR-18/25, NFR-6 ×2 passes). |
| [test-plan.md](test-plan.md) | Draft | Concrete, numbered test cases for every RTM verification method; entry/exit criteria, defect-severity gating, CI integration. |
