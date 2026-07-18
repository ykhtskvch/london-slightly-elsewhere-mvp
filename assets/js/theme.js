(() => {
  const root = document.documentElement;
  root.classList.add("js");
  const storedTheme = localStorage.getItem("lse-theme");
  if (storedTheme === "light" || storedTheme === "dark") root.dataset.theme = storedTheme;

  document.addEventListener("DOMContentLoaded", () => {
    initialiseHeader();

    document.querySelectorAll("[data-theme-toggle]").forEach(button => {
      const currentTheme = () => root.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      const updateLabel = () => {
        const isDark = currentTheme() === "dark";
        button.setAttribute("aria-label", `Switch to ${isDark ? "light" : "dark"} mode`);
        button.setAttribute("aria-checked", String(isDark));
      };
      updateLabel();
      button.addEventListener("click", () => {
        const next = currentTheme() === "dark" ? "light" : "dark";
        root.dataset.theme = next;
        localStorage.setItem("lse-theme", next);
        updateLabel();
      });
    });
  });

  function initialiseHeader() {
    const header = document.querySelector(".site-header");
    const actions = header?.querySelector(".header-actions");
    const nav = header?.querySelector(".site-nav");
    if (!header || !actions || !nav) return;

    if (!nav.id) nav.id = "site-navigation";
    const basePath = document.body.dataset.basePath || "./";
    const themeToggle = header.querySelector("[data-theme-toggle]");
    if (!nav.querySelector("[data-nav-contact]")) {
      const contact = document.createElement("a");
      contact.href = `${basePath}contact/`;
      contact.dataset.navContact = "true";
      contact.textContent = "Contact";
      if (window.location.pathname.endsWith("/contact/") || window.location.pathname.endsWith("/contact/index.html")) {
        contact.setAttribute("aria-current", "page");
      }
      nav.appendChild(contact);
    }
    if (themeToggle && !nav.querySelector(".theme-control")) {
      const themeControl = document.createElement("div");
      themeControl.className = "theme-control";
      themeControl.innerHTML = "<span class=\"theme-control-label\">Theme</span>";
      themeToggle.setAttribute("role", "switch");
      themeToggle.innerHTML = "<span class=\"theme-option\">Light</span><span class=\"theme-switch-track\" aria-hidden=\"true\"><span></span></span><span class=\"theme-option\">Dark</span>";
      themeControl.appendChild(themeToggle);
      nav.appendChild(themeControl);
    }

    const toggle = document.createElement("button");
    toggle.className = "nav-toggle";
    toggle.type = "button";
    toggle.setAttribute("aria-controls", nav.id);
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-label", "Open navigation");
    toggle.innerHTML = "<span></span><span></span><span></span>";
    actions.appendChild(toggle);

    const setOpen = open => {
      header.classList.toggle("nav-open", open);
      toggle.setAttribute("aria-expanded", String(open));
      toggle.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
      if (open) header.classList.remove("is-hidden");
    };

    toggle.addEventListener("click", () => setOpen(!header.classList.contains("nav-open")));
    nav.addEventListener("click", event => {
      if (event.target.closest("a")) setOpen(false);
    });
    document.addEventListener("click", event => {
      if (!header.contains(event.target)) setOpen(false);
    });
    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && header.classList.contains("nav-open")) {
        setOpen(false);
        toggle.focus();
      }
    });

    const desktop = matchMedia("(min-width: 48rem)");
    const handleDesktopChange = event => {
      if (event.matches) setOpen(false);
    };
    if (desktop.addEventListener) desktop.addEventListener("change", handleDesktopChange);
    else desktop.addListener(handleDesktopChange);

    let lastScrollY = window.scrollY;
    let scheduled = false;
    const updateHeader = () => {
      const currentScrollY = Math.max(window.scrollY, 0);
      const delta = currentScrollY - lastScrollY;
      const menuOpen = header.classList.contains("nav-open");

      if (currentScrollY < 64 || menuOpen || delta < -6) {
        header.classList.remove("is-hidden");
      } else if (delta > 6 && currentScrollY > header.offsetHeight) {
        header.classList.add("is-hidden");
      }

      lastScrollY = currentScrollY;
      scheduled = false;
    };

    window.addEventListener("scroll", () => {
      if (!scheduled) {
        scheduled = true;
        requestAnimationFrame(updateHeader);
      }
    }, { passive: true });
    header.addEventListener("focusin", () => header.classList.remove("is-hidden"));
  }
})();
