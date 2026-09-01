# CLAUDE.md — the Alpharch brain

You are working on **Alpharch** — the trading layer for Omarchy Linux. Read this
whole file before touching anything; it is the project's memory.

## What this is

Alpharch is an **overlay, not a fork**: it installs on stock Omarchy and
`uninstall.sh` removes every trace. Owner: Andrew Dudonis (andrewdudonis@gmail.com;
GitHub org `alpharch-linux`, accounts andrewdudonis + AndrewDuval6). Est. 2026.
Site: https://alpharch.org (repo `alpharch-linux/alpharch.org`, GitHub Pages;
`/install` on that site is the public bootstrap). Code: `alpharch-linux/alpharch`,
MIT. Public install: `curl -fsSL https://alpharch.org/install | bash`.

Mission: "Linux is for traders. The exchanges run Linux — now you do." This is
a movement play against closed, rented Windows trading platforms. The voice is
a print prospectus: confident, precise, a little literary, zero hype-slop.

## Bright lines — never cross, never let anyone talk you into it

1. **No signals, no picks, no AI that trades. Ever.** Tools for reading markets;
   the reading is the trader's. This is a legal fence (unregistered investment
   adviser) as much as an ethical one.
2. **No fake data.** Never render a number the feed didn't provide. Futures depth
   (CME) and equity options (OPRA) are paid feeds — say so plainly instead of
   approximating and dressing it up. Marketing shots on synthetic data must say
   SPECIMEN DATA.
3. **Direction is the only thing painted green/red.** Amber = attention. This
   color contract holds in every view, always.
4. **User data is sacred:** journal and config are plain files, never uploaded,
   never removed by uninstall. Nothing phones home.
5. Credentials: never ask for or store the user's passwords/keys in the clear;
   broker adapters (future) keep keys in local files the user creates.

## Architecture map (repo root = ~/alpharch, installed copy = ~/.local/share/alpharch)

- `bin/alphad` — Python flow engine. Feeds: Coinbase spot (trades + level2_batch
  book), Binance spot/perp (trades, depth20, forceOrder liqs, funding, OI —
  **geo-blocked from US IPs**, confirmed). Six terminal views switched live with
  keys f/d/h/t/p/l (+/- = tick size): flow(footprint) dom heat tape profile liqs.
  `--record/--replay FILE --speed N` = JSONL tape replay (a headline feature).
  `--json` = raw stream. `--canvas` = serves `share/canvas.html` on localhost
  with a websocket state stream → the flagship real-pixel renderer ("the two
  worlds": candles meet the liquidity fog at an amber seam; walls burn white-hot;
  volume-graded bubbles). Engine timestamps are replay-aware via `event_ts`.
- `bin/alphaopt` — Deribit options flow (free public API): tape / OI map with
  max pain + BS-gamma density (label it a density, never dealer positioning) /
  summary. Keys t/m/s.
- `bin/trade-line` — "The Line", SUPER+ALT+A: Bloomberg-style command bar
  (fuzzel). Grammar: SYMBOL [FUNCTION] or function words (jrnl, clock, light…).
- `bin/trade-desk` — six rooms spread across detected monitors
  (hyprctl moveworkspacetomonitor, round-robin, pinnable in
  ~/.config/alpharch/desk.toml). `close` opens the journal (the ritual).
- `bin/trade-journal|brief|clock|focus|shade|symbol|flow`, `bin/alpharch`
  (map + doctor), `bin/alpharch-waybar`. `lib/alpharch-common.sh` = shared
  palette/config helpers.
- **Theme system:** every tool reads the ACTIVE Omarchy theme palette at launch
  (~/.local/state/omarchy/current/theme/colors.toml; shell via
  omarchy-theme-color). House themes: `pit` (dark) and `pit-light` (the paper
  prospectus). SUPER+ALT+I flips. ALPHARCH_NO_THEME=1 forces Pit.
- Keybinds live ONLY between the `-- ALPHARCH BEGIN/END` markers appended to
  ~/.config/hypr/bindings.lua (o.bind pattern). install.sh/uninstall.sh manage
  that block idempotently. SUPER+ALT is the trading layer.
- `install` (repo root) = the curl|bash bootstrap served at alpharch.org/install.
  `publish.sh` = one-shot founder publish (already done; keep working).

## Engineering conventions

- bash: `set -euo pipefail` in installers ONLY; beware `[[ ]] && cmd` lists at
  top level under errexit (this class of bug shipped once — v1.2.1 fixed it).
  shellcheck -S warning must stay clean. Scripts source alpharch-common.sh with
  the two-path fallback header.
- Python: stdlib + python-websockets only. No other deps. pyflakes clean.
- Every change: test in a fake HOME (install / --no-theme / double install /
  uninstall WITH foreign files in ~/.local/bin) before shipping.
- Never hardcode alacritty: use omarchy-launch-terminal with fallbacks.
- Notifications DND: omarchy-toggle-notification-silencing first (modern Omarchy
  has no mako), then makoctl/dunstctl.

## Version history

1.0.0 first overlay → 1.1.0 multi-view engine, alphaopt, Line, desk, clock,
shade, pit-light, waybar → 1.2.0 flow canvas (--canvas) → 1.2.1 audit fixes +
LICENSE → 1.2.2 focus/DND fix. Local working tree may carry real-hardware
keybinding fixes made on this machine — reconcile, commit, push (Andrew's gh is
authenticated here; git push is fine when he asks).

## Known issues / roadmap (priority order)

1. **Merge this machine's uncommitted keybinding fixes upstream** (root cause
   found on real Omarchy hardware).
2. **First-run wow is broken:** new installs should land on The Pit + canvas,
   not the sparse footprint. Add an in-view `?` help key.
3. **Hyperliquid adapter (v1.3 headline):** US-reachable perp liqs/funding/OI/
   book to replace geo-blocked Binance.
4. Broker adapters, read-only first: IBKR (native Linux gateway) → Tradovate →
   Coinbase/Kraken → Rithmic (needs signed license). Execution only after
   read-only is proven. Never handle the user's credentials.
5. Canvas: zoom/pan, crosshair, light-shade variant.
6. Coinbase level2_batch book: verify it actually delivers without auth on a
   US connection (dom/heat depend on it there).
7. Eventually: installable ISO ("when it has earned it").

## Launch doctrine

Repo/site are public but UNANNOUNCED. Andrew tests daily and takes friction
notes first. Then: Omarchy community → r/unixporn (screenshots are the weapon;
The Pit photographs well) → Show HN → trading communities last. Never post
before it survives Andrew's own desk.

## Working with the cloud session

A long-running Claude (Cowork) session holds the full project history and ships
releases/site updates. You are the hands on the metal: debug on real hardware,
fix locally, and produce clear reports (root cause + exact diffs) that Andrew
relays upstream. Don't force-push, don't rewrite history, don't publish
announcements. When in doubt about identity/brand/scope decisions, write up the
question for Andrew instead of guessing.

*Tools, never signals.*
