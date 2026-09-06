"""Optional official TWS API bridge. No broker credentials or order operations.

Commands are called by one owner; SDK callbacks run on a reader thread. Drain
poll() only to that owner's browser. Decimal strings retain SDK-provided values;
the SDK itself represents prices as doubles. See docs/ibkr-bridge.md.
"""
from decimal import Decimal, InvalidOperation
import queue
import re
import threading
import time


class IBKRError(ValueError):
    pass


def _sdk():
    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from ibapi.contract import Contract
    return EClient, EWrapper, Contract


def number(value, nonnegative=False):
    """Reject unset/nonfinite API numbers; never round to a guessed tick."""
    try:
        result = Decimal(str(value))
        if not result.is_finite() or abs(result) >= Decimal('1e30'):
            raise ValueError()
        if nonnegative and result < 0:
            raise ValueError()
        return format(result, 'f')
    except (InvalidOperation, ValueError, TypeError):
        raise IBKRError('Missing or invalid numeric data from IBKR.') from None


def price_increment(price, rules, minimum=None):
    """Resolve an exchange's returned price bands, including negative prices."""
    price = Decimal(number(price))
    matches = [(Decimal(number(r['lowEdge'])), number(r['increment'], True)) for r in rules]
    matches = [(edge, tick) for edge, tick in matches if edge <= price and Decimal(tick) > 0]
    if matches:
        return max(matches, key=lambda row: row[0])[1]
    if minimum is not None and Decimal(number(minimum, True)) > 0:
        return number(minimum, True)
    return None


CONTRACT_FIELDS = ('conId', 'symbol', 'secType', 'exchange', 'currency',
                   'lastTradeDateOrContractMonth', 'localSymbol', 'tradingClass', 'multiplier')


def contract_spec(value, resolved=False):
    if not isinstance(value, dict) or set(value) - set(CONTRACT_FIELDS):
        raise IBKRError('Choose a futures contract returned by contract search.')
    data = dict(value)
    if data.get('secType', 'FUT') != 'FUT':
        raise IBKRError('This bridge supports dated futures, not continuous contracts.')
    data['secType'] = 'FUT'
    for key, text in data.items():
        if key == 'conId':
            if isinstance(text, bool) or not isinstance(text, int) or not 0 < text < 2**31:
                raise IBKRError('Invalid IBKR contract ID.')
        elif not isinstance(text, str) or len(text) > 64 or any(ord(c) < 32 for c in text):
            raise IBKRError('Invalid contract field.')
    if not data.get('exchange') or not data.get('currency'):
        raise IBKRError('Specify the contract exchange and currency.')
    if not data.get('conId') and not data.get('symbol'):
        raise IBKRError('Specify a futures symbol or contract ID.')
    expiry = data.get('lastTradeDateOrContractMonth', '')
    if expiry and not re.fullmatch(r'\d{6}(\d{2})?', expiry):
        raise IBKRError('Use a YYYYMM or YYYYMMDD contract expiry.')
    if resolved and not data.get('conId'):
        raise IBKRError('Select a resolved contract ID before subscribing.')
    return data


