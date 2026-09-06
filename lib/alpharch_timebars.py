"""Exact time buckets from retained prints plus non-overlapping public OHLC history.

UTC boundaries. History requests are bounded, cached, and never used in replay.
Historical OHLCV never acquires an invented aggressor classification.
"""
import asyncio
import math
import time
from datetime import datetime, timezone
from decimal import Decimal
from alpharch_public import request_json


def history_resolution(seconds):
    # Only use a base candle that divides the requested interval exactly.
    return next((r for r in (86400, 3600, 900, 300, 60) if seconds % r == 0), None)


def time_bars(trades, seconds, history=(), resolution=60):
    if isinstance(seconds, bool) or not isinstance(seconds, int) or not 1 <= seconds <= 31622400:
        raise ValueError('Invalid time interval')
    rows = []
    # Exclude the REST minute/hour containing our first print. This deliberately
    # leaves the unobserved transition partial, rather than counting volume twice.
    cut = math.floor(trades[0]['t'] / resolution) * resolution if trades else math.inf
    for row in history:
        if row['t'] < cut:
            rows.append({**row, 'end': row['t'] + resolution, 'partial': False})
    for trade in trades:
        p, q = float(trade['p']), float(trade['q'])
        side = trade['side']
        rows.append({'t': trade['t'], 'end': trade['t'], 'o': p, 'h': p, 'l': p, 'c': p,
                     'v': q, 'buy': q if side == 'buy' else 0 if side else None,
                     'sell': q if side == 'sell' else 0 if side else None,
                     'pv': float(trade['p'] * trade['q']),
                     'footprint': [[p, q if side == 'sell' else 0, q if side == 'buy' else 0]] if side else [],
                     'partial': True})
    buckets = {}
    for row in sorted(rows, key=lambda r: r['t']):
        start = math.floor(row['t'] / seconds) * seconds
        b = buckets.get(start)
        if b is None:
            b = {'t': start, 'end': start + seconds, 'o': row['o'], 'h': row['h'], 'l': row['l'], 'c': row['c'],
                 'v': Decimal(0), 'buy': Decimal(0), 'sell': Decimal(0), 'pv': Decimal(0), 'historical': False,
                 'partial': row['t'] > start and (row.get('historical') or trades and row['t'] == trades[0]['t']), 'coveredUntil': start, 'cells': {}}
            buckets[start] = b
        if row.get('historical') and row['t'] > b['coveredUntil']:
            b['partial'] = True
        b['h'], b['l'], b['c'] = max(b['h'], row['h']), min(b['l'], row['l']), row['c']
        b['v'] += Decimal(str(row['v']))
        for key in ('buy', 'sell', 'pv'):
            if row.get(key) is None:
                b[key] = None
            elif b[key] is not None:
                b[key] += Decimal(str(row[key]))
        b['historical'] |= row.get('historical', False)
        b['coveredUntil'] = max(b['coveredUntil'], row['end'])
        if row.get('partial') and b['historical'] and row['t'] - (cut if math.isfinite(cut) else row['t']) < resolution:
            b['partial'] = True
        for p, bid, ask in row.get('footprint', []):
            cell = b['cells'].setdefault(p, [Decimal(0), Decimal(0)])
            cell[0] += Decimal(str(bid)); cell[1] += Decimal(str(ask))
    result = []
    for b in buckets.values():
        cells = b.pop('cells'); b.pop('coveredUntil')
        b['footprint'] = [[p, float(q[0]), float(q[1])] for p, q in sorted(cells.items())]
        result.append({k: float(v) if isinstance(v, Decimal) else v for k, v in b.items()})
    return result


class History:
    def __init__(self):
        self.cache = {}
        self.tasks = {}
        self.semaphore = asyncio.Semaphore(2)

    def get(self, market, seconds, bars=300, days=None):
        resolution = history_resolution(seconds)
        if resolution is None or market.provider not in ('coinbase', 'kraken', 'hyperliquid'):
            return [], 'Captured trades only', resolution or 1
        needed = min(2400, max(300, math.ceil(bars * seconds / resolution)))
        key = (market.key, resolution, needed)
        entry = self.cache.get(key)
        if key not in self.tasks and (not entry or time.monotonic() - entry[0] > 60):
            if len(self.cache) >= 64:
                oldest = min(self.cache, key=lambda k: self.cache[k][0]); self.cache.pop(oldest)
            self.tasks[key] = asyncio.create_task(self.load(market, resolution, key, needed))
        return (entry[1], entry[2], resolution) if entry else ([], 'Loading exchange history…', resolution)

    async def load(self, market, resolution, key, needed):
        try:
            async with self.semaphore:
                now = time.time()
                if market.provider == 'coinbase':
                    rows = []
                    end = math.floor(now / resolution) * resolution
                    for _ in range(math.ceil(needed / 300)):
                        start = end - 300 * resolution
                        stamp = lambda value: datetime.fromtimestamp(value, timezone.utc).isoformat().replace('+00:00', 'Z')
                        raw = await asyncio.to_thread(request_json, 'https://api.exchange.coinbase.com/products/' + market.asset + '-USD/candles?granularity=' + str(resolution) + '&start=' + stamp(start) + '&end=' + stamp(end))
                        batch = [(v[0], v[3], v[2], v[1], v[4], v[5]) for v in raw if start <= v[0] < end]
                        rows.extend(batch)
                        if not batch: break
                        end = start
                        if len(rows) < needed: await asyncio.sleep(.2)
                elif market.provider == 'kraken':
                    raw = await asyncio.to_thread(request_json, 'https://api.kraken.com/0/public/OHLC?interval=' + str(resolution // 60) + '&pair=' + ('XBT' if market.asset == 'BTC' else market.asset) + 'USD')
                    values = next(v for k, v in raw['result'].items() if k != 'last')
                    rows = [(v[0], v[1], v[2], v[3], v[4], v[6]) for v in values]
                else:
                    interval = {60:'1m', 300:'5m', 900:'15m', 3600:'1h', 86400:'1d'}[resolution]
                    raw = await asyncio.to_thread(request_json, 'https://api.hyperliquid.xyz/info', {'type':'candleSnapshot', 'req':{'coin':market.asset, 'interval':interval, 'startTime':int((now - needed * resolution)*1000), 'endTime':int(now*1000)}})
                    rows = [(v['t']/1000, v['o'], v['h'], v['l'], v['c'], v['v']) for v in raw]
                clean = []
                for values in rows:
                    t, o, h, l, c, v = map(float, values)
                    if not all(math.isfinite(x) for x in (t, o, h, l, c, v)) or min(o,l,c)<=0 or h<max(o,l,c) or l>min(o,c) or v<0:
                        raise ValueError('Invalid candle')
                    if t + resolution <= now and t % resolution == 0:
                        clean.append(dict(t=t,o=o,h=h,l=l,c=c,v=v,buy=None,sell=None,pv=None,historical=True))
                clean = sorted({r['t']:r for r in clean}.values(), key=lambda r:r['t'])[-needed:]
                self.cache[key] = (time.monotonic(), clean, ('Exchange OHLCV + captured trades · '+str(len(clean))+' source candles') if clean else 'Exchange returned no history')
        except Exception:
            self.cache[key] = (time.monotonic(), self.cache.get(key, (0,[],''))[1], 'History request failed · retrying')
        finally:
            self.tasks.pop(key, None)

    async def close(self):
        tasks = list(self.tasks.values())
        for task in tasks: task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
