-- Alpharch — the trading layer.
-- SUPER + ALT is the desk: every trading command lives on it.
-- This file is appended to ~/.config/hypr/bindings.lua by install.sh
-- (between the ALPHARCH BEGIN/END markers, so uninstall is clean).
--
-- See everything:  omarchy menu keybindings --print | grep -i trade

-- The Line: type where you want to go. btc heat · opt map · jrnl · clock…
o.bind("SUPER + ALT + A", "The Line (command bar)", "trade-line")

-- The desk itself: six rooms across your monitors, one keystroke.
o.bind("SUPER + ALT + T", "Trading desk", "trade-desk open")

-- Order flow on the current symbol. Views switch live inside: f/d/h/t/p/l.
o.bind("SUPER + ALT + O", "Order flow", "omarchy-launch-terminal alphad --view flow")
o.bind("SUPER + ALT + E", "Depth ladder (DOM)", "omarchy-launch-terminal trade-flow '' dom")
o.bind("SUPER + ALT + H", "Liquidity heatmap", "omarchy-launch-terminal trade-flow '' heat")

-- The flow canvas: the two worlds — candles into the liquidity fog. Real pixels.
o.bind("SUPER + ALT + V", "Flow canvas", "alphad --canvas")

-- The Desk Brain: your own record, read back to you. Q for Question.
-- Q was the only clean letter left under SUPER+ALT on a stock Omarchy desk
-- (U and Y were the others); verified against `hyprctl binds`, and SUPER+Q
-- alone is unbound, so there is no close-window fumble next to it.
o.bind("SUPER + ALT + Q", "Desk Brain (debrief)", "omarchy-launch-terminal trade-brain debrief")

-- Options flow (deribit, free public data).
o.bind("SUPER + ALT + P", "Options flow", "omarchy-launch-terminal alphaopt")

-- Market switcher: fuzzy-pick a coin, contract, or options book.
o.bind("SUPER + ALT + M", "Markets", "trade-symbol")

-- The clocks and the sheet.
o.bind("SUPER + ALT + W", "Session clock", "omarchy-launch-terminal trade-clock --watch")
o.bind("SUPER + ALT + B", "Morning brief", "omarchy-launch-terminal bash -c 'trade-brief; read -n1 -s'")

-- Journal: today's entry, and instant chart capture into it.
o.bind("SUPER + ALT + J", "Journal (today)", "omarchy-launch-terminal trade-journal today")
o.bind("SUPER + ALT + N", "Journal capture", "trade-journal capture")

-- Focus: the anti-tilt switch. Mutes notifications while you read the tape.
o.bind("SUPER + ALT + D", "Focus (do not disturb)", "trade-focus")

-- The shade: flip the whole OS between The Pit and the white prospectus.
o.bind("SUPER + ALT + I", "Light/dark flip", "trade-shade")
