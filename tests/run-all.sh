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
if [[ $rc -eq 0 ]]; then printf '\033[38;2;70;179;123mALL SUITES PASSED\033[0m\n'
else printf '\033[38;2;220;80;87mSOME SUITES FAILED\033[0m\n'; fi
exit $rc
