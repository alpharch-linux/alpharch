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
  (fuzzel). Grammar: SYMBOL [FUNCTION] or function words (jrnl, clock, light,
  update…). With no fuzzel it re-execs itself in a terminal so fzf gets a tty.
- `bin/trade-desk` — six rooms spread across detected monitors (round-robin,
  pinnable in ~/.config/alpharch/desk.toml). `close` opens the journal (the
  ritual). Monitors come from parsed JSON, never a flat grep — see conventions.
- `bin/trade-journal|brief|clock|focus|shade|symbol|flow`, `bin/alpharch`
  (map + doctor + `update`), `bin/alpharch-waybar`. `lib/alpharch-common.sh` =
  shared palette/config helpers plus the Hyprland dispatch layer
  (`hypr_workspace`, `hypr_exec_on_workspace`, `hypr_workspace_to_monitor`,
  `no_tty`, `reexec_in_terminal`).
- `alpharch update` — finds the checkout (~/.local/share/alpharch-src, then
  ~/alpharch, else clones), `git pull --ff-only`, reruns install.sh, prints the
  new version. Dirty tree and offline both get one plain sentence, never a
  trace. Bare `alpharch` also does one quiet `git ls-remote` per day (2s
  timeout, silent on every failure) — the only network call `alpharch` makes.
- **Theme system:** every tool reads the ACTIVE Omarchy theme palette at launch
  (~/.local/state/omarchy/current/theme/colors.toml; shell via
  omarchy-theme-color). House themes: `pit` (dark) and `pit-light` (the paper
  prospectus). SUPER+ALT+I flips. ALPHARCH_NO_THEME=1 forces Pit.
- Keybinds live ONLY between the `-- ALPHARCH BEGIN/END` markers appended to
  ~/.config/hypr/bindings.lua (o.bind pattern). install.sh/uninstall.sh manage
  that block idempotently. SUPER+ALT is the trading layer. Current map — this
  is authoritative, and the free keys were chosen deliberately (see conventions):

      A Line · T desk · O flow · E dom · H heat · V canvas · P options
      M markets · W clock · B brief · J journal · N capture · D focus · I shade

  Keys Alpharch must NEVER take: F S G K (stock Omarchy) and C L (Andrew's own
  bindings — Claude Code, workspace layout toggle). v1.2.2 moved off G/C/L.
- `install` (repo root) = the curl|bash bootstrap served at alpharch.org/install.
  `publish.sh` = one-shot founder publish (already done; keep working).

## Engineering conventions

- bash: `set -euo pipefail` in installers ONLY; beware `[[ ]] && cmd` lists at
  top level under errexit (this class of bug shipped once — v1.2.1 fixed it).
  shellcheck -S warning must stay clean — NOTE: shellcheck is not installed on
  this machine and sudo needs a password, so ask Andrew to run
  `sudo pacman -S shellcheck` rather than claiming a clean lint you couldn't
  run. Scripts source alpharch-common.sh with the two-path fallback header.
- Python: stdlib + python-websockets only. No other deps. pyflakes clean.
- Every change: test in a fake HOME (install / --no-theme / double install /
  uninstall WITH foreign files in ~/.local/bin) before shipping.
- Never hardcode alacritty: use omarchy-launch-terminal with fallbacks.
- Notifications DND: omarchy-toggle-notification-silencing first (modern Omarchy
  has no mako), then makoctl/dunstctl.
- **Never raw `hyprctl dispatch` strings.** Hyprland 0.5x with a Lua config
  parses dispatch args as Lua, so `dispatch exec "[workspace 2 silent] cmd"` is
  a syntax error — and behind `>/dev/null` it looks like success. Use the
  `hypr_*` helpers in lib/, which probe the compositor once and speak either
  dialect. Symptom when violated: trade-desk reports six rooms and opens none.
- **A keybind launch has no controlling terminal.** Anything that draws a TUI
  from a binding must check `no_tty` and `reexec_in_terminal`. Test /dev/tty,
  never `-t 0`/`-t 1` — these helpers run inside `$(...)` where stdout is always
  a pipe, so a -t 1 test re-execs forever.
- **Never take a key the host or the user already holds.** Our block is
  APPENDED to bindings.lua and the last o.bind wins, so a collision silently
  steals their binding with no error. Check `hyprctl binds` and
  /usr/share/omarchy/default/hypr/bindings/ before claiming a key.
- **Never overwrite a running bash script.** install.sh rewrites bin/alpharch,
  which is the file `alpharch update` is itself executing; bash reads scripts
  lazily by byte offset and will execute garbage from the new file (observed,
  not theoretical). Hand off via `exec bash -c` so nothing is reading the file
  off disk. Same trap for any future self-updating command.
- Parse hyprctl JSON with jq/python, never a flat grep: `hyprctl -j monitors`
  nests activeWorkspace.name, so grepping "name" invents monitors that
  don't exist and scatters the desk onto them.
- `alpharch version` prints PLAIN text — publish.sh and `alpharch update` parse
  it, and a styled one put an ANSI reset inside the version string.

## Version history

1.0.0 first overlay → 1.1.0 multi-view engine, alphaopt, Line, desk, clock,
shade, pit-light, waybar → 1.2.0 flow canvas (--canvas) → 1.2.1 audit fixes +
LICENSE → 1.2.2 the keybinding layer fixed on real hardware (collisions off
G/C/L, Lua dispatch dialect, no-tty pickers, monitor JSON parse, canvas
EADDRINUSE, installer reload, block idempotency) → 1.3.0 `alpharch update` +
the once-a-day check. Andrew's gh is authenticated here; git push is fine when
he asks. Don't force-push, don't rewrite history.

## Known issues / roadmap (priority order)

1. **First-run wow is broken:** new installs should land on The Pit + canvas,
   not the sparse footprint. Add an in-view `?` help key.
2. **Hyperliquid adapter (v1.4 headline):** US-reachable perp liqs/funding/OI/
   book to replace geo-blocked Binance.
3. Broker adapters, read-only first: IBKR (native Linux gateway) → Tradovate →
   Coinbase/Kraken → Rithmic (needs signed license). Execution only after
   read-only is proven. Never handle the user's credentials.
4. Canvas: zoom/pan, crosshair, light-shade variant.
5. Coinbase level2_batch book: verify it actually delivers without auth on a
   US connection (dom/heat depend on it there).
6. Eventually: installable ISO ("when it has earned it").

## Verifying on real hardware (after a reboot or a bindings change)

- Three terminals on an empty workspace must tile, not stack. A single window
  filling its workspace is correct dwindle, NOT a bug — check
  `hyprctl -j clients` for `fullscreen != 0` before believing "everything is
  maximized". `fullscreen=1` is maximized (stock SUPER+ALT+F), `2` is true
  fullscreen, and grouped/tabbed windows also render full-size.
- `hyprctl reload` must print exactly `ok`. Per-workspace layout overrides
  persist in ~/.local/state/omarchy/workspace-layouts/*.lua and survive reloads
  — check there before blaming a config change.
- SUPER+ALT+A opens The Line; with no fuzzel it should open a terminal running
  fzf (that is the reexec path working, not a bug).
- SUPER+ALT+V canvas · N capture · I shade. And confirm the keys we gave back
  still belong to their owners: C = Claude Code, L = workspace layout toggle,
  G = move out of group.
- `alpharch update` on a clean checkout; `alpharch` bare should print at most
  one dim update line per day, and nothing at all when current.
- Bootstrap gotcha: `alpharch update` cannot install the release that first
  introduces it. Closing that gap needs one `./install.sh` from the checkout.

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
