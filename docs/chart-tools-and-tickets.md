# Chart tools and tickets

Each chart keeps its own drawings, indicators, history, interval favorites,
grid settings and ticket visibility. Save a named desk to keep that setup.

## Drawing rail

The slim rail at the left of a chart groups lines, zones/channels, Fibonacci,
markup and planning drawings. Open a group to choose a tool, then place its
anchors on the chart. Three-point tools preview each stage. Freehand tools
follow a drag. Escape returns to the cursor.

Select a drawing to drag its anchors or move the whole object. The object
manager edits exact prices and UTC times, labels, colors, line styles,
Fibonacci ratios, visibility and locks. Undo/redo apply to drawing edits.
Crosshair, magnet, show/hide and lock controls are on the same rail.
Short charts scroll the rail. Shortcuts apply to the focused chart; they do
not replace Omarchy shortcuts.

## Intervals and loaded history

The standard favorites are **1m, 5m, 30m, 1h, 3h, 4h, 1d and 1w**. Each chart's
picker also lists seconds, other minutes/hours, days/months, tick, range and
volume bars. Custom / favorites accepts typed intervals and saved favorites.

Examples: `30s`, `150m`, `4h`, `1w`, `1M`, `1000T`, `40R`, `10P`, `100V`.
An uppercase `M` means months; lowercase `m` means minutes. `T` counts trades;
`R` measures high–low range in the instrument's native ticks. `P` converts
price points to ticks and rejects a fractional-tick size. With a 0.25 tick,
40R and 10P specify the same range. Volume uses the feed's traded quantity.
An event bar retains its completing print whole, so a large print may exceed
a volume threshold. Event bars use sequential slots and retain exchange times.

**History** controls maximum loaded bars (1–2,000) and an optional lookback in
days for this chart. Actual coverage and its source are displayed on the chart
and in the dialog. A requested limit does not promise unavailable provider
history. Supported historical time candles come from the chosen provider;
fine/custom intervals and event bars need captured trades. Historical candles
do not acquire invented aggressor sides or trade bubbles. Replay uses the
recorded session and does not fetch live history.

Calendar bars use UTC boundaries, with Monday-start weeks and calendar months.
Exchange-session/RTH/ETH templates, continuous futures rollover, Renko and Kagi
are not implemented by this interval picker.

## Grid, depth and prints

The rail's grid control adjusts density, contrast, visibility and minor lines
per chart. Horizontal divisions and editable prices follow native ticks.

**Classic DOM** places bid/ask quantities on a native-tick ladder. Wheel scrolls
the ladder; Fit recenters. A dash means the feed did not supply a quantity at
that level. **Depth heatmap + DOM** aligns captured resting liquidity with a
current L2 column. It adds Trade bubbles when there is room in the chart's
eight-study limit. Depth is limited to the levels and snapshots provided by
the connection; these views do not reconstruct MBO or queue position.

**Trade bubbles** and **Large trades** are in Indicators → Volume & flow.
Set minimum traded quantity, side, size, opacity and colors there. These
overlays use up to 2,000 latest retained actual prints. Unknown aggressor side
stays neutral, including IBKR prints. Turning off the studies stops their raw
print requests unless another chart needs them. Entering/exiting or rewinding
replay clears cached prints to prevent live/replay context from mixing.

## Compact trading ticket: local drafts only

**Trade** in each chart's title opens a 214 px ticket. Ticket, Account and
Activity tabs keep secondary information out of the chart. Narrow tiles use
an overlay; closing it restores the full chart area.

Buy Bid, Buy Ask, Sell Bid and Sell Ask copy the current quoted price into a
limit ticket and select its side. They do not submit, follow the market or
change price after selection. They require a fresh bid and ask.

Market, Limit, Stop Market and Stop Limit are selectable. Stop Limit keeps the
trigger and limit separate. Quantity, exact prices and optional bracket/TIF
fields can be edited. **Order setup** selects Single, OCO, Bracket or OTO.
Single keeps the extra fields collapsed; choosing a linked setup opens its
fields, which can be collapsed again to keep the ticket small.

