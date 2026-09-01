# Alpharch

**The trading layer for [Omarchy](https://omarchy.org).**
Linux is for traders. The exchanges run Linux — now you do.

Alpharch is an overlay, not a fork. It installs on top of a stock Omarchy
system in seconds and adds the complete free-data trading stack: order
flow in six live views, options flow, a multi-monitor desk, a command
bar, session clocks, tape recording and replay, a journal, and two house
themes. `uninstall.sh` removes every trace. Your Omarchy stays yours.

*Est. 2026 · [alpharch.org](https://alpharch.org)*

---

## Install

Install [Omarchy](https://omarchy.org), then run this. That's it.

```bash
curl -fsSL https://alpharch.org/install | bash
```

Or by hand:

```bash
git clone https://github.com/alpharch-linux/alpharch.git
cd alpharch && ./install.sh
sudo pacman -S python-websockets   # the one dependency for live flow
```

Then `alpharch doctor` checks every dependency and feed.

Flags: `--no-theme` keeps your current theme, `--no-branding` keeps
Omarchy's fastfetch logo and screensaver.

## The Line

Bloomberg taught the world that a terminal is driven, not clicked.
`SUPER+ALT+A` opens Alpharch's command bar. Type where you want to go:

```
btc            order flow on BTC          opt            options tape
btc heat       liquidity heatmap          opt map        OI map · max pain
btc dom        depth ladder               eth opt        ETH options
btc perp       liqs · funding · OI        clock          session clock
jrnl           today's journal            light / dark   flip the shade
```

## Order flow — every situation, one engine

`alphad` reads the public trade and book streams (Coinbase, Binance —
no keys, no accounts) and renders six views. **Switch live with one
key** — no restarting, no menus:

| Key | View | What you're reading |
|---|---|---|
| `f` | **flow** | Footprint — volume at price per time bucket, delta, 3:1 imbalances, absorption flags |
| `d` | **dom** | Depth ladder — resting size, walls (⚑ at 3× median), book pressure, session profile shadow |
| `h` | **heat** | Liquidity heatmap — the book through time, prints overlaid. Bookmap, in a tty |
| `t` | **tape** | Time & sales — speed meter, big prints at 8× mean, CVD |
| `p` | **profile** | Session volume profile — POC, 70% value area, delta per level |
| `l` | **liqs** | Liquidations + funding countdown + open interest (binance perp) |

`+`/`-` change the price grid live. Direction is the only thing painted
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

## Two shades, every theme

The Pit (dark): near-black, one amber line. The Pit, white: the printed
prospectus — paper, ink, amber marker. `SUPER+ALT+I` flips the whole OS
between them. Both wallpapers plot the same market line — once on the
screen, once in print.

And because Alpharch reads the active Omarchy theme's palette at
launch, `omarchy-theme-set kanagawa` (or any of the community's 150+
themes) reskins every Alpharch view too. Nothing to configure.

## The rest of the desk

`trade-journal` — plan/notes/trades/debrief in plain Markdown, with
`SUPER+ALT+N` screenshotting straight into today's entry.
`trade-focus` (`SUPER+ALT+D`) — do-not-disturb while you read the tape.
`alpharch-waybar setup` — optional bar ticker with price direction and
a focus-mode indicator. `alpharch` — the mark and the full command map.

## Feeds — the honest part

Live and free today: Coinbase spot trades + book, Binance spot/perp
streams (note: binance.com is geo-blocked from US IPs), Deribit options.
`alpharch doctor` tests each one from your machine and says what's
reachable.

CME futures depth (ES, NQ, CL…) requires a paid feed — Rithmic,
Databento, or a broker entitlement. Equity/index options flow requires
OPRA. Alpharch does not fake those numbers, does not scrape delayed
data and present it as live, and does not print a footprint it cannot
verify. When you plug in a real feed, the same engine renders it.

## What Alpharch will never do

No signals. No picks. No AI that trades. Nothing here tells you to buy
or sell — these are tools for reading markets, and the reading is
yours. Your journal and config are plain files on your disk. Nothing
phones home.

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
