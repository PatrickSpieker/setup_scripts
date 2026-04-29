-- Hyper key: cmd + alt + ctrl. Single chord for global Hammerspoon bindings
-- so they don't collide with app-level shortcuts.
local hyper = {"cmd", "alt", "ctrl"}

-- Hyper+R reloads this file. Useful when iterating from this repo without
-- restarting Hammerspoon.
hs.hotkey.bind(hyper, "R", function()
  hs.reload()
end)

hs.alert.show("Hammerspoon config loaded")
