# Independent chart themes

Implemented in the local review worktree; the installed application is unchanged.

- Each chart offers dark, light and custom colors through its chart menu. The top appearance control opens the same editor. Colors include price scales, labels, grids, candles, crosshair and three heatmap intensity colors.
- Chart colors persist in layout documents, including native Hyprland chart files. Named presets save resolved colors so later palette changes cannot silently alter a saved theme. Presets can be exported/imported as bounded, validated JSON.
- Window bars default to following Omarchy, with Alpharch and custom alternatives. The server reads only allowlisted color metadata from the current Omarchy state directory (legacy configuration directory fallback). It reads at most once every two seconds while subscribed clients request it. No hooks, desktop configuration edits or theme scripts are involved.
- Omarchy theme messages change window styling only. They do not reset chart state, colors, drawings, indicators or market subscriptions. Switching window styling off unsubscribes from theme updates.
- Existing indicator and drawing colors remain editable through their own tools. Low-contrast study labels use the chart text color without changing the saved study color.

Validation: theme tests cover fixed saved colors, import validation, readable defaults and desktop/chart isolation. Python metadata tests cover both paths, reload/cache behavior, invalid/oversized input and removal. Existing chart calculation, interval/drawing, DOM/ticket and native window tests pass. Browser checks confirmed independent light/dark charts, saved presets after reload, following the current aurentum palette, and switching back to Alpharch bars. No browser console errors were observed.

Actual native Hyprland captures were taken on the laptop display with live public Coinbase BTC/USD data. A two-chart review desk remains on workspace 7; the original active workspace was restored after capture. The screenshots show a review build, not a deployed application update or a newly available execution integration.
