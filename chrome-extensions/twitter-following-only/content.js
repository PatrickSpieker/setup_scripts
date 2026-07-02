(() => {
  "use strict";

  const HIDDEN_ATTR = "data-twitter-following-only-hidden";
  const HOME_PATHS = new Set(["/home"]);
  const LIVE_HOME_PARAM = "live";
  const OBSERVER_OPTIONS = { childList: true, subtree: true };
  const SCAN_THROTTLE_MS = 100;

  let scanTimer = 0;
  let lastActivatedUrl = "";
  const activatedSortMenus = new WeakSet();

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

  function isVisible(element) {
    return Boolean(element.offsetParent || element.getClientRects().length);
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
      || element.getAttribute("aria-current") === "page"
      || element.getAttribute("aria-checked") === "true";
  }

  function closestActionRow(element, boundary) {
    let current = element;

    while (current && current !== boundary) {
      const role = current.getAttribute("role");
      if (
        current.matches("button, [tabindex]")
        || role === "menuitem"
        || role === "option"
        || role === "button"
      ) {
        return current;
      }

      current = current.parentElement;
    }

    return element.parentElement || element;
  }

  function sharedAncestor(first, second) {
    const firstAncestors = new Set();
    let current = first;

    while (current && current !== document.body) {
      firstAncestors.add(current);
      current = current.parentElement;
    }

    current = second;
    while (current && current !== document.body) {
      if (firstAncestors.has(current)) {
        return current;
      }
      current = current.parentElement;
    }

    return null;
  }

  function sortMenus() {
    const candidates = Array.from(document.querySelectorAll('button, div, span, [role="menuitem"], [role="option"]'))
      .filter((element) => isVisible(element));
    const popularItems = candidates.filter((element) => hasExactLabel(element, "Popular"));
    const recentItems = candidates.filter((element) => hasExactLabel(element, "Recent"));
    const menus = [];

    for (const popular of popularItems) {
      for (const recent of recentItems) {
        const root = sharedAncestor(popular, recent);
        if (!root || !isVisible(root)) {
          continue;
        }

        const rect = root.getBoundingClientRect();
        if (rect.width > 500 || rect.height > 500) {
          continue;
        }

        menus.push({
          root,
          popular: closestActionRow(popular, root),
          recent: closestActionRow(recent, root),
        });
      }
    }

    return menus;
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

  function hidePopularSortOption(popular) {
    popular.setAttribute(HIDDEN_ATTR, "true");
    popular.setAttribute("aria-hidden", "true");
    popular.style.setProperty("display", "none", "important");
  }

  function activateFollowing(following) {
    if (lastActivatedUrl === window.location.href) {
      return;
    }

    lastActivatedUrl = window.location.href;
    following.click();
  }

  function activateRecentSort(menu) {
    if (activatedSortMenus.has(menu.root) || isExplicitlySelected(menu.recent)) {
      return;
    }

    activatedSortMenus.add(menu.root);
    menu.recent.click();
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

    for (const menu of sortMenus()) {
      hidePopularSortOption(menu.popular);
      activateRecentSort(menu);
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
