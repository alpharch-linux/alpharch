#!/usr/bin/env bash
# alpharch-common.sh — shared helpers, sourced by every trade-* command.
# The Pit palette, config paths, and small utilities.

set -uo pipefail

# ── paths ──────────────────────────────────────────────────────────────────
ALPHARCH_HOME="${ALPHARCH_HOME:-$HOME/.config/alpharch}"
ALPHARCH_STATE="${ALPHARCH_STATE:-$HOME/.local/state/alpharch}"
ALPHARCH_JOURNAL="${ALPHARCH_JOURNAL:-$HOME/Documents/trading-journal}"
ALPHARCH_CONFIG="$ALPHARCH_HOME/config.toml"
mkdir -p "$ALPHARCH_HOME" "$ALPHARCH_STATE" "$ALPHARCH_JOURNAL" 2>/dev/null || true

# ── palette ────────────────────────────────────────────────────────────────
# Follows the active Omarchy theme (~/.local/state/omarchy/current/theme),
# so `omarchy-theme-set <anything>` reskins every Alpharch tool too.
# Falls back to The Pit when no theme is active. ALPHARCH_NO_THEME=1 forces Pit.

_hex_ansi() { # "#rrggbb" -> 24-bit fg escape (empty input -> empty)
  local h="${1#\#}"
  [[ ${#h} == 6 ]] || return 1
  printf '\033[38;2;%d;%d;%dm' "0x${h:0:2}" "0x${h:2:2}" "0x${h:4:2}"
}

# The Pit defaults
PIT_AMBER=$'\033[38;2;232;163;61m'
PIT_UP=$'\033[38;2;70;179;123m'
PIT_DOWN=$'\033[38;2;220;80;87m'
PIT_TEXT=$'\033[38;2;198;207;223m'
PIT_DIM=$'\033[38;2;125;135;152m'
PIT_FAINT=$'\033[38;2;85;96;112m'
PIT_HEAD=$'\033[38;2;237;241;248m'
PIT_BOLD=$'\033[1m'
PIT_RESET=$'\033[0m'

if [[ -z "${ALPHARCH_NO_THEME:-}" ]] && command -v omarchy-theme-color >/dev/null 2>&1 \
   && [[ -f "$HOME/.local/state/omarchy/current/theme/colors.toml" ]]; then
  _t() { omarchy-theme-color "$1" "$2" 2>/dev/null; }
  _v="$(_t accent '#e8a33d')"            && PIT_AMBER="$(_hex_ansi "$_v" || printf '%s' "$PIT_AMBER")"
  _v="$(_t green '#46b37b')"             && PIT_UP="$(_hex_ansi "$_v" || printf '%s' "$PIT_UP")"
  _v="$(_t red '#dc5057')"               && PIT_DOWN="$(_hex_ansi "$_v" || printf '%s' "$PIT_DOWN")"
  _v="$(_t foreground '#c6cfdf')"        && PIT_TEXT="$(_hex_ansi "$_v" || printf '%s' "$PIT_TEXT")"
  _v="$(_t dark_foreground '#7d8798')"   && PIT_DIM="$(_hex_ansi "$_v" || printf '%s' "$PIT_DIM")"
  _v="$(_t muted '#556070')"             && PIT_FAINT="$(_hex_ansi "$_v" || printf '%s' "$PIT_FAINT")"
  _v="$(_t bright_foreground '#edf1f8')" && PIT_HEAD="$(_hex_ansi "$_v" || printf '%s' "$PIT_HEAD")"
  unset _v
fi

alpharch_logo() {
  printf '%b' "${PIT_AMBER}"
  cat <<'EOF'
        ⟋╲    ___
   ⟋╲ ⟋   ╲  (   )╲
  ⟋   ╲    ╲  ‾‾   ╲___
EOF
  printf '%b' "${PIT_RESET}"
}

say()  { printf '%b%s%b\n' "${PIT_TEXT}" "$*" "${PIT_RESET}"; }
head_() { printf '%b%s%b\n' "${PIT_HEAD}${PIT_BOLD}" "$*" "${PIT_RESET}"; }
amber(){ printf '%b%s%b\n' "${PIT_AMBER}" "$*" "${PIT_RESET}"; }
dim()  { printf '%b%s%b\n' "${PIT_DIM}"  "$*" "${PIT_RESET}"; }
err()  { printf '%b✗ %s%b\n' "${PIT_DOWN}" "$*" "${PIT_RESET}" >&2; }
ok()   { printf '%b✓ %s%b\n' "${PIT_UP}"   "$*" "${PIT_RESET}"; }

have() { command -v "$1" >/dev/null 2>&1; }

# read a key from the flat config.toml (key = "value" or key = value)
#
# The trailing comment MUST come off. Every line of the shipped config.toml has
# one, and the old version only stripped a closing quote at end-of-line: with a
# comment after it, `tick = "10"   # price grid` returned the whole tail, and
# `alphad --tick '10"   # price grid'` died on argparse. That killed
# SUPER+ALT+E, SUPER+ALT+H and every symbol typed into The Line, on a stock
# install, silently — the terminal opened and closed again. Fixed in 1.4.0.
cfg() {
  local key="$1" default="${2:-}"
  [[ -f "$ALPHARCH_CONFIG" ]] || { printf '%s' "$default"; return; }
  local v
  v="$(grep -E "^[[:space:]]*${key}[[:space:]]*=" "$ALPHARCH_CONFIG" 2>/dev/null | head -1)"
  v="${v#*=}"                        # drop the key and the =
  v="${v#"${v%%[![:space:]]*}"}"     # ltrim
  if [[ "$v" == '"'* ]]; then
    v="${v#\"}"; v="${v%%\"*}"       # quoted: take up to the CLOSING quote
  else
    v="${v%%#*}"                     # bare: drop an inline comment
    v="${v%"${v##*[![:space:]]}"}"   # rtrim
  fi
  [[ -n "$v" ]] && printf '%s' "$v" || printf '%s' "$default"
}

# is Hyprland actually running? (commands degrade gracefully if not)
in_hypr() { [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]] && have hyprctl; }

# Launched from a keybinding rather than a shell: Hyprland's exec dispatcher
# gives us no controlling terminal, so a TUI picker (fzf) has nowhere to draw
# and dies without a sound. Pickers use this to know they must open a window.
#
# Test the controlling terminal, NOT -t 0/-t 1: these helpers run inside $(...),
# where stdout is always a pipe, and a -t 1 test would report "no terminal" even
# in a real terminal — re-exec'ing forever. fzf draws on /dev/tty anyway.
no_tty() { ! : 2>/dev/null >/dev/null </dev/tty; }

# ── hyprctl dispatch, both dialects ────────────────────────────────────────
# Hyprland 0.5x with a Lua config parses `hyprctl dispatch` arguments as Lua:
# the legacy string form (`dispatch exec "[workspace 2 silent] cmd"`) is a
# syntax error there, and fails silently behind >/dev/null. Probe the running
# compositor once, then speak whichever dialect it wants.
_ALPHARCH_HYPR_LUA=""
hypr_lua_dispatch() {
  if [[ -z "$_ALPHARCH_HYPR_LUA" ]]; then
    if hyprctl dispatch 'hl.dsp.no_op()' 2>&1 | grep -qx 'ok'; then
      _ALPHARCH_HYPR_LUA=1
    else
      _ALPHARCH_HYPR_LUA=0
    fi
  fi
  [[ "$_ALPHARCH_HYPR_LUA" == 1 ]]
}

# quote a shell string for embedding in a Lua "..." literal
lua_quote() { local v="$1"; v="${v//\\/\\\\}"; v="${v//\"/\\\"}"; printf '%s' "$v"; }

# focus workspace <id>
hypr_workspace() {
  in_hypr || return 0
  if hypr_lua_dispatch; then
    hyprctl dispatch "hl.dsp.focus({ workspace = \"$(lua_quote "$1")\" })" >/dev/null 2>&1
  else
    hyprctl dispatch workspace "$1" >/dev/null 2>&1
  fi
}

# launch <cmd...> onto workspace <id> without stealing focus
hypr_exec_on_workspace() {
  in_hypr || return 0
  local ws="$1"; shift
  if hypr_lua_dispatch; then
    hyprctl dispatch \
      "hl.dsp.exec_cmd(\"$(lua_quote "$*")\", { workspace = \"$(lua_quote "$ws") silent\" })" \
      >/dev/null 2>&1
  else
    hyprctl dispatch exec "[workspace $ws silent] $*" >/dev/null 2>&1
  fi
}

# move workspace <id> onto monitor <name>
hypr_workspace_to_monitor() {
  in_hypr || return 0
  if hypr_lua_dispatch; then
    hyprctl dispatch \
      "hl.dsp.workspace.move({ workspace = \"$(lua_quote "$1")\", monitor = \"$(lua_quote "$2")\" })" \
      >/dev/null 2>&1
  else
    hyprctl dispatch moveworkspacetomonitor "$1" "$2" >/dev/null 2>&1
  fi
}

# Re-run this script inside a terminal window. Used by the pickers when fuzzel
# is absent, so fzf gets a tty instead of failing invisibly behind a keybind.
# ALPHARCH_REEXEC is a hard stop: the child can never re-exec a grandchild, so a
# misdetected terminal costs one stray window instead of a fork bomb.
reexec_in_terminal() {
  [[ -n "${ALPHARCH_REEXEC:-}" ]] && return 1
  local self="$1"; shift
  export ALPHARCH_REEXEC=1
  if have omarchy-launch-terminal; then omarchy-launch-terminal "$self" "$@"
  elif have alacritty; then setsid -f alacritty -e "$self" "$@" >/dev/null 2>&1
  elif have ghostty;   then setsid -f ghostty   -e "$self" "$@" >/dev/null 2>&1
  elif have foot;      then setsid -f foot         "$self" "$@" >/dev/null 2>&1
  elif have kitty;     then setsid -f kitty        "$self" "$@" >/dev/null 2>&1
  else return 1; fi
}

# notify through the desktop if possible, else stderr
notify() {
  local title="$1" body="${2:-}"
  if have notify-send; then notify-send -a Alpharch "$title" "$body"
  else printf '%b%s%b %s\n' "${PIT_AMBER}" "$title" "${PIT_RESET}" "$body" >&2; fi
}
