# Connections in the development desk

Verified 2026-09-05. This is local development capability, not a claim that these adapters have shipped or passed funded-account acceptance.

| Provider | Actual implemented path | Acceptance evidence / boundary |
|---|---|---|
| Coinbase | Public BTC/ETH/SOL USD trades, depth and historical candles | Nine-source real network check; no account required |
| Hyperliquid | Public BTC/ETH/SOL perpetual trades, top-20 depth, hourly funding and OI | Nine-source real network check; no wallet or signing key required |
| Kraken | Public BTC/ETH/SOL USD trades, CRC32-validated top-100 depth, completed 1m candles | All three real streams checked; taker side and Decimal ingestion tested |
| Kraken account | Signed read-only Spot balance query, optional API one-time code | Protocol/request/error tests only; no real API key used |
| Deribit account | Read-only WebSocket `account:read` authentication/query; live or testnet | Protocol/error paths tested; no real account authenticated |
| Binance account | Signed WebSocket Spot `account.status` / USER_DATA query | Protocol/error paths tested; region restrictions remain; no real account authenticated |
| Interactive Brokers | Optional official TWS API bridge to signed-in local Linux TWS/IB Gateway; exact dated-futures search, contract IDs, market-rule ticks, trades and aggregated depth | Official-SDK protocol tests and desk adapter tests pass. No installed/signed-in gateway or market-data entitlement acceptance on this host |
| CQG / Rithmic | Provider-specific setup entries and guides | Vendor development access, protocol adapters and production conformance remain required |
| Tradovate / TradeStation / tastytrade | Provider-owned OAuth setup entries and guides | Registered integrations/approval and adapters remain required; no password forms or fake OAuth success |
| Other broker/exchange entries | Named route requirements and connection guides | Setup-only where a working adapter does not exist. Brokers using CQG/Rithmic are not duplicated as fake direct adapters |

Use **Connect** to select a provider. Public chart buttons open the named source directly. For IBKR, sign in using IBKR's own software, enable its local socket API and Read-Only API setting, connect the corresponding loopback port, search an exact futures symbol/exchange/expiry, then select a resolved contract. See [IBKR bridge setup](ibkr-bridge.md).

TWS tick-by-tick trades do not provide aggressor side. Alpharch retains `side: null`, renders neutral tape/volume profile, and leaves delta/footprint classification unavailable. Quotes and quote-size updates never create trades or volume. Frozen/delayed/unknown market-data types are labeled separately. Depth timestamps are local receive times because TWS does not supply exchange timestamps for those callbacks.

Private API credentials stay in the owning browser connection's server memory. There is no credential persistence feature, password-login endpoint, arbitrary remote URL, order operation or withdrawal operation. Disconnect/page closure discards credentials. Private HTTPS requests refuse redirects, and Kraken nonces are monotonic per key with serialized requests. Account identifiers never enter shared public market snapshots or desk exports.

Read-only account polling runs only while that account connection remains enabled. Public sources are shared between browser windows and recorders, and close after their last owner leaves. Optional Deribit public options requests occur only when the observations panel/overlay is enabled, with a 60-second response cache and explicit stale expiry.

Official references: [Kraken REST signing](https://docs.kraken.com/exchange/guides/rest/authentication), [Kraken book checksum](https://docs.kraken.com/exchange/guides/websockets/book-checksum-v2), [Kraken taker-side trades](https://docs.kraken.com/exchange/api-reference/spot-websocket-v2/trade), [Deribit authentication](https://docs.deribit.com/api-reference/authentication/public-auth), [Binance account request](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/ws-api/account), [IBKR TWS API](https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/), [provider-specific website guides](https://alpharch.org/connections/).
