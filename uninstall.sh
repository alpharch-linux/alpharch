#!/usr/bin/env bash
# Alpharch uninstaller — removes everything install.sh added.
# Your journal and your config are yours; they stay.

set -euo pipefail

DEST="$HOME/.local/share/alpharch"
BINDIR="$HOME/.local/bin"
HYPR_BINDINGS="$HOME/.config/hypr/bindings.lua"
MARK_BEGIN="-- ALPHARCH BEGIN (managed block — do not edit inside; edit ~/.local/share/alpharch)"
MARK_END="-- ALPHARCH END"

UP=$'\033[38;2;70;179;123m'; DIM=$'\033[38;2;125;135;152m'; R=$'\033[0m'
done_() { printf '%b✓ %s%b\n' "$UP" "$*" "$R"; }

# 1. bindings block out
if [[ -f "$HYPR_BINDINGS" ]]; then
  # Second pass drops the blank separator install.sh appends ahead of the
  # markers, so the file comes back exactly as Alpharch found it.
  awk -v b="$MARK_BEGIN" -v e="$MARK_END" '
    $0 == b {skip=1; next}
    $0 == e {skip=0; next}
    !skip {print}
  ' "$HYPR_BINDINGS" | awk '
    {l[NR] = $0}
    END {for (i = 1; i <= NR; i++) if (l[i] ~ /[^[:space:]]/) last = i
         for (i = 1; i <= last; i++) print l[i]}
  ' > "$HYPR_BINDINGS.tmp" && mv "$HYPR_BINDINGS.tmp" "$HYPR_BINDINGS"
  done_ "bindings removed"
fi

# 2. symlinks out (anything that points into our repo)
for f in "$BINDIR"/*; do
  if [[ -L "$f" && "$(readlink -f "$f" 2>/dev/null)" == "$DEST"/* ]]; then
    rm -f "$f"
  fi
done
done_ "commands unlinked"

# 3. branding restored
BRAND="$HOME/.config/omarchy/branding"
for f in about.txt screensaver.txt; do
  if [[ -f "$BRAND/$f.pre-alpharch" ]]; then
    mv "$BRAND/$f.pre-alpharch" "$BRAND/$f"
  fi
done
done_ "branding restored"

# 4. themes out (switch away first if one is active)
cur=""
if command -v omarchy-theme-current >/dev/null 2>&1; then
  cur="$(omarchy-theme-current 2>/dev/null || true)"
fi
if [[ "$cur" == "pit" || "$cur" == "pit-light" ]] && command -v omarchy-theme-set >/dev/null 2>&1; then
  omarchy-theme-set tokyo-night >/dev/null 2>&1 || true
fi
rm -rf "$HOME/.config/omarchy/themes/pit" "$HOME/.config/omarchy/themes/pit-light"
done_ "The Pit (both shades) removed"

# 5. repo out
rm -rf "$DEST"
done_ "repo removed"

if [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]] && command -v hyprctl >/dev/null 2>&1; then
  hyprctl reload >/dev/null 2>&1 || true
fi

echo
printf '%bkept (your data): ~/Documents/trading-journal and ~/.config/alpharch%b\n' "$DIM" "$R"
printf '%bremove them yourself if you want a clean slate. so long, and trade well.%b\n' "$DIM" "$R"
