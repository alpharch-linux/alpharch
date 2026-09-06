"""Local paper execution only. No network transport, broker login or real orders.

Fills model a cross against observed top-of-book, capped at displayed quantity.
They do not model queue position, fees, latency or exchange matching priority.
"""
import math
import sqlite3
import time
import uuid
from decimal import Decimal


class PaperAccount:
    environment = 'SIMULATION'
    account = 'SIM-LOCAL'

    def __init__(self, path, symbol):
        self.symbol = symbol
        self.enabled = False
        self.quote_version = None
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('''CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY, symbol TEXT NOT NULL, side TEXT NOT NULL,
            quantity INTEGER NOT NULL, kind TEXT NOT NULL, price REAL,
            status TEXT NOT NULL, filled INTEGER NOT NULL DEFAULT 0,
            average REAL, created REAL NOT NULL)''')
        self.db.execute('''CREATE TABLE IF NOT EXISTS fills (
            id TEXT PRIMARY KEY, order_id TEXT NOT NULL, quantity INTEGER NOT NULL,
            price REAL NOT NULL, source_time REAL NOT NULL, created REAL NOT NULL)''')
        self.db.commit()

    def submit(self, message, tick):
        if not self.enabled:
            raise ValueError('Enable local paper trading first')
        if message.get('environment') != self.environment or message.get('account') != self.account:
            raise ValueError('Explicit SIMULATION / SIM-LOCAL identity required')
        if message.get('symbol') != self.symbol:
            raise ValueError('Order symbol does not match this workspace')
        side, kind, quantity = (message.get(k) for k in ('side', 'kind', 'quantity'))
        if side not in ('buy', 'sell') or kind not in ('market', 'limit'):
            raise ValueError('Paper orders support buy/sell and market/limit only')
        if type(quantity) is not int or not 1 <= quantity <= 100:
            raise ValueError('Paper quantity must be 1–100 whole units')
        price = message.get('price') if kind == 'limit' else None
        if kind == 'limit':
            if not isinstance(price, (float, int)) or not math.isfinite(price):
                raise ValueError('Finite limit price required')
            if Decimal(str(price)) % Decimal(str(tick)):
                raise ValueError('Limit price must align with the contract tick')
        order_id = message.get('id')
        if not isinstance(order_id, str) or not 8 <= len(order_id) <= 80:
            raise ValueError('Stable client order ID required')
        existing = self.db.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
        if existing:
            expected = (self.symbol, side, quantity, kind, price)
            if tuple(existing[k] for k in ('symbol','side','quantity','kind','price')) != expected:
                raise ValueError('Order ID already used with different fields')
            return order_id
        with self.db:
            self.db.execute('INSERT INTO orders VALUES(?,?,?,?,?,?,?,0,NULL,?)',
                            (order_id, self.symbol, side, quantity, kind, price, 'working', time.time()))
        return order_id

    def cancel(self, order_id):
        with self.db:
            self.db.execute("UPDATE orders SET status='cancelled' WHERE id=? AND symbol=? AND status IN ('working','partial')",
                            (order_id, self.symbol))

    def match(self, bids, asks, source_time, version, stale=False):
        if not self.enabled or stale or version is None or self.quote_version == version:
            return
        self.quote_version = version
        available = {'buy': [min(asks), int(asks[min(asks)])] if asks else None,
                     'sell': [max(bids), int(bids[max(bids)])] if bids else None}
        with self.db:
            for order in self.db.execute("SELECT * FROM orders WHERE symbol=? AND status IN ('working','partial') ORDER BY created,id", (self.symbol,)).fetchall():
                quote = available[order['side']]
                if not quote or quote[1] <= 0:
                    continue
                price = quote[0]
                if order['kind'] == 'limit' and ((order['side']=='buy' and price>order['price']) or (order['side']=='sell' and price<order['price'])):
                    continue
                quantity = min(order['quantity'] - order['filled'], quote[1])
                quote[1] -= quantity
                filled = order['filled'] + quantity
                average = ((order['average'] or 0)*order['filled']+price*quantity)/filled
                self.db.execute('INSERT INTO fills VALUES(?,?,?,?,?,?)',
                                (str(uuid.uuid4()), order['id'], quantity, price, source_time, time.time()))
                self.db.execute('UPDATE orders SET filled=?, average=?, status=? WHERE id=?',
                                (filled, average, 'filled' if filled==order['quantity'] else 'partial', order['id']))

    def snapshot(self):
        return {'environment':self.environment,'account':self.account,'enabled':self.enabled,
                'orders':[dict(r) for r in self.db.execute('SELECT * FROM orders WHERE symbol=? ORDER BY created DESC LIMIT 50', (self.symbol,))],
                'fills':[dict(r) for r in self.db.execute('SELECT f.* FROM fills f JOIN orders o ON f.order_id=o.id WHERE o.symbol=? ORDER BY f.created DESC LIMIT 100',(self.symbol,))],
                'model':'Observed top-of-book cross; whole units; no queue, fees or latency model. Not broker execution.'}
