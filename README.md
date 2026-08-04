# Traveller_TNE Archive

A static archive of the **Traveller_TNE** Yahoo! Group — a mailing list for *Traveller: The New Era* fans, active May 2005 – August 2019 — preserved as threaded, full-text-searchable posts after Yahoo Groups shut down in 2020.

Unofficial fan project. Not affiliated with or endorsed by Mongoose Publishing. See the site's Help page for the full disclaimer and the Notice-and-Takedown policy.

## Documentation

Full design documentation — vision, requirements, architecture, data schema, UI design, requirements traceability, and test plan — lives in [`docs/`](docs/README.md). Architecture decisions are individually recorded in [`docs/adr/`](docs/adr/README.md).

## Development

```
make help    # list all available targets
make data    # regenerate data/posts.json from mail_archives/ (local only — not run in CI)
make build   # build the static site into _site/
make serve   # local dev server with live reload
make test    # run the automated test suite
```

Requires Node 20+ and Python (version pinned in `.python-version`). Install dependencies with `npm install` and `pip install -r requirements.txt`.

The raw source archive (`mail_archives/`) is intentionally excluded from this repository — see `.gitignore` and [ADR-0008](docs/adr/0008-no-email-addresses-in-output.md).

## License

Source code is licensed under [Apache License 2.0](LICENSE). Archived post content is not covered by this license — see the site's Help page for the content-rights statement.
