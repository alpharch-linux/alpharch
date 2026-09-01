-- The Pit — window chrome. Amber means "this one is live."
local active_border_color = "rgb(e8a33d)"
local active_shadow_color = "rgba(e8a33d55)"
local inactive_border_color = "rgba(2a303d99)"
local inactive_shadow_color = "rgba(04060b77)"

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
