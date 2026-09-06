"""Read-only provider connections. Secrets live only in the owning socket's memory.

No order, withdrawal, arbitrary URL, password-login or credential persistence paths.
Authenticated adapters are development integrations until account-tested.
"""
import asyncio
import base64
import hashlib
import hmac
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

CATALOG = [
    ('coinbase', 'Coinbase', 'Crypto exchange', 'public', 'Public USD spot trades, depth and candles. An account is not required. Account OAuth is not implemented.'),
    ('hyperliquid', 'Hyperliquid', 'Crypto exchange', 'public', 'Public perpetual trades, depth, funding and open interest. No wallet or signing key required.'),
    ('kraken', 'Kraken', 'Crypto exchange', 'kraken', 'Read-only Spot balance connection using an API key with Query funds permission. Public chart data is independent of account access.'),
    ('deribit', 'Deribit', 'Crypto exchange', 'deribit', 'Read-only account connection with account:read scope. Public options context is available separately in Review. This does not enable Deribit charts.'),
    ('binance', 'Binance', 'Crypto exchange', 'binance', 'Read-only Spot account connection with USER_DATA permission. Regional restrictions apply. This adapter does not enable Binance charts.'),
    ('interactive-brokers', 'Interactive Brokers', 'Broker', 'ibkr', 'Connect to your signed-in local TWS or IB Gateway on Linux. The optional official TWS Python API is required. Resolve an exact futures expiry and exchange; live data permissions are verified per request. Development integration: gateway/account acceptance remains untested.'),
    ('cqg', 'CQG', 'Feed / routing provider', 'setup', 'CQG Web API requires vendor application access and broker-enabled credentials, plus exchange data entitlements. The Alpharch protocol adapter and production conformance remain required.'),
    ('rithmic', 'Rithmic', 'Feed / routing provider', 'setup', 'Rithmic development kit, test system and production conformance are required. Obtain the Rithmic system and feed login from your broker; this adapter is not implemented.'),
    ('tradovate', 'Tradovate', 'Broker / platform', 'setup', 'Provider-owned OAuth needs a registered integration, eligible API account and separate market-data permissions. No registered Alpharch OAuth client is configured.'),
    ('tradestation', 'TradeStation', 'Broker', 'setup', 'Provider-owned OAuth requires a registered client and approved account/data scopes. Alpharch adapter is not implemented.'),
    ('ironbeam', 'Ironbeam', 'Broker', 'setup', 'Ironbeam API access and entitled demo/live symbols are required. Alpharch adapter is not implemented.'),
    ('tastytrade', 'tastytrade', 'Broker', 'setup', 'OAuth integration and third-party verification are required. Legacy session/password login is not supported. Alpharch adapter is not implemented.'),
    ('amp-futures', 'AMP Futures', 'Broker', 'route', 'Select the CQG or Rithmic route actually enabled on your account. Broker portal credentials are different from feed credentials.'),
    ('edgeclear', 'Edge Clear', 'Broker', 'route', 'Use the data/routing provider assigned to your account. Broker portal login alone cannot connect a market-data stream.'),
    ('optimus-futures', 'Optimus Futures', 'Broker', 'route', 'Use the CQG, Rithmic or other feed route confirmed by your broker. Each route needs its own implemented adapter and entitlements.'),
    ('ninjatrader', 'NinjaTrader', 'Broker / platform', 'setup', 'A NinjaTrader account is not a universal market-data login. Confirm the supported API/feed route; Alpharch direct integration is not implemented.'),
    ('okx', 'OKX', 'Crypto exchange', 'setup', 'Provider-specific API key, passphrase and regional eligibility apply. Alpharch adapter is not implemented.'),
    ('bybit', 'Bybit', 'Crypto exchange', 'setup', 'Provider-specific API access and regional eligibility apply. Alpharch adapter is not implemented.'),
    ('bitget', 'Bitget', 'Crypto exchange', 'setup', 'Provider-specific API key and passphrase are required for private access. Alpharch adapter is not implemented.'),
    ('bitfinex', 'Bitfinex', 'Crypto exchange', 'setup', 'Provider-specific signed API access is required for private accounts. Alpharch adapter is not implemented.'),
    ('kucoin', 'KuCoin', 'Crypto exchange', 'setup', 'Provider-specific API key and passphrase are required. Alpharch adapter is not implemented.'),
    ('gemini', 'Gemini', 'Crypto exchange', 'setup', 'Provider-specific signed API access is required for accounts. Alpharch adapter is not implemented.'),
    ('stonex', 'StoneX', 'Broker / clearing firm', 'setup', 'StoneX publishes a directory of third-party futures platforms using CQG. Whether a given StoneX account can use Alpharch requires confirmation and a released CQG adapter. Live adapter not implemented in this desk.'),
    ('dorman', 'Dorman Trading', 'Broker / clearing firm', 'setup', 'Dorman offers a range of third-party trading technology. The clearing relationship alone does not identify the data API or authorize an Alpharch connection. Live adapter not implemented in this desk.'),
    ('phillip-capital', 'Phillip Capital', 'Broker / clearing firm', 'setup', 'Phillip Capital describes support for authorized trading platforms through its broker relationships. Confirm the platform and account permissions assigned to you; a clearing account is not a generic charting API. Live adapter not implemented in this desk.'),
    ('schwab', 'Charles Schwab / thinkorswim', 'Broker / clearing firm', 'setup', 'Schwab has a developer portal, but this review could not verify the futures market-data permissions needed for Alpharch from its public portal. thinkorswim access should not be treated as automatic external API access. Live adapter not implemented in this desk.'),
    ('binance-us', 'Binance.US', 'Crypto exchange', 'setup', 'Binance.US has its own API documentation and market-data endpoints. It must not reuse a Binance global connection or be presented as the same derivatives service. Alpharch has no Binance.US adapter. Live adapter not implemented in this desk.'),
    ('gate', 'Gate', 'Crypto exchange', 'setup', 'Gate documents direct subscriptions to public channels and API-key authentication for private channels. Alpharch has not implemented a Gate connection. Live adapter not implemented in this desk.'),
    ('crypto-com', 'Crypto.com Exchange', 'Crypto exchange', 'setup', 'Crypto.com Exchange documents separate user and market-data WebSocket services. Its Exchange API should not be confused with a login to another Crypto.com product. Live adapter not implemented in this desk.'),
    ('bitmex', 'BitMEX', 'Crypto exchange', 'setup', 'BitMEX publishes a WebSocket API with incremental table updates. Alpharch must implement its snapshots and updates before it can offer a reliable BitMEX feed. Live adapter not implemented in this desk.'),
    ('databento', 'Databento', 'Data provider', 'setup', 'Databento supplies live and historical market data through documented APIs. Alpharch’s development build has a CSV import path; that is not a live Databento connection. Live adapter not implemented in this desk.'),
    ('dxfeed', 'dxFeed', 'Data provider', 'setup', 'dxFeed documents dxLink market-data connections with multiple authorization modes. A demo endpoint is not proof of live exchange entitlement or a working Alpharch adapter. Live adapter not implemented in this desk.'),
]


