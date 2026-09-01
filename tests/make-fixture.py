#!/usr/bin/env python3
"""Build a SYNTHETIC tape that deterministically exercises every branch of
`alphad --analyze`: a bid wall that holds, an ask wall that breaks, an
absorption bucket, a CVD divergence, and a liquidation cascade.

This is a TEST FIXTURE, never market data. Nothing renders it to a trader.
Same seed in, same tape out, so the assertions in analyze.sh are exact.
"""
import json, sys

T0 = 1700000000.0
TICK = 0.5
out = []
def ev(d): out.append(json.dumps(d))

ev({"k": "h", "ts": T0, "feed": "synthetic fixture", "symbol": "TEST"})

def book(ts, mid, bid_wall=True, ask_wall=True):
    bids = [[round(mid - 0.5 - i * 0.5, 2), 5.0] for i in range(10)]
    asks = [[round(mid + 0.5 + i * 0.5, 2), 5.0] for i in range(10)]
    if bid_wall:
        bids.append([99.0, 50.0])          # 10x the median level -> a wall
    if ask_wall:
        asks.append([101.0, 50.0])
    ev({"k": "b", "ts": ts, "bids": bids, "asks": asks})

def trade(ts, px, sz, aggr):
    ev({"k": "t", "ts": ts, "p": round(px, 2), "s": sz, "a": aggr})

t = T0
# ── 0-190s: chop between 99.5 and 100.5. Never below 99.0, so the bid wall HOLDS.
for i in range(190):
    px = 100.0 + (0.5 if i % 4 in (1, 2) else -0.5 if i % 4 == 3 else 0.0)
    px = max(px, 99.5)
    trade(t, px, 1.0, "buy" if i % 2 == 0 else "sell")
    book(t, px)
    t += 1

# ── 190-210s: ABSORPTION — heavy volume, price pinned (tight range, big size).
for i in range(20):
    trade(t, 100.0 if i % 2 else 100.1, 8.0, "sell")
    book(t, 100.0)
    t += 1

# ── 210-250s: back to chop so the absorption bucket stands out against averages.
for i in range(40):
    px = 100.0 + (0.5 if i % 3 == 0 else -0.5 if i % 3 == 1 else 0.0)
    trade(t, px, 1.0, "buy" if i % 2 == 0 else "sell")
    book(t, px)
    t += 1

# ── 250-260s: DIVERGENCE — a new session high made on negative delta.
for i in range(10):
    trade(t, 100.9, 2.0, "sell")
    book(t, 100.9)
    t += 1

# ── 260-285s: a liquidation CASCADE (gaps of 5s, well under the 30s window).
for i in range(5):
    ev({"k": "l", "ts": t, "side": "long", "p": 100.5 - i * 0.1, "q": 3.0})
    t += 5

# ── 285-320s: price breaks ABOVE 101.0, so the ask wall BROKE.
for i in range(35):
    trade(t, 101.5 + i * 0.05, 1.0, "buy")
    book(t, 101.5 + i * 0.05, ask_wall=False)
    t += 1

ev({"k": "f", "ts": t, "r": 0.0000125, "n": T0 + 3600, "h": 1, "oi": 1234.5})
sys.stdout.write("\n".join(out) + "\n")
