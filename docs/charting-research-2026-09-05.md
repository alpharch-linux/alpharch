# Chart workflow research — 2026-09-05

Representative official documentation review, not an exhaustive internet search or a hands-on performance benchmark. Product descriptions establish documented features, not quality, accuracy, feed entitlement, or Alpharch parity. No predictive/promotional claims are adopted.

| Platform / primary source | Useful documented workflow | Alpharch acceptance direction |
|---|---|---|
| [Deepcharts Deep Print](https://helpdesk.deepcharts.com/portal/en/kb/articles/order-flow-bid-and-ask-footprint), [Replay](https://www.deepcharts.com/helpcenter/article/replay-data) | Bid/ask, volume and delta display modes; footprint readability controls; replay manager, date and speed | Exact captured per-price quantities; explicit display grouping; no reconstructed bid/ask from candles; isolated replay clock |
| [Bookmap navigation](https://bookmap.com/learning-center/bookmap-features/chart-navigation/zooming-and-navigating), [FAQ](https://bookmap.com/faq/) | Navigating between current and historical depth; recorded session replay | Clear depth capture extent and age, zoom without changing source semantics; never invent preconnection liquidity |
| [TradingView chart shortcuts](https://www.tradingview.com/charting-library-docs/latest/configuration/Shortcuts/), [focused zoom](https://www.tradingview.com/blog/en/stay-in-focus-15704/) | Keyboard chart navigation and fixed-position zoom | Focus-local shortcuts, cursor anchoring, discoverable buttons; avoid Omarchy global key collisions. Library docs differ from retail TradingView UI |
| [Sierra Chart scaling](https://www.sierrachart.com/index.php?l=doc/Scaling.html) | Independent study scales, automatic/manual/constant ranges, reset, scale movement | Independent time/price and lower-pane scales; visible manual state; restore automatic fitting |
| [Quantower chart overview](https://help.quantower.com/quantower/analytics-panels/chart/general-overview), [standalone panels](https://help.quantower.com/quantower/general-settings/standalone-panels) | Auto/manual centering, return-to-last, native panels, duplicate/template, symbol groups, object manager | Per-chart state, native app windows, saved monitor routing, explicit symbol linking, inspectable drawings. CQG export restrictions must be respected if later integrated |
| [ATAS footprint modes](https://atas.net/blog/how-footprint-charts-work-footprint-modes-and-what-they-are-for/) | Volume, trade count, bid/ask and delta representations | User-selectable measured representation; trade count only when actual event counts exist |
| [MotiveWave user guide](https://www.motivewave.com/guides/MotiveWave_Users_Guide.pdf) | Linked charts sharing a replay session | A shared recorded clock before claiming synchronized replay; no live values mixed into replay. Guide is version 5, not proof of current limits |
| [NinjaTrader navigation](https://ninjatrader.com/support/helpguides/nt8/navigating_a_chart.htm) | X/Y dragging, fixed/auto scale, box zoom/undo, go-to date, bar spacing, global crosshair | Precise inspection, fit/reset/live, then anchored box selection and history navigation |
| [Exocharts grid/cursor](https://help.exocharts.com/hc/en-us/articles/11118962878353-Grid-Cursor-settings) | Session grid and shared price/time cursor | Time-zone-explicit sessions and linked crosshair; share price only for the same instrument/source |
| [TRDR alerts](https://docs.trdr.io/key-features-and-indicators/alerts), [chart alerts](https://docs.trdr.io/key-features-and-indicators/alerts/alert-on-chart) | Explicit thresholds, crossing conditions, alert log | Local user-defined threshold crossings, timestamp/source, rearm, clear browser-open limitation; no generated recommendations |

## Implementation sequence and evidence

1. **Navigation and numerical detail:** continuous cursor-anchored time zoom, independent manual price zoom/pan, draggable axes, fit/auto/live, keyboard controls, real elapsed-time gaps, exact OHLC inspector and per-chart persistence. Implemented in the live desk; mathematical regressions and browser validation in progress.
2. **Analysis workflow:** drawings stored as price/time anchors, editable object list, optional linked instruments/cursor, footprint grouping that conserves total quantity, study parameters/templates, independent pane scaling. Pending completion and testing.
3. **Native workspace:** launch live desk or independent chart app windows with current Omarchy browser launcher; named monitor/workspace routing and missing-monitor fallback. Validate in disposable layouts without overwriting current desktop configuration.
4. **Review and context:** existing recorded-tape replay, journal, calendar, options and Desk Brain exposed through documented local commands; shared replay clock and browser integration need explicit coverage. Never attach live options to historical replay.
5. **Quality:** disconnected/stale states, reconnection gaps, bounded capture and rendering, malformed persistence, narrow windows, keyboard navigation, installer idempotence and foreign-file preservation. Long soak and real multimonitor behavior remain separate evidence.

## Feed-dependent capabilities

- Public crypto trades + market-by-price depth are connected. These do not establish market-by-order queue identity, hidden order detection, historical full depth, or liquidation events.
- CME/CQG/Rithmic and broker account data require documented access/entitlements and a real tested adapter. No substitute is presented as those feeds.
- Options OI/gamma calculations need explicit underlying/source/time and model assumptions. A gamma density is not dealer positioning.
- Replay from OHLC must not synthesize trades/depth; imported or recorded events define available detail.
- Alerts, templates and drawings are reading tools. No AI-generated entries, stops, sizing or automated trading is added.