class IBKRBridge:
    def __init__(self, *, capacity=20000, sdk_loader=None, handshake_timeout=12):
        if not isinstance(capacity, int) or not 4 <= capacity <= 200000:
            raise ValueError('Event capacity must be between 4 and 200000.')
        self._queue = queue.Queue(capacity)
        self._loader = sdk_loader or _sdk
        self._timeout = handshake_timeout
        self._lock = threading.RLock()
        self._generation = 0
        self._client = None
        self._thread = None
        self._timer = None
        self._overflow = False
        self._state = 'disconnected'
        self._ready = False
        self._accounts = []
        self._requests = {}
        self._next_request = 1000
        self._contract_class = None

    def status(self):
        with self._lock:
            return {'state': self._state, 'ready': self._ready,
                    'accountCount': len(self._accounts), 'subscriptions': len(self._requests),
                    'accountTested': False, 'execution': False}

    def _push(self, kind, **values):
        with self._lock:
            if self._overflow:
                return
            event = {'type': kind, 'provider': 'ibkr', 'receivedAt': time.time(), **values}
            try:
                self._queue.put_nowait(event)
                return
            except queue.Full:
                self._overflow = True
                self._ready = False
                self._state = 'overflow'
                while not self._queue.empty():
                    try: self._queue.get_nowait()
                    except queue.Empty: break
                self._queue.put_nowait({'type': 'state', 'provider': 'ibkr', 'state': 'overflow',
                    'receivedAt': time.time(), 'gap': True,
                    'message': 'The chart consumer fell behind. Data was discarded; reconnect to rebuild the book.'})
        # No silent data loss, no blocking the reader behind a frozen UI.
        if self._client:
            self._client.disconnect()

    def _state_event(self, state, message):
        with self._lock:
            if self._overflow:
                return
            self._state = state
            self._ready = state == 'connected'
        self._push('state', state=state, message=message)

    def poll(self, limit=1000):
        if not isinstance(limit, int) or not 1 <= limit <= 20000:
            raise ValueError('Poll between 1 and 20000 events.')
        events = []
        for _ in range(limit):
            try: events.append(self._queue.get_nowait())
            except queue.Empty: break
        return events

    def connect(self, host='127.0.0.1', port=7497, client_id=71):
        if host not in ('127.0.0.1', 'localhost'):
            raise IBKRError('Only a gateway on this computer is supported.')
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise IBKRError('Choose the API socket port configured in TWS or IB Gateway.')
        if isinstance(client_id, bool) or not isinstance(client_id, int) or not 1 <= client_id < 2**31:
            raise IBKRError('Choose a nonzero client ID unique to this connection.')
        self.disconnect()
        with self._lock:
            self._overflow = False
            while not self._queue.empty():
                try: self._queue.get_nowait()
                except queue.Empty: break
        try:
            Client, Wrapper, self._contract_class = self._loader()
        except (ImportError, ModuleNotFoundError):
            self._state_event('setup required', 'Install the official TWS API Python client in the Alpharch runtime. Public crypto does not require it.')
            return False
        generation = self._generation
        bridge = self

        class Adapter(Wrapper, Client):
            def __init__(self):
                Wrapper.__init__(self)
                Client.__init__(self, self)
            def nextValidId(self, _order_id):
                # This callback establishes API readiness; no order ID is used.
                bridge._callback(generation, 'ready')
            def managedAccounts(self, accountsList):
                bridge._callback(generation, 'accounts', accountsList)
            def connectionClosed(self):
                bridge._callback(generation, 'closed')
            def error(self, reqId, *args):
                # Legacy: code, message, advanced JSON. Current SDK inserts errorTime.
                code = args[1] if len(args) > 1 and isinstance(args[1], int) else args[0] if args else -1
                bridge._callback(generation, 'error', reqId, code)
            def contractDetails(self, reqId, details):
                bridge._callback(generation, 'contract', reqId, details)
            def contractDetailsEnd(self, reqId):
                bridge._callback(generation, 'contract_end', reqId)
            def marketRule(self, marketRuleId, priceIncrements):
                bridge._callback(generation, 'rule', marketRuleId, priceIncrements)
            def marketDataType(self, reqId, marketDataType):
                bridge._callback(generation, 'data_type', reqId, marketDataType)
            def tickPrice(self, reqId, tickType, price, attrib):
                bridge._callback(generation, 'quote', reqId, tickType, price)
            def tickSize(self, reqId, tickType, size):
                bridge._callback(generation, 'quote_size', reqId, tickType, size)
            def tickByTickAllLast(self, reqId, tickType, timestamp, price, size, attrib, exchange, specialConditions):
                bridge._callback(generation, 'trade', reqId, tickType, timestamp, price, size, attrib, exchange, specialConditions)
            def updateMktDepth(self, reqId, position, operation, side, price, size):
                bridge._callback(generation, 'depth', reqId, position, operation, side, price, size, '', False)
            def updateMktDepthL2(self, reqId, position, marketMaker, operation, side, price, size, isSmartDepth=False):
                bridge._callback(generation, 'depth', reqId, position, operation, side, price, size, marketMaker, isSmartDepth)

        self._client = Adapter()
        client = self._client
        self._state_event('connecting', 'Waiting for the local gateway API handshake. Sign in through IBKR itself.')

        def run():
            try:
                client.connect('127.0.0.1', port, clientId=client_id)
                if generation == self._generation:
                    client.run()
            except Exception:
                if generation == self._generation:
                    self._state_event('disconnected', 'Could not connect to the local IBKR API. Check the socket port, sign-in and API settings.')
            finally:
                if generation == self._generation and self._state in ('connecting', 'connected'):
                    self._callback(generation, 'closed')

        def expired():
            if generation == self._generation and not self._ready:
                self._state_event('timeout', 'The gateway did not complete its API handshake. Check the IBKR connection prompt and API settings.')
                client.disconnect()

        self._thread = threading.Thread(target=run, name='alpharch-ibkr', daemon=True)
        self._timer = threading.Timer(self._timeout, expired)
        self._timer.daemon = True
        self._thread.start()
        self._timer.start()
        return True

    def disconnect(self):
        with self._lock:
            self._generation += 1
            self._ready = False
            self._accounts = []
            self._requests.clear()
        if self._timer:
            self._timer.cancel()
        client, self._client = self._client, None
        if client:
            client.disconnect()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=1)
        self._state_event('disconnected', 'Local API connection closed.')

    def _request(self, kind, contract=None, **extra):
        if not self._ready:
            raise IBKRError('Wait for the gateway API handshake.')
        if len(self._requests) >= 64:
            raise IBKRError('Close an unused request before opening another.')
        self._next_request += 1
        rid = self._next_request
        self._requests[rid] = {'kind': kind, 'contract': contract, 'dataType': 0, **extra}
        return rid

    def _contract(self, data):
        obj = self._contract_class()
        for key, value in data.items():
            setattr(obj, key, value)
        return obj

    def search_futures(self, symbol, exchange='CME', currency='USD', expiry=''):
        if not isinstance(symbol, str) or not re.fullmatch(r'[A-Za-z0-9.]{1,15}', symbol):
            raise IBKRError('Enter a futures root such as ES, NQ, MES or MNQ.')
        return self.request_details({'symbol': symbol.upper(), 'secType': 'FUT',
            'exchange': exchange, 'currency': currency, 'lastTradeDateOrContractMonth': expiry})

    def request_details(self, contract):
        data = contract_spec(contract)
        with self._lock:
            rid = self._request('contract', data)
            self._client.reqContractDetails(rid, self._contract(data))
            return rid

    def request_market_rule(self, rule_id):
        if isinstance(rule_id, bool) or not isinstance(rule_id, int) or not 0 < rule_id < 2**31:
            raise IBKRError('Invalid market rule ID.')
        if not self._ready:
            raise IBKRError('Wait for the gateway API handshake.')
        self._client.reqMarketRule(rule_id)

    def subscribe(self, contract, *, trades=True, depth_rows=10):
        data = contract_spec(contract, resolved=True)
        if not isinstance(trades, bool) or isinstance(depth_rows, bool) or not isinstance(depth_rows, int) or not 0 <= depth_rows <= 50:
            raise IBKRError('Choose zero to fifty depth rows and a boolean trade setting.')
        if not self._ready:
            raise IBKRError('Wait for the gateway API handshake.')
        if len(self._requests) + 1 + int(trades) + int(depth_rows > 0) > 64:
            raise IBKRError('Close unused requests before opening this chart.')
        ids = {}
        with self._lock:
            try:
                obj = self._contract(data)
                self._client.reqMarketDataType(1)  # Request live; observe actual type separately.
                ids['quote'] = self._request('quote', data)
                self._client.reqMktData(ids['quote'], obj, '', False, False, [])
                if trades:
                    ids['trade'] = self._request('trade', data)
                    self._client.reqTickByTickData(ids['trade'], obj, 'Last', 0, False)
                if depth_rows:
                    ids['depth'] = self._request('depth', data, rows=depth_rows, bids=[], asks=[])
                    self._client.reqMktDepth(ids['depth'], obj, depth_rows, False, [])
            except Exception:
                for rid in list(ids.values()): self.unsubscribe(rid)
                raise IBKRError('IBKR could not start this market-data request.') from None
        return ids

    def unsubscribe(self, request_id):
        with self._lock:
            request = self._requests.pop(request_id, None)
            if not request or not self._client:
                return
            method = {'quote': 'cancelMktData', 'trade': 'cancelTickByTickData', 'depth': 'cancelMktDepth'}.get(request['kind'])
            if method:
                args = (request_id, False) if request['kind'] == 'depth' else (request_id,)
                try: getattr(self._client, method)(*args)
                except Exception: pass
            self._push('unsubscribed', requestId=request_id)

    def _callback(self, generation, kind, *args):
        with self._lock:
            if generation != self._generation or self._overflow:
                return
            try:
                self._handle(kind, *args)
            except (ValueError, TypeError, AttributeError, IndexError, KeyError):
                self._push('error', state='invalid data', requestId=args[0] if args and isinstance(args[0], int) else -1,
                           message='IBKR supplied incomplete or invalid data; do not use it as a current price.')

    def _handle(self, kind, *args):
        if kind == 'ready':
            if self._timer: self._timer.cancel()
            self._state_event('connected', 'Local gateway API is ready. Market-data permission is checked per request.')
            return
        if kind == 'accounts':
            self._accounts = [a.strip() for a in args[0].split(',') if a.strip()]
            self._push('accounts', accounts=self._accounts.copy())
            return
        if kind == 'closed':
            self._accounts = []
            self._requests.clear()
            if self._state != 'timeout':
                self._state_event('disconnected', 'Gateway connection closed. Clear displayed quotes and depth before reconnecting.')
            return
        if kind == 'rule':
            rid, rows = args
            increments = [{'lowEdge': number(r.lowEdge), 'increment': number(r.increment, True)} for r in rows]
            if any(Decimal(r['increment']) <= 0 for r in increments): raise IBKRError('Invalid price increment.')
            self._push('market_rule', marketRuleId=rid, increments=increments)
            return
        rid = args[0]
        request = self._requests.get(rid)
        if kind == 'error':
            code = args[1]
            state, message = 'request error', 'IBKR could not complete the request. Check the code in the official API guide.'
            if code in (354, 10089, 10090, 10167, 10168, 10186):
                state, message = 'not entitled', 'Check the market-data subscriptions and API permissions for this exact contract.'
            elif code in (100, 101, 309, 10189, 10190):
                state, message = 'subscription limit', 'IBKR subscription or pacing limit reached. Close unused streams or wait before retrying.'
            elif code in (200, 321):
                state, message = 'contract error', 'Resolve the exact exchange, expiry and contract ID before requesting data.'
            elif code in (326,):
                state, message = 'client ID in use', 'Choose a client ID not already used by another gateway connection.'
            elif code in (502, 504, 1100, 1300):
                state, message = 'disconnected', 'IBKR connectivity was lost. Current data must be invalidated.'
                self._ready = False
                self._state_event(state, message)
            elif code in (1101, 1102):
                state, message = 'resubscribe required', 'IBKR restored connectivity. Reconnect this bridge to establish and verify subscriptions again.'
                self._ready = False
                self._state_event(state, message)
            elif code in (2103, 2105):
                state, message = 'stale', 'An IBKR data farm is unavailable; clear affected live data until the feed is reverified.'
            elif code in (2104, 2106, 2107, 2108, 2158):
                state, message = 'information', 'IBKR data-farm status notification; this does not establish a live subscription.'
            if request and code in (316, 317):
                request['bids'] = []; request['asks'] = []
                self._push('depth_reset', requestId=rid, bids=[], asks=[], reason='IBKR reset or halted the depth book.')
            self._push('error', requestId=rid, code=code, state=state, message=message)
            if request and request['kind'] == 'contract' and state != 'information':
                self._requests.pop(rid, None)
            return
        if not request:
            return  # Late data for a canceled request is never routed to another chart.
        base = {'requestId': rid, 'contract': request['contract'], 'dataType': request['dataType']}
        if kind == 'contract':
            details = args[1]
            obj = details.contract
            spec = {name: getattr(obj, name) for name in CONTRACT_FIELDS if getattr(obj, name, None) not in (None, '', 0)}
            exchanges = str(getattr(details, 'validExchanges', '')).split(',')
            rules = str(getattr(details, 'marketRuleIds', '')).split(',')
            mapping = [{'exchange': exchange, 'marketRuleId': int(rule)} for exchange, rule in zip(exchanges, rules) if exchange and rule.isdigit()]
            self._push('contract', requestId=rid, contract=spec, minTick=number(details.minTick, True),
                       marketRules=mapping, timeZoneId=getattr(details, 'timeZoneId', ''),
                       tradingHours=getattr(details, 'tradingHours', ''), liquidHours=getattr(details, 'liquidHours', ''))
        elif kind == 'contract_end':
            self._requests.pop(rid, None)
            self._push('contract_end', requestId=rid)
        elif kind == 'data_type':
            request['dataType'] = args[1]
            self._push('data_type', requestId=rid, dataType=args[1], label={1:'live',2:'frozen',3:'delayed',4:'delayed frozen'}.get(args[1], 'unknown'))
        elif kind in ('quote', 'quote_size'):
            field = ({1:'bid',2:'ask',4:'last',66:'bid',67:'ask',68:'last'} if kind == 'quote' else {0:'bid',3:'ask',5:'last',69:'bid',70:'ask',71:'last'}).get(args[1])
            if field:
                if args[1] >= 66: base['dataType'] = 3
                self._push(kind, **base, field=field, value=number(args[2], kind == 'quote_size'), exchangeTime=None,
                           scope='Watchlist quote update; not a trade event.')
        elif kind == 'trade':
            _, tick_type, timestamp, price, size, attrib, exchange, conditions = args
            self._push('trade', **base, tickType=tick_type, exchangeTime=int(timestamp), price=number(price),
                       size=number(size, True), side=None, exchange=str(exchange), specialConditions=str(conditions),
                       pastLimit=bool(getattr(attrib, 'pastLimit', False)), unreported=bool(getattr(attrib, 'unreported', False)),
                       scope='IBKR tick-by-tick Last. Aggressor side is not provided.')
        elif kind == 'depth':
            _, position, operation, side, price, size, maker, smart = args
            if side not in (0, 1) or operation not in (0, 1, 2) or not isinstance(position, int) or position < 0:
                raise IBKRError('Invalid depth operation.')
            rows = request['bids' if side == 1 else 'asks']
            if position > len(rows) or (operation != 0 and position >= len(rows)):
                request['bids'] = []; request['asks'] = []
                self._push('depth_reset', requestId=rid, bids=[], asks=[], reason='Depth positions became inconsistent; resubscribe.')
                return
            if operation == 2: rows.pop(position)
            else:
                row = {'price': number(price), 'size': number(size, True), 'marketMaker': str(maker)}
                if operation == 0: rows.insert(position, row)
                else: rows[position] = row
                del rows[request['rows']:]
            self._push('depth', **base, position=position, operation=operation, side='bid' if side == 1 else 'ask',
                       bids=[dict(row) for row in request['bids']], asks=[dict(row) for row in request['asks']],
                       smartDepth=bool(smart), exchangeTime=None, scope='Positional Level-2 book; not market-by-order.')
