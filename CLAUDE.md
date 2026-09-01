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
  book), Hyperliquid perp (**the perp default** — trades, l2Book, activeAssetCtx;
  US-reachable, keyless), Binance spot/perp (trades, depth20, forceOrder liqs,
  funding, OI — **geo-blocked from US IPs**, confirmed). Six terminal views switched live with
  keys f/d/h/t/p/l (+/- = tick size): flow(footprint) dom heat tape profile liqs.
  `--record/--replay FILE --speed N` = JSONL tape replay (a headline feature).
  `--json` = raw stream. `--analyze FILE` = deterministic JSON facts from a
  tape (pure arithmetic, no model, no network) — the Desk Brain's only source
  of market numbers. `--canvas` = serves `share/canvas.html` on localhost
  with a websocket state stream → the flagship real-pixel renderer ("the two
  worlds": candles meet the liquidity fog at an amber seam; walls burn white-hot;
  volume-graded bubbles). Engine timestamps are replay-aware via `event_ts`.
- `bin/trade-brain` — **the Desk Brain** (SUPER+ALT+Q): debrief / ask / replay /
  check. Shells out to the USER'S own `claude` CLI (`-p`, tools off, no session
  persistence, run from the journal dir so no project CLAUDE.md leaks in). We
  ship no key and run no server. Grounded ONLY in `alphad --analyze` output.
  The fence lives in `$BRAIN_FENCE` and the closing line is re-applied in the
  script after the model speaks, so it cannot be dropped. See the Desk Brain
  section below before touching any of it.
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
      Q Desk Brain (debrief)

  Keys Alpharch must NEVER take: F S G K (stock Omarchy) and C L (Andrew's own
  bindings — Claude Code, workspace layout toggle). v1.2.2 moved off G/C/L.
  As of 1.5.0 the SUPER+ALT letter space is FULL except U and Y: `hyprctl binds`
  on a stock desk shows every other letter bound by Omarchy, us, or Andrew.
  Q went to the Desk Brain in 1.5.0. Take U or Y next, and re-run the check —
  do not assume this list is still current.
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
- **Anything AI-shaped goes through the user's own `claude` CLI.** Alpharch
  never holds a key, never runs a server, never calls a model API directly. If
  the CLI is missing, say so in one line and stop — never degrade to a guess.
- **A model may never be the source of a market number.** It narrates
  `alphad --analyze` output and nothing else. If a fact is not in the DATA
  block, the honest answer is that the record does not contain it. When you add
  a field to the analysis, add its definition to the `definitions` block too —
  and if you decimate a series, say so in the payload, or a reader will quote
  the largest sampled point as the extreme (that bug was caught in testing).
- `alpharch version` prints PLAIN text — publish.sh and `alpharch update` parse
  it, and a styled one put an ANSI reset inside the version string.

## Version history

1.0.0 first overlay → 1.1.0 multi-view engine, alphaopt, Line, desk, clock,
shade, pit-light, waybar → 1.2.0 flow canvas (--canvas) → 1.2.1 audit fixes +
LICENSE → 1.2.2 the keybinding layer fixed on real hardware (collisions off
G/C/L, Lua dispatch dialect, no-tty pickers, monitor JSON parse, canvas
EADDRINUSE, installer reload, block idempotency) → 1.3.0 `alpharch update` +
the once-a-day check → 1.4.0 the Hyperliquid adapter (US perps) + the cfg() inline-comment fix
→ 1.5.0 the Desk Brain (trade-brain, alphad --analyze, tests/). Andrew's gh is authenticated here; git push is fine when
he asks. Don't force-push, don't rewrite history.

## Known issues / roadmap (priority order)

1. **First-run wow is broken:** new installs should land on The Pit + canvas,
   not the sparse footprint. Add an in-view `?` help key.
2. ~~**Hyperliquid adapter (v1.4 headline).**~~ **DONE in 1.4.0** — perp depth,
   hourly funding and OI, US-reachable. One thing the roadmap assumed is not
   true: there is no public per-event liquidation stream (see below), so the
   liqs view says so for hyperliquid instead of showing an empty panel.
3. ~~**The Desk Brain / the Narrator (v1.5 headline).**~~ **DONE in 1.5.0** —
   `trade-brain` on the user's own `claude` CLI, grounded in
   `alphad --analyze`. The fence (no forecasts, no picks, no sizing) is in the
   system prompt AND re-enforced in the script, with live adversarial tests.
4. Broker adapters, read-only first: IBKR (native Linux gateway) → Tradovate →
   Coinbase/Kraken → Rithmic (needs signed license). Execution only after
   read-only is proven. Never handle the user's credentials.
5. Canvas: zoom/pan, crosshair, light-shade variant.
6. Coinbase level2_batch book: verify it actually delivers without auth on a
   US connection (dom/heat depend on it there).
7. Eventually: installable ISO ("when it has earned it").

## Hyperliquid — what the live API actually is (verified on this machine, v1.4.0)

Do not re-derive this from guesses; it was measured against production.

- WS `wss://api.hyperliquid.xyz/ws`, subscribe `{"method":"subscribe",
  "subscription":{"type":T,"coin":"BTC"}}`. Channels used: `trades`, `l2Book`,
  `activeAssetCtx`. REST is POST `https://api.hyperliquid.xyz/info` with a
  `{"type":...}` body.
- **`trades` side is the AGGRESSOR: `B` lifted the ask, `A` hit the bid.** Verified
  against the bbo strictly preceding each print at a 1-tick spread: 132/132 `A`
  prints landed on the bid, 97 vs 9 for `B` on the ask. Getting this backwards
  inverts CVD, delta and every green/red on screen, so re-verify it the same way
  if you ever touch it. Fields are exactly `coin side px sz time hash tid users`
  and `time` is ms.
