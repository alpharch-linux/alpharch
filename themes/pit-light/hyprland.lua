-- The Pit, white — window chrome. Amber ink means "this one is live."
local active_border_color = "rgb(9a6b14)"
local active_shadow_color = "rgba(9a6b1440)"
local inactive_border_color = "rgba(c9c2b099)"
local inactive_shadow_color = "rgba(d8d2c455)"

hl.config({
  general = {
    col = {
      active_border = active_border_color,
      inactive_border = inactive_border_color,
    }
  },

  group = {
    col = {
      border_active = active_border_color,
      border_inactive = inactive_border_color,
    },
  },

  decoration = {
    shadow = {
      enabled = true,
      range = 5,
      render_power = 4,
      color = active_shadow_color,
      color_inactive = inactive_shadow_color,
    },
  },
})
