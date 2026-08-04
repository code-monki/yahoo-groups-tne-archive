#!/usr/bin/env bash
# Orchestrates `make test` (dd.md §10, test-plan.md §12): data-integrity
# checks run first and gate everything else (a data problem should stop
# the suite before wasting time on a site built from bad data), then the
# site-dependent checks all need a real server -- Pagefind's runtime fetch
# and linkinator's crawl both need actual HTTP responses, not just files
# on disk, and (per ADR-0017) the dev server is what correctly serves
# under the same /yahoo-groups-tne-archive/ pathPrefix production does.
set -uo pipefail

cd "$(dirname "$0")/.."

python3 tests/test_data_integrity.py
DATA_EXIT=$?
if [ $DATA_EXIT -ne 0 ]; then
  echo "Data integrity checks failed -- stopping before site-dependent tests."
  exit $DATA_EXIT
fi

npx @11ty/eleventy --serve --port 8098 --quiet &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null' EXIT

for i in $(seq 1 30); do
  curl -s -o /dev/null http://localhost:8098/yahoo-groups-tne-archive/ && break
  sleep 1
done

npx playwright test
PLAYWRIGHT_EXIT=$?

npx lhci autorun --config=lighthouserc.js
LHCI_MOBILE_EXIT=$?

npx lhci autorun --config=lighthouserc.desktop.js
LHCI_DESKTOP_EXIT=$?

# TC-LINK-01 is scoped to internal links (test-plan.md §5's own framing --
# "no forms that write anywhere... no attack surface" already puts
# third-party concerns out of scope, §1). External links in 15-20-year-old
# archived posts are expected to rot over time and this project can't fix
# that; canonical <link> tags point at the real production URL, which
# doesn't exist yet in a pre-deploy CI run by definition. Both are
# excluded so this only gates on the site's own link graph.
npx linkinator http://localhost:8098/yahoo-groups-tne-archive/ --recurse \
  --skip "^(?!http://localhost:8098).*"
LINKINATOR_EXIT=$?

EXIT=0
[ $PLAYWRIGHT_EXIT -ne 0 ] && { echo "FAIL: playwright"; EXIT=1; }
[ $LHCI_MOBILE_EXIT -ne 0 ] && { echo "FAIL: lighthouse (mobile)"; EXIT=1; }
[ $LHCI_DESKTOP_EXIT -ne 0 ] && { echo "FAIL: lighthouse (desktop)"; EXIT=1; }
[ $LINKINATOR_EXIT -ne 0 ] && { echo "FAIL: linkinator"; EXIT=1; }
exit $EXIT
