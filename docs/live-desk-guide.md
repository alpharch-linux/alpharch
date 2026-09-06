# Live desk and native workspace

Open the local preview at http://127.0.0.1:17863/. On an installed overlay, `trade-workspace` opens the live desk from the app launcher or the existing SUPER+ALT+V binding.

## Read a chart precisely

Wheel over the plot zooms time around the cursor; wheel over a price scale zooms that scale. Drag the plot through history. Shift-drag moves the price range. Drag either axis to stretch it. Fit resets the view; Auto fits price; Live returns to the latest bar. Focus the plot to use +/−, left/right, Home, A and 0. Tools contains exact UTC end time and price bounds, box zoom, drawings and row grouping. Drawings store actual price/time anchors, not screen pixels. Drag their endpoints, edit exact coordinates, or use Undo/Redo (Ctrl+Z / Ctrl+Shift+Z on the plot). Tools include levels, lines, rays, rectangles, Fibonacci retracements, notes and measurements. Candle formation can use elapsed time, trade count, traded volume or native-tick high–low range; event bars retain each completing print whole and use sequential, non-overlapping slots. Their inspector retains exact exchange start/end seconds. Time bars continue to use elapsed-time spacing. A retained-history reset returns a pinned event chart to its latest bars.

Hover a candle for OHLC, volume and classified delta where captured. Auto footprint rows group actual quantities; the row's tick count is shown. Empty historical delta/footprints mean that aggressor data was not provided. Captured depth/profile/VWAP cover only retained events, not the full trading day.

Use Markets to select among the nine public source/market combinations across Coinbase, Hyperliquid and Kraken. Set an optional A/B/C group in Tools to link symbols; compatible charts share a cursor. Native windows in the same browser profile/origin can share those groups. Indicators supports named study templates and independent lower-pane scale zoom. Layouts autosave in this browser; named saves and import/export are available under Desk.

For the left drawing rail, full interval picker, per-chart history and grid, DOM views and compact ticket, see [Chart tools and tickets](chart-tools-and-tickets.md).

## Independent native windows

```sh
trade-live --window btc --asset BTC --view heat --workspace 31
trade-live --window eth --asset ETH --workspace 31
trade-live --window sol --asset SOL --feed hyperliquid --view footprint --workspace 31
trade-live save morning
trade-live load morning --dry-run
trade-live load morning
```

Each window has a stable identity and its own browser state. Omarchy tiles/resizes it normally. Save records workspace/monitor routing; load preserves already open windows. Missing monitors fall back to connected outputs. Export browser Desk layouts too when moving to another machine/profile. The preview service is separate from full overlay installation.

## Connections and appearance

Connect opens provider-specific public-feed, API-key or local-gateway flows. Public charts need no account. IBKR uses your signed-in local Linux TWS/IB Gateway and the optional official API SDK; select an exact exchange/expiry/contract ID. Other futures routes clearly show their actual implementation/access requirements. See [connection coverage](connections-development.md).

The palette control also adjusts directional colors, heat intensity, grid contrast, candle glow, filled/hollow candles and interface motion. Reduced-motion preferences are respected. Heat colors encode displayed quantity from indigo through amber to ivory; profile colors distinguish actual classified buy/sell volume. TWS unclassified volume stays neutral.

Tools → Observed market reads deterministic captured high/low/volume/VWAP/delta, and can display expiring depth concentrations. Optional Deribit options context keeps expiry and put/call groups separate. It is not dealer positioning or a signal. Append your own note with its source/time to the local journal or export the observed facts.

## Review a session

Review opens the existing journal, economic calendar, options tool, and Desk Brain help locally. Brain help makes no model call; narration requires the user's own Claude CLI and explicit invocation. No AI trading or signals are added.

**Review → Record / replay in this desk** records the current live streams into local JSONL files. Stop from the recording strip or session dialog; page closure stops its recording. Exact received trades are retained, with up to 100 available depth levels per side sampled at most once per second. Select several compatible recordings to replay on one shared exchange-time clock. Replay starts paused; Play, Step, speed, seek and Return to live remain visible. Returning live restores the previous chart composition. Seeking clears future observations; no historical prices or aggressor classifications are fabricated. The local desk limits a session to 100 MB / 500,000 events.

The separate advanced replay/record tool remains available for older tapes and the existing optional paper-order simulator. Its recorder retains 15 depth levels per side at most once per second. Its explicit paper ledger is disabled by default and models displayed liquidity only; it is not exchange-accurate execution. Seeking disables paper execution and clears derived level tracking; it does not rewind a paper ledger. Use `trade-workspace --replay FILE` or the advanced tool buttons in Review.

## Installation choices

`./install.sh` installs the overlay commands, app entry, managed trading bindings and theme assets. Theme activation remains explicit. Use `./install.sh --no-theme --no-branding --no-keybindings` for commands and the app entry without those desktop changes. Existing config/journal files remain user-owned; conflicting foreign command/app entries stop installation before changes.

No CQG/CME/broker connection is installed by supplying a public crypto feed. Live licensed markets require both real access and an implemented, validated adapter. See the coverage checklist for remaining acceptance work.

Bollinger Bands use the selected price source, an editable 2–200-bar SMA and 0.1–10 population standard deviations (default 20/2). Middle, upper and lower lines have independent colors. Stochastic uses a 2–200-bar high/low lookback and separate 1–200-bar SMA smoothing for %K and %D (default 14/3/3); a zero range is neutral 50. Both leave warm-up values empty, support price overlay or a separate pane, and retain settings/colors in study templates and desk layouts. Stochastic panes default to 0–100.

A one-trade event bar uses movement from the preceding bar close for its candle color; unchanged prices and the first print are neutral. This is price movement only, not an inferred aggressor classification. Multi-trade candles retain open/close coloring.

## Starting desks

A new desk offers Bitcoin desk (1m candles, 15s heatmap, tape), Crypto overview (independent BTC/ETH/SOL 5m charts with EMA 20 and volume), Single chart, or Blank desk. These use Coinbase USD spot; templates contain settings only. Captured VWAP, flow and depth accumulate from actual received events. The compact layout reflows into a grid when a window is narrow or short.

The chooser appears every time you open or reload the main desk, including when a saved desk exists. **Continue current desk**, Close or Escape returns to that saved desk without changing its charts. On a first launch with no saved desk, Close or Escape starts empty. Explicit chart launches and individual Hyprland chart windows open directly. Choose again from **Desk → Choose a starting desk…**. Switching keeps the current desk in **Desk → Restore previous desk**, retains named layouts and appearance, and saves the new composition. That recovery slot contains the desk immediately before the most recent template change, not an unlimited history. Export or name a layout to keep more versions. Each named native window keeps its own current desk and recovery slot. Template switching is unavailable during replay; return to live first.
