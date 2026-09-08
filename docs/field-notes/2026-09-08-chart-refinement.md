# Chart presentation review

Local review only; no installed application replacement or public deployment.

The chart frame now emphasizes the instrument, interval, price scale and studies. Native utility bars are smaller. Chart tools and drawing rails use each chart's own colors while Omarchy styling stays on window headers. A compact source/status strip opens the existing per-chart history dialog; disconnected, replay, partial-history and capture-gap states remain explicit.

Candle bodies have more width and a quieter edge treatment. Price markers have a small pointer onto their actual scale position. Grid divisions still use integer native ticks. Study panes take less space in short windows, and volume labels use compact significant digits while inspection retains full quantities. No price precision or candle aggregation is changed.

Tape and classic DOM no longer show irrelevant timeframe or drawing controls. Their chart menu remains accessible in the title bar; DOM Fit still recenters the ladder. Switching back to a chart restores its full controls. Tape timestamps and quantities are neutral, with trade side on the price and marker. Prices use the instrument's exact display precision.

Browser validation covered source/history access, chart-to-tape-to-chart control restoration, tape appearance settings and light theme, DOM Fit and menu interaction. Fixed a Classic title-bar drag handler intercepting the newly placed menu. Existing chart, interval/drawing and theme-isolation tests pass, with no browser console errors during these checks.

Actual live Coinbase preview captured in three native windows on workspace 7. Original active workspace restored afterwards. Image: `Alpharch-Chart-Refinement-2026-09-08.png` in the conversation outputs directory.
