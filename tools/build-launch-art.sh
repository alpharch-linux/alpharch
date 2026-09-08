#!/usr/bin/env bash
set -euo pipefail
# Optional development step. Installed Alpharch serves the checked-in bundle;
# startup does not contact npm or a CDN.
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="$(mktemp -d -t alpharch-launch-build.XXXXXX)"
trap 'rm -rf -- "$build_dir"' EXIT
npm install --prefix "$build_dir" --no-audit --no-fund --ignore-scripts --save-exact three@0.185.1 esbuild@0.25.12
NODE_PATH="$build_dir/node_modules" "$build_dir/node_modules/.bin/esbuild" \
  "$project_dir/share/launch-scene.source.js" --bundle --minify --format=esm --target=es2020 \
  --legal-comments=eof --outfile="$project_dir/share/launch-scene.js"
cp "$build_dir/node_modules/three/LICENSE" "$project_dir/share/THREE-LICENSE.txt"