def catalog():
    return [dict(id=i, name=n, category=c, method=m, detail=d,
                 guide='https://alpharch.org/connections/' + i + '/',
                 environments=['live', 'test'] if i == 'deribit' else ['live'],
                 accountTested=False, chartFeed=i if i in ('coinbase', 'hyperliquid', 'kraken') else None)
            for i, n, c, m, d in CATALOG]


class ConnectionError(ValueError):
    def __init__(self, state, message):
        self.state = state
        super().__init__(message)


def kraken_signature(path, payload, secret):
    digest = hashlib.sha256((str(payload['nonce']) + urllib.parse.urlencode(payload)).encode()).digest()
    return base64.b64encode(hmac.new(base64.b64decode(secret, validate=True), path.encode() + digest, hashlib.sha512).digest()).decode()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ConnectionError('stale', 'Provider redirected a private request; connection stopped.')


_NONCES = {}

def next_nonce(key):
    identity = hashlib.sha256(key.encode()).digest()
    value = max(time.time_ns() // 1000000, _NONCES.get(identity, 0) + 1)
    _NONCES[identity] = value
    return str(value)


def post(url, body, headers):
    # Exact endpoints selected by adapters below. TLS verification stays enabled.
    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=12) as response:
            return json.loads(response.read(1024 * 1024))
    except urllib.error.HTTPError as error:
        if error.code == 451:
            raise ConnectionError('access restricted', 'Provider access is restricted in this region.') from None
        if error.code in (401, 403):
            raise ConnectionError('authentication denied', 'Provider denied account access. Check the key, permissions and environment.') from None
        raise ConnectionError('stale', 'Provider request failed. Retry later.') from None


