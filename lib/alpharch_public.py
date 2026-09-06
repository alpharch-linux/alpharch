"""Read-only public market data for the independent chart desk.

No credentials or trading endpoints. Decimal ingestion preserves exchange quantities.
Historical candles are explicitly unclassified; order-flow studies use captured trades.
"""
import asyncio
from collections import deque
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import json
import math
import time
import urllib.request
import zlib

ASSETS = ('BTC', 'ETH', 'SOL')
PROVIDERS = ('coinbase', 'hyperliquid', 'kraken')


def timestamp(value):
    if isinstance(value, (float, int)):
        return float(value)
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def decimal(value, positive=False):
    v = Decimal(str(value))
    if not v.is_finite() or v < 0 or (positive and v <= 0):
        raise ValueError('Invalid market number')
    return v


def request_json(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                 headers={'User-Agent': 'Alpharch/desktop', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read())


class Market:
    def __init__(self, provider, asset):
        if provider not in PROVIDERS or asset not in ASSETS:
            raise ValueError('Unsupported public market')
        self.provider, self.asset = provider, asset
        self.key = provider + ':' + asset
        self.symbol = asset + ('-USD' if provider != 'hyperliquid' else '-PERP')
        self.tick = None
        self.size_decimals = 8
        self.connected = False
        self.last_message = None
        self.trade_received = None
        self.book_received = None
        self.book_time = None
        self.trades = deque(maxlen=30000)
        self.seen = set()
        self.seen_order = deque()
        self.bids, self.asks = {}, {}
        self.heat = deque(maxlen=180)
        self.last_heat = 0
        self.historical = []
        self.note = ''
        self.gap = False
        self.last_id = None
        self.funding = None
        self.oi = None
        self.started = time.time()
        self.reconnects = 0
        self.revision = 0
        self._trade_cache = None
        self._bar_cache = {}
        self._profile = {}
        self.listeners = []

    def price_tick(self, price=None):
        if self.provider != 'hyperliquid':
            return self.tick
        if price is None and self.trades:
            price = self.trades[-1]['p']
        if price is None:
            return self.tick
        # Hyperliquid permits integer prices at any magnitude; non-integers
        # have five significant figures and MAX_DECIMALS - szDecimals places.
        exponent = Decimal(str(price)).adjusted() - 4
        return min(Decimal(1), max(Decimal(10) ** exponent, self.tick or Decimal('.01')))

    def add_trade(self, ident, ts, price, size, side, received=None):
        if side not in ('buy', 'sell') and not (side is None and self.provider == 'ibkr'):
            raise ValueError('Unclassified trade')
        if ident in self.seen:
            return False
        p, q = (Decimal(str(price)) if self.provider == 'ibkr' else decimal(price, True)), decimal(size, True)
        if not p.is_finite():
            raise ValueError('Invalid trade price')
        ts = timestamp(ts)
        if not math.isfinite(ts) or ts <= 0:
            raise ValueError('Invalid exchange timestamp')
        self.seen.add(ident)
        self.seen_order.append(ident)
        if len(self.seen_order) > 60000:
            self.seen.discard(self.seen_order.popleft())
        if len(self.trades) == self.trades.maxlen:
            expired = self.trades[0]
            cell = self._profile[expired['p']]
            cell[0 if expired['side'] == 'buy' else 1 if expired['side'] == 'sell' else 2] -= expired['q']
            if not any(cell):
                del self._profile[expired['p']]
        self._profile.setdefault(p, [Decimal(0), Decimal(0), Decimal(0)])[0 if side == 'buy' else 1 if side == 'sell' else 2] += q
        self.revision += 1
        self.trades.append({'id': ident, 't': ts, 'p': p, 'q': q, 'side': side})
        self.trade_received = received or time.time()
        for listener in self.listeners:
            listener({'k':'t','id':ident,'ts':ts,'p':str(p),'s':str(q),'a':side})
        return True

    def book(self, bids, asks, ts, replace=True):
        target_bids, target_asks = ({}, {}) if replace else (self.bids.copy(), self.asks.copy())
        for rows, target in ((bids, target_bids), (asks, target_asks)):
            for price, size in rows:
                p, q = decimal(price, True), decimal(size)
                if q:
                    target[p] = q
                else:
                    target.pop(p, None)
        if target_bids and target_asks and max(target_bids) >= min(target_asks):
            self.bids, self.asks = {}, {}
            self.book_received = None
            self.note = 'Crossed book rejected; waiting for a new snapshot'
            raise ValueError('Crossed book')
        self.bids, self.asks = target_bids, target_asks
        self.book_received, self.book_time = time.time(), timestamp(ts)
        if self.listeners:
            event={'k':'b','ts':self.book_time,'bids':[[str(p),str(q)] for p,q in sorted(self.bids.items(),reverse=True)[:100]],'asks':[[str(p),str(q)] for p,q in sorted(self.asks.items())[:100]]}
            for listener in self.listeners:listener(event)
        if self.book_received - self.last_heat >= 1 and self.bids and self.asks:
            self.last_heat = self.book_received
            # Keep actual nearest levels. No invented intermediate prices.
            rows = sorted(self.bids.items(), reverse=True)[:60] + sorted(self.asks.items())[:60]
            self.heat.append({'t': self.book_time, 'levels': [[float(p), float(q)] for p, q in rows]})

    def disconnect(self, reason='Reconnecting to exchange'):
        self.connected = False
        self.bids, self.asks = {}, {}
        self.book_received = None
        self.note = reason
        if self.trades:
            self.gap = True
        self.reconnects += 1
        for listener in self.listeners:listener({'k':'g','ts':time.time(),'reason':'feed interruption'})

    def ingest_coinbase(self, msg):
        if msg.get('product_id') not in (None, self.asset + '-USD'):
            return
        self.last_message = time.time()
        kind = msg.get('type')
        if kind in ('match', 'last_match'):
            if msg.get('side') not in ('buy', 'sell'):
                raise ValueError('Unclassified Coinbase trade')
            ident = int(msg['trade_id'])
            if self.last_id is not None and ident > self.last_id + 1:
                self.gap = True
            self.last_id = max(self.last_id or 0, ident)
            self.add_trade(str(ident), msg['time'], msg['price'], msg['size'],
                           'sell' if msg['side'] == 'buy' else 'buy')
        elif kind == 'snapshot':
            self.book(msg['bids'], msg['asks'], time.time())
        elif kind == 'l2update':
            if not self.bids or not self.asks:
                raise ValueError('Book update before snapshot')
            self.book([(p, q) for s, p, q in msg['changes'] if s == 'buy'],
                      [(p, q) for s, p, q in msg['changes'] if s == 'sell'], msg['time'], False)
        elif kind == 'heartbeat':
            if self.last_id is not None and int(msg.get('last_trade_id', self.last_id)) > self.last_id:
                self.gap = True
        elif kind == 'error':
            raise ValueError(msg.get('message', 'Exchange error'))

    def ingest_hyperliquid(self, msg):
        self.last_message = time.time()
        channel, data = msg.get('channel'), msg.get('data')
        if channel == 'trades':
            for t in data or []:
                if t.get('coin') != self.asset:
                    continue
                if t.get('side') not in ('B', 'A'):
                    raise ValueError('Unclassified Hyperliquid trade')
                self.add_trade(str(t['tid']), t['time'] / 1000, t['px'], t['sz'],
                               'buy' if t['side'] == 'B' else 'sell')
        elif channel == 'l2Book' and data.get('coin') == self.asset:
            bids, asks = data['levels']
            self.book([(v['px'], v['sz']) for v in bids], [(v['px'], v['sz']) for v in asks], data['time'] / 1000)
        elif channel == 'activeAssetCtx' and data.get('coin') == self.asset:
            ctx = data.get('ctx', {})
            self.funding = float(ctx['funding']) if ctx.get('funding') else None
            self.oi = float(ctx['openInterest']) if ctx.get('openInterest') else None
        elif channel == 'error':
            raise ValueError(str(data)[:160])

    @staticmethod
    def kraken_checksum(bids, asks):
        def digits(value):
            return format(value, 'f').replace('.', '').lstrip('0')
        levels = sorted(asks.items())[:10] + sorted(bids.items(), reverse=True)[:10]
        return zlib.crc32(''.join(digits(p) + digits(q) for p, q in levels).encode()) & 0xffffffff

    def ingest_kraken(self, msg):
        self.last_message = time.time()
        if msg.get('success') is False:
            raise ValueError('Kraken subscription rejected')
        for data in msg.get('data', []) if isinstance(msg.get('data'), list) else []:
            if data.get('symbol') != self.asset + '/USD':
                continue
            if msg.get('channel') == 'trade':
                self.add_trade(str(data['trade_id']), data['timestamp'], data['price'], data['qty'], data['side'])
            elif msg.get('channel') == 'book':
                is_snapshot = msg.get('type') == 'snapshot'
                if not is_snapshot and (not self.bids or not self.asks):
                    raise ValueError('Kraken book update before snapshot')
                bids, asks = ({}, {}) if is_snapshot else (self.bids.copy(), self.asks.copy())
                for field, target in (('bids', bids), ('asks', asks)):
                    for row in data.get(field, []):
                        price, size = decimal(row['price'], True), decimal(row['qty'])
                        if size:
                            # Replacing the key also preserves its newest decimal representation.
                            target.pop(price, None)
                            target[price] = size
                        else:
                            target.pop(price, None)
                bids = dict(sorted(bids.items(), reverse=True)[:100])
                asks = dict(sorted(asks.items())[:100])
                if self.kraken_checksum(bids, asks) != int(data['checksum']):
                    self.disconnect('Kraken book checksum mismatch; resubscribing')
                    raise ValueError('Kraken checksum mismatch')
                self.book(bids.items(), asks.items(), data.get('timestamp', time.time()))

    async def metadata(self):
        if self.provider == 'coinbase':
            data = await asyncio.to_thread(request_json, 'https://api.exchange.coinbase.com/products/' + self.asset + '-USD')
            self.tick = decimal(data['quote_increment'], True)
            self.size_decimals = max(0, -Decimal(data['base_increment']).normalize().as_tuple().exponent)
            if data.get('status') != 'online':
                raise ValueError('Product is not online')
        elif self.provider == 'kraken':
            data = await asyncio.to_thread(request_json, 'https://api.kraken.com/0/public/AssetPairs?pair=' + ('XBT' if self.asset == 'BTC' else self.asset) + 'USD')
            product = next(iter(data['result'].values()))
            self.tick = decimal(product['tick_size'], True)
            self.size_decimals = int(product['lot_decimals'])
            if product.get('status') != 'online':
                raise ValueError('Kraken product is not online')
        else:
            data = await asyncio.to_thread(request_json, 'https://api.hyperliquid.xyz/info', {'type': 'meta'})
            product = next(v for v in data['universe'] if v['name'] == self.asset and not v.get('isDelisted'))
            self.size_decimals = int(product['szDecimals'])
            self.tick = Decimal(10) ** -(6 - self.size_decimals)

    async def load_history(self):
        try:
            if self.provider == 'coinbase':
                rows = await asyncio.to_thread(request_json, 'https://api.exchange.coinbase.com/products/' + self.asset + '-USD/candles?granularity=60')
                self.historical = [{'t': int(v[0]), 'o': float(v[3]), 'h': float(v[2]), 'l': float(v[1]), 'c': float(v[4]), 'v': float(v[5]), 'buy': None, 'sell': None, 'historical': True} for v in rows]
            elif self.provider == 'kraken':
                data = await asyncio.to_thread(request_json, 'https://api.kraken.com/0/public/OHLC?interval=1&pair=' + ('XBT' if self.asset == 'BTC' else self.asset) + 'USD')
                rows = next(v for k,v in data['result'].items() if k != 'last')
                self.historical = [{'t': int(v[0]), 'o': float(v[1]), 'h': float(v[2]), 'l': float(v[3]), 'c': float(v[4]), 'v': float(v[6]), 'buy': None, 'sell': None, 'historical': True} for v in rows]
            else:
                now = int(time.time() * 1000)
                rows = await asyncio.to_thread(request_json, 'https://api.hyperliquid.xyz/info', {'type': 'candleSnapshot', 'req': {'coin': self.asset, 'interval': '1m', 'startTime': now - 300 * 60000, 'endTime': now}})
                self.historical = [{'t': v['t'] / 1000, 'o': float(v['o']), 'h': float(v['h']), 'l': float(v['l']), 'c': float(v['c']), 'v': float(v['v']), 'buy': None, 'sell': None, 'historical': True} for v in rows]
            # Never include the exchange's unfinished REST candle.
            cut = int(time.time() // 60) * 60
            self.historical = sorted([v for v in self.historical if v['t'] < cut], key=lambda x: x['t'])
        except Exception as e:
            self.note = 'Historical candles unavailable: ' + type(e).__name__

    async def run(self):
        import websockets
        backoff = 1
        history_task = None
        while True:
            try:
                if self.tick is None:
                    await self.metadata()
                if history_task is None:
                    history_task = asyncio.create_task(self.load_history())
                url = 'wss://ws-feed.exchange.coinbase.com' if self.provider == 'coinbase' else 'wss://ws.kraken.com/v2' if self.provider == 'kraken' else 'wss://api.hyperliquid.xyz/ws'
                async with websockets.connect(url, open_timeout=12, ping_interval=20, max_size=2**24) as ws:
                    if self.provider == 'coinbase':
                        await ws.send(json.dumps({'type': 'subscribe', 'product_ids': [self.asset + '-USD'], 'channels': ['matches', 'level2_batch', 'heartbeat']}))
                    elif self.provider == 'kraken':
                        for channel in ('trade', 'book'):
                            params = {'channel': channel, 'symbol': [self.asset + '/USD'], 'snapshot': True}
                            if channel == 'book':
                                params['depth'] = 100
                            await ws.send(json.dumps({'method': 'subscribe', 'params': params}))
                    else:
                        for kind in ('trades', 'l2Book', 'activeAssetCtx'):
                            await ws.send(json.dumps({'method': 'subscribe', 'subscription': {'type': kind, 'coin': self.asset}}))
                    self.connected = True
                    self.note = ''
                    backoff = 1
                    while True:
                        raw = await asyncio.wait_for(ws.recv(), 35)
                        msg = json.loads(raw, parse_float=Decimal) if self.provider == 'kraken' else json.loads(raw)
                        if self.provider == 'coinbase':
                            self.ingest_coinbase(msg)
                        elif self.provider == 'kraken':
                            self.ingest_kraken(msg)
                        else:
                            self.ingest_hyperliquid(msg)
            except asyncio.CancelledError:
                if history_task:
                    history_task.cancel()
                raise
            except Exception as e:
                self.disconnect('Reconnecting · ' + type(e).__name__)
                await asyncio.sleep(backoff)
                backoff = min(30, backoff * 2)

    def trade_data(self):
        if self._trade_cache and self._trade_cache[0] == self.revision:
            return self._trade_cache[1:]
        trades = sorted(self.trades, key=lambda x: (x['t'], int(x['id']) if x['id'].isdigit() else 0))
        buckets = {}
        for trade in trades:
            buckets.setdefault(int(trade['t']//15)*15, []).append(trade)
        packed = []
        for start, rows in buckets.items():
            signature = tuple(t['id'] for t in rows)
            cached = self._bar_cache.get(start)
            if cached and cached[0] == signature:
                packed.append(cached[1])
                continue
            b = {'t':start,'o':rows[0]['p'],'h':rows[0]['p'],'l':rows[0]['p'],'c':rows[-1]['p'],
                 'v':Decimal(0),'buy':Decimal(0),'sell':Decimal(0),'pv':Decimal(0)}
            cells = {}
            for trade in rows:
                p, q, side = trade['p'], trade['q'], trade['side']
                b['h'], b['l'] = max(b['h'],p), min(b['l'],p)
                b['v'] += q
                if side is None:
                    b['buy'], b['sell'] = None, None
                elif b[side] is not None:
                    b[side] += q
                b['pv'] += p*q
                if side is not None:
                    cells.setdefault(p,[Decimal(0),Decimal(0)])[0 if side == 'sell' else 1] += q
            row = {k:float(v) if isinstance(v,Decimal) else v for k,v in b.items()}
            row['footprint'] = [[float(p),float(v[0]),float(v[1])] for p,v in sorted(cells.items())]
            self._bar_cache[start] = (signature,row)
            packed.append(row)
        for start in self._bar_cache.keys()-buckets.keys():
            del self._bar_cache[start]
        self._trade_cache = (self.revision, packed, self._profile, trades)
        return packed, self._profile, trades

    def snapshot(self):
        now = time.time()
        packed, profile, trades = self.trade_data()
        last = trades[-1] if trades else None
        stale_book = not self.connected or not self.book_received or now - self.book_received > 15
        return {'key': self.key, 'symbol': self.symbol, 'provider': self.provider, 'asset': self.asset,
                'connected': self.connected, 'status': 'disconnected' if not self.connected else 'stale' if not self.last_message or now-self.last_message > 15 else 'receiving',
                'tick': float(self.price_tick()) if self.price_tick() else None, 'sizeDecimals': self.size_decimals,
                'last': float(last['p']) if last else None, 'lastRaw': str(last['p']) if last else None,
                'tradeTime': last['t'] if last else None, 'tradeAge': now-last['t'] if last else None,
                'bookAge': now-self.book_received if self.book_received else None, 'bookTime': self.book_time,
                'capturedSince': trades[0]['t'] if trades else None, 'note': self.note, 'incomplete': self.gap,
                'bars': packed, 'historical': self.historical,
                'book': {'bids': [[str(p), str(q)] for p,q in sorted(self.bids.items(), reverse=True)[:100]] if not stale_book else [],
                         'asks': [[str(p), str(q)] for p,q in sorted(self.asks.items())[:100]] if not stale_book else []},
                'heat': list(self.heat), 'profile': [[float(p), float(q[0]), float(q[1]), float(q[2])] if q[2] else [float(p), float(q[0]), float(q[1])] for p,q in sorted(profile.items())],
                'tape': [{'id':t['id'],'t':t['t'],'p':str(t['p']),'s':str(t['q']),'a':t['side']} for t in trades[-100:]],
                'funding': self.funding, 'oi': self.oi, 'fundingHours': 1 if self.provider=='hyperliquid' else None,
                'receivedAt': now}
