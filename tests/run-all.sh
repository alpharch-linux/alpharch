#!/usr/bin/env bash
# tests/run-all.sh — everything, in order of cost.
#
#   tests/run-all.sh            all of it, including live model calls
#   tests/run-all.sh --offline  skip the live half of the fence tests
set -uo pipefail
cd "$(dirname "$(readlink -f "$0")")/.." || exit 1
rc=0
./tests/analyze.sh || rc=1
echo
./tests/desk-control.sh || rc=1
echo
./tests/calendar.sh || rc=1
echo
./tests/brain-fence.sh "${1:-}" || rc=1
echo
# Workstation, adapter, indicator, execution-simulator and layout checks.
python3 -m unittest discover -s tests -p '*.py' || rc=1
if command -v node >/dev/null 2>&1; then
    node tests/price-scale.cjs || rc=1
    node tests/live_desk.cjs || rc=1
    node tests/starters.cjs || rc=1
    node tests/chart-controls.cjs || rc=1
    node tests/trade-panel.cjs || rc=1
else
    printf 'Node.js is required for chart precision checks.\n'
    rc=1
fi
bash tests/install.sh || rc=1
if [[ $rc -eq 0 ]]; then printf '\033[38;2;70;179;123mALL SUITES PASSED\033[0m\n'
else printf '\033[38;2;220;80;87mSOME SUITES FAILED\033[0m\n'; fi
exit $rc