async def rpc(ws, ident, method, params):
    await ws.send(json.dumps({'jsonrpc': '2.0', 'id': ident, 'method': method, 'params': params}))
    for _ in range(20):
        reply = json.loads(await asyncio.wait_for(ws.recv(), 12))
        if reply.get('id') == ident:
            if reply.get('error'):
                code = reply['error'].get('code')
                state = 'not entitled' if code in (10005, 13021, -2015) else 'authentication denied'
                raise ConnectionError(state, 'Provider denied this read-only request. Check the key scope, environment and account access.')
            return reply.get('result', {})
    raise ConnectionError('stale', 'Provider response did not arrive.')


async def _verify(provider, credentials, environment):
    import websockets
    key, secret = credentials['key'], credentials['secret']
    if provider == 'kraken':
        path = '/0/private/Balance'
        payload = {'nonce': next_nonce(key)}
        if credentials.get('otp'):
            payload['otp'] = credentials['otp']
        try:
            signature = kraken_signature(path, payload, secret)
        except (ValueError, TypeError):
            raise ConnectionError('authentication denied', 'The Kraken private key must be valid base64.') from None
        result = await asyncio.to_thread(post, 'https://api.kraken.com' + path,
                                         urllib.parse.urlencode(payload).encode(),
                                         {'API-Key': key, 'API-Sign': signature,
                                          'Content-Type': 'application/x-www-form-urlencoded'})
        if result.get('error'):
            state = 'not entitled' if any('Permission' in str(e) for e in result['error']) else 'authentication denied'
            raise ConnectionError(state, 'Kraken denied the balance query. Check Query funds permission, nonce settings and API two-factor authentication.')
        if not isinstance(result.get('result'), dict):
            raise ConnectionError('stale', 'Kraken account response could not be verified.')
        return {'account': 'Authenticated API key', 'permission': 'Balance query verified',
                'assetCount': len(result['result']), 'refresh': not bool(credentials.get('otp'))}
    if provider == 'deribit':
        url = 'wss://test.deribit.com/ws/api/v2' if environment == 'test' else 'wss://www.deribit.com/ws/api/v2'
        async with websockets.connect(url, open_timeout=12, max_size=1024*1024) as ws:
            auth = await rpc(ws, 1, 'public/auth', {'grant_type': 'client_credentials', 'client_id': key,
                                                  'client_secret': secret, 'scope': 'account:read'})
            if not auth.get('access_token'):
                raise ConnectionError('authentication denied', 'Deribit did not grant an account session.')
            result = await rpc(ws, 2, 'private/get_account_summaries', {'extended': False})
            if not isinstance(result.get('summaries'), list):
                raise ConnectionError('stale', 'Deribit account response could not be verified.')
            return {'account': 'Authenticated API key', 'permission': 'account:read verified', 'assetCount': len(result['summaries']), 'refresh': True}
    if provider == 'binance':
        params = {'apiKey': key, 'timestamp': int(time.time()*1000), 'recvWindow': 5000}
        params['signature'] = hmac.new(secret.encode(), urllib.parse.urlencode(sorted(params.items())).encode(), hashlib.sha256).hexdigest()
        async with websockets.connect('wss://ws-api.binance.com:443/ws-api/v3', open_timeout=12, max_size=1024*1024) as ws:
            result = await rpc(ws, 1, 'account.status', params)
            if not isinstance(result.get('balances'), list):
                raise ConnectionError('stale', 'Binance account response could not be verified.')
            return {'account': result.get('accountType', 'Spot'), 'permission': 'USER_DATA verified', 'assetCount': len(result['balances']), 'refresh': True}
    raise ConnectionError('setup required', 'This provider adapter is not implemented.')


