# Twitter Following Only

Tiny unpacked Chrome extension that hides the **For you** home timeline tab on X/Twitter, switches the home timeline to **Following** when **For you** is active, and keeps the **Following** sort menu on **Recent**.

## Install

1. Open `chrome://extensions`.
2. Enable **Developer mode**.
3. Click **Load unpacked**.
4. Select this folder: `chrome-extensions/twitter-following-only/`.

The extension is always on while installed and enabled. Disable it from Chrome's extensions page when you want the default X/Twitter home timeline back.

## Behavior

- Runs only on `https://x.com/*` and `https://twitter.com/*`.
- Watches the client-rendered page for the home timeline tab bar.
- Hides only the tab-like **For you** control when it appears next to **Following**.
- If **For you** is selected, activates **Following**.
- When the **Following** sort menu is open, hides **Popular** and activates **Recent**.
- Does not add a toolbar button, popup, options page, or extension icon.

## Verify

```bash
node --check chrome-extensions/twitter-following-only/content.js
node -e "JSON.parse(require('fs').readFileSync('chrome-extensions/twitter-following-only/manifest.json', 'utf8')); console.log('manifest ok')"
```

Manual check:

1. Load the extension unpacked in Chrome.
2. Open `https://x.com/home` or `https://twitter.com/home`.
3. Confirm the **For you** tab disappears.
4. Confirm the home timeline is on **Following**.
5. Open the **Following** sort menu.
6. Confirm **Popular** is hidden and **Recent** is selected.

For local markup experiments, open `test-fixtures/home-tabs.html` in a browser and paste the content script into DevTools.
