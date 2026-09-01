#!/usr/bin/env bash
# tests/calendar.sh — trade-cal against a fixture feed. Offline, no network.
set -uo pipefail
cd "$(dirname "$(readlink -f "$0")")/.." || exit 1

UP=$'\033[38;2;70;179;123m'; RED=$'\033[38;2;220;80;87m'; R=$'\033[0m'
pass=0; fail=0
ok()  { printf '  %b✓%b %s\n' "$UP" "$R" "$1"; pass=$((pass+1)); }
bad() { printf '  %b✗%b %s\n' "$RED" "$R" "$1"; fail=$((fail+1)); }

printf '\033[1mCALENDAR — trade-cal on a fixture feed\033[0m\n'

FIX="$(mktemp -d)"
trap 'rm -rf "$FIX"' EXIT
cat > "$FIX/feed.json" <<'EOF'
[
 {"title":"CPI m/m","country":"USD","date":"2026-09-01T08:30:00-04:00","impact":"High","forecast":"0.3%","previous":"0.2%"},
 {"title":"G20 Meetings","country":"ALL","date":"2026-09-01T11:15:00-04:00","impact":"Low","forecast":"","previous":""},
 {"title":"Prelim Industrial Production m/m","country":"JPY","date":"2026-08-30T19:50:00-04:00","impact":"Medium","forecast":"-0.7%","previous":"1.3%"},
 {"title":"ECB Press Conference","country":"EUR","date":"2026-09-03T08:45:00-04:00","impact":"High","forecast":"","previous":""},
 {"title":"FOMC Member Speaks","country":"USD","date":"2026-09-02T14:00:00-04:00","impact":"Medium","forecast":"","previous":""}
]
EOF
export ALPHARCH_CAL_FILE="$FIX/feed.json"
export ALPHARCH_CAL_NOW="2026-09-01T07:00:00-04:00"
export ALPHARCH_NO_THEME=1
export TZ=America/New_York

# 1. today filters to the day and the configured currencies (USD default)
out="$(./bin/trade-cal today --plain)"
if grep -q "CPI m/m" <<<"$out" && ! grep -q "ECB" <<<"$out" && ! grep -q "Industrial" <<<"$out"; then
  ok "today shows today's USD events only"
else bad "today filter wrong: $out"; fi

# 2. high impact is flagged, forecast/previous survive
if grep -q '^! .*CPI m/m.*f 0.3% · p 0.2%' <<<"$out"; then
  ok "high impact flagged with forecast and previous"
else bad "impact/forecast row wrong: $out"; fi

# 3. --all widens currencies; week shows the week ordered
out="$(./bin/trade-cal week --plain --all)"
first="$(grep -v '^$' <<<"$out" | head -1)"
if grep -q "ECB Press Conference" <<<"$out" && grep -q "Industrial" <<<"$first"; then
  ok "week --all shows every currency, time-ordered"
else bad "week ordering/currencies wrong: $out"; fi

# 4. next counts down to the nearest future high-impact event
out="$(./bin/trade-cal next --plain)"
if grep -q "CPI m/m (USD) in 1h 30m" <<<"$out"; then
  ok "next computes the countdown to the nearest high-impact event"
else bad "next wrong: $out"; fi

# 5. after the last event, next says so honestly
out="$(ALPHARCH_CAL_NOW="2026-09-04T00:00:00-04:00" ./bin/trade-cal next --plain)"
if grep -q "no more events this week" <<<"$out"; then
  ok "an exhausted week says so instead of inventing"
else bad "exhausted week wrong: $out"; fi

# 6. --json is machine-clean and carries the source label
out="$(./bin/trade-cal --json today)"
if python3 -c '
import json,sys
d = json.loads(sys.stdin.read())
assert d["source"] == "forexfactory weekly feed"
assert len(d["events"]) == 1 and d["events"][0]["title"] == "CPI m/m"
' <<<"$out" 2>/dev/null; then
  ok "--json emits valid, labeled machine output"
else bad "--json wrong: $out"; fi

# 7. hostile/garbage feed entries are skipped, not fatal
cat > "$FIX/bad.json" <<'EOF'
[
 {"title":"No date at all","country":"USD","impact":"High"},
 {"title":"Bad date","country":"USD","date":"not-a-date","impact":"High"},
 {"title":"NFP","country":"USD","date":"2026-09-01T08:30:00-04:00","impact":"High","forecast":"180K","previous":"140K"}
]
EOF
out="$(ALPHARCH_CAL_FILE="$FIX/bad.json" ./bin/trade-cal today --plain)"
if grep -q "NFP" <<<"$out" && ! grep -q "Bad date" <<<"$out"; then
  ok "malformed feed rows are dropped, good rows survive"
else bad "garbage handling wrong: $out"; fi

echo
printf '  %d passed, %d failed\n' "$pass" "$fail"
exit "$((fail > 0))"
