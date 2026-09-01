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
cfg() {
  local key="$1" default="${2:-}"
  [[ -f "$ALPHARCH_CONFIG" ]] || { printf '%s' "$default"; return; }
  local v
  v="$(grep -E "^[[:space:]]*${key}[[:space:]]*=" "$ALPHARCH_CONFIG" 2>/dev/null \
        | head -1 | sed -E 's/^[^=]*=[[:space:]]*//; s/^"//; s/"[[:space:]]*$//; s/[[:space:]]*$//')"
  [[ -n "$v" ]] && printf '%s' "$v" || printf '%s' "$default"
}

# is Hyprland actually running? (commands degrade gracefully if not)
in_hypr() { [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]] && have hyprctl; }

# notify through the desktop if possible, else stderr
notify() {
  local title="$1" body="${2:-}"
  if have notify-send; then notify-send -a Alpharch "$title" "$body"
  else printf '%b%s%b %s\n' "${PIT_AMBER}" "$title" "${PIT_RESET}" "$body" >&2; fi
}
