# Two ways to open Alpharch

Choose **Classic desk** or **Hyprland desk** on the starting-template screen.
The main desk shows this screen on every launch, even with a saved layout.
**Continue current desk** returns to the saved Classic desk. Individual
Hyprland chart windows open directly without another chooser.
If the local service starts before the desktop session, it discovers Omarchy's
current session when needed. The chooser retries while the desktop is starting;
it does not require a service restart or changes to your Hyprland configuration.
Reopen that screen from **Desk → Choose a starting desk…**. The Classic desk,
its saved layouts, and the existing `Super+Alt+V` launcher remain available.

Classic keeps its charts together inside one browser/app window. Hyprland opens
each chart as a separate Wayland browser app window, with the same chart engine,
drawings, exact instrument increments, custom intervals, indicators and draft
trading panel. It uses Omarchy's installed app-browser launcher; this is not a
second implementation of the chart renderer.

Choosing a Hyprland template creates its windows on an unused numbered workspace
(9 when available), reachable with Omarchy's normal workspace shortcuts.
**New chart** or **Ctrl+N** opens the chart picker. From an existing chart, Add
opens another real window on that chart's workspace. An empty window receives
its first chart directly. Futures contracts are selected through **Connect**;
selecting an IBKR contract changes that window's chart. Gateway connections
remain window-local and read-only; this edition does not add broker execution.

Use the desktop's own focus, resize, grouping, fullscreen and monitor shortcuts.
No new global shortcuts or window rules are installed. Omarchy normally uses
Super+arrows to focus, Super+Shift+arrows to swap, and Super+right-drag to resize.
Personal keybindings take precedence. The in-window **Keys** button explains
the distinction between desktop controls and chart controls.

**Desk → Save Hyprland desk…** or **Ctrl+Shift+S** saves all open native charts.
Named desks appear in that menu for reopening. Charts, drawings, studies,
appearance, intervals and history settings are saved with workspace/monitor
assignments. Keep a desk's windows in the same app browser and local service so
the save operation can confirm every chart's latest changes. An unresponsive
window is reported rather than silently claiming to save it.

Hyprland decides the tile proportions when windows reopen; exact split ratios,
groups and floating geometry are not serialized. Missing monitors fall back to
an attached monitor. Restoring preserves already-open charts, including edits
made since the snapshot. Up to twelve native windows can be open at once.

Native documents are stored separately in `~/.config/alpharch/hyprland/`.
Classic browser layouts are untouched. Local chart exports contain settings,
not credentials. Uninstall leaves saved chart documents in place.

Replay stays local to its window. When a recording contains several streams,
the replay bar lets that window choose its visible stream. Replay clocks are
not synchronized between native windows. Multi-chart replay on one shared
clock remains available in Classic desk.

There is also an **Alpharch Hyprland Desk** application-menu entry. From a
terminal, `trade-hyprland` returns to an open native desk or opens an empty one;
`trade-hyprland save NAME` and `trade-hyprland load NAME` save and restore native
desks. The normal `trade-workspace` launcher still opens Classic.
