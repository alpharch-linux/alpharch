#!/usr/bin/env bash
# tests/analyze.sh — the grounding layer must be exact.
#
# `alphad --analyze` is what keeps the Desk Brain honest: the model narrates
# these numbers and is forbidden from producing market data of its own. So the
# numbers have to be right, and they have to be the same every run. This drives
# a synthetic fixture (tests/make-fixture.py — a TEST FIXTURE, never presented
# as market data) through every branch and asserts the computed facts.
#
#   tests/analyze.sh            run it
set -uo pipefail
cd "$(dirname "$(readlink -f "$0")")/.." || exit 1
ALPHAD="./bin/alphad"
TAPE="$(mktemp -t alpharch-fixture-XXXXXX.jsonl)"
OUT="$(mktemp -t alpharch-analysis-XXXXXX.json)"
trap 'rm -f "$TAPE" "$OUT"' EXIT

pass=0; fail=0
ok_()   { printf '  \033[38;2;70;179;123m✓\033[0m %s\n' "$1"; pass=$((pass+1)); }
bad_()  { printf '  \033[38;2;220;80;87m✗\033[0m %s\n     expected: %s\n     got:      %s\n' "$1" "$2" "$3"; fail=$((fail+1)); }
check() { # label jq-ish-python-expr expected
  local got; got="$(python3 -c "
import json;d=json.load(open('$OUT'))
v=$2
print(v)" 2>&1)"
  [[ "$got" == "$3" ]] && ok_ "$1" || bad_ "$1" "$3" "$got"
}

printf '\033[1mANALYZE — deterministic tape facts\033[0m\n'
python3 tests/make-fixture.py > "$TAPE" || { echo "fixture build failed"; exit 1; }
"$ALPHAD" --analyze "$TAPE" --tick 0.5 --bucket 10 > "$OUT" || { echo "analyze failed"; cat "$OUT"; exit 1; }

check "schema is declared"            "d['schema']"                                     "alpharch.tape-analysis/1"
check "definitions travel with facts" "'wall' in d['definitions'] and 'cascade' in d['definitions']" "True"
check "feed read from tape header"    "d['tape']['feed']"                               "synthetic fixture"
check "symbol read from tape header"  "d['tape']['symbol']"                             "TEST"
check "session open"                  "d['session']['open']"                            "100.0"
check "session high"                  "d['session']['high']"                            "103.2"
check "session low"                   "d['session']['low']"                             "99.5"
check "bid wall detected at 99.0"     "[w['price'] for w in d['walls'] if w['side']=='bid']" "[99.0]"
check "bid wall HELD (low never < 99)" "[w['outcome'] for w in d['walls'] if w['side']=='bid'][0]" "held"
check "ask wall detected at 101.0"    "[w['price'] for w in d['walls'] if w['side']=='ask']" "[101.0]"
check "ask wall BROKE (price went through)" "[w['outcome'] for w in d['walls'] if w['side']=='ask'][0]" "broke"
check "absorption flagged"            "any('absorption' in f['note'] for f in d['flags'])" "True"
check "divergence flagged"            "any('divergence' in f['note'] for f in d['flags'])" "True"
check "one liquidation cascade"       "len(d['liquidations']['cascades'])"              "1"
check "cascade counted 5 events"      "d['liquidations']['cascades'][0]['events']"      "5"
check "cascade long qty"              "d['liquidations']['cascades'][0]['long_qty']"    "15.0"
check "funding interval carried"      "d['funding']['interval_hours']"                  "1"
check "cvd path capped at 120 points" "len(d['cvd']['path']) <= 120"                    "True"
check "timestamps carry a readable clock" "all('clock' in x for x in d['big_prints']+d['flags']) and all('first_clock' in w and 'last_clock' in w for w in d['walls'])" "True"

# determinism: the same tape must give byte-identical facts
"$ALPHAD" --analyze "$TAPE" --tick 0.5 --bucket 10 > "$OUT.2" 2>/dev/null
if diff -q <(grep -v '"path"' "$OUT") <(grep -v '"path"' "$OUT.2") >/dev/null 2>&1; then
  ok_ "deterministic — same tape, same facts"
else
  bad_ "deterministic — same tape, same facts" "identical" "differs"
fi
rm -f "$OUT.2"

# An empty or bogus tape must fail honestly, not print a session of zeros.
# NOTE: capture first, then grep — under `set -o pipefail` a pipeline inherits
# alphad's deliberate exit 1 and the `if` would read it as "no error found".
: > "$TAPE"
empty_out="$("$ALPHAD" --analyze "$TAPE" 2>/dev/null)"; empty_rc=$?
if grep -q '"error"' <<<"$empty_out" && [[ "$empty_rc" -ne 0 ]]; then
  ok_ "empty tape reports an error and exits non-zero"
else
  bad_ "empty tape reports an error and exits non-zero" "error key + rc!=0" "rc=$empty_rc out=${empty_out:0:60}"
fi

# a tape that is not JSON at all must also fail honestly
printf 'this is not json\n' > "$TAPE"
junk_out="$("$ALPHAD" --analyze "$TAPE" 2>/dev/null)"; junk_rc=$?
if grep -q '"error"' <<<"$junk_out" && [[ "$junk_rc" -ne 0 ]]; then
  ok_ "unreadable tape reports an error and exits non-zero"
else
  bad_ "unreadable tape reports an error and exits non-zero" "error key + rc!=0" "rc=$junk_rc out=${junk_out:0:60}"
fi

printf '\n  %d passed, %d failed\n' "$pass" "$fail"
[[ "$fail" -eq 0 ]]
