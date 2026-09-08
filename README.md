# Alpharch

**The trading layer for [Omarchy](https://omarchy.org).**
Linux is for traders. The exchanges run Linux — now you do.

Alpharch adds a futures and crypto trading workspace to Omarchy Linux. The
**1.8.0-alpha.1 public preview** includes the new live chart desk: resizable
charts, starting layouts, indicators, drawings, order flow, local recording
and replay. Terminal tools, the journal, calendar and optional house themes
remain available. Your configuration and journal are preserved by uninstall.

Public crypto feeds are available in the preview. The read-only IBKR futures
bridge still needs real-account acceptance; Rithmic/CQG and live execution are
not implemented. The optional paid hosted assistant is planned, not launched.
See [release notes](docs/releases/1.8.0-alpha.1.md) for tested behavior and limits.

*Est. 2026 · [alpharch.org](https://alpharch.org)*

---

## Install

On an existing [Omarchy](https://omarchy.org) installation:

```bash
curl -fsSL https://alpharch.org/install | bash
```

Or by hand:

```bash
git clone https://github.com/alpharch-linux/alpharch.git
cd alpharch && ./install.sh
sudo pacman -S python-websockets   # the one dependency for live flow
```

Open **Alpharch Live Desk** from the app launcher, press **SUPER+ALT+V**, or run
`trade-workspace`. First launch offers Bitcoin, crypto overview, single chart
and blank desks. Existing installs can run `alpharch update`, then reopen the
desk. `alpharch version` should report `1.8.0-alpha.1`.

`alpharch doctor` checks dependencies and feed reachability. The optional IBKR
bridge needs the official SDK and your signed-in local gateway; it is not
needed for public crypto charts. [Live desk guide](docs/live-desk-guide.md).

The opening template screen also offers **Classic desk** (charts in one window)
or **Hyprland desk** (one chart per real tiled window). Both share the chart tools;
their saved desks stay separate. [Hyprland desk guide](docs/hyprland-desk.md).

Flags: `--no-theme` keeps your current theme, `--no-branding` keeps
Omarchy's fastfetch logo and screensaver. `--no-keybindings` leaves your existing shortcuts alone.

## The Line

Bloomberg taught the world that a terminal is driven, not clicked.
The chart workspace has its own searchable **Commands** menu: **Super+Alt+U**
(or **Ctrl+K** inside a chart). Type “new”, “indicators”, “timeframe”, “draw”,
“style” or “save” and press Enter. The **Keys** button shows the full reference.

With an Alpharch chart focused, **Super+Alt+Shift** plus **N / I / T** opens
New chart / Indicators / Timeframe; **D / P / S** opens Drawing objects /
Style / Save desk; **C / R / H** opens Connections / Replay / History;
**L / Z / O** returns to latest bars / fits the chart / opens saved layouts.
These shortcuts act only on the focused Alpharch window. Omarchy retains
its window tiling, focus, resize and workspace shortcuts. On the standard
keyboard layout, **Super+− / =** resizes width, **Super+Shift+− / =** resizes
height, and **Super+F** toggles full screen.

Draw without a mouse: choose a tool through Commands, use **Alt+arrows** to
move one bar or one native price tick, then **Enter** for each anchor.
**Alt+Shift+arrows** moves faster. **Ctrl+Z** undoes a drawing. Drawing objects
lets you enter exact anchor prices and times. **+ / −** zoom the focused
chart, **Left / Right** pan, and **Home** returns to the latest bars.

Each chart has independent dark, light and saved custom colors under **Style**.
Following Omarchy changes the window headers; it leaves chart colors as chosen.

`SUPER+ALT+A` opens Alpharch's command bar. Type where you want to go:

```
btc            order flow on BTC          opt            options tape
btc heat       liquidity heatmap          opt map        OI map · max pain
btc dom        depth ladder               eth opt        ETH options
btc perp       funding · OI · depth       clock          session clock
debrief        the Desk Brain debrief     ask <question> your record, questioned
jrnl           today's journal            light / dark   flip the shade
```

## Order flow — every situation, one engine

`alphad` reads the public trade and book streams (Coinbase, Hyperliquid,
Binance — no keys, no accounts) and renders six views. **Switch live with one
key** — no restarting, no menus:

| Key | View | What you're reading |
|---|---|---|
| `f` | **flow** | Footprint — volume at price per time bucket, delta, 3:1 imbalances, absorption flags |
| `d` | **dom** | Depth ladder — resting size, walls (⚑ at 3× median), book pressure, session profile shadow |
| `h` | **heat** | Liquidity heatmap — the book through time, prints overlaid. Bookmap, in a tty |
| `t` | **tape** | Time & sales — speed meter, big prints at 8× mean, CVD |
| `p` | **profile** | Session volume profile — POC, 70% value area, delta per level |
| `l` | **liqs** | Funding countdown + open interest + liquidations (perp feeds) |

`+`/`-` change the price grid live; `?` shows the key map right in the view. Direction is the only thing painted
green or red; amber means attention. That contract holds everywhere.

### The flow canvas — the two worlds

`SUPER+ALT+V` (or `alphad --canvas`) opens the real-pixel renderer: your
session's past as candles, meeting the live order book at an amber seam —
liquidity fog, resting walls burning white-hot at their prices, the tape
riding the path as volume-graded bubbles, CVD underneath. It's a single
self-contained page served by alphad on localhost and streamed over a
local websocket; Chromium opens it as a bare app window and Hyprland
tiles it like everything else. No cloud, no accounts — the data never
leaves your machine. The terminal views stay for SSH and purists.

### Drive it with plain words

The Narrator takes the wheel when you ask. `trade-brain do "set this chart
to candlesticks with a 40 range with VWAP and cumulative delta"` — and the
live chart rebuilds itself: range bars, VWAP line, delta strip. Views,
grids, indicators, new windows: typed sentences, applied to running charts
over a local socket, every parameter validated twice. The model maps words
to whitelisted settings — it never writes code, and asking it for a trade
gets the same refusal as always.

The canvas grew hands too: scroll to zoom, drag to pan, double-click to
reset, crosshair with price and time. A green dot means live; amber means
replay.

### Record and replay

The platforms sell replay. Alpharch records to a plain JSONL file and
feeds it back through the same engine — drill your reads at 4× on a
Sunday, free:

```bash
alphad --record ~/tapes/cpi-day.jsonl
alphad --replay ~/tapes/cpi-day.jsonl --speed 4
```

## Options flow

`alphaopt` reads Deribit's public API — the actual crypto options
market, live, keyless: options tape with premium and IV per print, an
open-interest map by strike with walls and max pain, put/call ratios,
and a Black–Scholes γ·OI density (labeled as a density — Alpharch makes
no dealer-positioning claims it can't verify). Views: `t`ape · `m`ap ·
`s`ummary.

## The desk

`SUPER+ALT+T` detects your monitors and raises six rooms across them —
flow, DOM, heatmap, options, clock, quant scratchpad — round-robin by
default, pinnable per room in `~/.config/alpharch/desk.toml`.
`trade-desk close` ends the day the right way: it opens your journal.

## The clocks

`SUPER+ALT+W`: Globex, NYSE, London, Tokyo — open/closed with live
countdowns, DST handled properly, plus perp funding marks and your own
calendar's next event. The Daily (`SUPER+ALT+B`) folds the same
countdowns into your morning sheet.

## The calendar

`trade-cal` puts the economic calendar on the desk: `today`, `week`,
and `next` (a countdown to the next high-impact event). Data is
ForexFactory's published weekly feed — keyless, no account, cached
locally and refreshed politely. It is a schedule with impact, forecast
and previous; high impact prints amber, because amber means attention.
The clock and The Daily read it too, and the Brain sees today's times
when it debriefs. Filter currencies with `calendar_currencies = "USD EUR"`
in `config.toml`. From The Line: `cal` or `news`.

## Two shades, every theme

The Pit (dark) now opens with **After Hours**: the Alpharch mark in brushed
metal and copper against deep petrol planes. A quieter alternate background
is included. The Pit, white keeps the printed prospectus palette: paper, ink
and amber. `SUPER+ALT+I` flips between the two themes. The new wallpaper is
also available from [alpharch.org](https://alpharch.org/#wallpaper).

And because Alpharch reads the active Omarchy theme's palette at
launch, `omarchy-theme-set kanagawa` (or any of the community's 150+
themes) reskins every Alpharch view too. Nothing to configure.

## The rest of the desk

`trade-journal` — plan/notes/trades/debrief in plain Markdown, with
`SUPER+ALT+N` screenshotting straight into today's entry.
`trade-focus` (`SUPER+ALT+D`) — do-not-disturb while you read the tape.
`alpharch-waybar setup` — optional bar ticker with price direction and
a focus-mode indicator. `alpharch` — the mark and the full command map.

## The Desk Brain

*It has read every tick. Ask it anything.*

`SUPER+ALT+Q`, or `trade-brain`. At the bell it reads your journal, the tape
you recorded and your calendar, and writes the debrief back into your journal
under `## Debrief — Desk Brain`: what you planned, what you noted, and what
the tape actually shows at those timestamps.

```bash
trade-brain debrief            # today: journal + tape + calendar
trade-brain ask "what do I keep noting on CPI days?"
trade-brain replay ~/tapes/cpi-day.jsonl
trade-brain check              # is it usable on this machine?
```

**It runs on your machine, on your account.** It shells out to your own
`claude` CLI. Alpharch operates no server, holds no account, and ships no key;
nothing is sent anywhere that wasn't already on your disk. No `claude` CLI, no
Brain — it says so in one line and stops.

**It cannot make market data up.** Every figure it sees comes from
`alphad --analyze`, which is pure arithmetic over tape you recorded — session
range, POC and value area, the CVD path, the biggest prints, absorption and
divergence flags, walls that held or broke, liquidation cascades. It emits
plain JSON and no model touches it:

```bash
alphad --record ~/tapes/$(date +%F).jsonl     # record while you watch
alphad --analyze ~/tapes/$(date +%F).jsonl    # computed facts, no AI
```

The engine computes, the model reads back. Definitions travel with the facts,
so "wall" and "held" mean one fixed thing.

**It reads the past and refuses the future.** The Brain will not predict,
forecast, or give a directional view; will not name an entry, exit, stop,
target or size; and will not tell you what to do next — asked plainly, asked
sideways, or asked as "just educational". Ask it for a pick and it declines in
a sentence and goes back to your record. Every answer ends the same way:

> Your record, read back to you. Never advice.

That is a bright line, not a setting, and `tests/brain-fence.sh` asks a real
model for picks, forecasts, stops and sizing when the Brain changes. This preview keeps Brain code unchanged and passes its offline checks; no live model call was made for this release.

## Feeds — the honest part

Live and free today: Coinbase spot trades + book, Hyperliquid perps,
Binance spot/perp streams (note: binance.com is geo-blocked from US IPs),
Deribit options. `alpharch doctor` tests each one from your machine and
says what's reachable.

**Perps run on Hyperliquid** by default — reachable from the US, keyless,
and the source for depth, open interest and funding:

```bash
alphad --exchange hyperliquid              # BTC perp, all six views
alphad --exchange hyperliquid --symbol ETH --view liqs
```

Its funding settles **every hour**, not every eight, so Alpharch prints it
as `funding/1h` wherever it renders — an hourly rate read as an 8h rate is
off by 8×. Hyperliquid publishes no public per-event liquidation stream
(liquidation fills are exposed only per-account), so the liqs view says so
in as many words rather than showing an empty panel that reads as a market
where nothing is being liquidated. Set `perp_exchange = "binance"` in
`~/.config/alpharch/config.toml` for per-event liqs, if you can reach it.

CME futures depth (ES, NQ, CL…) requires a paid feed — Rithmic,
Databento, or a broker entitlement. Equity/index options flow requires
OPRA. Alpharch does not fake those numbers, does not scrape delayed
data and present it as live, and does not print a footprint it cannot
verify. Provider access alone is not enough: an implemented adapter and tested connection are also required. The preview includes a read-only IBKR bridge awaiting real-account acceptance and a Databento CSV importer for owner-supplied licensed files. See [connection status](docs/connections-development.md).

## What Alpharch will never do

No signals. No picks. No AI that trades. Nothing here tells you to buy
or sell — these are tools for reading markets, and the reading is
yours. Your journal and config are plain files on your disk. Market data connects to the selected providers. The optional Brain sends selected context through your own Claude CLI; it is not offline inference.

There is a model in the box now, and the promise did not change. The Desk
Brain reads your own past record and is fenced against forecasts, picks,
sizing and stops; it narrates numbers the engine computed and is barred from
producing market data of its own. It runs on your `claude` CLI, under your
account, on your machine — Alpharch operates no server and holds no key.
Turn it off by not installing the CLI: every other tool works exactly as
before.

## Staying current

```bash
alpharch update
```

Pulls the latest Alpharch into your checkout, reruns the installer, and
prints the version you landed on. It finds the checkout at
`~/.local/share/alpharch-src` or `~/alpharch`, and clones one there if
you installed via `curl | bash` and never had a repo. Reinstalling is
idempotent — your bindings block, config, and journal are untouched.

If your checkout has uncommitted work, update says so and stops rather
than pulling over it. If you're offline, it says that too. `UPDATE` in
The Line (`SUPER+ALT+A`) runs the same thing in a window.

Run bare, `alpharch` checks once a day whether the remote has moved and
prints a single dim line if it has. That check has a two-second timeout
and is silent on any failure — it is the only network call `alpharch`
itself makes. Skip it entirely by keeping no checkout, or run
`alpharch version` instead of the bare command.

## Uninstall

```bash
~/.local/share/alpharch/uninstall.sh
```

Removes bindings, commands, themes, and branding (restoring your
originals). Keeps your journal and config — they were never ours.

## License

MIT. Built on the shoulders of Omarchy, Hyprland, and Arch.

---

*Tools, never signals.*

### Optional installation reports

Installation reporting is **off by default**. After a successful install, an
interactive terminal asks once whether to share a small completion report.
Non-interactive installs default to off. Your choice persists across updates.
Use `alpharch install-reports status`, `on`, or `off` to change it. Turning it on
later applies to future installations and updates; it does not send past reports.
Turning it off clears any pending reports. No reporting service runs in the background.

The report contains only an event type (install/update/reinstall), app version,
build revision and a random per-event retry ID. The server records the receipt
date. No account information, trading data, hardware or persistent device ID is
included. Hosting providers receive the connection IP; the reporting database
never stores IP addresses. Details: <https://alpharch.org/privacy.html>.

For unattended setup, append `--install-reports=off` to `install.sh`, or use
`curl -fsSL https://alpharch.org/install | bash -s -- --install-reports=off`.
An explicit `--install-reports=on` opts in. Network errors never fail an install.
Retries keep their ID to prevent double-counting. A maximum of ten pending events
is retained locally, with at most three attempted during a subsequent install.
