-- Hyper key: cmd + alt + ctrl. Single chord for global Hammerspoon bindings
-- so they don't collide with app-level shortcuts.
local hyper = {"cmd", "alt", "ctrl"}

-- Hyper+R reloads this file. Useful when iterating from this repo without
-- restarting Hammerspoon.
hs.hotkey.bind(hyper, "R", function()
  hs.reload()
end)

-- Cmd+Shift+4 -> interactive selection screenshot.
-- Copies the image to the clipboard AND saves a PNG to ~/Desktop.
--
-- We use `screencapture -c -i` (clipboard + interactive) and let
-- screencapture's own pipeline put the image on the pasteboard, then
-- read it back via hs.pasteboard and save it to disk ourselves. This
-- avoids the modern-macOS gotcha where `screencapture -i <path>` is
-- delegated to the screenshotui XPC handler, which ignores the path
-- argument and writes to the system default location with native
-- naming. Reading from the clipboard sidesteps the path question
-- entirely.
--
-- changeCount() detects Escape: if the pasteboard wasn't touched
-- between hotkey press and screencapture exit, the user cancelled.
hs.hotkey.bind({"cmd", "shift"}, "4", function()
  local before_count = hs.pasteboard.changeCount()
  hs.task.new("/usr/sbin/screencapture", function()
    if hs.pasteboard.changeCount() == before_count then return end
    local img = hs.pasteboard.readImage()
    if not img then return end
    local stamp = os.date("%Y-%m-%d at %H.%M.%S")
    local path = os.getenv("HOME") .. "/Desktop/Screenshot " .. stamp .. ".png"
    img:saveToFile(path)
  end, {"-c", "-i"}):start()
end)

hs.alert.show("Hammerspoon config loaded")
