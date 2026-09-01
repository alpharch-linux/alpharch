#!/usr/bin/env bash
# desk-control tests: validation, socket round-trip, hostile input.
set -uo pipefail
cd "$(dirname "$(readlink -f "$0")")/.." || exit 1
UP=$'\033[38;2;70;179;123m'; RED=$'\033[38;2;220;80;87m'; R=$'\033[0m'
pass=0; fail=0
ok(){ printf '  %b✓%b %s\n' "$UP" "$R" "$1"; pass=$((pass+1)); }
bad(){ printf '  %b✗%b %s\n' "$RED" "$R" "$1"; fail=$((fail+1)); }

ALPHARCH_STATE="$(mktemp -d)"
export ALPHARCH_STATE
python3 - <<'PY' && ok "apply_ctrl validates and applies" || bad "apply_ctrl validates and applies"
import importlib.util, shutil, sys
shutil.copy("bin/alphad", "/tmp/_ad_dc.py")
spec = importlib.util.spec_from_file_location("_ad_dc", "/tmp/_ad_dc.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
eng = m.Engine(10, 60, 8, 3); state = {"view": "flow"}
r = m.apply_ctrl(eng, state, {"view":"heat","tick":25,"bars":{"mode":"range","range":40},"indicators":{"vwap":True}})
assert r["applied"]["view"] == "heat" and eng.tick == 25 and eng.bar_mode == "range" and eng.bar_range == 40
assert state["indicators"]["vwap"] is True
sys.exit(0)
PY

python3 - <<'PY' && ok "hostile input applies nothing" || bad "hostile input applies nothing"
import importlib.util, sys
spec = importlib.util.spec_from_file_location("_ad_dc", "/tmp/_ad_dc.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
eng = m.Engine(10, 60, 8, 3); state = {"view": "flow"}
r = m.apply_ctrl(eng, state, {"view":"x; rm -rf /","tick":-1,"bars":{"mode":"range","range":1e12},
                              "indicators":{"vwap":"yes","evil":True}})
assert r["applied"].get("view") is None and eng.tick == 10 and eng.bar_mode == "time"
sys.exit(0)
PY

python3 - <<'PY' && ok "range bars roll on travel, not time" || bad "range bars roll on travel, not time"
import importlib.util, sys
spec = importlib.util.spec_from_file_location("_ad_dc", "/tmp/_ad_dc.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
eng = m.Engine(1, 60, 8, 3); eng.bar_mode = "range"; eng.bar_range = 10
t = 1000.0
for px in (100, 104, 109, 110.5, 111, 121):   # crosses 10 travel twice
    eng.on_trade(m.Trade(t, px, 1.0, "buy")); t += 1
assert len(eng.buckets) == 2, len(eng.buckets)
sys.exit(0)
PY

python3 - <<'PY' && ok "vwap series is the true volume-weighted mean" || bad "vwap series correctness"
import importlib.util, sys
spec = importlib.util.spec_from_file_location("_ad_dc", "/tmp/_ad_dc.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
eng = m.Engine(1, 60, 8, 3)
eng.on_trade(m.Trade(1, 100, 1, "buy")); eng.on_trade(m.Trade(2, 200, 3, "sell"))
assert abs(eng.vwap_series[-1][1] - 175.0) < 1e-9
sys.exit(0)
PY

printf '\n  %d passed, %d failed\n' "$pass" "$fail"
exit "$fail"
