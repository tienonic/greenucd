/*
 * nav.js
 * ------
 * Vanilla JavaScript replacement for jQuery + Bootstrap JS.
 * Handles three things:
 *   1. Mobile navbar toggle (hamburger menu)
 *   2. Dropdown menus (click to open, click outside to close)
 *   3. Prefetch on hover (McMaster-Carr style instant navigation)
 *
 * No dependencies. ~50 lines.
 */

document.addEventListener("DOMContentLoaded", function () {

  // ===== 1. Mobile navbar toggle =====
  // Clicking the hamburger button toggles the .in class on the
  // navbar-collapse div, which shows/hides the mobile menu.

  var toggle = document.querySelector(".navbar-toggle");
  var collapse = document.querySelector(".navbar-collapse");

  if (toggle && collapse) {
    toggle.addEventListener("click", function () {
      collapse.classList.toggle("in");
    });
  }

  // ===== 2. Dropdown menus =====
  // Clicking a dropdown-toggle adds .open to its parent .dropdown li,
  // which makes the dropdown-menu visible via CSS.

  var dropdownToggles = document.querySelectorAll(".dropdown-toggle");

  dropdownToggles.forEach(function (trigger) {
    trigger.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      var parent = trigger.closest(".dropdown");
      // Close other open dropdowns first
      document.querySelectorAll(".dropdown.open").forEach(function (d) {
        if (d !== parent) d.classList.remove("open");
      });
      parent.classList.toggle("open");
    });
  });

  // Close all dropdowns when clicking anywhere else on the page
  document.addEventListener("click", function () {
    document.querySelectorAll(".dropdown.open").forEach(function (d) {
      d.classList.remove("open");
    });
  });

  // ===== 3. Auto-close mobile menu after link click =====
  // When a user taps a link inside the mobile menu, collapse it
  // so they see the page content instead of the open menu.

  if (collapse) {
    collapse.addEventListener("click", function (e) {
      var link = e.target.closest("a");
      if (link && collapse.classList.contains("in")) {
        collapse.classList.remove("in");
      }
    });
  }

  // ===== 4. Protect scrapbook & officer images =====
  // Block right-click context menu and drag on gallery/officer photos
  // so visitors can't easily save or copy them.

  document.addEventListener("contextmenu", function (e) {
    if (e.target.closest(".green-photo, .officer-card, .green-hero")) {
      e.preventDefault();
    }
  });

  // ===== 5. Prefetch on hover (McMaster-Carr style) =====
  // When the user hovers over an internal link for 65ms+, inject a
  // <link rel="prefetch"> so the browser fetches that page in the
  // background. If they click, navigation feels instant.

  var prefetched = {};

  document.addEventListener("mouseover", function (e) {
    var link = e.target.closest("a");
    if (!link) return;

    var href = link.getAttribute("href");
    // Only prefetch local paths, skip anchors/javascript/external
    if (!href || href.charAt(0) !== "/" || prefetched[href]) return;

    // Small delay to avoid prefetching on accidental hover-throughs
    link._prefetchTimer = setTimeout(function () {
      prefetched[href] = true;
      var hint = document.createElement("link");
      hint.rel = "prefetch";
      hint.href = href;
      document.head.appendChild(hint);
    }, 65);
  });

  document.addEventListener("mouseout", function (e) {
    var link = e.target.closest("a");
    if (link && link._prefetchTimer) {
      clearTimeout(link._prefetchTimer);
    }
  });

});
