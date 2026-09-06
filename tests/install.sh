#!/usr/bin/env bash
# Disposable homes and stub desktop commands: never touches the running desktop.
set -euo pipefail
cd "$(dirname "$0")/.."
test_root=$(mktemp -d)
trap 'rm -rf "$test_root"' EXIT
mkdir -p "$test_root/stubs"
for command in hyprctl omarchy-theme-current omarchy-theme-set notify-send; do
  printf '#!/bin/sh\nexit 0\n' > "$test_root/stubs/$command"
  chmod +x "$test_root/stubs/$command"
done
for variant in full no-theme commands-only; do
  test_home="$test_root/$variant"
  mkdir -p "$test_home/.local/bin" "$test_home/.config/hypr"
  printf 'foreign command\n' > "$test_home/.local/bin/foreign-tool"
  printf '%s\n' '-- user bindings' > "$test_home/.config/hypr/bindings.lua"
  flags=(); [[ $variant != no-theme ]] || flags=(--no-theme)
  [[ $variant != commands-only ]] || flags=(--no-theme --no-branding --no-keybindings)
  for repetition in 1 2; do
    env HOME="$test_home" PATH="$test_root/stubs:$PATH" HYPRLAND_INSTANCE_SIGNATURE= XDG_RUNTIME_DIR="$test_root/runtime" bash install.sh "${flags[@]}" > "$test_root/install.log"
  done
  if [[ $variant == commands-only ]]; then
    [[ $(cat "$test_home/.config/hypr/bindings.lua") == '-- user bindings' ]]
  else
    [[ $(rg -c '^-- ALPHARCH BEGIN' "$test_home/.config/hypr/bindings.lua") == 1 ]]
  fi
  [[ -L "$test_home/.local/share/applications/alpharch.desktop" ]]
  [[ -L "$test_home/.local/bin/trade-live" ]]
  [[ -L "$test_home/.local/bin/alpha-import-futures" ]]
  printf 'journal stays\n' > "$test_home/Documents/trading-journal/test.md"
  env HOME="$test_home" PATH="$test_root/stubs:$PATH" HYPRLAND_INSTANCE_SIGNATURE= bash uninstall.sh > "$test_root/uninstall.log"
  [[ $(cat "$test_home/.local/bin/foreign-tool") == 'foreign command' ]]
  [[ $(cat "$test_home/.config/hypr/bindings.lua") == '-- user bindings' ]]
  [[ -f "$test_home/Documents/trading-journal/test.md" ]]
  [[ ! -e "$test_home/.config/omarchy/branding/about.txt" ]]
  [[ ! -e "$test_home/.local/share/alpharch" ]]
  [[ ! -L "$test_home/.local/share/applications/alpharch.desktop" ]]
  echo "$variant: repeated install and uninstall passed"
done
test_home="$test_root/conflict"
mkdir -p "$test_home/.local/bin"
printf 'user program' > "$test_home/.local/bin/alphad"
if env HOME="$test_home" PATH="$test_root/stubs:$PATH" bash install.sh > "$test_root/conflict.log" 2>&1; then
  echo 'Expected install conflict failure' >&2; exit 1
fi
[[ $(cat "$test_home/.local/bin/alphad") == 'user program' ]]
[[ ! -e "$test_home/.local/share/alpharch" ]]
echo 'Command collision preserves user file and stops before installation'
