#!/usr/bin/env bash
# Alpharch installer — an overlay, not a fork.
# Everything this script does is reversible with ./uninstall.sh.
#
#   ./install.sh                 full install
#   ./install.sh --no-branding   keep Omarchy's fastfetch logo & screensaver
#   ./install.sh --no-theme      skip The Pit theme
#
# What it touches (and nothing else):
#   ~/.local/share/alpharch          the repo (copied here if run elsewhere)
#   ~/.local/bin/                    symlinks to alpharch, trade-*
#   ~/.config/hypr/bindings.lua      one marked block, appended
#   ~/.config/omarchy/themes/pit     The Pit theme
#   ~/.config/omarchy/branding/      about.txt + screensaver.txt (originals backed up)
#   ~/.config/alpharch/              your config (created, never overwritten)

set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.local/share/alpharch"
BINDIR="$HOME/.local/bin"
HYPR_BINDINGS="$HOME/.config/hypr/bindings.lua"
MARK_BEGIN="-- ALPHARCH BEGIN (managed block — do not edit inside; edit ~/.local/share/alpharch)"
MARK_END="-- ALPHARCH END"

NO_BRANDING=0; NO_THEME=0
for a in "$@"; do
  case "$a" in
    --no-branding) NO_BRANDING=1 ;;
    --no-theme)    NO_THEME=1 ;;
    *) echo "unknown flag: $a"; exit 1 ;;
  esac
done

AMBER=$'\033[38;2;232;163;61m'; UP=$'\033[38;2;70;179;123m'
DIM=$'\033[38;2;125;135;152m'; R=$'\033[0m'
say()  { printf '%s\n' "$*"; }
step() { printf '%b▸ %s%b\n' "$AMBER" "$*" "$R"; }
done_() { printf '%b✓ %s%b\n' "$UP" "$*" "$R"; }

printf '%b' "$AMBER"
cat "$SRC/branding/about.txt" 2>/dev/null || echo "alpharch"
printf '%b\n' "$R"
say "Alpharch — the trading layer for Omarchy. Overlay install; uninstall.sh reverses it."
echo

# ── 0. sanity ──────────────────────────────────────────────────────────────
if ! command -v hyprctl >/dev/null 2>&1 && [[ ! -d "$HOME/.config/omarchy" ]]; then
  printf '%bThis looks like neither Omarchy nor Hyprland. Continuing anyway —%b\n' "$DIM" "$R"
  printf '%bthe trade-* commands work in any terminal; desk/bindings need Hyprland.%b\n' "$DIM" "$R"
fi

# ── 1. put the repo in its place ───────────────────────────────────────────
step "installing to $DEST"
if [[ "$SRC" != "$DEST" ]]; then
  mkdir -p "$DEST"
  cp -r "$SRC/bin" "$SRC/lib" "$SRC/branding" "$SRC/config" "$SRC/themes" "$SRC/share" "$DEST/"
  cp "$SRC/install.sh" "$SRC/uninstall.sh" "$DEST/" 2>/dev/null || true
  cp "$SRC/README.md" "$DEST/" 2>/dev/null || true