_KEY_LOCKS = {}

async def verify(provider, credentials, environment):
    identity = (provider, hashlib.sha256(credentials['key'].encode()).digest())
    lock = _KEY_LOCKS.setdefault(identity, asyncio.Lock())
    async with lock:
        return await _verify(provider, credentials, environment)


class Connections:
    """Per-browser-socket ownership; no secret ever leaves this object in a reply."""
    def __init__(self):
        self.states = {}
        self.secrets = {}
        self.jobs = {}

    def snapshot(self):
        return {'providers': catalog(), 'states': self.states.copy()}

    async def command(self, msg, emit):
        action, provider = msg.get('action'), msg.get('provider')
        if action == 'catalog':
            await emit(self.snapshot())
            return
        entry = next((p for p in catalog() if p['id'] == provider), None)
        if entry is None or action not in ('connect', 'disconnect'):
            raise ValueError('Choose a supported connection action.')
        if provider in self.jobs:
            job = self.jobs.pop(provider)
            job.cancel()
            await asyncio.gather(job, return_exceptions=True)
        self.secrets.pop(provider, None)
        if action == 'disconnect':
            self.states[provider] = {'state': 'disconnected', 'message': 'Account connection closed; credentials discarded.'}
            await emit(self.snapshot())
            return
        if entry['method'] not in ('kraken', 'deribit', 'binance'):
            self.states[provider] = {'state': 'setup required', 'message': entry['detail']}
            await emit(self.snapshot())
            return
        environment = msg.get('environment', 'live')
        if environment not in entry['environments']:
            raise ValueError('Choose a supported provider environment.')
        credentials = msg.get('credentials', {})
        if not isinstance(credentials, dict) or any(not isinstance(credentials.get(k), str) or not 1 <= len(credentials[k]) <= 4096 for k in ('key', 'secret')):
            raise ValueError('Enter the provider API key and secret in this local form.')
        if any(c in credentials['key'] for c in '\r\n') or not re.fullmatch(r'[0-9]{0,10}', str(credentials.get('otp', ''))):
            raise ValueError('Invalid API key or one-time code format.')
        self.secrets[provider] = {k: credentials[k] for k in ('key', 'secret', 'otp') if k in credentials}
        self.states[provider] = {'state': 'connecting', 'environment': environment, 'message': 'Checking read-only account access…'}
        await emit(self.snapshot())
        self.jobs[provider] = asyncio.create_task(self._watch(provider, environment, emit))

    async def _watch(self, provider, environment, emit):
        try:
            while True:
                try:
                    result = await verify(provider, self.secrets[provider], environment)
                    self.states[provider] = {'state': 'connected', 'environment': environment,
                        'checkedAt': time.time(), 'message': 'Read-only account query verified. No order access is used.', **result}
                except ConnectionError as error:
                    self.states[provider] = {'state': error.state, 'environment': environment, 'message': str(error)}
                except Exception:
                    # Never forward remote exception text: it can contain request credentials.
                    self.states[provider] = {'state': 'stale', 'environment': environment, 'message': 'Provider connection unavailable. Check network, region and service status.'}
                await emit(self.snapshot())
                state = self.states[provider]
                if state['state'] in ('authentication denied', 'not entitled', 'access restricted'):
                    self.secrets.pop(provider, None)
                    return
                if state.get('refresh') is False:
                    self.secrets.pop(provider, None)
                    await asyncio.sleep(60)
                    self.states[provider] = {'state': 'stale', 'message': 'API one-time code expired. Reconnect with a fresh code to verify again.'}
                    await emit(self.snapshot())
                    return
                await asyncio.sleep(60)
        finally:
            self.secrets.pop(provider, None)

    async def close(self):
        jobs = list(self.jobs.values())
        for job in jobs:
            job.cancel()
        await asyncio.gather(*jobs, return_exceptions=True)
        self.jobs.clear()
        self.secrets.clear()
