(() => {
  "use strict";

  const HIDDEN_ATTR = "data-twitter-following-only-hidden";
  const HOME_PATHS = new Set(["/home"]);
  const LIVE_HOME_PARAM = "live";
  const OBSERVER_OPTIONS = { childList: true, subtree: true };
  const SCAN_THROTTLE_MS = 100;

  let scanTimer = 0;
  let lastActivatedUrl = "";

  function normalizedText(element) {
    return [
      element.getAttribute("aria-label"),
      element.textContent,
    ]
      .filter(Boolean)
      .join(" ")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
  }

  function hasExactLabel(element, label) {
    return normalizedText(element) === label.toLowerCase();
  }

  function isHomeTimeline() {
    return HOME_PATHS.has(window.location.pathname);
  }

  function isFollowingUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get("f") === LIVE_HOME_PARAM;
  }

  function timelineControls(root) {
    return Array.from(root.querySelectorAll('a, button, [role="tab"]'))
      .filter((element) => hasExactLabel(element, "For you") || hasExactLabel(element, "Following"));
  }

  function timelineTabLists() {
    return Array.from(document.querySelectorAll('[role="tablist"], nav, header'))
      .map((root) => {
        const controls = timelineControls(root);
        return {
          root,
          forYou: controls.find((element) => hasExactLabel(element, "For you")),
          following: controls.find((element) => hasExactLabel(element, "Following")),
        };
      })
      .filter((tabs) => tabs.forYou && tabs.following);
  }

  function isExplicitlySelected(element) {
    return element.getAttribute("aria-selected") === "true"
      || element.getAttribute("aria-current") === "page";
  }

  function shouldActivateFollowing(forYou, following) {
    if (isFollowingUrl() || isExplicitlySelected(following)) {
      return false;
    }

    if (isExplicitlySelected(forYou)) {
      return true;
    }

    return !isExplicitlySelected(following)
      && !isFollowingUrl()
      && lastActivatedUrl !== window.location.href;
  }

  function hideForYouTab(forYou) {
    forYou.setAttribute(HIDDEN_ATTR, "true");
    forYou.setAttribute("aria-hidden", "true");
    forYou.style.setProperty("display", "none", "important");
  }

  function activateFollowing(following) {
    if (lastActivatedUrl === window.location.href) {
      return;
    }

    lastActivatedUrl = window.location.href;
    following.click();
  }

  function scan() {
    scanTimer = 0;

    if (!isHomeTimeline()) {
      return;
    }

    for (const tabs of timelineTabLists()) {
      hideForYouTab(tabs.forYou);

      if (shouldActivateFollowing(tabs.forYou, tabs.following)) {
        activateFollowing(tabs.following);
      }
    }
  }

  function scheduleScan() {
    if (scanTimer) {
      return;
    }

    scanTimer = window.setTimeout(scan, SCAN_THROTTLE_MS);
  }

  scan();

  const observer = new MutationObserver(scheduleScan);
  observer.observe(document.documentElement, OBSERVER_OPTIONS);

  let lastUrl = window.location.href;
  window.setInterval(() => {
    if (window.location.href !== lastUrl) {
      lastUrl = window.location.href;
      scheduleScan();
    }
  }, 500);
})();
