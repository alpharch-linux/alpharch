# Alpharch visual refresh — working preview

The owner's direction is a personal trading desk on Omarchy: expressive and
precise, with the feeling of the multimonitor workspace they actually trade in.
The existing Hyprland window model remains central. This pass changes its chart
surface and the shared starting-desk chooser, not compositor configuration.

The entrance borrows copper, deep teal and the machined mark from the approved
After Hours wallpaper. A locally bundled Three.js scene adds gentle depth and
pointer response. Layout selection remains usable immediately, including when
WebGL or the art module is unavailable. Motion is optional, respects reduced
motion and the existing interface-motion preference, and releases its scene on
close, native launch or a hidden tab. No background animation runs in the desk.

The chart surface uses clearer price-axis contrast, crisp lime/magenta candles,
more legible lower study panes and a restrained drawing rail. Intervals lead the
toolbar. Zoom, fit, automatic scale and latest-bar controls remain available in
narrow tiles; chart settings and per-chart history share a compact menu. The
full indicator library is still available on each chart. Tick snapping,
aggregation, data sources and saved drawings are unchanged.

The original vector mark is retained as the static fallback. The scene uses
Three.js 0.185.1 (MIT; license in `share/THREE-LICENSE.txt`). Rebuild its bundled
asset with `tools/build-launch-art.sh`; npm is only needed for that development
step. Installed startup has no external art, font, CDN or npm requests.

Validation: existing live-desk, chart-controls, starting-desk and trade-panel
checks; dedicated opening-art lifecycle checks; live local browser review of
timeframes, zoom, indicators, history and responsive layout. This is a visual
review build, not a claim of new broker execution or data coverage.
