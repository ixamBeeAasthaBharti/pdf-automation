/**
 * reader.js
 * ---------------------------------------------------------
 * Standalone JS for the ixamBee PDF reader.
 *
 * Features:
 *   1. Sticky header glass effect on scroll
 *   2. Reading progress bar
 *   3. Kindle-style A+ / A- font-size controls (localStorage)
 *   4. Dynamic Table of Contents + ScrollSpy
 * ---------------------------------------------------------
 */

(function () {
  "use strict";

  /* --- 1. SCROLL : sticky header + progress bar --- */

  var header         = document.querySelector(".doc-header");
  var globalProgress = document.getElementById("read-progress");
  var tocProgress    = document.getElementById("toc-progress-bar");

  window.addEventListener("scroll", function () {
    var scrollTop = window.scrollY;
    var docHeight = document.documentElement.scrollHeight - window.innerHeight;
    var pct       = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;

    if (header)         header.classList.toggle("scrolled", scrollTop > 10);
    if (globalProgress) globalProgress.style.width = pct + "%";
    if (tocProgress)    tocProgress.style.width    = pct + "%";
  }, { passive: true });


  /* --- 2. FONT-SIZE CONTROLS --- */

  var FONT_LEVELS = [
    { label: "100%", scale: 1.0  },
    { label: "110%", scale: 1.1  },
    { label: "120%", scale: 1.2  },
    { label: "130%", scale: 1.3  },
    { label: "140%", scale: 1.4  },
    { label: "155%", scale: 1.55 },
    { label: "170%", scale: 1.7  }
  ];

  var currentFontIndex = 0;

  var savedIndex = localStorage.getItem("readerFontScale");
  if (savedIndex !== null && !isNaN(savedIndex)) {
    var parsed = parseInt(savedIndex, 10);
    if (parsed >= 0 && parsed < FONT_LEVELS.length) {
      currentFontIndex = parsed;
    }
  }

  function applyFontScale(index) {
    currentFontIndex = index;
    var level = FONT_LEVELS[index];
    document.documentElement.style.setProperty("--reader-font-scale", level.scale);
    localStorage.setItem("readerFontScale", index);

    var decBtn = document.getElementById("font-size-dec");
    var incBtn = document.getElementById("font-size-inc");
    if (decBtn) decBtn.disabled = (index === 0);
    if (incBtn) incBtn.disabled = (index === FONT_LEVELS.length - 1);
  }

  /* Apply saved / default scale immediately */
  applyFontScale(currentFontIndex);


  /* --- 3. DOM-READY : bind buttons + build TOC --- */

  document.addEventListener("DOMContentLoaded", function () {

    /* Font buttons */
    var decBtn = document.getElementById("font-size-dec");
    var incBtn = document.getElementById("font-size-inc");

    if (decBtn) {
      decBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        if (currentFontIndex > 0) applyFontScale(currentFontIndex - 1);
      });
    }

    if (incBtn) {
      incBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        if (currentFontIndex < FONT_LEVELS.length - 1) applyFontScale(currentFontIndex + 1);
      });
    }

    /* Dynamic Table of Contents + ScrollSpy */
    var tocList  = document.getElementById("toc-list");
    var sections = document.querySelectorAll(
      "article:not(.cover-article) section, main section"
    );

    if (tocList && sections.length > 0) {

      sections.forEach(function (section) {
        var heading   = section.querySelector("h2.section-title, h2, h1, h3");
        var sectionId = section.getAttribute("aria-labelledby") || section.id
                        || (heading && heading.id) || "";

        if (!heading) return;

        if (!section.id) {
          var slug = (sectionId || heading.textContent.trim())
            .toLowerCase().replace(/[^a-z0-9]+/g, "-");
          section.id = slug.replace("-heading", "-section");
        }

        var targetId = section.id;
        var li = document.createElement("li");
        var a  = document.createElement("a");
        a.href      = "#" + targetId;
        a.textContent = heading.textContent.trim();

        a.addEventListener("click", function (e) {
          e.preventDefault();
          var el = document.getElementById(targetId);
          if (el) {
            el.scrollIntoView({ behavior: "smooth" });
            history.pushState(null, null, "#" + targetId);
          }
        });

        li.appendChild(a);
        tocList.appendChild(li);
      });

      /* ScrollSpy via IntersectionObserver */
      var tocLinks = tocList.querySelectorAll("a");

      var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          var id = entry.target.id;
          tocLinks.forEach(function (link) {
            link.classList.remove("active");
            link.removeAttribute("aria-current");
            if (link.getAttribute("href") === "#" + id) {
              link.classList.add("active");
              link.setAttribute("aria-current", "true");
            }
          });
        });
      }, { root: null, rootMargin: "-15% 0px -60% 0px", threshold: 0 });

      sections.forEach(function (s) { observer.observe(s); });
    }
  });

})();