fi
chmod +x "$DEST"/bin/*

# ── 2. commands on PATH ────────────────────────────────────────────────────
step "linking commands into $BINDIR"
mkdir -p "$BINDIR"
for f in "$DEST"/bin/*; do
  [[ -f "$f" ]] || continue
  ln -sf "$f" "$BINDIR/$(basename "$f")"
done
case ":$PATH:" in
  *":$BINDIR:"*) ;;
  *) printf '%bnote: %s is not on PATH — Omarchy adds it by default; add it to your shell rc if needed.%b\n' "$DIM" "$BINDIR" "$R" ;;
esac
done_ "$(ls "$DEST"/bin | tr '\n' ' ')"

# ── 3. keybindings (marked block, idempotent) ──────────────────────────────
step "wiring SUPER+ALT bindings into $HYPR_BINDINGS"
mkdir -p "$(dirname "$HYPR_BINDINGS")"
touch "$HYPR_BINDINGS"
# Strip any previous alpharch block, then append fresh. The trailing-blank pass
# matters: the separator line below sits OUTSIDE the markers, so without it every
# re-install leaks one more blank line into the user's bindings.lua.
awk -v b="$MARK_BEGIN" -v e="$MARK_END" '
  $0 == b {skip=1; next}
  $0 == e {skip=0; next}
  !skip {print}
' "$HYPR_BINDINGS" | awk '
  {l[NR] = $0}
  END {for (i = 1; i <= NR; i++) if (l[i] ~ /[^[:space:]]/) last = i
       for (i = 1; i <= last; i++) print l[i]}
' > "$HYPR_BINDINGS.tmp" && mv "$HYPR_BINDINGS.tmp" "$HYPR_BINDINGS"
{
  echo ""
  echo "$MARK_BEGIN"
  cat "$DEST/config/hypr/bindings-alpharch.lua"
  echo "$MARK_END"
} >> "$HYPR_BINDINGS"
done_ "bindings installed (SUPER+ALT+A/T/O/M/B/J/N/D)"

# ── 4. The Pit theme ───────────────────────────────────────────────────────
if [[ "$NO_THEME" == 0 ]]; then
  step "installing The Pit (dark) and The Pit, white (light)"
  THEMES_DIR="$HOME/.config/omarchy/themes"
  mkdir -p "$THEMES_DIR"
  for th in pit pit-light; do
    rm -rf "${THEMES_DIR:?}/$th"
    cp -r "$DEST/themes/$th" "$THEMES_DIR/$th"
  done
  done_ "themes at $THEMES_DIR/{pit,pit-light} — flip anytime with SUPER+ALT+I"
  if command -v omarchy-theme-set >/dev/null 2>&1; then
    printf '%bapply now:  omarchy-theme-set pit   (or pit-light)%b\n' "$DIM" "$R"
  fi
fi

# ── 5. branding (backed up, restorable) ────────────────────────────────────
if [[ "$NO_BRANDING" == 0 ]]; then
  step "branding fastfetch + screensaver (originals backed up)"
  BRAND="$HOME/.config/omarchy/branding"
  mkdir -p "$BRAND"
  for f in about.txt screensaver.txt; do
    if [[ -f "$BRAND/$f" && ! -f "$BRAND/$f.pre-alpharch" ]]; then
      cp "$BRAND/$f" "$BRAND/$f.pre-alpharch"
    fi
    cp "$DEST/branding/$f" "$BRAND/$f"
  done
  done_ "fastfetch shows the mark; screensaver runs the banner"
fi

# ── 6. seed config (never overwrites) ──────────────────────────────────────
step "seeding ~/.config/alpharch"
CFG="$HOME/.config/alpharch"
mkdir -p "$CFG" "$HOME/Documents/trading-journal"
if [[ ! -f "$CFG/config.toml" ]]; then
  cat > "$CFG/config.toml" <<'EOF'
# alpharch config — flat keys, plain text, yours.
exchange = "coinbase"          # coinbase | binance (binance is geo-blocked from US IPs)
default_symbol = "BTC-USD"     # BTC-USD, ETH-USD… or BTCUSDT on binance
tick = "10"                    # price grid ($) — also +/- live inside alphad
bucket = "60"                  # footprint time bucket (seconds)
watchlist = "BTC-USD ETH-USD SOL-USD"
waybar_symbol = "BTC-USD"      # ticker shown by the optional waybar module
EOF
fi
if [[ ! -f "$CFG/calendar.txt" ]]; then
  cat > "$CFG/calendar.txt" <<EOF
# one event per line: '<Day|YYYY-MM-DD|*> HH:MM  what'
# lines starting with * show every day
* 08:30  check the calendar — CPI/FOMC days change everything
EOF
fi
done_ "config.toml + calendar.txt (edit freely — installer never overwrites them)"

# ── 7. reload ──────────────────────────────────────────────────────────────
if command -v hyprctl >/dev/null 2>&1; then
  # A reload here is what makes the block live. If we were launched from a shell
  # without HYPRLAND_INSTANCE_SIGNATURE (tty, ssh, an editor's task runner), find
  # the running instance ourselves instead of silently skipping the reload.
  if [[ -z "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
    _hypr_run="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/hypr"
    if [[ -d "$_hypr_run" ]]; then
      for _sig in $(ls -t "$_hypr_run" 2>/dev/null); do
        [[ -S "$_hypr_run/$_sig/.socket.sock" ]] || continue
        export HYPRLAND_INSTANCE_SIGNATURE="$_sig"
        break
      done
    fi
  fi
  if [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]] && [[ "$(hyprctl reload 2>&1)" == "ok" ]]; then
    done_ "Hyprland reloaded — bindings are live"
  else
    printf '%bcould not reach a running Hyprland — run  hyprctl reload  to activate the bindings.%b\n' "$DIM" "$R"
  fi
fi

echo
printf '%b' "$AMBER"
echo "  ────────────────────────────────────────────"
printf '%b\n' "$R"
say "Done. Start here:"
say "  alpharch            the command map"
say "  alpharch doctor     check every dependency and feed"
say "  SUPER+ALT+A         The Line — type 'btc heat' and go"
say "  SUPER+ALT+T         the desk, across all your monitors"
if [[ "$NO_THEME" == 0 ]]; then
  say "  omarchy-theme-set pit    put on The Pit (SUPER+ALT+I flips light/dark)"
fi
say "  alpharch-waybar setup    optional bar ticker"
say ""
say "  If a command says 'not found', open a new terminal."
echo
printf '%btools, never signals · est. 2026 · alpharch.org%b\n' "$DIM" "$R"
