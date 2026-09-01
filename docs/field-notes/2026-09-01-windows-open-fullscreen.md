# Every window opens fullscreen — not our bug

**Date:** 2026-09-01 (early hours)
**Machine:** Andrew's Omarchy laptop, Hyprland 0.56.2, single eDP-1 (1920x1080 @ scale 1.6 → 1200x675 logical)
**Reported as:** urgent regression — "every window now opens fullscreen/maximized, started after your changes"
**Outcome:** no code change. Alpharch was not the cause.

## Symptom

Flipping through workspaces, nearly every one showed a single window filling
the whole screen. Reported immediately after the v1.2.2 keybinding commit and a
reinstall + `hyprctl reload`, so the timing pointed straight at us.

## What was ruled out, and how

| Check | Result |
|---|---|
| `hyprctl reload` | `ok` — no Lua error, nothing aborts Omarchy's config mid-load |
| `hyprctl getoption general:layout` | `dwindle` (stock) |
| `hyprctl plugin list` | none loaded |
| grep `fullscreen\|maximiz\|windowrule\|layout` across `~/.config/hypr/*.lua` and all of `~/.config/omarchy/` (incl. the active Pit theme's `hyprland.lua`) | **zero hits**; the ALPHARCH block is `o.bind` lines only |
| `diff` of `bindings.lua` vs the 23:48 backup predating the session | only 8 blank lines removed + `G→V`, `C→N`, `L→I` **inside** the ALPHARCH block. Nothing outside it |
| Empirical: 3 fresh terminals on an empty workspace | tiled `581x306` / `581x625` / `581x305` — textbook dwindle. Repeated before and after reload |

Nothing to revert; `omarchy-refresh-*` was not needed.

## Root cause

`trade-desk open` had been run at **23:56:42–44 on Aug 31 — 20 minutes before
the session started (00:16:19)**. Process start times line up with `desk.toml`
(five of the six rooms were still open — ws2's DOM room had since been replaced
by a browser and a terminal):

```
23:56:42  foot -e alphad --view flow   → ws1
23:56:43  foot -e alphad --view heat   → ws3
23:56:43  foot -e alphaopt             → ws4
23:56:43  foot -e trade-clock --watch  → ws5
23:56:44  foot -e bash                 → ws6
```

**One window on a workspace correctly fills that workspace in dwindle.** It is
not maximized; there is simply nothing to tile against. Six workspaces each
holding one room reads exactly as "every window opens fullscreen."

Worth noting for the record: the desk worked here because the uncommitted
`hypr_exec_on_workspace` fix was already present in the working tree that
evening. Before that fix `trade-desk open` silently opened nothing.

## Three pre-existing contributors

- **ws3 had a genuinely maximized window** (`fullscreen=1`), from Omarchy's
  stock `SUPER+ALT+F` "Full width" in `default/hypr/bindings/tiling.lua` — a
  binding Alpharch does not touch. **Cleared it**; ws3 then tiled two windows
  side by side.
- **ws2's two windows were grouped/tabbed.** A group renders at full size.
  Left alone — deliberate user action.
- **ws1 is on the `scrolling` layout**, from
  `~/.local/state/omarchy/workspace-layouts/1.lua`, written **Aug 28 07:37**,
  four days earlier. Left alone — it is Andrew's setting, and it persists
  across reloads.

## Changed vs. left alone

Changed: cleared the one maximized window. Left alone: ws1's scrolling layout,
ws2's grouping, and `bindings.lua` (nothing outside the managed block had
changed). Verified afterwards: `SUPER+ALT+A` opens The Line via the fzf
re-exec path, and no window anywhere is fullscreen or maximized.

## Residual risk worth watching

v1.2.2 gave `SUPER+ALT+L` back to Andrew's own "Toggle workspace layout";
Alpharch's shade flip moved to `SUPER+ALT+I`. Muscle memory reaching for the
old shade key now flips that workspace to `scrolling` — full-width columns that
look maximized — and it persists in `workspace-layouts/`. The state-file mtimes
show this did **not** happen on the night in question, but it is the one route
by which this exact symptom could genuinely originate with us.

## Lesson

Before believing "everything is maximized", check `hyprctl -j clients` for
`fullscreen != 0`. `1` = maximized, `2` = true fullscreen, `0` with a full-size
geometry = a single tiled window or a group, which is correct behaviour. The
diagnosis that mattered here was distinguishing a healthy WM from a regression.