- **OCO:** two orders for the chart's instrument, each with its own side, type,
  quantity, limit and/or trigger. The saved plan links them so a full fill of
  either is intended to cancel the other. They can be same-side exits or
  opposite-side entries; neither depends on the other filling first.
- **Bracket:** the entry has two opposite-side exits of matching quantity:
  a limit target and a Stop Market or Stop Limit. The saved plan activates
  those exits after entry fills and links only the exits as OCO.
- **OTO:** the saved plan activates a second configurable order after the
  entry fills. It does not add an OCO relationship.

Time in force applies to all legs created by this editor. Saved plans display
each leg and the intended link in Activity and retain the relationship on
reload/export. Earlier drafts with unlinked stop/target prices remain readable
and are not silently converted into bracket orders. Selecting Single ignores
the hidden linked-order fields when saving a new ticket.

These relationships are **local draft metadata**, not a cancellation or order
activation engine. Partial-fill handling and where conditional orders would
be held are explicitly unverified. Broker adapters must validate order support,
partial-fill sizing/cancellation, rejection handling and transmission before
any linked group can be submitted. No live OCO protection is active here.

Notional is a local estimate before fees, not an account balance or margin
calculation; an OCO ticket labels it as the first order's estimate. Futures
quantities in every leg require whole contracts and prices must follow
the native tick. Saved drafts appear in Activity; up to 20 fit on each chart.

**No broker orders are sent by this ticket.** Live/paper broker execution is
unavailable, and equity, margin, positions and broker activity remain blank.
The existing IBKR bridge supplies read-only market data. Saving a draft does
not submit it or arrange a later submission. The separate local paper engine
is not connected to this ticket.

In-platform execution remains unfinished. It needs account synchronization,
provider-specific order adapters, order/fill reconciliation, cancel/replace,
supported bracket behavior and broker demo verification. Rithmic requires its
developer integration access; a trading login alone does not provide that kit.
Rithmic/CQG routing through different brokerages is not a universal password
login. Provider capabilities must be verified before enabling order types.

## Research references

- [TradingView intervals and favorites](https://www.tradingview.com/support/solutions/43000747934-time-intervals-a-quick-introduction-and-tips/)
- [TradingView custom intervals](https://www.tradingview.com/support/solutions/43000543883-custom-chart-intervals-personalizing-your-analysis/)
- [TradingView range charts](https://www.tradingview.com/support/solutions/43000474007-understanding-range-charts/)
- [NinjaTrader bar construction and required data](https://ninjatrader-devel.ninjatrader.com/support/helpguides/nt8/how_bars_are_built.htm)
- [Sierra Chart settings](https://www.sierrachart.com/index.php?page=doc/ChartSettings.html)
- [Bookmap depth and trade visualization](https://bookmap.com/learning-center/getting-started/overview-of-bookmap/the-3-elements-on-the-chart)
- [Coinbase candle limits](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles)
- [Rithmic integration documentation](https://www.rithmic.com/documentation)
- [IBKR API order submission and callbacks](https://ibkrcampus.com/campus/trading-lessons/python-placing-orders/?retakeFinal=1)
- [IBKR bracket order relationships and transmission](https://www.interactivebrokers.com/docs/general/order-types/complex-orders/bracket-orders)
- [IBKR OCA fill and cancellation behavior](https://www.interactivebrokers.com/campus/glossary-terms/one-cancels-all-oca-order/)
- [CQG bracket and linked order entry](https://help.cqg.com/cqgic/25/Documents/enteringbracketorders.htm)

Validation: offline suites cover drawing geometry and persistence, interval
boundaries, per-chart history, history/live aggregation, native-tick grids,
missing-depth handling, actual-print filters and quote-side selection. Fake
HOME full/no-theme/commands-only repeated installs and uninstalls pass. Public
Coinbase history and retained-trade requests were checked live. Browser checks
cover the compact ticket, all four quote choices, Stop Limit fields, tab
separation, local draft save/remove and the classic DOM. Linked-ticket tests
cover OCO/OTO/bracket relationships, opposite-side bracket exits, native prices
and quantities in every leg, malformed links and compatibility with older
drafts. Browser checks verify OCO save/reload, bracket Stop Limit fields and
switching back to Single. No real broker order or broker account test was
performed.
