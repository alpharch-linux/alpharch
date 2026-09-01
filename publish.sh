#!/usr/bin/env bash
# publish.sh — one-time, one-command launch. Run from the alpharch folder.
#
#   ./publish.sh
#
# Does everything: installs Alpharch on THIS machine, then puts it in the
# world — creates github.com/alpharch-linux/alpharch, pushes the code,
# publishes https://alpharch.org/install, and verifies the one-liner.
# The only human moment is a GitHub login in your own browser (your
# credentials never pass through anything else).

set -euo pipefail
AMBER=$'\033[38;2;232;163;61m'; UP=$'\033[38;2;70;179;123m'
DIM=$'\033[38;2;125;135;152m'; RED=$'\033[38;2;220;80;87m'; R=$'\033[0m'
step(){ printf '%b▸ %s%b\n' "$AMBER" "$*" "$R"; }
ok(){ printf '%b✓ %s%b\n' "$UP" "$*" "$R"; }

ORG="alpharch-linux"; REPO="alpharch"; SITE="alpharch.org"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; cd "$HERE"

command -v gh >/dev/null || { printf '%bneeds the gh CLI:  sudo pacman -S github-cli%b\n' "$RED" "$R"; exit 1; }
command -v git >/dev/null || { printf '%bneeds git:  sudo pacman -S git%b\n' "$RED" "$R"; exit 1; }

# 1. install locally first — publisher is user zero
step "installing Alpharch on this machine"
bash ./install.sh < /dev/null
command -v pacman >/dev/null && ! python3 -c 'import websockets' 2>/dev/null && \
  sudo pacman -S --needed --noconfirm python-websockets || true

# 2. GitHub auth (browser login, one time)
gh auth status >/dev/null 2>&1 || { step "GitHub login — follow the browser prompt"; gh auth login -h github.com -p https -w; }
ok "authenticated as $(gh api user -q .login)"

# 3. push the code
if [[ ! -d .git ]]; then
  git init -b main >/dev/null
  git config user.name  "$(gh api user -q .name  2>/dev/null || echo Alpharch)"
  git config user.email "$(gh api user -q '.email // empty' 2>/dev/null || echo "$(gh api user -q .login)@users.noreply.github.com")"
fi
git add -A
git commit -m "Alpharch $(bin/alpharch version 2>/dev/null | awk '{print $2}' || echo 1.2.0) — the trading layer for Omarchy" >/dev/null 2>&1 || true
if gh repo view "$ORG/$REPO" >/dev/null 2>&1; then
  step "repo exists — pushing"
  git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://github.com/$ORG/$REPO.git"
  git push -u origin main
else
  step "creating github.com/$ORG/$REPO and pushing"
  gh repo create "$ORG/$REPO" --public --source=. --remote=origin --push \
    --description "The trading layer for Omarchy. Linux is for traders."
fi
ok "code is live: https://github.com/$ORG/$REPO"

# 4. publish the install endpoint on the site repo
step "publishing https://$SITE/install"
sha="$(gh api "repos/$ORG/$SITE/contents/install" -q .sha 2>/dev/null || true)"
gh api -X PUT "repos/$ORG/$SITE/contents/install" \
  -f message="Publish the one-line installer" \
  -f content="$(base64 -w0 install)" \
  ${sha:+-f sha="$sha"} >/dev/null
ok "install endpoint committed (GitHub Pages deploys in ~a minute)"

# 5. verify
step "verifying the one-liner"
for i in $(seq 1 24); do
  if curl -fsSL "https://$SITE/install" 2>/dev/null | head -2 | grep -q bash; then
    ok "LIVE:  curl -fsSL https://$SITE/install | bash"
    echo
    printf '%bAlpharch is public. Anyone with Omarchy is one line away.%b\n' "$AMBER" "$R"
    printf '%btools, never signals · est. 2026%b\n' "$DIM" "$R"
    exit 0
  fi
  sleep 5
done
printf '%bendpoint not serving yet — Pages can take a few minutes; check https://%s/install shortly.%b\n' "$DIM" "$SITE" "$R"
