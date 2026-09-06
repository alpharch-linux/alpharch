# IBKR read-only bridge — development

`lib/alpharch_ibkr.py` implements an optional bridge to the official TWS API Python client. It does not install TWS, sign in, accept a password, submit an order, or enable a live account by itself. There has been no real-account or gateway acceptance test. Connection UI and chart integration must be validated separately.

## Runtime and Linux setup

IBKR provides native Linux [TWS / IB Gateway downloads](https://www.interactivebrokers.com/en/trading/ibgateway-latest.php?menu=A). The user signs in through that software and enables API socket clients, retaining the gateway's read-only API setting for charting. Use the configured socket port; the bridge does not infer paper/live from a port number. It permits only IPv4 loopback and nonzero client IDs. Each concurrent bridge requires a distinct client ID.

The official `ibapi` package is **optional**. Obtain it from the [official TWS API download](https://interactivebrokers.github.io/) and follow [IBKR's Python client installation instructions](https://www.interactivebrokers.com/campus/trading-lessons/accessing-the-tws-python-api-source-code/). Install the downloaded `source/pythonclient` package and its declared dependencies into the same runtime used by Alpharch. IBKR's documentation discourages using an arbitrary network `pip install ibapi` package. Current official SDK 10.50.1 declares protobuf 5.29.5; use the dependencies declared by the version you install. No SDK code is vendored or redistributed here, and the basic crypto tools retain their existing dependencies.

The missing-SDK path returns `setup required` without opening a socket. A TCP connection is not readiness: `nextValidId` from the API handshake establishes readiness, and its order ID is discarded. Account IDs from `managedAccounts` belong only to that bridge's owning session. Never broadcast, log, persist or export them. Do not enable SDK debug logging in ordinary use; vendor logging can include raw account messages.

## Integration interface

One caller owns each bridge. Commands run on that owner's thread; callbacks run on an SDK reader thread. The bounded event queue is drained using `poll()`; no callbacks directly touch an asyncio loop or browser socket. Call `connect`/`disconnect` through `asyncio.to_thread` if the caller must avoid the bounded thread-join delay. No automatic reconnect attempts are made.

```python
from alpharch_ibkr import IBKRBridge

bridge = IBKRBridge()
bridge.connect(host="127.0.0.1", port=7497, client_id=71)
# Poll until a state event says connected; then:
request_id = bridge.search_futures("ES", exchange="CME", currency="USD")
# Display returned contracts and let the user select the actual expiry/conId.
# ids = bridge.subscribe(selected_contract, trades=True, depth_rows=10)
# Request the market rule matching the selected contract's exchange.
# bridge.request_market_rule(rule_id)
# for event in bridge.poll(limit=1000): ...
# for request_id in ids.values(): bridge.unsubscribe(request_id)
# bridge.disconnect()
```

The example's socket port is illustrative: use the user's configured port. Contract search uses `reqContractDetails` for `FUT`; stock-oriented symbol matching is not used. `CONTFUT` and unresolved subscriptions are rejected. Do not auto-pick the first search result as the front month. `request_details(contract_dict)` also accepts an explicit conId query. Contract dictionaries accept only conId, symbol, secType, exchange, currency, lastTradeDateOrContractMonth, localSymbol, tradingClass and multiplier.

`subscribe()` returns a dictionary of `quote`, optional `trade`, and optional `depth` request IDs. Each request is canceled independently. At most 64 active requests are tracked; provider limits can be lower. Search completion releases its slot. `request_market_rule(id)` returns through a `market_rule` event; use `price_increment(price, increments, minimum)` on the exchange-specific returned rule. `minTick` alone may not describe every price band.

## Events and data fidelity

All events have `type`, `provider: "ibkr"` and `receivedAt` (local Unix seconds). Request-scoped events carry `requestId`; market events also carry a contract dictionary and `dataType`. Events are JSON-safe; prices and quantities are decimal strings. Values preserve what the SDK supplies, including negative futures prices; SDK price callbacks are doubles, so this is not a claim to recover precision the SDK did not deliver. Unknown or nonfinite/unset numbers produce an error rather than a plotted price.

| Event | Payload and meaning |
|---|---|
| `state` | state/message; connected means API handshake ready, not an exchange entitlement |
| `accounts` | managed account IDs; session-private, not exportable |
| `contract` / `contract_end` | exact contract identity; minTick; exchange-to-marketRuleId mapping; timezone and trading/liquid hours |
| `market_rule` | marketRuleId and lowEdge/increment bands |
| `data_type` | 0 unknown, 1 live, 2 frozen, 3 delayed, 4 delayed frozen |
| `quote` / `quote_size` | bid/ask/last value from watchlist updates; never count these as trades |
| `trade` | tick-by-tick Last, exchangeTime, price, size, special conditions and flags; **side is null** because the callback does not provide aggressor side |
| `depth` | positional Level-2 bid/ask arrays with price, size and marketMaker; exchangeTime is null because the callback supplies no timestamp; this is not MBO |
| `depth_reset` | empty book after reset/halt or invalid positions; do not keep displaying the previous book |
| `error` | code, requestId, state and sanitized guidance; no raw vendor error text |
| `unsubscribed` | requestId removed; subsequent callbacks for it are ignored |

Requesting live data does not prove that data is live. Keep delayed/frozen/unknown labels visible. Tick-by-tick and depth requests have their own limits and permissions. The bridge makes no claim that IBKR supplies full exchange MBO data. Do not calculate an aggressor CVD/footprint from these trades without a separately specified and clearly labeled classification method.

On disconnection, overflow, resubscribe-required, stale farm errors, invalid data, or depth reset, the consumer must invalidate the appropriate displayed quotes/book. Restore notifications do not silently mark prior data live. Queue overflow is terminal for the connection: buffered events are discarded, a gap is reported and the socket closes. Require a new connection and book reconstruction. A canceled generation cannot contaminate the next connection. The bridge does not persist subscription plans or credentials.

## Validation

`python3 -m unittest discover -s tests -p ibkr.py -v` runs offline boundary regressions covering handshake, account isolation, exact contract/rules, negative prices, Decimal sizes, unknown trade side, positional depth mutation/reset, entitlement errors in old and current SDK signatures, cancellation, delayed data, queue overflow, reconnection generations and timeout. An additional test uses the official SDK's protobuf decoder when that SDK is available; all network entry points are replaced for that test.

The official SDK 10.50.1 compatibility check uses the downloaded Python source in a temporary isolated runtime. It does **not** install a broker app or test a real gateway, entitlement, account, live CME feed, latency or order execution. Those remain required acceptance evidence before a supported public release.

Official references, reviewed September 5, 2026: [connection handshake](https://interactivebrokers.github.io/tws-api/connection.html), [futures contract identity](https://interactivebrokers.github.io/tws-api/basic_contracts.html), [minimum increments](https://interactivebrokers.github.io/tws-api/minimum_increment.html), [tick-by-tick requests](https://www.interactivebrokers.com/docs/tws-api/doc/market-data-live/tick-by-tick-data/request-tick-by-tick-data), [depth updates](https://interactivebrokers.github.io/tws-api/market_depth.html).