- **`l2Book` is a FULL snapshot** (`levels:[bids,asks]`, 20 a side) → `on_book`
  replaces. Measured 0.23/s. `{"fast":true}` gives 1.87/s but only 5 levels a
  side; we keep the deep book because dom/heat exist to show depth. Never merge
  the two — a composite of snapshots of different ages is a book that never was.
- **Funding is HOURLY, on the hour.** The API says so itself: `info`
  `{"type":"predictedFundings"}` reports `HlPerp` `fundingIntervalHours: 1` with
  `nextFundingTime` on an exact hour boundary. Binance is 8h. Label the interval
  everywhere the rate renders (`funding/1h`) — the same number means eight
  different things at the two intervals, and that is a bright-line-2 problem.
- **No public per-event liquidation feed exists.** `liquidations` and
  `allLiquidations` subscriptions are rejected ("Error parsing JSON into valid
  websocket request"), and the public tape carries no liquidation marker.
  Liquidation fills appear only in `userFills`, which needs a wallet address.
  `Engine.liq_note` carries that sentence into the liqs view. Do not infer liqs
  from the `users` field or a guessed liquidator address — that is invented data.
- **An unknown coin — or the right coin in lowercase — closes the socket with no
  error frame at all.** A plain reconnect loop spins on that forever behind an
  empty screen. `hl_coin()` uppercases and strips -USD/USDT/-PERP; `hl_universe()`
  (`info` `{"type":"meta"}`, skip `isDelisted`) validates before subscribing and
  exits with a real message listing live coins.
- Keepalive: the websockets protocol ping (`ping_interval=20`) holds the socket
  open indefinitely — verified over 75s+. App-level `{"method":"ping"}` →
  `{"channel":"pong"}` exists but is not needed on top of it.
- OI (`openInterest`) is in base units (BTC), like binance's — no poll task
  needed, `activeAssetCtx` pushes it ~1/s along with funding and marks.
- Tapes now start with a `{"k":"h",...}` header naming the feed and symbol, so
  replay can label the instrument and repeat the no-liq-stream note. Tapes cut
  before 1.4.0 have no header and replay exactly as they always did.

## The Desk Brain — read this before touching trade-brain (v1.5.0)

The site calls it the Narrator: "It has read every tick. Ask it anything." It
is the first AI surface in Alpharch, so it is also the one most able to damage
the project's credibility and its legal footing. The design exists to make that
hard.

- **Two layers, and the split is the whole point.** `alphad --analyze TAPE`
  computes facts — pure arithmetic, no model, no network, deterministic (same
  tape, same numbers; `tests/analyze.sh` asserts it). `trade-brain` hands those
  facts to the user's `claude` CLI and asks it to narrate. The engine computes,
  the model reads back. A model must never be the origin of a market number.
- **Never our key, never our server.** `trade-brain` shells out to the user's
  own `claude`. If it is absent: one honest line pointing at claude.com, exit
  non-zero. If it fails: report the failure, never a hollow answer.
- **Invocation hygiene.** `claude -p --append-system-prompt "$BRAIN_FENCE"
  --allowedTools "" --no-session-persistence`, run with cwd = the journal
  directory. The cwd matters: without it, CLAUDE.md auto-discovery can pull a
  project's instructions into the Brain's context. Do NOT switch to `--bare` —
  it forces API-key auth and would break every OAuth user.
- **The fence is defence in depth.** It is stated in the system prompt (no
  forecasts, no directional views, no entries/exits/stops/targets/sizes, no
  market numbers of its own, refuse in one sentence then read the record back),
  AND the closing line "Your record, read back to you. Never advice." is
  re-applied by the script if the model omits it. Never rely on the model alone
  for a guarantee you can enforce in bash.
- **The tests are not optional.** `tests/brain-fence.sh` has a deterministic
  half (stubbed `claude`: closing-line enforcement, no duplication, CLI failure,
  CLI absent, fence actually reaching the system prompt) and a live half that
  asks a real model for picks, hedged forecasts, entries/stops, sizing, an
  "educational" framing, and an instruction override. Run `--offline` for the
  free half. Run the full thing before any release that touches the Brain.
- **Analysis payload rules.** Definitions ship inside the JSON (`definitions`),
  so "wall", "held", "cascade" and "big print" mean one fixed thing to whoever
  reads it. Any decimated series must say it is decimated: the model once
  quoted the largest point of the sampled CVD path as the session extreme —
  a real number, attached to a false claim. `cvd.max/min` now carry their own
  timestamps and the path carries `path_note`.
- **Context is capped** (`MAX_JOURNAL_BYTES`, `MAX_ANALYSIS_BYTES`) and tapes
  come from `tape_dir` (config, default `~/tapes`). `debrief` writes under a
  `## Debrief — Desk Brain` heading with an attribution line; it appends and
  never rewrites the user's own words.

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

**Field notes — standing convention.** Whenever you diagnose a machine-side
issue whose fix produces no code commit (config repairs, environment problems,
hardware quirks, "it turned out not to be a bug"), write a short root-cause
note to `docs/field-notes/YYYY-MM-DD-<topic>.md` and push it. The cloud session
only sees this repo; a diagnosis that lives in a terminal transcript is a
diagnosis it will have to pay for again. Keep them short and factual: symptom,
what you ruled out and how, root cause, what you changed, what you deliberately
left alone. A note saying "not our bug, here's the proof" is worth as much as
one describing a fix.

*Tools, never signals.*
